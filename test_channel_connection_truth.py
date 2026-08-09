import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()
import channel_connections


class ChannelConnectionTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_file = handle.name
        handle.close()
        cls.original = (channel_connections.DATABASE_URL, channel_connections.DB_FILE,
                        channel_connections.USE_POSTGRES)
        channel_connections.DATABASE_URL = ""
        channel_connections.DB_FILE = cls.db_file
        channel_connections.USE_POSTGRES = False
        channel_connections._SCHEMA_READY = False
        cls.restore = bind_sqlite_database(cls.db_file, channel_connections)

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        channel_connections.DATABASE_URL, channel_connections.DB_FILE, channel_connections.USE_POSTGRES = cls.original
        channel_connections._SCHEMA_READY = False
        os.unlink(cls.db_file)

    def truth(self, channel, persisted, runtime=None, user=None, now=None):
        return channel_connections.resolve_channel_connection_truth(
            "workspace_truth", channel, persisted, runtime, user, now=now
        )

    def setUp(self):
        channel_connections.disconnect("workspace_truth", "telegram")

    def test_telegram_linked_fresh_is_ready(self):
        now = datetime.now(timezone.utc)
        value = self.truth("telegram", {"status": "connected"},
                           {"state": "ready", "last_heartbeat_at": now.isoformat()}, now=now)
        self.assertEqual(value["state"], "ready")

    def test_telegram_linked_stale_is_attention(self):
        now = datetime.now(timezone.utc)
        value = self.truth("telegram", {"status": "connected"},
                           {"state": "ready", "last_heartbeat_at": (now-timedelta(minutes=2)).isoformat()}, now=now)
        self.assertEqual(value["state"], "attention")

    def test_telegram_unlinked_healthy_is_not_connected(self):
        self.assertEqual(self.truth("telegram", {"status": "disconnected"},
                                    {"state": "ready", "fresh": True})["state"], "not_connected")

    def test_telegram_heartbeat_does_not_create_linkage(self):
        self.assertEqual(channel_connections.mark_telegram_runtime_state(True), 0)
        self.assertEqual(channel_connections.get_connection("workspace_truth", "telegram")["status"], "disconnected")

    def test_telegram_heartbeat_updates_linked_only(self):
        channel_connections.set_connection_for_test("workspace_truth", "telegram", "connected", {})
        self.assertEqual(channel_connections.mark_telegram_runtime_state(True), 1)
        metadata = channel_connections.get_connection("workspace_truth", "telegram")["metadata"]
        self.assertTrue(metadata["polling_owner"])
        self.assertTrue(metadata["polling_ready"])

    def test_telegram_restart_attention_then_ready(self):
        persisted = {"status": "connected"}
        self.assertEqual(self.truth("telegram", persisted, {"state": "unavailable"})["state"], "attention")
        self.assertEqual(self.truth("telegram", persisted, {"state": "ready", "fresh": True})["state"], "ready")

    def test_company_stale_connected_bridge_unavailable_is_attention(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "connected"},
                                    {"state": "unavailable"})["state"], "attention")

    def test_company_linked_runtime_connected_is_ready(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "connected"},
                                    {"state": "connected"})["state"], "ready")

    def test_company_invalid_auth_requires_reconnect(self):
        value = self.truth("whatsapp_company", {"status": "error"}, {"state": "invalid_auth"})
        self.assertEqual((value["state"], value["recovery_action"]), ("reconnect_required", "reconnect"))

    def test_company_logged_out_requires_reconnect(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "error"},
                                    {"state": "logged_out"})["state"], "reconnect_required")

    def test_company_persisted_invalid_auth_survives_bridge_restart(self):
        persisted = {"status": "error", "metadata": {"runtime_state": "invalid_auth"}}
        self.assertEqual(self.truth("whatsapp_company", persisted,
                                    {"state": "unavailable"})["state"], "reconnect_required")

    def test_company_pairing_with_qr_is_pending(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "pending"},
                                    {"state": "connecting", "qr_available": True})["state"], "qr_pending")

    def test_company_pairing_preparing_qr_is_pending(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "pending"},
                                    {"state": "connecting"})["reason_code"], "company_pairing_preparing")

    def test_company_unlinked_is_not_connected(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "disconnected"},
                                    {"state": "disconnected"})["state"], "not_connected")

    def test_company_runtime_cannot_fabricate_linkage(self):
        self.assertEqual(self.truth("whatsapp_company", {"status": "disconnected"},
                                    {"state": "connected"})["state"], "not_connected")

    def test_company_ready_is_not_recoverable(self):
        self.assertFalse(self.truth("whatsapp_company", {"status": "connected"},
                                    {"state": "connected"})["recoverable"])

    def test_web_unhealthy_is_attention(self):
        self.assertEqual(self.truth("web", {"status": "connected"},
                                    {"service_ready": False}, {"workspace_usable": True})["state"], "attention")

    def test_web_healthy_without_workspace_is_not_ready(self):
        self.assertEqual(self.truth("web", {"status": "connected"},
                                    {"service_ready": True}, {"workspace_usable": False})["state"], "not_ready")

    def test_web_healthy_usable_workspace_is_ready(self):
        self.assertEqual(self.truth("web", {"status": "connected"},
                                    {"service_ready": True}, {"workspace_usable": True})["state"], "ready")

    def test_truth_contract_contains_no_secret(self):
        value = self.truth("telegram", {"status": "connected", "secret_ref": "secret"},
                           {"state": "ready", "fresh": True})
        self.assertNotIn("secret_ref", value)

    def test_truth_contract_fields_are_stable(self):
        self.assertEqual(set(self.truth("telegram", {"status": "disconnected"})),
                         {"state", "linked", "runtime_ready", "recoverable", "recovery_action", "reason_code"})

    def test_attention_is_recoverable(self):
        self.assertTrue(self.truth("telegram", {"status": "connected"},
                                   {"state": "unavailable"})["recoverable"])

    def test_ready_requires_linkage_for_telegram(self):
        value = self.truth("telegram", {"status": "pending"}, {"state": "ready", "fresh": True})
        self.assertFalse(value["linked"])
        self.assertEqual(value["state"], "not_connected")


if __name__ == "__main__":
    unittest.main()
