import os
import tempfile
import unittest
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class NaturalWorkRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "routing.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()

        import work_objects
        import work_engine
        import web_app

        cls.work_objects = work_objects
        cls.work_engine = work_engine
        cls.web_app = web_app
        cls.original_work_db = (
            work_objects.DATABASE_URL,
            work_objects.DB_FILE,
            work_objects.USE_POSTGRES,
        )
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        cls.restore_database = bind_sqlite_database(cls.db_file, work_objects)
        initialize_ready_web(web_app)

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        (
            cls.work_objects.DATABASE_URL,
            cls.work_objects.DB_FILE,
            cls.work_objects.USE_POSTGRES,
        ) = cls.original_work_db
        cls.work_objects._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work_objects.ensure_work_objects_schema()
        connection = self.work_objects._connect()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM nina_work_objects")
        connection.commit()
        cursor.close()
        connection.close()

    def _assert_task(self, text, expected_title, due_date=""):
        result = self.work_engine.execute_natural_work_request(
            text, workspace_id="demo_small_business", channel="web"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "create_task")
        objects = self.work_objects.list_work_objects(workspace_id="demo_small_business")
        self.assertEqual(len(objects), 1)
        task = objects[0]
        self.assertEqual(task.object_type, "task")
        self.assertIn(expected_title, task.title)
        self.assertEqual(task.due_date, due_date)
        self.assertEqual(task.origin_channel, "web")
        self.assertFalse(any(obj.object_type == "estimate" for obj in objects))
        return task

    def test_latvian_task_precedes_offer_noun(self):
        task = self._assert_task(
            "Izveido uzdevumu: rīt piezvanīt Jānim par piedāvājumu.",
            "piezvanīt Jānim par piedāvājumu",
            "tomorrow",
        )
        response = self.web_app.app.test_client().get("/tasks?lang=lv")
        self.assertEqual(response.status_code, 200)
        self.assertIn(task.title, response.get_data(as_text=True))

    def test_latvian_create_offer_as_task(self):
        self._assert_task(
            "Izveido uzdevumu sagatavot piedāvājumu Jānim.",
            "sagatavot piedāvājumu Jānim",
        )

    def test_tasks_get_does_not_seed_or_duplicate_canonical_work(self):
        task = self._assert_task(
            "Create a task: preserve canonical work during rendering.",
            "preserve canonical work during rendering",
        )
        before = self.work_objects.list_work_objects(workspace_id="demo_small_business")
        before_ids = sorted(obj.object_id for obj in before)

        response = self.web_app.app.test_client().get("/tasks?lang=en")

        after = self.work_objects.list_work_objects(workspace_id="demo_small_business")
        after_ids = sorted(obj.object_id for obj in after)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(after), len(before))
        self.assertEqual(after_ids, before_ids)
        self.assertIn(task.title, response.get_data(as_text=True))
        self.assertFalse(any((obj.source_key or "").startswith("demo:") for obj in after))

    def test_latvian_reminder_precedes_offer_noun(self):
        self._assert_task(
            "Atgādini rīt piezvanīt Jānim par piedāvājumu.",
            "piezvanīt Jānim par piedāvājumu",
            "tomorrow",
        )

    def test_english_task_precedes_offer_noun(self):
        self._assert_task(
            "Create a task: call John tomorrow about the offer.",
            "call John tomorrow about the offer",
            "tomorrow",
        )

    def test_english_reminder_precedes_offer_noun(self):
        self._assert_task(
            "Remind me to call John tomorrow about the offer.",
            "call John tomorrow about the offer",
            "tomorrow",
        )

    def test_russian_task_precedes_offer_noun(self):
        self._assert_task(
            "Создай задачу: завтра позвонить Янису по предложению.",
            "позвонить Янису по предложению",
            "tomorrow",
        )

    def test_russian_reminder_precedes_offer_noun(self):
        self._assert_task(
            "Напомни завтра позвонить Янису по предложению.",
            "позвонить Янису по предложению",
            "tomorrow",
        )

    def test_direct_offer_still_uses_estimate_resolution(self):
        with patch.object(self.work_engine, "_production_estimates", return_value=[]):
            result = self.work_engine.execute_natural_work_request(
                "Sagatavo piedāvājumu Jānim.",
                workspace_id="demo_small_business",
                channel="web",
            )
        self.assertTrue(result["handled"])
        self.assertEqual(result["error"], "estimate_not_resolved")
        self.assertEqual(
            self.work_objects.list_work_objects(workspace_id="demo_small_business"), []
        )


if __name__ == "__main__":
    unittest.main()
