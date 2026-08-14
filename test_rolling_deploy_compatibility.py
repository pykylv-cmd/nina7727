import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet

import deployment_compatibility
import runtime_readiness


ROOT = Path(__file__).resolve().parent


class CompatibilityContractTests(unittest.TestCase):
    def test_compatible_old_and_new_runtime_contracts_become_ready(self):
        with patch.dict(
            os.environ, {"NINA_DATABASE_COMPATIBILITY_VERSION": "1"}, clear=False
        ):
            for version in ("web-old", "web-new"):
                state = runtime_readiness.RuntimeReadiness(version)
                contract = deployment_compatibility.DeploymentCompatibilityContract(
                    application_version=version,
                    service_role="secure-rebirth:web-core",
                )
                state.register("deployment_compatibility", contract.assert_compatible)
                state.begin_startup()
                state.run_checks()
                state.complete_startup()
                self.assertTrue(state.ready)

    def test_incompatible_database_version_stays_not_ready_explicitly(self):
        state = runtime_readiness.RuntimeReadiness("incompatible")
        contract = deployment_compatibility.DeploymentCompatibilityContract(
            application_version="web-current",
            service_role="secure-rebirth:web-core",
        )
        state.register("deployment_compatibility", contract.assert_compatible)
        state.begin_startup()
        with patch.dict(
            os.environ, {"NINA_DATABASE_COMPATIBILITY_VERSION": "2"}, clear=False
        ):
            with self.assertRaisesRegex(
                deployment_compatibility.DeploymentCompatibilityError,
                "nina_database_compatibility_unsupported",
            ):
                state.run_checks()
        self.assertFalse(state.ready)
        self.assertEqual(
            state.snapshot()["failure_class"], "DeploymentCompatibilityError"
        )

    def test_identity_contains_only_safe_version_metadata(self):
        with patch.dict(
            os.environ,
            {
                "NINA_DATABASE_COMPATIBILITY_VERSION": "1",
                "RAILWAY_GIT_COMMIT_SHA": "abcdef1234567890",
                "DATABASE_URL": "postgresql://secret:password@host/database",
            },
            clear=False,
        ):
            identity = deployment_compatibility.DeploymentCompatibilityContract(
                "web-current", "secure-rebirth:web-core"
            ).identity()
        self.assertEqual(identity["commit_identifier"], "abcdef1234567890")
        rendered = json.dumps(identity)
        for forbidden in ("postgresql://", "secret", "password"):
            self.assertNotIn(forbidden, rendered)


class RollingDatabaseInteropTests(unittest.TestCase):
    def _environment(self, db_file):
        env = dict(os.environ)
        env.update({
            "NINA_RUNTIME_ENV": "test",
            "NINA_DB_FILE": str(db_file),
            "NINA_DATABASE_COMPATIBILITY_VERSION": "1",
            "NINA_CONTACT_IDENTITY_KEY": "rolling-contact-key-at-least-32-bytes",
            "NINA_CHANNEL_CREDENTIAL_KEY": Fernet.generate_key().decode(),
            "NINA_WEB_WORKSPACE_ID": "rolling-workspace",
            "PYTHONPATH": os.pathsep.join(
                filter(None, [str(ROOT), env.get("PYTHONPATH", "")])
            ),
        })
        for name in (
            "DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRIVATE_URL",
            "POSTGRES_PUBLIC_URL", "DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL",
            "PGURL", "PG_URL", "RAILWAY_DATABASE_URL", "RAILWAY_POSTGRES_URL",
            "POSTGRES_CONNECTION_URL", "DATABASE_CONNECTION_URL",
        ):
            env.pop(name, None)
        return env

    def _run(self, code, env):
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_old_and_new_processes_read_each_others_additive_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._environment(Path(tmp) / "rolling.sqlite")
            old_write = """
from deployment_compatibility import DeploymentCompatibilityContract
from nina_message_service import save_channel_turn
DeploymentCompatibilityContract('web-old','secure-rebirth:web-core').assert_compatible()
save_channel_turn('rolling-workspace','old-user','old-nina',conversation_id='rolling:shared')
"""
            new_read_write = """
from deployment_compatibility import DeploymentCompatibilityContract
from nina_message_service import load_channel_conversation,save_channel_turn
DeploymentCompatibilityContract('web-new','secure-rebirth:web-core').assert_compatible()
assert [x['text'] for x in load_channel_conversation('rolling:shared')] == ['old-user','old-nina']
save_channel_turn('rolling-workspace','new-user','new-nina',conversation_id='rolling:shared')
"""
            old_read = """
from deployment_compatibility import DeploymentCompatibilityContract
from nina_message_service import load_channel_conversation
DeploymentCompatibilityContract('web-old','secure-rebirth:web-core').assert_compatible()
assert [x['text'] for x in load_channel_conversation('rolling:shared')] == ['old-user','old-nina','new-user','new-nina']
"""
            self._run(old_write, env)
            self._run(new_read_write, env)
            self._run(old_read, env)

    def test_internal_bridge_compatibility_is_authenticated_and_diagnosable(self):
        import web_app

        web_app.WEB_RUNTIME_READINESS.reset()
        web_app._WEB_RUNTIME_INITIALIZED = False
        client = web_app.app.test_client()
        unauthorized = client.post("/internal/runtime/compatibility", json={})
        self.assertEqual(unauthorized.status_code, 401)

        with patch.object(web_app, "authorize_bridge", return_value=True):
            response = client.post(
                "/internal/runtime/compatibility",
                headers={"Authorization": "Bearer test"},
                json={},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            payload["runtime"]["internal_api_compatibility_version"], 1
        )
        self.assertEqual(
            payload["bridge_requirement"]["internal_api_compatibility_version"], 1
        )

        bridge_source = (
            ROOT / "personal_whatsapp_bridge" / "src" / "server.js"
        ).read_text(encoding="utf-8")
        self.assertIn("'/v1/compatibility'", bridge_source)
        self.assertIn("internal_api_compatibility_version:1", bridge_source)


if __name__ == "__main__":
    unittest.main()
