import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class ReminderDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "reminder-delivery.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import reminder_delivery
        import work_objects
        import channel_connections
        import contact_identity
        import managed_migrations
        cls.delivery = reminder_delivery
        cls.work = work_objects
        cls.channel_connections = channel_connections
        cls.contact_identity = contact_identity
        cls.original = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        cls.restore = bind_sqlite_database(
            cls.db_file, work_objects, channel_connections, contact_identity,
        )
        managed_migrations.run_migrations()

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.work.DATABASE_URL, cls.work.DB_FILE, cls.work.USE_POSTGRES = cls.original
        cls.work._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work.ensure_work_objects_schema()
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM nina_channel_message_events")
        cur.execute("DELETE FROM nina_channel_messages")
        cur.execute("DELETE FROM nina_channel_connections")
        conn.commit()
        cur.close()
        conn.close()
        self.now = datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc)

    def reminder(self, *, owner="123", channel="telegram", status="scheduled", planned=None, workspace="tenant-a"):
        planned = planned or (self.now - timedelta(minutes=1)).isoformat(timespec="seconds")
        return self.work.create_work_object(
            object_type="reminder", title="Atgādinājums: pārbaudīt Ninu",
            workspace_id=workspace, status="active", origin_channel=channel,
            origin_user_id=owner,
            metadata={
                "source_work_object_id": "source-1", "planned_at": planned,
                "reminder_at": planned, "delivery_status": status,
                "attempt_count": 0, "unread": False,
            },
        )

    def test_due_reminder_is_claimed(self):
        reminder = self.reminder()
        claimed = self.delivery.claim_next(now=self.now)
        self.assertEqual(claimed.object_id, reminder.object_id)
        self.assertEqual(claimed.metadata["delivery_status"], "claimed")
        self.assertEqual(claimed.metadata["attempt_count"], 1)

    def test_web_relative_command_executes_brain_and_work_effect(self):
        from nina_message_service import send_message_to_nina
        from task_engine import detect_reminder_schedule
        fixed_now = datetime(
            2026, 8, 1, 12, 0, tzinfo=timezone(timedelta(hours=3)),
        )
        parsed = detect_reminder_schedule(
            "Atgādini pēc 5 minūtēm izvest suni.", now=fixed_now,
        )
        self.assertEqual(parsed["reminder_at"], "2026-08-01T12:05+03:00")
        with patch("task_engine.detect_reminder_schedule", return_value=parsed):
            result = send_message_to_nina(
                "Atgādini pēc 5 minūtēm izvest suni.",
                workspace_id="tenant-a", channel="web",
                conversation_id="contact:contact-a:web", contact_id="contact-a",
                canonical_work_workspace_id="tenant-a",
            )
        self.assertTrue(result["decision"]["create_work_object"])
        self.assertTrue(result["decision"]["create_reminder"])
        objects = self.work.list_work_objects(workspace_id="tenant-a")
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].origin_channel, "web")
        self.assertEqual(objects[0].origin_user_id, "contact-a")
        self.assertEqual(
            objects[0].metadata["reminder_at"], "2026-08-01T12:05+03:00",
        )

    def test_one_reminder_is_sent_once_across_two_workers(self):
        self.reminder()
        first = self.delivery.claim_next("worker-1", self.now)
        second = self.delivery.claim_next("worker-2", self.now)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        asyncio.run(self.delivery.deliver_claimed(first, sender, self.now))
        self.assertIsNone(self.delivery.claim_next("worker-2", self.now))
        self.assertEqual(len(sent), 1)

    def test_restart_recovers_stale_claim_and_overdue(self):
        stale = (self.now - timedelta(minutes=10)).isoformat(timespec="seconds")
        reminder = self.reminder(status="claimed")
        metadata = dict(reminder.metadata)
        metadata["claimed_at"] = stale
        self.work.update_work_object(reminder.object_id, metadata=metadata)
        self.assertIsNotNone(self.delivery.claim_next("restart-worker", self.now))

    def test_telegram_identity_receives_only_its_reminder(self):
        self.reminder(owner="111")
        claimed = self.delivery.claim_next(now=self.now)
        targets = []

        async def sender(**kwargs):
            targets.append(kwargs["chat_id"])

        asyncio.run(self.delivery.deliver_claimed(claimed, sender, self.now))
        self.assertEqual(targets, [111])
        self.assertNotIn(222, targets)

    def test_web_only_becomes_unread_notification(self):
        reminder = self.reminder(owner="contact-a", channel="web")
        claimed = self.delivery.claim_next(now=self.now)
        result = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        self.assertEqual(result.metadata["delivery_status"], "delivered")
        self.assertTrue(result.metadata["unread"])
        self.assertEqual(result.metadata["channel"], "web")
        from channel_layer import list_messages
        messages = list_messages("tenant-a")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].direction, "OUTBOUND")
        self.assertEqual(messages[0].delivery_status, "DELIVERED")
        self.assertEqual(messages[0].contact_id, "contact-a")
        self.assertEqual(messages[0].related_work_object_id, reminder.object_id)

    def test_web_delivery_additionally_invokes_push_sender(self):
        reminder = self.reminder(owner="contact-a", channel="web")
        claimed = self.delivery.claim_next(now=self.now)
        with patch("web_push.deliver_reminder_push") as push_sender:
            result = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        self.assertEqual(result.metadata["delivery_status"], "delivered")
        push_sender.assert_called_once()
        self.assertEqual(push_sender.call_args.args[0].object_id, reminder.object_id)

    def test_push_failure_does_not_fail_canonical_web_delivery(self):
        reminder = self.reminder(owner="contact-a", channel="web")
        claimed = self.delivery.claim_next(now=self.now)
        with patch("web_push.deliver_reminder_push", side_effect=RuntimeError("push unavailable")):
            result = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        self.assertEqual(result.metadata["delivery_status"], "delivered")

    def test_web_delivery_is_idempotent_after_existing_message(self):
        reminder = self.reminder(owner="contact-a", channel="web")
        claimed = self.delivery.claim_next(now=self.now)
        first = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        outbound = self.delivery.persist_web_delivery(first)
        from channel_layer import list_messages
        self.assertEqual(outbound.delivery_status, "DELIVERED")
        self.assertEqual(len(list_messages("tenant-a")), 1)

    def test_no_channel_awaits_channel(self):
        self.reminder(owner="", channel="")
        claimed = self.delivery.claim_next(now=self.now)
        result = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        self.assertEqual(result.metadata["delivery_status"], "awaiting_channel")

    def test_failed_send_increments_attempt_and_keeps_safe_error(self):
        reminder = self.reminder()
        claimed = self.delivery.claim_next(now=self.now)

        async def sender(**kwargs):
            raise RuntimeError("secret text must not persist")

        result = asyncio.run(self.delivery.deliver_claimed(claimed, sender, self.now))
        self.assertEqual(result.metadata["attempt_count"], 1)
        self.assertEqual(result.metadata["error_code"], "telegram_runtimeerror")
        self.assertNotIn("secret text", str(result.metadata))

    def test_snooze_preserves_history_and_reschedules(self):
        reminder = self.reminder(channel="web", owner="contact-a")
        claimed = self.delivery.claim_next(now=self.now)
        delivered = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        later = (self.now + timedelta(minutes=10)).isoformat(timespec="seconds")
        snoozed = self.delivery.snooze_reminder(delivered.object_id, "contact-a", later)
        self.assertEqual(snoozed.metadata["delivery_status"], "scheduled")
        self.assertEqual(snoozed.metadata["planned_at"], later)
        self.assertEqual(len(snoozed.metadata["delivery_history"]), 1)

    def test_completed_and_cancelled_are_not_sent(self):
        done = self.reminder(owner="contact-a", channel="web")
        self.delivery.complete_reminder(done.object_id, "contact-a")
        self.assertIsNone(self.delivery.claim_next(now=self.now))
        cancelled = self.reminder(owner="contact-b", channel="web")
        self.work.update_work_object(cancelled.object_id, status="cancelled")
        self.assertIsNone(self.delivery.claim_next(now=self.now))

    def test_owner_and_workspace_isolation(self):
        first = self.reminder(owner="contact-a", channel="web", workspace="tenant-a")
        self.assertIsNone(self.delivery.complete_reminder(first.object_id, "contact-b"))
        untouched = self.work.get_work_object(first.object_id)
        self.assertEqual(untouched.status, "active")

    def test_delivery_status_survives_store_reload(self):
        self.reminder(owner="contact-a", channel="web")
        claimed = self.delivery.claim_next(now=self.now)
        result = asyncio.run(self.delivery.deliver_claimed(claimed, now=self.now))
        self.work.WORK_OBJECT_STORE.clear()
        reloaded = self.work.get_work_object(result.object_id)
        self.assertEqual(reloaded.metadata["delivery_status"], "delivered")
        self.assertTrue(reloaded.metadata["idempotency_key"])


