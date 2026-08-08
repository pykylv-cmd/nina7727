import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "diff-preview-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "diff-preview-admin-token-at-least-32")

import nina_developer_agent
import web_app


QUESTION = (
    "Analizē, kā Developer Console nosaka Agent Connected/Disconnected statusu "
    "un sagatavo diff preview, neko nemainot."
)


class DeveloperDiffPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)
        cls.root = Path(__file__).resolve().parent
        cls.agent = nina_developer_agent.ReadOnlyDeveloperAgent(cls.root)

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(
            web_app.ADMIN_COOKIE,
            web_app.create_admin_session(web_app._workspace_cookie_secret()),
        )
        return client

    def completed_jobs(self):
        kind, plan = web_app._developer_investigation_plan(QUESTION)
        jobs = []
        for role, query, path in plan:
            result = self.agent.execute("search_text", {"query": query, "path": path})
            jobs.append({
                "status": "completed", "result": result,
                "arguments": {"evidence_role": role, "investigation_kind": kind},
            })
        return kind, jobs

    def test_owner_only_access_is_preserved(self):
        self.assertEqual(web_app.app.test_client().get("/admin/developer").status_code, 403)
        self.assertEqual(self.admin_client().get("/admin/developer").status_code, 200)

    def test_repo_investigation_generates_grounded_diff(self):
        kind, jobs = self.completed_jobs()
        result = web_app._developer_investigation_answer(kind, jobs)
        self.assertIn("developer_control.py", result["answer"])
        self.assertIn("web_app.py", result["answer"])
        self.assertIn("--- a/web_app.py", result["proposed_change"]["diff"])
        self.assertIn("if not _developer_connection_ready(status):", result["proposed_change"]["diff"])
        self.assertTrue(all(item["path"] for item in result["evidence"]))

    def test_preview_does_not_write_repository(self):
        tracked = [self.root / "web_app.py", self.root / "developer_control.py"]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked}
        kind, jobs = self.completed_jobs()
        result = web_app._developer_investigation_answer(kind, jobs)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked}
        self.assertEqual(before, after)
        self.assertFalse(result["write_executed"])
        self.assertEqual(result["safety_notice"], "WRITE NOT EXECUTED.")

    def test_insufficient_evidence_fails_closed_without_diff(self):
        result = web_app._developer_investigation_answer("developer_status_diff_preview", [])
        self.assertEqual(result["answer"], "INSUFFICIENT EVIDENCE")
        self.assertNotIn("proposed_change", result)
        self.assertFalse(result["write_executed"])

    def test_generic_web_research_is_not_used(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create, \
             patch.object(web_app, "send_message_to_nina") as generic_nina:
            response = client.post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"), "message": QUESTION},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(create.called)
        self.assertTrue(all(call.args[0] == "search_text" for call in create.call_args_list))
        generic_nina.assert_not_called()

    def test_write_and_deploy_access_stay_disabled(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        self.assertIn("Write Access</small><b>Disabled", page)
        self.assertIn("Deploy Access</small><b>Disabled", page)
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
            self.agent.execute("write_text_file", {"path": "web_app.py", "text": "unsafe"})


if __name__ == "__main__":
    unittest.main()
