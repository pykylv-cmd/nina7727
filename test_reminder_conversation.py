import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class ReminderConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "reminder-conversation.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import managed_migrations
        import nina_message_service
        import persistence_backend
        import reminder_delivery
        import work_objects
        cls.messaging = nina_message_service
        cls.delivery = reminder_delivery
        cls.work = work_objects
        cls.persistence = persistence_backend
        cls.original_work = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        cls.original_message = (
            nina_message_service.DATABASE_URL,
            nina_message_service.DB_FILE,
            nina_message_service.USE_POSTGRES,
        )
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        nina_message_service.DATABASE_URL = ""
        nina_message_service.DB_FILE = cls.db_file
        nina_message_service.USE_POSTGRES = False
        cls.restore = bind_sqlite_database(cls.db_file, work_objects)
        managed_migrations.run_migrations()

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.work.DATABASE_URL, cls.work.DB_FILE, cls.work.USE_POSTGRES = cls.original_work
        cls.messaging.DATABASE_URL, cls.messaging.DB_FILE, cls.messaging.USE_POSTGRES = cls.original_message
        cls.work._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work.ensure_work_objects_schema()
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM conversation_state")
        conn.commit()
        cur.close()
        conn.close()

    def send(self, text, conversation="company:contact-a"):
        return self.messaging.send_message_to_nina(
            text,
            workspace_id="tenant-a",
            channel="whatsapp_company",
            conversation_id=conversation,
            contact_id="contact-a",
            canonical_work_workspace_id="tenant-a",
            delivery_recipient="37120000000@s.whatsapp.net",
            generator=lambda _: self.fail("generic provider must not handle reminder operations"),
        )

    def sources(self):
        return [
            obj for obj in self.work.list_work_objects(workspace_id="tenant-a", limit=500)
            if (obj.metadata or {}).get("reminder_state") == "scheduled"
        ]

    def create_daily_set(self):
        result = self.send(
            "Katru dienu 7.00, 12.00 un 19.00 atgādini: Tu esi miljardieris 😊"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["object_ids"]), 3)
        return self.sources()

    def create_production_daily_set(self):
        result = self.send(
            "Katru dienu 7.00 atgādini: Labrīt, miljardieri 😊\n"
            "Vēl 12.00 saki: Tu esi miljardieris\n"
            "Un 19.00 arī: Tu esi miljardieris 😊"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["object_ids"]), 3)
        return self.sources()

    def test_exact_latvian_production_conversation_uses_persisted_truth(self):
        sources = self.create_production_daily_set()
        expected = {
            "07:00": "Labrīt, miljardieri 😊",
            "12:00": "Tu esi miljardieris",
            "19:00": "Tu esi miljardieris 😊",
        }
        self.assertEqual(
            {self.messaging._reminder_local_clock(obj): obj.metadata["reminder_text"] for obj in sources},
            expected,
        )
        original_ids = {obj.object_id for obj in sources}

        listed = self.send("Kādi man ir atgādinājumi?")
        self.assertEqual(listed["decision"]["reminder_operation"], "LIST")
        for clock, text in expected.items():
            self.assertIn(clock, listed["text"])
            self.assertIn(text, listed["text"])
        self.assertEqual({obj.object_id for obj in self.sources()}, original_ids)

        midday = self.send("Pa dienu kas tev jāatgādina?")
        self.assertEqual(midday["decision"]["reminder_operation"], "ASK")
        self.assertIn("12:00", midday["text"])
        self.assertIn("Tu esi miljardieris", midday["text"])
        self.assertNotIn("Kad tieši", midday["text"])

        evening_before = next(obj for obj in sources if self.messaging._reminder_local_clock(obj) == "19:00")
        updated = self.send("Vakarā arī labrīt nesaki")
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["decision"]["reminder_operation"], "UPDATE")
        self.assertEqual(updated["reminder_object_id"], evening_before.object_id)
        after = self.sources()
        self.assertEqual({obj.object_id for obj in after}, original_ids)
        self.assertEqual(len(after), 3)

        listed_after = self.send("Kādi man ir atgādinājumi?")
        evening_after = next(obj for obj in after if self.messaging._reminder_local_clock(obj) == "19:00")
        self.assertEqual(evening_after.object_id, evening_before.object_id)
        self.assertNotIn("Labrīt", evening_after.metadata["reminder_text"])
        self.assertIn(evening_after.metadata["reminder_text"], listed_after["text"])

    def test_latvian_list_is_read_only_not_create(self):
        self.create_daily_set()
        before = [obj.object_id for obj in self.sources()]
        result = self.send("Kādi man ir atgādinājumi?")
        after = [obj.object_id for obj in self.sources()]
        self.assertEqual(result["decision"]["reminder_operation"], "LIST")
        self.assertNotIn("Kad tieši", result["text"])
        self.assertEqual(before, after)
        self.assertEqual(result["text"].count("katru dienu"), 3)

    def test_midday_question_reads_persisted_noon_truth(self):
        self.create_daily_set()
        result = self.send("Pa dienu kas tev jāatgādina?")
        self.assertEqual(result["decision"]["reminder_operation"], "ASK")
        self.assertIn("12:00", result["text"])
        self.assertIn("Tu esi miljardieris", result["text"])
        self.assertEqual(len(self.sources()), 3)

    def test_evening_update_keeps_same_canonical_identity(self):
        sources = self.create_daily_set()
        evening = next(obj for obj in sources if self.messaging._reminder_local_clock(obj) == "19:00")
        before_ids = {obj.object_id for obj in sources}
        before_by_id = {
            obj.object_id: {
                "clock": self.messaging._reminder_local_clock(obj),
                "title": obj.title,
                "metadata": dict(obj.metadata or {}),
                "updated_at": obj.updated_at,
            }
            for obj in sources
        }
        result = self.send("Vakarā arī labrīt nesaki")
        after = self.sources()
        after_by_id = {obj.object_id: obj for obj in after}
        self.assertTrue(result["ok"])
        self.assertEqual(result["reminder_object_id"], evening.object_id)
        self.assertEqual(set(after_by_id), before_ids)
        self.assertEqual(len(after), 3)
        self.assertEqual(
            self.messaging._reminder_local_clock(after_by_id[evening.object_id]),
            "19:00",
        )
        self.assertNotEqual(after_by_id[evening.object_id].updated_at, before_by_id[evening.object_id]["updated_at"])
        for object_id in before_ids - {evening.object_id}:
            self.assertEqual(after_by_id[object_id].title, before_by_id[object_id]["title"])
            self.assertEqual(after_by_id[object_id].metadata, before_by_id[object_id]["metadata"])
            self.assertEqual(after_by_id[object_id].updated_at, before_by_id[object_id]["updated_at"])

    def test_clean_tomorrow_reminder_is_created_once(self):
        result = self.send("Atgādini man rīt 11.00 saskaitīt naudu")
        self.assertTrue(result["ok"])
        sources = self.sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].title, "saskaitīt naudu")
        self.assertEqual(sources[0].metadata["reminder_text"], "saskaitīt naudu")
        self.assertNotEqual(sources[0].metadata["raw_text"], sources[0].title)

    def test_multiple_daily_times_are_distinct_and_clean(self):
        sources = self.create_daily_set()
        self.assertEqual(
            sorted(self.messaging._reminder_local_clock(obj) for obj in sources),
            ["07:00", "12:00", "19:00"],
        )
        self.assertEqual({obj.title for obj in sources}, {"Tu esi miljardieris 😊"})
        self.assertTrue(all(obj.metadata["recurrence"] == "daily" for obj in sources))

    def test_structured_clarification_preserves_action(self):
        first = self.send("Atgādini man saskaitīt naudu")
        self.assertTrue(first["decision"]["needs_clarification"])
        pending = self.messaging._pending_reminder_context("company:contact-a")
        self.assertEqual(pending["operation"], "CREATE")
        self.assertEqual(pending["action_text"], "saskaitīt naudu")
        second = self.send("Rīt 11.00")
        self.assertTrue(second["ok"])
        self.assertEqual(self.sources()[0].title, "saskaitīt naudu")
        self.assertEqual(self.messaging._pending_reminder_context("company:contact-a"), {})

    def test_duplicate_confirmation_does_not_duplicate(self):
        command = "Atgādini man rīt 11.00 saskaitīt naudu"
        first = self.send(command)
        second = self.send(command)
        self.assertTrue(first["ok"] and second["ok"])
        self.assertEqual(first["object_id"], second["object_id"])
        self.assertEqual(len(self.sources()), 1)

    def test_failed_persistence_never_claims_success(self):
        with patch.object(self.messaging, "execute_natural_work_request", side_effect=RuntimeError("db down")):
            result = self.send("Atgādini man rīt 11.00 saskaitīt naudu")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "reminder_creation_failed")
        self.assertNotIn("saglabāts", result["text"].casefold())

    def test_daily_delivery_advances_source_and_preserves_recipient(self):
        due = datetime.now(timezone.utc) - timedelta(minutes=1)
        source = self.work.create_work_object(
            object_type="task", title="Labrīt, miljardieri 😊",
            workspace_id="tenant-a", origin_channel="whatsapp_company",
            origin_user_id="contact-a", source_key="daily-source:test",
            metadata={
                "reminder_state": "scheduled",
                "reminder_at": due.isoformat(timespec="minutes"),
                "reminder_text": "Labrīt, miljardieri 😊",
                "recurrence": "daily", "timezone": "Europe/Riga",
                "whatsapp_recipient_jid": "37120000000@s.whatsapp.net",
            },
        )
        created = self.messaging.materialize_due_reminders("tenant-a", now=due)
        self.assertEqual(len(created), 1)
        reminder = created[0]
        self.assertEqual(
            reminder.metadata["whatsapp_recipient_jid"],
            "37120000000@s.whatsapp.net",
        )
        claimed = self.delivery.claim_next(now=due + timedelta(minutes=2))
        with patch("personal_whatsapp.bridge_request", return_value={"ok": True, "message_id": "wa-1"}):
            delivered = asyncio.run(self.delivery.deliver_claimed(claimed, now=due + timedelta(minutes=2)))
        self.assertEqual(delivered.metadata["delivery_status"], "delivered")
        advanced = self.work.get_work_object(source.object_id)
        self.assertGreater(
            datetime.fromisoformat(advanced.metadata["reminder_at"]),
            due + timedelta(minutes=2),
        )

    def test_exact_hourly_create_list_delete_conversation_uses_persisted_truth(self):
        first = self.send("Atgādini man: es esmu laimīgs dzīvot miljardiera dzīvi")
        self.assertEqual(first["source"], "brain_clarification")
        self.assertEqual(first["text"], "Kad tieši man tev to atgādināt?")

        created = self.send("Ik pa apaļai stundai")
        self.assertTrue(created["ok"])
        self.assertEqual(created["decision"]["reminder_operation"], "CREATE")
        sources = self.sources()
        self.assertEqual(len(sources), 1)
        source = sources[0]
        self.assertEqual(source.title, "es esmu laimīgs dzīvot miljardiera dzīvi")
        self.assertEqual(source.metadata["reminder_text"], source.title)
        self.assertEqual(source.metadata["recurrence"], "hourly")
        scheduled = datetime.fromisoformat(source.metadata["reminder_at"])
        self.assertEqual(scheduled.minute, 0)

        listed = self.send("Kādi man ir atgādinājumi?")
        self.assertEqual(listed["decision"]["reminder_operation"], "LIST")
        self.assertIn("katru apaļu stundu", listed["text"])
        self.assertIn(source.title, listed["text"])

        before_ids = {obj.object_id for obj in self.sources()}
        deleted = self.send("Izdzēs visus")
        self.assertTrue(deleted["ok"])
        self.assertEqual(deleted["decision"]["reminder_operation"], "CANCEL")
        self.assertEqual(deleted["remaining_reminders"], 0)
        self.assertEqual(deleted["cancelled_reminders"], 1)
        self.assertEqual(before_ids, {source.object_id})
        self.assertEqual(self.sources(), [])

        empty = self.send("Kādi man ir atgādinājumi?")
        self.assertEqual(empty["text"], "Tev nav aktīvu atgādinājumu.")
        repeated = self.send("Izdzēs visus")
        self.assertTrue(repeated["ok"])
        self.assertEqual(repeated["cancelled_reminders"], 0)

    def test_all_supported_hourly_phrases_schedule_the_next_whole_hour(self):
        from task_engine import detect_reminder_schedule
        fixed = datetime(2026, 8, 9, 12, 34, tzinfo=timezone(timedelta(hours=3)))
        for phrase in (
            "ik pēc stundas", "ik pa apaļai stundai",
            "ik pēc apaļas stundas", "katru apaļu stundu",
        ):
            with self.subTest(phrase=phrase):
                parsed = detect_reminder_schedule(
                    f"Atgādini man {phrase}: pārbaudīt Ninu",
                    now=fixed, reminder_requested=True,
                )
                self.assertEqual(parsed["reminder_at"], "2026-08-09T13:00+03:00")

    def test_delete_persistence_failure_never_claims_success(self):
        self.send("Atgādini man rīt 11.00 saskaitīt naudu")
        before_ids = {obj.object_id for obj in self.sources()}
        with patch.object(self.messaging, "update_work_object", return_value=None):
            result = self.send("atcel visus manus atgādinājumus")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "reminder_cancel_failed")
        self.assertNotIn("atcēlu", result["text"].casefold())
        self.assertNotIn("dzēsti", result["text"].casefold())
        self.assertEqual({obj.object_id for obj in self.sources()}, before_ids)

    def test_pending_reminder_context_cannot_fall_through_to_generic_chat(self):
        self.send("Atgādini man: pārbaudīt Ninu")
        result = self.send("kaut kā regulāri")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "reminder_schedule_still_pending")
        self.assertIn("atgādinājuma", result["text"].casefold())
        self.assertEqual(self.sources(), [])

    def test_hourly_delivery_advances_to_next_whole_hour_once(self):
        due = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        source = self.work.create_work_object(
            object_type="task", title="Stundas apliecinājums",
            workspace_id="tenant-a", origin_channel="whatsapp_company",
            origin_user_id="contact-a", source_key="hourly-source:test",
            metadata={
                "reminder_state": "scheduled", "reminder_at": due.isoformat(timespec="minutes"),
                "reminder_text": "Stundas apliecinājums", "recurrence": "hourly",
                "timezone": "Europe/Riga", "contact_id": "contact-a",
                "whatsapp_recipient_jid": "37120000000@s.whatsapp.net",
            },
        )
        occurrences = self.messaging.materialize_due_reminders("tenant-a", now=due)
        self.assertEqual(len(occurrences), 1)
        claimed = self.delivery.claim_next(now=due + timedelta(minutes=1))
        with patch("personal_whatsapp.bridge_request", return_value={"ok": True, "message_id": "wa-hourly-1"}):
            delivered = asyncio.run(self.delivery.deliver_claimed(claimed, now=due + timedelta(minutes=1)))
        self.assertEqual(delivered.metadata["delivery_status"], "delivered")
        advanced = self.work.get_work_object(source.object_id)
        next_at = datetime.fromisoformat(advanced.metadata["reminder_at"])
        self.assertEqual(next_at.minute, 0)
        self.assertGreater(next_at, due + timedelta(minutes=1))
        self.assertIsNone(self.delivery.claim_next(now=due + timedelta(minutes=2)))


if __name__ == "__main__":
    unittest.main()
