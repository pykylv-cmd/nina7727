import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime_readiness import RuntimeReadiness


ROOT = Path(__file__).resolve().parent


class ReleaseConfigurationTests(unittest.TestCase):
    def test_railway_config_is_minimal_production_contract(self):
        config = json.loads((ROOT / "railway.json").read_text("utf-8"))
        self.assertEqual(config["build"]["builder"], "RAILPACK")
        deploy = config["deploy"]
        self.assertEqual(deploy["healthcheckPath"], "/ready")
        self.assertEqual(
            deploy["preDeployCommand"],
            [
                "python manage_migrations.py preflight",
            ],
        )
        command = json.loads(
            (ROOT / "railway.web.json").read_text("utf-8")
        )["deploy"]["startCommand"]
        self.assertIn("gunicorn web_app:app", command)
        self.assertIn("0.0.0.0:$PORT", command)
        self.assertNotIn("app.py", command)
        self.assertEqual(
            json.loads(
                (ROOT / "railway.core.json").read_text("utf-8")
            )["deploy"]["startCommand"],
            "python app.py",
        )

    def test_python_runtime_and_gunicorn_dependency_are_versioned(self):
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.12")
        requirements = {
            line.strip().lower()
            for line in (ROOT / "requirements.txt").read_text().splitlines()
        }
        self.assertIn("gunicorn", requirements)

    def test_wsgi_module_exports_flask_app_without_starting_server(self):
        import web_app
        self.assertEqual(web_app.app.import_name, "web_app")
        self.assertTrue(callable(web_app.app))

    def test_ready_initializes_runtime_for_wsgi_server(self):
        import web_app

        state = RuntimeReadiness("release-ready-test")
        state.register("required_web_capability", lambda: True)
        with (
            patch.object(web_app, "WEB_RUNTIME_READINESS", state),
            patch.object(web_app, "_WEB_RUNTIME_INITIALIZED", False),
        ):
            response = web_app.app.test_client().get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "ready": True,
                "runtime": "release-ready-test",
                "startup_started": True,
                "startup_completed": True,
                "checks": {"required_web_capability": True},
                "failure_class": "",
                "failure_component": "",
            },
        )


class SameOriginMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault(
            "NINA_WEB_WORKSPACE_COOKIE_SECRET", "r" * 64
        )
        import web_app
        cls.web_app = web_app

    def setUp(self):
        state = RuntimeReadiness("release-origin-test")
        state.begin_startup()
        state.run_checks()
        state.complete_startup()
        self.readiness = patch.object(
            self.web_app, "WEB_RUNTIME_READINESS", state
        )
        self.readiness.start()
        self.client = self.web_app.app.test_client()

    def tearDown(self):
        self.readiness.stop()

    def test_same_origin_cookie_api_mutation_passes_origin_gate(self):
        response = self.client.post(
            "/work-objects",
            json={},
            headers={
                "Origin": "http://localhost",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        self.assertNotEqual(response.status_code, 403)

    def test_cross_origin_cookie_api_mutation_is_rejected(self):
        response = self.client.post(
            "/work-objects",
            json={},
            headers={
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.get_json()["error"], "cross_origin_forbidden"
        )

    def test_get_is_not_blocked_by_origin_gate(self):
        with patch.object(
            self.web_app, "list_universal_work_objects", return_value=[]
        ):
            response = self.client.get(
                "/work-objects",
                headers={
                    "Origin": "https://attacker.example",
                    "Sec-Fetch-Site": "cross-site",
                },
            )
        self.assertNotEqual(response.status_code, 403)

    def test_token_authenticated_endpoint_is_not_cookie_csrf_gated(self):
        response = self.client.post(
            "/internal/runtime/compatibility",
            json={},
            headers={
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
