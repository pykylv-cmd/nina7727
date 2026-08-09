import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class OneNinaNaturalUnderstandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "natural-understanding.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import managed_migrations
        import nina_message_service
        import work_objects
        cls.messaging = nina_message_service
        cls.work = work_objects
        cls.original_work = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        cls.original_message = (nina_message_service.DATABASE_URL, nina_message_service.DB_FILE, nina_message_service.USE_POSTGRES)
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
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM conversation_state")
        conn.commit()
        cur.close()
        conn.close()

    def send(self, text, channel="web", contact="person-a"):
        return self.messaging.route_nina_message(self.messaging.NinaMessageEnvelope(
            text=text, workspace_id="tenant-a", channel=channel,
            conversation_id=f"{channel}:{contact}", contact_id=contact,
            canonical_work_workspace_id="tenant-a",
        ), generator=lambda _: "generic")

    def active_reminders(self, contact="person-a"):
        return [obj for obj in self.work.list_work_objects(workspace_id="tenant-a", limit=100)
                if (obj.metadata or {}).get("reminder_state") == "scheduled"
                and (obj.metadata or {}).get("contact_id") == contact]

    def test_cross_turn_reminder_reference_updates_then_cancels_same_object(self):
        created = self.send("Atgādini rīt 11.00 piezvanīt Jānim")
        object_id = created["object_ids"][0]
        moved = self.send("Pārcel uz 12")
        self.assertEqual(moved["reminder_object_id"], object_id)
        moved_again = self.send("Nē, uz 13")
        self.assertEqual(moved_again["reminder_object_id"], object_id)
        listed = self.send("Kādi man ir atgādinājumi?")
        self.assertIn("13:00", listed["text"])
        cancelled = self.send("Izdzēs to")
        self.assertEqual(cancelled["reminder_object_id"], object_id)
        self.assertEqual(self.active_reminders(), [])

    def test_task_list_and_ordinal_completion_use_canonical_work_object(self):
        created = self.send("Izveido uzdevumu: piezvanīt Jānim")
        object_id = created["object_id"]
        moved = self.send("Pievieno rīt 10")
        self.assertEqual(moved["object_id"], object_id)
        self.assertEqual(self.work.get_work_object(object_id).due_date, "tomorrow 10:00")
        listed = self.send("Parādi manus uzdevumus")
        self.assertEqual(listed["work_object_ids"], [object_id])
        completed = self.send("Atzīmē pirmo uzdevumu kā pabeigtu")
        self.assertEqual(completed["object_id"], object_id)
        self.assertEqual(self.work.get_work_object(object_id).status, "done")

    def test_contact_reference_isolation_across_channels(self):
        created = self.send("Atgādini rīt 11.00 piezvanīt Jānim", "web", "person-a")
        moved = self.send("Pārcel uz 12", "telegram", "person-a")
        self.assertEqual(moved["reminder_object_id"], created["object_ids"][0])
        other = self.send("Pārcel uz 13", "whatsapp_company", "person-b")
        self.assertNotEqual(other.get("reminder_object_id"), created["object_ids"][0])

    def test_understanding_payload_is_structured(self):
        result = self.send("Kādi man ir atgādinājumi?")
        self.assertEqual(result["understanding"]["domain"], "reminders")
        self.assertEqual(result["understanding"]["operation"], "LIST")
        self.assertIn("needs_clarification", result["understanding"])

    def test_explicit_day_with_bare_hour_creates_clean_reminder(self):
        before = datetime.now(ZoneInfo("Europe/Riga"))
        result = self.send("Atgādini man rīt 11 piezvanīt Jānim")
        reminders = self.active_reminders()

        self.assertTrue(result["ok"])
        self.assertEqual(result["understanding"]["operation"], "CREATE")
        self.assertFalse(result["understanding"]["needs_clarification"])
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].title, "piezvanīt Jānim")
        scheduled = datetime.fromisoformat(reminders[0].metadata["reminder_at"])
        self.assertEqual(scheduled.astimezone(ZoneInfo("Europe/Riga")).date(), (before + timedelta(days=1)).date())
        self.assertEqual((scheduled.hour, scheduled.minute), (11, 0))

    def test_explicit_day_without_hour_still_requires_clarification(self):
        result = self.send("Atgādini man rīt piezvanīt Jānim")

        self.assertTrue(result["decision"]["needs_clarification"])
        self.assertEqual(result["source"], "brain_clarification")
        self.assertEqual(self.active_reminders(), [])

    def test_complete_explicit_reminder_supersedes_pending_clarification(self):
        pending = self.send("Atgādini man rīt piezvanīt Jānim")
        self.assertEqual(pending["source"], "brain_clarification")

        created = self.send(
            "Atgādini man ik pēc apaļas stundas — man ļoti patīk kad es esmu miljardieris"
        )
        reminders = self.active_reminders()

        self.assertTrue(created["ok"])
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].metadata["recurrence"], "hourly")
        self.assertEqual(reminders[0].metadata["reminder_text"], "man ļoti patīk kad es esmu miljardieris")
        self.assertNotIn("Jānim", reminders[0].metadata["reminder_text"])
        self.assertEqual(self.messaging._pending_reminder_context("person-a"), {})

    def test_clock_only_answer_still_continues_pending_reminder(self):
        pending = self.send("Atgādini man rīt piezvanīt Jānim")
        self.assertEqual(pending["source"], "brain_clarification")

        created = self.send("11")
        reminders = self.active_reminders()

        self.assertTrue(created["ok"])
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].metadata["reminder_text"], "piezvanīt Jānim")
        scheduled = datetime.fromisoformat(reminders[0].metadata["reminder_at"])
        self.assertEqual((scheduled.hour, scheduled.minute), (11, 0))

    def test_complete_timed_reminder_supersedes_pending_clarification(self):
        self.send("Atgādini man rīt piezvanīt Jānim")

        created = self.send("Atgādini man rīt 15 piezvanīt Pēterim")
        reminders = self.active_reminders()

        self.assertTrue(created["ok"])
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].metadata["reminder_text"], "piezvanīt Pēterim")
        self.assertNotIn("Jānim", reminders[0].metadata["reminder_text"])
        scheduled = datetime.fromisoformat(reminders[0].metadata["reminder_at"])
        self.assertEqual((scheduled.hour, scheduled.minute), (15, 0))

    def test_parit_and_weekday_bare_hours_are_valid(self):
        before = datetime.now(ZoneInfo("Europe/Riga"))
        parit = self.send("Atgādini man parīt 9 piezvanīt klientam")
        parit_object = self.work.get_work_object(parit["object_ids"][0])
        parit_at = datetime.fromisoformat(parit_object.metadata["reminder_at"])
        self.assertEqual(parit_at.date(), (before + timedelta(days=2)).date())
        self.assertEqual((parit_at.hour, parit_at.minute), (9, 0))
        self.assertEqual(parit_object.title, "piezvanīt klientam")

        friday = self.send("Atgādini piektdien 7 aizvest dokumentus", contact="person-b")
        friday_object = self.work.get_work_object(friday["object_ids"][0])
        friday_at = datetime.fromisoformat(friday_object.metadata["reminder_at"])
        self.assertEqual(friday_at.weekday(), 4)
        self.assertEqual((friday_at.hour, friday_at.minute), (7, 0))
        self.assertEqual(friday_object.title, "aizvest dokumentus")

    def test_hourly_next_occurrence_followups_are_read_only(self):
        created = self.send(
            "Atgādini man ik pēc apaļas stundas — man ļoti patīk kad es esmu miljardieris"
        )
        object_id = created["object_ids"][0]
        before = self.work.get_work_object(object_id)
        before_count = len(self.work.list_work_objects(workspace_id="tenant-a", limit=100))

        first = self.send("Pēc 19.00 nākamais kad?")
        second = self.send("Un pēc tam?")
        midnight = self.send("Pēc 23.00?")

        self.assertEqual(first["understanding"]["operation"], "GET_NEXT_OCCURRENCE")
        self.assertEqual(first["text"], "20:00.")
        self.assertEqual(second["text"], "21:00.")
        self.assertEqual(midnight["text"], "00:00.")
        self.assertEqual(first["reminder_object_id"], object_id)
        self.assertEqual(second["reminder_object_id"], object_id)
        self.assertEqual(midnight["reminder_object_id"], object_id)
        after = self.work.get_work_object(object_id)
        self.assertEqual(after.metadata, before.metadata)
        self.assertEqual(len(self.work.list_work_objects(workspace_id="tenant-a", limit=100)), before_count)
        self.assertEqual(first["source"], "shared_work")

    def test_all_next_occurrence_phrasings_keep_the_canonical_reference(self):
        created = self.send(
            "Atgādini man ik pēc apaļas stundas — pārbaudīt Ninu"
        )
        object_id = created["object_ids"][0]
        before = self.work.get_work_object(object_id)
        before_count = len(self.work.list_work_objects(workspace_id="tenant-a", limit=100))

        explicit = self.send("Pēc 19.00 nākamais kad?")
        next_time = self.send("Kad nākamreiz?")
        next_clock = self.send("Nākamais cikos?")
        after_this = self.send("Pēc šī kad?")
        reminder_wording = self.send("Kad tev man nākamreiz jāatgādina?")

        self.assertEqual(
            [explicit["text"], next_time["text"], next_clock["text"],
             after_this["text"], reminder_wording["text"]],
            ["20:00.", "21:00.", "22:00.", "23:00.", "00:00."],
        )
        for result in (explicit, next_time, next_clock, after_this, reminder_wording):
            self.assertEqual(result["understanding"]["operation"], "GET_NEXT_OCCURRENCE")
            self.assertEqual(result["reminder_object_id"], object_id)
            self.assertEqual(result["source"], "shared_work")
        after = self.work.get_work_object(object_id)
        self.assertEqual(after.metadata, before.metadata)
        self.assertEqual(len(self.work.list_work_objects(workspace_id="tenant-a", limit=100)), before_count)


if __name__ == "__main__":
    unittest.main()
