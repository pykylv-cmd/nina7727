import os
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
