import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()

import channel_connections
import channel_layer
import contact_identity
import managed_migrations
import permission_engine
import persistence_backend
import production_schema_adoption
import universal_work_objects


class ChannelLayerV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "channels.sqlite")
        self.restore_database = bind_sqlite_database(
            self.db_file, channel_connections, contact_identity
        )
        managed_migrations.run_migrations()
        self.web = channel_layer.ensure_web_connection(
            "workspace_a", actor="owner"
        )

    def tearDown(self):
        self.restore_database()
        self.temp_dir.cleanup()

    def ingest(self, **values):
        payload = {
            "external_message_id": "provider-message-1",
            "thread_reference": "thread-1",
            "external_sender_id": "sender-1",
            "message_type": "TEXT",
            "text_content": "Please prepare the plan.",
            "safe_metadata": {"provider": "web"},
            "received_at": "2026-07-30T08:00:00+00:00",
        }
        payload.update(values)
        return channel_layer.ingest_inbound(
            "workspace_a", self.web.channel_connection_id, **payload
        )

    def test_registry_unknown_type_and_adapter_contract(self):
        self.assertEqual(
            channel_layer.CHANNEL_TYPES,
            {"WEB", "TELEGRAM", "WHATSAPP", "EMAIL"},
        )
        self.assertEqual(set(channel_layer.ADAPTERS), set(channel_layer.CHANNEL_TYPES))
        self.assertTrue(channel_layer.ADAPTERS["WEB"].health_check())
        self.assertFalse(
            channel_layer.ADAPTERS["EMAIL"].provider_send_supported
        )
        with self.assertRaises(channel_layer.ChannelValidationError):
            channel_layer.create_connection(
                "workspace_a", channel_type="SMS", display_name="SMS",
                created_by="owner",
            )

    def test_connection_create_update_suspend_disconnect_and_audit(self):
        connection = channel_layer.create_connection(
            "workspace_a", channel_type="EMAIL", display_name="Mailbox",
            external_account_id="mailbox-1", status="CONNECTED",
            capabilities=("receive_text", "send_text"), created_by="owner",
        )
        self.assertEqual(connection.capabilities, ("receive_text",))
        renamed = channel_layer.update_connection(
            "workspace_a", connection.channel_connection_id,
            display_name="Support Mailbox", updated_by="owner",
        )
        self.assertEqual(renamed.display_name, "Support Mailbox")
        suspended = channel_layer.update_connection(
            "workspace_a", connection.channel_connection_id,
            target_status="SUSPENDED", updated_by="owner",
        )
        self.assertEqual(suspended.status, "SUSPENDED")
        disconnected = channel_layer.update_connection(
            "workspace_a", connection.channel_connection_id,
            target_status="DISCONNECTED", updated_by="owner",
        )
        self.assertEqual(disconnected.status, "DISCONNECTED")
        event_types = {
            item["event_type"]
            for item in channel_layer.list_events("workspace_a")
        }
        self.assertTrue({
            "channel_connected", "channel_updated", "channel_suspended",
            "channel_disconnected",
        }.issubset(event_types))

    def test_status_transition_validation_and_external_identity_uniqueness(self):
        connection = channel_layer.create_connection(
            "workspace_a", channel_type="TELEGRAM", display_name="Telegram",
            external_account_id="account-unique", created_by="owner",
        )
        with self.assertRaises(channel_layer.ChannelConflictError):
            channel_layer.update_connection(
                "workspace_a", connection.channel_connection_id,
                target_status="SUSPENDED",
            )
        with self.assertRaises(channel_layer.ChannelConflictError):
            channel_layer.create_connection(
                "workspace_b", channel_type="TELEGRAM",
                display_name="Other Telegram",
                external_account_id="account-unique", created_by="owner",
            )

    def test_server_workspace_and_cross_workspace_protection(self):
        with self.assertRaises(channel_layer.ChannelNotFoundError):
            channel_layer.get_connection(
                "workspace_b", self.web.channel_connection_id
            )
        with self.assertRaises(channel_layer.ChannelNotFoundError):
            channel_layer.ingest_inbound(
                "workspace_b", self.web.channel_connection_id,
                external_message_id="cross", external_sender_id="sender",
                message_type="TEXT", text_content="Cross workspace",
            )

    def test_web_provisioning_is_stable_and_single(self):
        again = channel_layer.ensure_web_connection("workspace_a")
        self.assertEqual(again.channel_connection_id, self.web.channel_connection_id)
        self.assertEqual(again.status, "CONNECTED")
        self.assertEqual(again.capabilities, ("receive_text", "send_text"))
        self.assertEqual(len(channel_layer.list_connections("workspace_a")), 1)

    def test_inbound_normalization_contact_and_external_identity(self):
        message, duplicate = self.ingest()
        self.assertFalse(duplicate)
        self.assertEqual(message.direction, "INBOUND")
        self.assertEqual(message.message_type, "TEXT")
        self.assertEqual(message.external_message_id, "provider-message-1")
        self.assertTrue(message.contact_id.startswith("contact_"))
        contact = contact_identity.get_contact(message.contact_id, "workspace_a")
        self.assertIn("web", contact["channels"])
        with self.assertRaises(channel_layer.ChannelValidationError):
            self.ingest(
                external_message_id="bad-direction",
                message_type="IMAGE",
            )

    def test_deterministic_deduplication_and_one_message(self):
        first, first_duplicate = self.ingest()
        second, second_duplicate = self.ingest()
        self.assertFalse(first_duplicate)
        self.assertTrue(second_duplicate)
        self.assertEqual(first.message_id, second.message_id)
        self.assertEqual(
            len(channel_layer.list_messages("workspace_a")), 1
        )
        self.assertIn(
            "inbound_deduplicated",
            {item["event_type"] for item in channel_layer.list_events("workspace_a")},
        )

    def test_concurrent_duplicate_protection(self):
        contact_identity.resolve_contact_identity(
            "workspace_a", "web", "sender-concurrent"
        )
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def run():
            try:
                barrier.wait()
                results.append(self.ingest(
                    external_message_id="concurrent-message",
                    external_sender_id="sender-concurrent",
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len({item[0].message_id for item in results}), 1)

    def test_fallback_deduplication_is_deterministic(self):
        first, _ = self.ingest(external_message_id="")
        second, duplicate = self.ingest(external_message_id="")
        self.assertTrue(duplicate)
        self.assertEqual(first.deduplication_key, second.deduplication_key)

    def test_work_object_linkage_and_cross_workspace_rejection(self):
        work_a = universal_work_objects.create_work_object(
            "workspace_a", object_type="TASK", title="Channel work",
            source_type="web", created_by="owner",
        )
        message, _ = self.ingest(
            external_message_id="work-link",
            related_work_object_id=work_a.work_object_id,
        )
        self.assertEqual(message.related_work_object_id, work_a.work_object_id)
        work_b = universal_work_objects.create_work_object(
            "workspace_b", object_type="TASK", title="Other work",
            source_type="web", created_by="owner",
        )
        with self.assertRaises(universal_work_objects.UniversalWorkNotFoundError):
            self.ingest(
                external_message_id="cross-work-link",
                related_work_object_id=work_b.work_object_id,
            )

    def test_duplicate_inbound_creates_no_work_object(self):
        self.ingest(external_message_id="no-work-duplicate")
        self.ingest(external_message_id="no-work-duplicate")
        self.assertEqual(
            universal_work_objects.list_work_objects("workspace_a"), ()
        )

    def test_outbound_references_and_delivery_safety(self):
        inbound, _ = self.ingest()
        outbound = channel_layer.create_outbound(
            "workspace_a", self.web.channel_connection_id,
            contact_id=inbound.contact_id, text_content="Draft response",
            related_inbound_message_id=inbound.message_id,
            approval_reference="approval_1",
            execution_reference="execution_1",
            status="APPROVED", created_by="reply_builder",
        )
        self.assertEqual(outbound.direction, "OUTBOUND")
        self.assertEqual(outbound.approval_reference, "approval_1")
        self.assertEqual(outbound.execution_reference, "execution_1")
        queued = channel_layer.transition_delivery(
            "workspace_a", outbound.message_id, "QUEUED"
        )
        with self.assertRaises(channel_layer.ChannelConflictError):
            channel_layer.transition_delivery(
                "workspace_a", queued.message_id, "SENT"
            )
        sent = channel_layer.transition_delivery(
            "workspace_a", queued.message_id, "SENT",
            provider_confirmed=True, external_delivery_id="provider-delivery-1",
        )
        with self.assertRaises(channel_layer.ChannelConflictError):
            channel_layer.transition_delivery(
                "workspace_a", sent.message_id, "DELIVERED"
            )
        delivered = channel_layer.transition_delivery(
            "workspace_a", sent.message_id, "DELIVERED",
            delivery_receipt=True,
        )
        self.assertEqual(delivered.delivery_status, "DELIVERED")

    def test_processing_transitions_and_safe_failure_metadata(self):
        inbound, _ = self.ingest(external_message_id="processing")
        routed = channel_layer.transition_processing(
            "workspace_a", inbound.message_id, "ROUTED"
        )
        failed = channel_layer.transition_processing(
            "workspace_a", routed.message_id, "FAILED",
            safe_metadata={
                "error_code": "adapter_unavailable",
                "api_key": "must-not-persist",
                "exception": "safe-class",
            },
        )
        self.assertEqual(failed.processing_status, "FAILED")
        events = channel_layer.list_events("workspace_a")
        encoded = repr(events)
        self.assertNotIn("must-not-persist", encoded)
        self.assertNotIn("api_key", encoded)
        self.assertNotIn("safe-class", encoded)
        self.assertNotIn("exception", encoded)

    def test_permissions_use_central_registry(self):
        for permission in (
            "channel_read", "channel_manage", "channel_message_read",
            "channel_message_send", "channel_audit_view",
        ):
            self.assertIsNotNone(permission_engine.get_permission_rule(permission))
        self.assertTrue(
            permission_engine.permission_requires_approval(
                "channel_message_send"
            )
        )

    def test_migration_fresh_idempotent_checksum_and_contract(self):
        result = managed_migrations.run_migrations()
        self.assertEqual(result["applied"], [])
        migration = next(
            item for item in managed_migrations.MIGRATIONS
            if item.identifier == "0013_channel_layer_v1"
        )
        self.assertEqual(migration.identifier, "0013_channel_layer_v1")
        self.assertEqual(len(migration.checksum), 64)
        self.assertIn(
            "0013_channel_layer_v1", production_schema_adoption.CONTRACTS
        )
        conn = sqlite3.connect(self.db_file)
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()
        self.assertTrue({
            "nina_channel_connections", "nina_channel_messages",
            "nina_channel_message_events",
        }.issubset(tables))

    def test_readiness_false_without_schema_and_true_with_schema(self):
        self.assertTrue(
            channel_layer.initialize_channel_layer(require_schema=True)
        )
        incomplete = str(Path(self.temp_dir.name) / "incomplete.sqlite")
        sqlite3.connect(incomplete).close()
        with patch.multiple(
            persistence_backend, DB_FILE=incomplete, USE_POSTGRES=False,
            DATABASE_URL="", HOSTED=False,
        ):
            self.assertFalse(
                channel_layer.initialize_channel_layer(require_schema=True)
            )


class ChannelLayerWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = str(Path(cls.temp_dir.name) / "channel-web.sqlite")
        import web_app

        cls.web_app = web_app
        cls.restore_database = bind_sqlite_database(
            cls.db_file, channel_connections, contact_identity, web_app
        )
        managed_migrations.run_migrations()
        initialize_ready_web(web_app)
        web_app.app.config.update(TESTING=True)
        cls.client = web_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        cls.temp_dir.cleanup()

    def test_dashboard_channels_messages_csrf_prg_and_escaping(self):
        page = self.client.get("/dashboard")
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Channels", body)
        self.assertIn("Messages", body)
        self.assertNotIn("Add Channel Connection", body)
        self.assertEqual(
            self.client.post(
                "/channel-layer/create",
                data={"channel_type": "EMAIL", "display_name": "No CSRF"},
            ).status_code,
            403,
        )
        admin = self.web_app.app.test_client()
        admin.set_cookie(
            self.web_app.ADMIN_COOKIE,
            self.web_app.create_admin_session(
                self.web_app._workspace_cookie_secret()
            ),
        )
        with patch.object(
            self.web_app, "current_web_contact",
            return_value={"contact_id": "contact_owner"},
        ):
            created = admin.post(
                "/channel-layer/create",
                data={
                    "csrf_token": self.web_app._channel_csrf("channel:create"),
                    "channel_type": "EMAIL",
                    "display_name": "<script>alert(1)</script>",
                    "external_account_id": "safe-mailbox",
                },
            )
        self.assertEqual(created.status_code, 302)
        body = admin.get("/dashboard").get_data(as_text=True)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_web_chat_persists_canonical_inbound_and_draft(self):
        with patch.object(
            self.web_app, "route_nina_message",
            return_value={
                "ok": True, "text": "One Nina response",
                "source": "nina", "channel": "web",
            },
        ):
            response = self.client.post(
                "/nina", data={"message": "Canonical web message"},
                headers={"Idempotency-Key": "web-regression-1"},
            )
        self.assertEqual(response.status_code, 302)
        messages = channel_layer.list_messages(
            self.web_app.NINA_WEB_WORKSPACE_ID, limit=20
        )
        matching = [
            item for item in messages
            if item.text_content in {
                "Canonical web message", "One Nina response",
            }
        ]
        self.assertEqual(len(matching), 2)
        outbound = next(item for item in matching if item.direction == "OUTBOUND")
        self.assertEqual(outbound.delivery_status, "DRAFT")


if __name__ == "__main__":
    unittest.main()
