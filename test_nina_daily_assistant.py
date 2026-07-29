import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_runtime_support import bind_sqlite_database, initialize_ready_web, install_test_environment

install_test_environment()


class FixedRigaDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = cls(2026, 7, 27, 12, 0, tzinfo=ZoneInfo("Europe/Riga"))
        return fixed if tz is None else fixed.astimezone(tz)


class NinaDailyAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "daily-assistant.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import nina_message_service
        import task_engine
        import web_app
        import work_engine
        import work_objects

        cls.service = nina_message_service
        cls.task_engine = task_engine
        cls.web_app = web_app
        cls.work_engine = work_engine
        cls.work_objects = work_objects
        cls.original_work_db = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        cls.restore_database = bind_sqlite_database(cls.db_file, work_objects, nina_message_service)
        initialize_ready_web(web_app)

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        self_db = cls.work_objects
        self_db.DATABASE_URL, self_db.DB_FILE, self_db.USE_POSTGRES = cls.original_work_db
        self_db._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work_objects.ensure_work_objects_schema()
        self.service._ensure_memory_store()
        conn = self.work_objects._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM memory_backups")
        conn.commit()
        cur.close()
        conn.close()

    def test_parse_reminder_phrases(self):
        now = datetime(2026, 7, 27, 12, 0, tzinfo=ZoneInfo("Europe/Riga"))
        tomorrow = self.task_engine.detect_reminder_schedule("Rīt 9:00 piezvanīt Jānim.", now=now)
        relative = self.task_engine.detect_reminder_schedule("Pēc divām stundām atgādini.", now=now)
        friday = self.task_engine.detect_reminder_schedule("Piektdien atsūti atgādinājumu.", now=now)
        monday = self.task_engine.detect_reminder_schedule("Nākamajā pirmdienā atgādini.", now=now)
        self.assertIn("2026-07-28T09:00", tomorrow["reminder_at"])
        self.assertIn("2026-07-27T14:00", relative["reminder_at"])
        self.assertIn("2026-07-31T09:00", friday["reminder_at"])
        self.assertIn("2026-08-03T09:00", monday["reminder_at"])

    def test_reminder_creates_existing_work_object(self):
        result = self.work_engine.execute_natural_work_request(
            "Rīt 9:00 piezvanīt Jānim.", workspace_id="daily", channel="web", contact_id="contact-1",
        )
        self.assertTrue(result["ok"])
        obj = self.work_objects.list_work_objects(workspace_id="daily")[0]
        self.assertEqual(obj.object_type, "task")
        self.assertEqual(obj.origin_user_id, "contact-1")
        self.assertEqual(obj.metadata["reminder_state"], "scheduled")
        self.assertTrue(obj.metadata["reminder_at"])

    def test_today_and_overdue_summary(self):
        now = FixedRigaDateTime.now(ZoneInfo("Europe/Riga"))
        for title, due in (
            ("Nokavētais", now - timedelta(days=1)),
            ("Šodienas", now + timedelta(hours=1)),
            ("Tuvākais", now + timedelta(days=2)),
        ):
            self.work_objects.create_work_object(
                object_type="task", title=title, workspace_id="daily",
                metadata={"reminder_at": due.isoformat(timespec="minutes")},
            )
        buckets = self.service.daily_work_summary("daily", now=now)
        self.assertEqual([x.title for x in buckets["overdue"]], ["Nokavētais"])
        self.assertEqual([x.title for x in buckets["today"]], ["Šodienas"])
        self.assertEqual([x.title for x in buckets["upcoming"]], ["Tuvākais"])
        with patch.object(self.service, "datetime", FixedRigaDateTime):
            answer = self.service._daily_assistant_answer(
                "Kas man šodien jādara?", "daily", "contact-1"
            )
        self.assertIn("Nokavēts", answer)
        self.assertIn("Šodienas", answer)

    def test_due_followup_becomes_idempotent_reminder_work_object(self):
        now = datetime.now(ZoneInfo("Europe/Riga"))
        source = self.work_objects.create_work_object(
            object_type="task", title="Piezvanīt Jānim", workspace_id="daily",
            metadata={
                "reminder_at": (now - timedelta(minutes=1)).isoformat(timespec="minutes"),
                "reminder_state": "scheduled",
            },
        )
        first = self.service.materialize_due_reminders("daily", now=now)
        second = self.service.materialize_due_reminders("daily", now=now)
        self.assertEqual(first[0].object_type, "reminder")
        self.assertEqual(first[0].metadata["source_work_object_id"], source.object_id)
        self.assertEqual(first[0].object_id, second[0].object_id)

    def test_daily_summary_does_not_cross_contact_boundary(self):
        now = FixedRigaDateTime.now(ZoneInfo("Europe/Riga"))
        for owner in ("contact-1", "contact-2"):
            self.work_objects.create_work_object(
                object_type="task", title=f"Darbs {owner}", workspace_id="daily",
                origin_user_id=owner,
                metadata={"reminder_at": (now + timedelta(hours=1)).isoformat(timespec="minutes")},
            )
        buckets = self.service.daily_work_summary("daily", now=now, owner_id="contact-1")
        titles = [item.title for item in buckets["today"]]
        self.assertIn("Darbs contact-1", titles)
        self.assertNotIn("Darbs contact-2", titles)

    def test_tomorrow_uses_existing_planner(self):
        now = datetime.now(ZoneInfo("Europe/Riga"))
        self.work_objects.create_work_object(
            object_type="task", title="Rītdienas zvans", workspace_id="daily",
            metadata={"reminder_at": (now + timedelta(days=1)).isoformat(timespec="minutes")},
        )
        answer = self.service._daily_assistant_answer("Kas man rīt jādara?", "daily", "contact-1")
        self.assertIn("Rītdienas zvans", answer)

    def test_remembered_facts_use_existing_memory(self):
        self.service._save_natural_memory("contact-1", "Man patīk melna kafija.")
        answer = self.service._daily_assistant_answer("Ko tu par mani atceries?", "daily", "contact-1")
        self.assertIn("melna kafija", answer)
        captured = {}

        def generator(prompt):
            captured["prompt"] = prompt
            return "Labi."

        self.service.send_message_to_nina(
            "Pastāsti kaut ko.", workspace_id="daily", contact_id="contact-1",
            conversation_id="web:contact-1", generator=generator,
        )
        self.assertIn("melna kafija", captured["prompt"])

    def test_dashboard_contains_today_panel(self):
        response = self.web_app.app.test_client().get("/dashboard")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Today's Tasks", body)
        self.assertIn("Overdue", body)
        self.assertIn("Upcoming", body)


if __name__ == "__main__":
    unittest.main()
