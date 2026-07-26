import unittest
from unittest.mock import patch

import runtime_readiness


class RuntimeReadinessUnitTests(unittest.TestCase):
    def test_healthy_startup_becomes_ready(self):
        state = runtime_readiness.RuntimeReadiness("healthy")
        state.register("database", lambda: True)
        state.register("module", lambda: {"ok": True})
        state.begin_startup()
        self.assertTrue(state.run_checks())
        state.complete_startup()
        self.assertTrue(state.ready)
        self.assertTrue(state.snapshot()["startup_completed"])

    def test_missing_database_remains_not_ready(self):
        state = runtime_readiness.RuntimeReadiness("missing-db")
        state.register("database", lambda: {"ok": False})
        state.begin_startup()
        with self.assertRaises(RuntimeError):
            state.run_checks()
        self.assertFalse(state.ready)
        self.assertFalse(state.snapshot()["checks"]["database"])

    def test_missing_mandatory_module_remains_not_ready(self):
        state = runtime_readiness.RuntimeReadiness("missing-module")
        state.register("module", lambda: False)
        state.begin_startup()
        with self.assertRaises(RuntimeError):
            state.run_checks()
        self.assertFalse(state.ready)

    def test_startup_exception_remains_not_ready(self):
        state = runtime_readiness.RuntimeReadiness("exception")
        state.register("startup", lambda: (_ for _ in ()).throw(ValueError("failed")))
        state.begin_startup()
        with self.assertRaises(ValueError):
            state.run_checks()
        self.assertFalse(state.ready)
        self.assertEqual(state.snapshot()["failure_class"], "ValueError")


class WebReadinessGateTests(unittest.TestCase):
    def setUp(self):
        import web_app
        self.web_app = web_app
        self.client = web_app.app.test_client()

    def test_liveness_is_separate_from_readiness(self):
        self.web_app.WEB_RUNTIME_READINESS.reset()
        self.web_app._WEB_RUNTIME_INITIALIZED = False
        live = self.client.get("/live")
        ready = self.client.get("/ready")
        self.assertEqual(live.status_code, 200)
        self.assertTrue(live.get_json()["alive"])
        self.assertEqual(ready.status_code, 503)
        self.assertFalse(ready.get_json()["ready"])

    def test_failed_startup_blocks_customer_request(self):
        self.web_app.WEB_RUNTIME_READINESS.reset()
        self.web_app._WEB_RUNTIME_INITIALIZED = False
        with patch.object(
            self.web_app, "initialize_web_runtime", side_effect=RuntimeError("failed")
        ):
            response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "runtime_not_ready")

    def test_healthy_web_startup_reports_ready(self):
        state = runtime_readiness.RuntimeReadiness("web-test")
        for name in (
            "persistence_backend", "work_objects", "contact_identity",
            "message_service", "channel_services",
        ):
            state.register(name, lambda: True)
        with patch.object(self.web_app, "WEB_RUNTIME_READINESS", state):
            self.web_app._WEB_RUNTIME_INITIALIZED = False
            try:
                self.assertTrue(self.web_app.initialize_web_runtime())
                response = self.client.get("/ready")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()["ready"])
            finally:
                self.web_app._WEB_RUNTIME_INITIALIZED = False


if __name__ == "__main__":
    unittest.main()
