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


class InitiativeEngineV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "initiative.db")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import work_objects
        import initiative_engine
        import web_app

        cls.work = work_objects
        cls.engine = initiative_engine
        cls.web_app = web_app
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

    def create(self, workspace="initiative-a", **values):
        defaults = {
            "object_type": "task", "title": "Initiative test",
            "workspace_id": workspace, "status": "open",
        }
        defaults.update(values)
        return self.work.create_work_object(**defaults)

    def queue(self, workspace="initiative-a"):
        objects = self.work.list_work_objects(workspace_id=workspace)
        return self.engine.initiative_queue(
            workspace, objects=objects, now=self.now,
        )

    def test_overdue_detection(self):
        item = self.create(
            due_date=(self.now - timedelta(days=2)).isoformat(),
            priority="high",
        )
        candidates = self.queue()
        self.assertEqual(candidates[0].type, "overdue")
        self.assertEqual(candidates[0].work_object_id, item.object_id)

    def test_priority_ordering(self):
        self.create(
            title="Normal", priority="normal",
            due_date=(self.now - timedelta(days=1)).isoformat(),
        )
        urgent = self.create(
            title="Urgent", priority="urgent",
            due_date=(self.now - timedelta(days=1)).isoformat(),
        )
        self.assertEqual(self.queue()[0].work_object_id, urgent.object_id)

    def test_duplicate_prevention(self):
        item = self.create(
            object_type="followup_task", status="scheduled",
            due_date=(self.now - timedelta(days=1)).isoformat(),
        )
        candidates = self.engine.detect_initiatives(
            "initiative-a", objects=[item, item], now=self.now,
        )
        self.assertEqual(len({candidate.initiative_id for candidate in candidates}), 2)
        self.assertEqual(len(candidates), 2)

    def test_workspace_isolation(self):
        foreign = self.create(
            workspace="initiative-b",
            due_date=(self.now - timedelta(days=1)).isoformat(),
        )
        candidates = self.engine.detect_initiatives(
            "initiative-a", objects=[foreign], now=self.now,
        )
        self.assertEqual(candidates, ())

    def test_deterministic_scoring(self):
        item = self.create(
            priority="high",
            due_date=(self.now - timedelta(days=3)).isoformat(),
            metadata={"initiative_priority": 4, "relationship_value": 8},
        )
        first = self.engine.initiative_score(item, "overdue", now=self.now)
        second = self.engine.initiative_score(item, "overdue", now=self.now)
        self.assertEqual(first, second)

    def test_empty_queue(self):
        self.assertEqual(self.queue(), ())

    def test_dashboard_rendering_is_read_only(self):
        response = self.web_app.app.test_client().get("/dashboard")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Initiative", body)
        self.assertIn("No action is taken automatically.", body)

    def test_reminder_regression_not_detected_without_signal(self):
        self.create(object_type="reminder", status="active")
        self.assertEqual(self.queue(), ())

    def test_planner_regression_projection_unchanged(self):
        item = self.create(
            priority="high", due_date=self.now.isoformat(),
        )
        from daily_planner import canonical_daily_work

        planned = canonical_daily_work("initiative-a")
        self.assertIn(item.object_id, [entry.work_object_id for entry in planned])


if __name__ == "__main__":
    unittest.main()
