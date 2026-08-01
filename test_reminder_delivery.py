import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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
        cls.delivery = reminder_delivery
        cls.work = work_objects
        cls.original = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        cls.restore = bind_sqlite_database(cls.db_file, work_objects)

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


if __name__ == "__main__":
    unittest.main()
