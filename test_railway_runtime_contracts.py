import ast
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent


class RailwayRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
        cls.web = json.loads((ROOT / "railway.web.json").read_text(encoding="utf-8"))
        cls.core = json.loads((ROOT / "railway.core.json").read_text(encoding="utf-8"))
        cls.app_tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))

    def test_service_configs_override_shared_start_command(self):
        self.assertNotEqual(
            self.web["deploy"]["startCommand"],
            self.core["deploy"]["startCommand"],
        )

    def test_web_runtime_contract_starts_only_gunicorn(self):
        command = self.web["deploy"]["startCommand"]
        self.assertIn("gunicorn web_app:app", command)
        self.assertNotIn("python app.py", command)

    def test_core_runtime_contract_starts_app_with_one_replica(self):
        self.assertEqual(self.core["deploy"]["startCommand"], "python app.py")
        self.assertEqual(self.core["deploy"]["healthcheckPath"], "/")

    def test_core_post_init_uses_guarded_scheduler_start(self):
        post_init = next(
            node for node in self.app_tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "post_init"
        )
        calls = {
            ast.unparse(node.func)
            for node in ast.walk(post_init)
            if isinstance(node, ast.Call)
        }
        self.assertIn("start_active_reminder_scheduler", calls)
        self.assertNotIn("active_work_object_reminder_worker", calls)

    def test_core_application_registers_shutdown_hook(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn(".post_shutdown(post_shutdown)", source)

    def test_web_module_does_not_import_or_start_scheduler(self):
        source = (ROOT / "web_app.py").read_text(encoding="utf-8")
        self.assertNotIn("active_work_object_reminder_worker", source)
        self.assertNotIn("start_active_reminder_scheduler", source)

    def test_web_reminder_actions_are_bound_at_module_scope(self):
        import web_app
        self.assertTrue(callable(web_app.snooze_reminder))
        self.assertTrue(callable(web_app.complete_reminder))


class SchedulerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.env_patch = patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "TELEGRAM_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                "NINA_RUNTIME_ENV": "test",
                "NINA_DB_FILE": str(Path(cls.temp_dir.name) / "runtime.sqlite"),
            },
        )
        cls.env_patch.start()
        import app
        cls.app_module = app

    @classmethod
    def tearDownClass(cls):
        cls.env_patch.stop()
        cls.temp_dir.cleanup()

    async def asyncSetUp(self):
        self.app = self.app_module
        self.app.ACTIVE_REMINDER_SCHEDULER_TASK = None

    async def asyncTearDown(self):
        await self.app.stop_active_reminder_scheduler()

    async def test_start_guard_returns_the_existing_scheduler_task(self):
        started = asyncio.Event()

        async def worker(application):
            started.set()
            await asyncio.Event().wait()

        with patch.object(
            self.app, "active_work_object_reminder_worker", side_effect=worker
        ):
            first = self.app.start_active_reminder_scheduler(object())
            second = self.app.start_active_reminder_scheduler(object())
            await started.wait()
            self.assertIs(first, second)
            self.assertFalse(first.done())

    async def test_shutdown_cancels_and_clears_scheduler_task(self):
        async def worker(application):
            await asyncio.Event().wait()

        with patch.object(
            self.app, "active_work_object_reminder_worker", side_effect=worker
        ):
            task = self.app.start_active_reminder_scheduler(object())
            await asyncio.sleep(0)
            await self.app.stop_active_reminder_scheduler()
            self.assertTrue(task.cancelled())
            self.assertIsNone(self.app.ACTIVE_REMINDER_SCHEDULER_TASK)


if __name__ == "__main__":
    unittest.main()