class TelegramReminderRoutingTests(unittest.TestCase):
    def test_relative_reminder_routes_through_one_nina_work_object_chain(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai-key",
            "TELEGRAM_TOKEN": "123456:test-telegram-token",
        }):
            import app

        expected = {"ok": True, "text": "Uzdevums izveidots.", "decision": {
            "create_work_object": True, "create_reminder": True,
        }}
        with patch.object(app, "can_create_reminder", return_value=(True, "")), patch.object(
            app, "workspace_for_telegram_identity", return_value="workspace-linked",
        ) as workspace_for_identity, patch(
            "nina_message_service.send_message_to_nina", return_value=expected,
        ) as send:
            answer = app.add_reminder(
                "123456", "Atgādini man pēc 5 minūtēm pārbaudīt Ninu.",
            )
        self.assertEqual(answer, "Uzdevums izveidots.")
        workspace_for_identity.assert_called_once_with(telegram_user_id="123456")
        send.assert_called_once_with(
            "Atgādini man pēc 5 minūtēm pārbaudīt Ninu.",
            workspace_id="workspace-linked",
            channel="telegram",
            conversation_id="telegram:123456",
            contact_id="123456",
            canonical_work_workspace_id="workspace-linked",
        )


class WebReminderVisibilityTests(unittest.TestCase):
    def test_nina_surface_filters_reminders_by_server_contact(self):
        import web_app
        own = SimpleNamespace(
            direction="OUTBOUND", channel_type="WEB", delivery_status="DELIVERED",
            contact_id="contact-a", safe_metadata={"notification_type": "reminder"},
            text_content="⏰ Atgādinājums: izvest suni", created_at="2026-08-01T09:05:00+00:00",
            message_id="message-own",
        )
        other = SimpleNamespace(**{**own.__dict__, "contact_id": "contact-b", "message_id": "message-other"})
        with patch.object(web_app, "list_channel_messages", return_value=(other, own)) as listed:
            items = web_app._web_reminder_notifications({"contact_id": "contact-a"})
        listed.assert_called_once_with(web_app.NINA_WEB_WORKSPACE_ID, limit=100)
        self.assertEqual([item["message_id"] for item in items], ["message-own"])
        with web_app.app.test_request_context("/nina?lang=en"):
            body = web_app.nina_chat_body(items)
        self.assertIn("message-own", body)
        self.assertIn("Atgādinājums: izvest suni", body)
        self.assertIn("/nina/notifications", body)
        self.assertNotIn("message-other", body)

    def test_notification_endpoint_uses_current_server_contact(self):
        import web_app
        items = [{"message_id": "message-own", "text": "Reminder", "created_at": "now"}]
        with web_app.app.test_request_context("/nina/notifications"), patch.object(
            web_app, "current_web_contact", return_value={"contact_id": "server-contact"},
        ), patch.object(web_app, "_web_reminder_notifications", return_value=items) as load:
            response = web_app.nina_notifications()
        load.assert_called_once_with({"contact_id": "server-contact"})
        self.assertEqual(response.get_json()["notifications"][0]["message_id"], "message-own")


if __name__ == "__main__":
    unittest.main()
