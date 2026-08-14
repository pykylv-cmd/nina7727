import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TEST_DIR = tempfile.TemporaryDirectory()
os.environ["NINA_DB_FILE"] = str(Path(_TEST_DIR.name) / "developer.sqlite")
os.environ["NINA_WEB_WORKSPACE_COOKIE_SECRET"] = "developer-test-cookie-secret-at-least-32"
os.environ["NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN"] = "developer-test-admin-token-at-least-32"
os.environ["NINA_DEVELOPER_AGENT_TOKEN"] = "developer-agent-test-token-at-least-32"

import developer_control
import nina_developer_agent
import web_app


class DeveloperReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)
        cls.fixture = tempfile.TemporaryDirectory()
        root = Path(cls.fixture.name)
        (root / "src").mkdir()
        (root / "README.md").write_text("NinaOS fixture\n", encoding="utf-8")
        (root / "src" / "service.py").write_text(
            "def send_message_to_nina():\n    return True\n", encoding="utf-8"
        )
        (root / ".env").write_text("SECRET=value", encoding="utf-8")
        cls.agent = nina_developer_agent.ReadOnlyDeveloperAgent(root)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()
        _TEST_DIR.cleanup()

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        return client

    def auth(self, valid=True):
        token = os.environ["NINA_DEVELOPER_AGENT_TOKEN"] if valid else "wrong"
        return {"Authorization": "Bearer " + token}

    def test_unauthorized_agent_request_rejected(self):
        response = web_app.app.test_client().post("/internal/developer-agent/heartbeat", json={})
        self.assertEqual(response.status_code, 401)

    def test_valid_agent_authentication_accepted(self):
        response = web_app.app.test_client().post(
            "/internal/developer-agent/heartbeat", json={"repository": "nina7727"}, headers=self.auth()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(developer_control.connection_status()["agent"], "connected")

    def test_path_traversal_blocked(self):
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "path_outside_repository"):
            self.agent.execute("read_text_file", {"path": "../outside.txt"})

    def test_blocked_secret_file_rejected(self):
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "blocked_sensitive_path"):
            self.agent.execute("read_text_file", {"path": ".env"})

    def test_list_root_returns_real_fixture_data(self):
        result = self.agent.execute("list_root")
        names = {entry["name"] for entry in result["entries"]}
        self.assertIn("README.md", names)
        self.assertIn("src", names)
        self.assertNotIn(".env", names)

    def test_search_text_returns_file_and_line(self):
        result = self.agent.execute("search_text", {"query": "send_message_to_nina"})
        self.assertEqual(result["matches"][0]["path"], str(Path("src") / "service.py"))
        self.assertEqual(result["matches"][0]["line"], 1)

    def test_git_status_uses_only_fixed_allowlisted_invocation(self):
        completed = type("Result", (), {"returncode": 0, "stdout": "## main\n"})()
        with patch("nina_developer_agent.subprocess.run", return_value=completed) as run:
            result = self.agent.execute("git_status")
        self.assertEqual(result["status"], "## main\n")
        self.assertEqual(run.call_args.args[0][0], "git")
        self.assertEqual(run.call_args.args[0][1], "-C")
        self.assertEqual(run.call_args.args[0][3:], ["status", "--short", "--branch"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_write_operation_rejected(self):
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
            self.agent.execute("write_text_file", {"path": "README.md", "text": "changed"})

    def test_arbitrary_shell_rejected(self):
        with patch("nina_developer_agent.subprocess.run") as run:
            with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
                self.agent.execute("shell", {"command": "whoami"})
        run.assert_not_called()

    def test_developer_console_disconnected_state_is_safe(self):
        conn = developer_control._connect()
        try:
            conn.execute("DELETE FROM nina_developer_agents")
            conn.commit()
        finally:
            conn.close()
        page = self.admin_client().get("/admin/developer?lang=en").get_data(as_text=True)
        self.assertIn("Local Developer Agent", page)
        self.assertIn("Not connected", page)
        self.assertIn("Write Access", page)
        self.assertIn("Disabled", page)

    def test_outbound_job_handshake_and_structured_result(self):
        client = web_app.app.test_client()
        client.post("/internal/developer-agent/heartbeat", json={}, headers=self.auth())
        job_id = developer_control.create_job("list_root", {})
        claimed = client.post("/internal/developer-agent/jobs/claim", json={}, headers=self.auth()).get_json()["job"]
        self.assertEqual(claimed["job_id"], job_id)
        result = self.agent.execute(claimed["operation"], claimed["arguments"])
        completed = client.post("/internal/developer-agent/jobs/result",
                                json={"job_id": job_id, "result": result}, headers=self.auth())
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(developer_control.list_jobs(1)[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
