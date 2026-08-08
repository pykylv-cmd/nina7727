import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_DB_DIR = tempfile.TemporaryDirectory()
os.environ["NINA_DB_FILE"] = str(Path(_DB_DIR.name) / "controlled-release.sqlite")
os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "release-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "release-admin-token-at-least-32")

import developer_control
import nina_developer_agent
import web_app


def result(stdout="", returncode=0, stderr=""):
    return type("Result", (), {"returncode": returncode, "stdout": stdout, "stderr": stderr})()


class DeveloperControlledReleaseTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        developer_control.ensure_schema()
        conn = developer_control._connect()
        try:
            conn.execute("DELETE FROM nina_developer_jobs")
            conn.execute("DELETE FROM nina_developer_events")
            conn.execute("DELETE FROM nina_developer_agents")
            conn.commit()
        finally:
            conn.close()
        self.diff = "--- a/web_app.py\n+++ b/web_app.py\n@@ -1 +1 @@\n-old\n+new\n"
        self.diff_hash = hashlib.sha256(self.diff.encode()).hexdigest()
        self.patch_job_id = self._ready_patch()

    def _ready_patch(self, quality="APPROVE FOR OWNER REVIEW", files=None):
        files = files or ["web_app.py", "test_admin_developer_console.py"]
        job_id = "devjob_patch_" + os.urandom(5).hex()
        args = {"lesson_context": {"quality_verdict": quality}}
        output = {"write_executed": True, "applied_files": files,
                  "validation": {"git_diff": self.diff, "checks": [{"returncode": 0}]}}
        conn = developer_control._connect()
        try:
            conn.execute(developer_control._sql(
                "INSERT INTO nina_developer_jobs (job_id,operation,arguments_json,status,result_json,error_code,created_at,claimed_at,completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"),
                (job_id, "apply_approved_patch", json.dumps(args), "completed", json.dumps(output), "",
                 developer_control._iso(), "", developer_control._iso()))
            conn.commit()
        finally:
            conn.close()
        return job_id

    def _approve(self, job_id=None, digest=None, branch=developer_control.RELEASE_BRANCH,
                 services=("web",)):
        return developer_control.create_approved_release_job(
            job_id or self.patch_job_id, digest or self.diff_hash, branch, services,
            owner_identity="owner-test",
        )

    def test_owner_only_release_route(self):
        response = web_app.app.test_client().post("/admin/developer", data={"action": "approve_release"})
        self.assertEqual(response.status_code, 403)

    def test_authenticated_owner_creates_one_time_release(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        response = client.post("/admin/developer", data={
            "action": "approve_release", "source_patch_job_id": self.patch_job_id,
            "release_hash": self.diff_hash, "target_services": "web",
            "csrf_token": web_app._channel_csrf("developer:release"),
        })
        self.assertEqual(response.status_code, 302)
        releases = [job for job in developer_control.list_jobs(10)
                    if job["operation"] == "execute_approved_release"]
        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0]["arguments"]["owner_identity"], "platform_admin_session")

    def test_exact_diff_hash_and_changed_diff_rejected(self):
        with self.assertRaisesRegex(ValueError, "developer_release_diff_changed"):
            self._approve(digest="0" * 64)

    def test_replay_and_wrong_branch_rejected(self):
        self._approve()
        with self.assertRaisesRegex(ValueError, "developer_release_replayed"):
            self._approve()
        other = self._ready_patch()
        with self.assertRaisesRegex(ValueError, "developer_release_branch_not_allowed"):
            self._approve(other, branch="main")

    def test_quality_block_prevents_release(self):
        blocked = self._ready_patch(quality="BLOCK")
        with self.assertRaisesRegex(ValueError, "developer_release_quality_not_approved"):
            self._approve(blocked)

    def test_target_service_selection(self):
        self.assertEqual(developer_control.select_release_services(["web_app.py", "test_x.py"]), ["web"])
        self.assertEqual(developer_control.select_release_services(["app.py"]), ["core"])
        self.assertEqual(developer_control.select_release_services(["nina_message_service.py"]), ["core", "web"])
        with self.assertRaisesRegex(ValueError, "developer_release_services_changed"):
            self._approve(services=("core",))

    def test_unauthorized_file_and_wrong_branch_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "web_app.py").write_text("new\n", encoding="utf-8")
            agent = nina_developer_agent.ReadOnlyDeveloperAgent(root)
            args = self._agent_args()
            with patch.object(agent, "_run_fixed", return_value=result("## main\n")):
                with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "release_wrong_branch"):
                    agent.execute("execute_approved_release", args)
            outputs = [result("## feature/web-chat-v1\n"), result("web_app.py\nother.py\n")]
            with patch.object(agent, "_run_fixed", side_effect=outputs):
                with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "release_unauthorized_files"):
                    agent.execute("execute_approved_release", args)

    def _agent_args(self):
        return {
            "release_id": "devrelease_test", "branch": "feature/web-chat-v1",
            "affected_files": ["web_app.py"], "target_services": ["web"],
            "quality_verdict": "APPROVE FOR OWNER REVIEW", "content_hash": self.diff_hash,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "commit_message": "Safe test", "live_verification": "developer_console_safety",
        }

    def test_allowlisted_git_release_and_health_live_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "web_app.py").write_text("new\n", encoding="utf-8")
            agent = nina_developer_agent.ReadOnlyDeveloperAgent(root)
            commands = [
                result("## feature/web-chat-v1\n M web_app.py\n"), result("web_app.py\n"),
                result(self.diff), result(), result("[feature/web-chat-v1 abc1234] Safe test\n"),
                result("## feature/web-chat-v1 [ahead 1]\n"), result(),
            ]
            proof = {"ok": True, "developer_agent": "connected", "repository": "connected",
                     "write_access": "disabled", "deploy_access": "disabled"}
            health = {"status": "ok", "deployment_compatibility": True}
            with patch.object(agent, "_run_fixed", side_effect=commands) as run, \
                 patch.object(agent, "_read_json_url", side_effect=[(200, health)] * 3 + [(200, proof)]), \
                 patch.dict(os.environ, {"NINA_DEVELOPER_WEB_URL": "https://web.example",
                                         "NINA_DEVELOPER_AGENT_TOKEN": "token"}):
                output = agent.execute("execute_approved_release", self._agent_args())
            self.assertEqual(output["stages"]["live_verify"], "pass")
            invoked = [call.args[0] for call in run.call_args_list]
            self.assertIn(["git", "add", "--", "web_app.py"], invoked)
            self.assertIn(["git", "push", "origin", "feature/web-chat-v1"], invoked)
            flattened = " ".join(" ".join(command) for command in invoked)
            for forbidden in ("reset", "rebase", "checkout", " pull "):
                self.assertNotIn(forbidden, " " + flattened + " ")

    def test_release_failure_is_reported_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "web_app.py").write_text("new\n", encoding="utf-8")
            agent = nina_developer_agent.ReadOnlyDeveloperAgent(root)
            commands = [result("## feature/web-chat-v1\n"), result("web_app.py\n"), result(self.diff),
                        result(), result("[feature/web-chat-v1 abc1234] Safe test\n"), result(), result()]
            with patch.object(agent, "_run_fixed", side_effect=commands), \
                 patch.object(agent, "_read_json_url", return_value=(503, {})), \
                 patch("nina_developer_agent.time.sleep"), \
                 patch.dict(os.environ, {"NINA_DEVELOPER_WEB_URL": "https://web.example"}):
                output = agent.execute("execute_approved_release", self._agent_args())
            self.assertEqual(output["failed_stage"], "health")
            self.assertNotEqual(output["stages"]["live_verify"], "pass")

    def test_no_public_channel_or_generic_shell_release(self):
        agent = nina_developer_agent.ReadOnlyDeveloperAgent(Path.cwd())
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
            agent.execute("shell", {"command": "git push"})
        self.assertNotIn("approve_release", web_app._developer_command("approve release"))

    def test_internal_live_verification_requires_agent_auth(self):
        response = web_app.app.test_client().get("/internal/developer-release/verify")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
