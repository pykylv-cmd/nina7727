import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class ReplyBuilderV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "reply-builder.db")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import initiative_engine
        import reply_builder
        import web_app
        import work_objects

        cls.initiative = initiative_engine
        cls.reply = reply_builder
        cls.web_app = web_app
        cls.work = work_objects
        cls.original = (
            work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES,
        )
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        cls.restore = bind_sqlite_database(cls.db_file, work_objects)
        initialize_ready_web(web_app)

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        (
            cls.work.DATABASE_URL, cls.work.DB_FILE, cls.work.USE_POSTGRES,
        ) = cls.original
        cls.work._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work._SCHEMA_READY = False
        self.work.ensure_work_objects_schema()
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        conn.commit()
        cur.close()
        conn.close()
        self.now = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)

    def create(self, workspace="reply-a", **values):
        defaults = {
            "object_type": "task", "title": "Prepare client update",
            "workspace_id": workspace, "status": "open",
        }
        defaults.update(values)
        return self.work.create_work_object(**defaults)

    def initiative_for(self, item, initiative_type="overdue"):
        return self.initiative.InitiativeCandidate(
            initiative_id=(
                f"initiative:{item.workspace_id}:{item.object_id}:"
                f"{initiative_type}"
            ),
            workspace_id=item.workspace_id,
            work_object_id=item.object_id,
            type=initiative_type,
            reason="Rule-backed reason",
            score=72,
            created_at=self.now.isoformat(),
        )

    def test_deterministic_drafts(self):
        item = self.create(client_id="client-a")
        initiative = self.initiative_for(item)
        first = self.reply.ReplyBuilder.build(initiative)
        second = self.reply.ReplyBuilder.build(initiative)
        self.assertEqual(first, second)

    def test_confidence(self):
        item = self.create(
            client_id="client-a", due_date=self.now.isoformat(),
        )
        reply = self.reply.ReplyBuilder.build(self.initiative_for(item))
        self.assertGreaterEqual(reply.confidence, 0.8)
        self.assertLessEqual(reply.confidence, 0.95)

    def test_action_selection(self):
        followup = self.create(
            object_type="followup_task", status="scheduled",
        )
        inactive = self.create(
            object_type="client", status="inactive", title="Client A",
        )
        self.assertEqual(
            self.reply.ReplyBuilder.build(
                self.initiative_for(followup, "follow_up_waiting")
            ).suggested_action,
            "FOLLOW_UP",
        )
        self.assertEqual(
            self.reply.ReplyBuilder.build(
                self.initiative_for(inactive, "inactive_client")
            ).suggested_action,
            "CHECK_IN",
        )

    def test_duplicate_prevention(self):
        item = self.create()
        initiative = self.initiative_for(item)
        queue = self.reply.build_reply_queue([initiative, initiative])
        self.assertEqual(len(queue), 1)

    def test_workspace_isolation(self):
        item = self.create(workspace="reply-b")
        initiative = self.initiative_for(item)
        forged = initiative.__class__(
            **{**initiative.as_dict(), "workspace_id": "reply-a"}
        )
        with self.assertRaisesRegex(ValueError, "not found"):
            self.reply.ReplyBuilder.build(forged)

    def test_empty_initiatives(self):
        self.assertEqual(self.reply.build_reply_queue([]), ())

    def test_dashboard_rendering_has_no_actions(self):
        response = self.web_app.app.test_client().get("/dashboard")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Reply Builder", body)
        self.assertIn("Nothing is sent or changed automatically.", body)
        self.assertNotIn(">Send<", body)

    def test_initiative_regression(self):
        item = self.create(
            due_date=(self.now - timedelta(days=1)).isoformat(),
        )
        initiatives = self.initiative.detect_initiatives(
            "reply-a", objects=[item], now=self.now,
        )
        self.assertEqual(initiatives[0].type, "overdue")

    def test_reminder_regression(self):
        self.create(object_type="reminder", status="active")
        initiatives = self.initiative.initiative_queue(
            "reply-a",
            objects=self.work.list_work_objects(workspace_id="reply-a"),
            now=self.now,
        )
        self.assertEqual(initiatives, ())


if __name__ == "__main__":
    unittest.main()
