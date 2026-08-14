import hashlib
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_DB_DIR = tempfile.TemporaryDirectory()
os.environ["NINA_DB_FILE"] = str(Path(_DB_DIR.name) / "controlled-write.sqlite")
os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "controlled-write-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "controlled-write-admin-token-at-least-32")

import developer_control
import nina_developer_agent
import web_app


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OneTimeFailingWriteAgent(nina_developer_agent.ReadOnlyDeveloperAgent):
    def __init__(self, root, fail_path):
        super().__init__(root)
        self.fail_path = str(fail_path)
        self.failed = False

    def _atomic_write(self, path, text):
        if str(path).endswith(self.fail_path) and not self.failed:
            self.failed = True
            raise OSError("controlled_write_failure")
        return super()._atomic_write(path, text)


class DeveloperControlledWriteTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.fixture = tempfile.TemporaryDirectory()
        self.root = Path(self.fixture.name)
        (self.root / "app.py").write_text('VALUE = "old"\n', encoding="utf-8")
        (self.root / "other.py").write_text('OTHER = "old"\n', encoding="utf-8")
        (self.root / ".env").write_text("SECRET=value\n", encoding="utf-8")
        self.agent = nina_developer_agent.ReadOnlyDeveloperAgent(self.root)
        self.patch_text = "\n".join((
            "--- a/app.py", "+++ b/app.py", "@@ -1,1 +1,1 @@",
            '-VALUE = "old"', '+VALUE = "new"',
        ))
        self.args = self.arguments(self.patch_text, ["app.py"])
        developer_control.ensure_schema()
        conn = developer_control._connect()
        try:
            conn.execute("DELETE FROM nina_developer_jobs")
            conn.execute("DELETE FROM nina_developer_events")
            conn.execute("DELETE FROM nina_developer_agents")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        self.fixture.cleanup()

    def arguments(self, patch_text, files, hashes=None, expires=None, validation=None):
        hashes = hashes or {path: file_sha(self.root / path) for path in files}
        return {
            "approval_id": "devapproval_test",
            "diff_hash": sha(patch_text),
            "patch": patch_text,
            "affected_files": files,
            "expected_source_hashes": hashes,
            "expires_at": (expires or datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "validation": validation or {"py_compile": [], "pytest": []},
        }

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        return client

    def test_owner_only_approval(self):
        anonymous = web_app.app.test_client().post("/admin/developer", data={"action": "approve_diff"})
        self.assertEqual(anonymous.status_code, 403)

    def test_authenticated_owner_can_approve_exact_preview(self):
        investigation = {
            "status": "completed",
            "arguments": {"investigation_id": "devinvest_owner",
                          "investigation_kind": "developer_status_diff_preview"},
        }
        proposal = {
            "developer_analysis": {
                "architecture_boundary": "Owner-authenticated Developer capability",
            },
            "proposed_change": {
                "diff": self.patch_text, "files": ["app.py"],
                "risk": "LOW",
                "focused_tests": ["exact approved diff", "owner-only approval"],
                "expected_source_hashes": {"app.py": file_sha(self.root / "app.py")},
                "validation": {"py_compile": ["app.py"], "pytest": []},
            },
            "evidence": [{
                "role": "fixture", "path": "app.py", "line": 1,
                "source_hash": file_sha(self.root / "app.py"),
            }],
        }
        with patch.object(web_app, "list_developer_jobs", return_value=[investigation]), \
             patch.object(web_app, "_developer_investigation_answer", return_value=proposal), \
             patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_approval_job") as create:
            response = self.admin_client().post(
                "/admin/developer",
                data={"action": "approve_diff", "investigation_id": "devinvest_owner",
                      "diff_hash": sha(self.patch_text),
                      "csrf_token": web_app._channel_csrf("developer:approve")},
            )
        self.assertEqual(response.status_code, 302)
        create.assert_called_once()

    def test_exact_diff_hash_required(self):
        with self.assertRaisesRegex(ValueError, "developer_diff_hash_changed"):
            developer_control.create_approved_patch_job(
                "devinvest_test", self.patch_text, "0" * 64, ["app.py"],
                {"app.py": file_sha(self.root / "app.py")}, {},
            )

    def test_stale_source_hash_rejected(self):
        args = dict(self.args)
        args["expected_source_hashes"] = {"app.py": "0" * 64}
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "stale_source_hash"):
            self.agent.execute("apply_approved_patch", args)
        self.assertIn('"old"', (self.root / "app.py").read_text(encoding="utf-8"))

    def test_changed_diff_rejected(self):
        args = dict(self.args)
        args["patch"] += "\n"
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "approved_diff_changed"):
            self.agent.execute("apply_approved_patch", args)

    def test_replayed_approval_rejected(self):
        hashes = {"app.py": file_sha(self.root / "app.py")}
        developer_control.create_approved_patch_job(
            "devinvest_replay", self.patch_text, sha(self.patch_text), ["app.py"], hashes, {})
        with self.assertRaisesRegex(ValueError, "developer_approval_replayed"):
            developer_control.create_approved_patch_job(
                "devinvest_replay", self.patch_text, sha(self.patch_text), ["app.py"], hashes, {})

    def test_expired_approval_rejected(self):
        args = self.arguments(self.patch_text, ["app.py"],
                              expires=datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "approval_expired"):
            self.agent.execute("apply_approved_patch", args)

    def test_path_traversal_blocked(self):
        patch_text = "\n".join(("--- a/../outside.py", "+++ b/../outside.py", "@@ -1,1 +1,1 @@", "-x", "+y"))
        args = self.arguments(patch_text, ["../outside.py"], {"../outside.py": sha("")})
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "path_outside_repository"):
            self.agent.execute("apply_approved_patch", args)

    def test_secret_file_blocked(self):
        patch_text = "\n".join(("--- a/.env", "+++ b/.env", "@@ -1,1 +1,1 @@", "-SECRET=value", "+SECRET=changed"))
        args = self.arguments(patch_text, [".env"])
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "blocked_sensitive_path"):
            self.agent.execute("apply_approved_patch", args)

    def test_write_outside_approved_files_blocked(self):
        args = dict(self.args)
        args["affected_files"] = ["other.py"]
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "approved_paths_changed"):
            self.agent.execute("apply_approved_patch", args)

    def test_partial_write_failure_rolls_back(self):
        patch_text = "\n".join((
            "--- a/app.py", "+++ b/app.py", "@@ -1,1 +1,1 @@", '-VALUE = "old"', '+VALUE = "new"',
            "--- a/other.py", "+++ b/other.py", "@@ -1,1 +1,1 @@", '-OTHER = "old"', '+OTHER = "new"',
        ))
        args = self.arguments(patch_text, ["app.py", "other.py"])
        agent = OneTimeFailingWriteAgent(self.root, "other.py")
        with self.assertRaises(OSError):
            agent.execute("apply_approved_patch", args)
        self.assertEqual((self.root / "app.py").read_text(encoding="utf-8"), 'VALUE = "old"\n')
        self.assertEqual((self.root / "other.py").read_text(encoding="utf-8"), 'OTHER = "old"\n')

    def test_validation_failure_rolls_back(self):
        with patch.object(self.agent, "_validate_approved_change",
                          side_effect=nina_developer_agent.DeveloperAgentError("focused_validation_failed")):
            with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "focused_validation_failed"):
                self.agent.execute("apply_approved_patch", self.args)
        self.assertEqual((self.root / "app.py").read_text(encoding="utf-8"), 'VALUE = "old"\n')

    def test_successful_patch_remains_local(self):
        with patch.object(self.agent, "_validate_approved_change", return_value={"checks": []}):
            result = self.agent.execute("apply_approved_patch", self.args)
        self.assertEqual((self.root / "app.py").read_text(encoding="utf-8"), 'VALUE = "new"\n')
        self.assertTrue(result["write_executed"])

    def test_py_compile_allowlist_only(self):
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "py_compile_not_allowlisted"):
            self.agent._validate_approved_change({"py_compile": ["other.py"]}, ["app.py"])

    def test_pytest_allowlist_only(self):
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "pytest_not_allowlisted"):
            self.agent._validate_approved_change({"pytest": ["app.py"]}, ["app.py"])

    def test_arbitrary_shell_rejected(self):
        with patch("nina_developer_agent.subprocess.run") as run:
            with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
                self.agent.execute("shell", {"command": "whoami"})
        run.assert_not_called()

    def test_git_diff_and_status_are_read_only(self):
        completed = type("Result", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""})()
        with patch.object(self.agent, "_run_fixed", return_value=completed) as run:
            result = self.agent._validate_approved_change({}, ["app.py"])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(["git", "diff", "--check", "--", "app.py"], commands)
        self.assertIn(["git", "diff", "--", "app.py"], commands)
        self.assertIn(["git", "status", "--short"], commands)
        self.assertEqual(result["git_status"], "ok\n")

    def test_write_access_returns_disabled_after_success(self):
        hashes = {"app.py": file_sha(self.root / "app.py")}
        approval = developer_control.create_approved_patch_job(
            "devinvest_success", self.patch_text, sha(self.patch_text), ["app.py"], hashes, {})
        self.assertEqual(developer_control.write_access_status(), "one_time_approved")
        job = developer_control.claim_job()
        developer_control.complete_job(job["job_id"], {"ok": True})
        self.assertEqual(job["job_id"], approval["job_id"])
        self.assertEqual(developer_control.write_access_status(), "disabled")

    def test_write_access_returns_disabled_after_failure(self):
        hashes = {"app.py": file_sha(self.root / "app.py")}
        developer_control.create_approved_patch_job(
            "devinvest_failure", self.patch_text, sha(self.patch_text), ["app.py"], hashes, {})
        job = developer_control.claim_job()
        developer_control.complete_job(job["job_id"], {}, "focused_validation_failed")
        self.assertEqual(developer_control.write_access_status(), "disabled")

    def test_deploy_access_remains_disabled(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        self.assertIn("Deploy Access</small><b>Disabled", page)

    def test_runtime_never_invokes_commit_push_or_deploy(self):
        completed = type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(self.agent, "_run_fixed", return_value=completed) as run:
            self.agent._validate_approved_change({}, ["app.py"])
        flattened = " ".join(" ".join(call.args[0]) for call in run.call_args_list)
        for forbidden in ("commit", "push", "deploy", "git add"):
            self.assertNotIn(forbidden, flattened)


if __name__ == "__main__":
    unittest.main()
