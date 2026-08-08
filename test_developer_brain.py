import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "developer-brain-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "developer-brain-admin-token-at-least-32")

import nina_developer_agent
import web_app


STATUS_QUESTION = (
    "Analizē, kā Developer Console nosaka Agent un Repository Connected/Disconnected "
    "stāvokli. Atrodi riskus un sagatavo minimālo drošo risinājumu, neko nemainot."
)
FLOW_QUESTION = (
    "Izskaidro Company WhatsApp message flow un pasaki, kuri moduļi būtu riskanti, "
    "ja mainītu send_message_to_nina."
)


class DeveloperBrainTests(unittest.TestCase):
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

    def investigate(self, question):
        kind, plan = web_app._developer_investigation_plan(question)
        jobs = []
        for role, query, path in plan:
            result = self.agent.execute("search_text", {"query": query, "path": path})
            jobs.append({
                "status": "completed",
                "result": result,
                "arguments": {"evidence_role": role, "investigation_kind": kind},
            })
        return kind, jobs, web_app._developer_investigation_answer(kind, jobs)

    def test_analysis_precedes_diff_preview_and_has_required_pipeline(self):
        _, _, result = self.investigate(STATUS_QUESTION)
        self.assertLess(list(result).index("developer_analysis"), list(result).index("proposed_change"))
        analysis = result["developer_analysis"]
        for field in (
            "problem", "repository_evidence", "architecture_boundary", "affected_modules",
            "call_chain_dependencies", "risks", "alternatives", "chosen_solution", "why",
            "focused_validation_plan",
        ):
            self.assertIn(field, analysis)
        self.assertEqual(analysis["risks"]["classification"], "LOW")
        self.assertIn("_developer_connection_ready", analysis["chosen_solution"])

    def test_current_canonical_readiness_evidence_is_distinct_and_self_match_safe(self):
        kind, plan = web_app._developer_investigation_plan(STATUS_QUESTION)
        jobs = []
        for role, query, path in plan:
            result = self.agent.execute("search_text", {"query": query, "path": path})
            jobs.append({"status": "completed", "result": result,
                         "arguments": {"evidence_role": role, "investigation_kind": kind}})
        payload = web_app._developer_investigation_answer(kind, jobs)
        by_role = {item["role"]: item for item in payload["evidence"]}
        self.assertIn("def _developer_connection_ready", by_role["readiness_helper"]["symbol"])
        self.assertIn("developer_ready = _developer_connection_ready", by_role["render_gate"]["symbol"])
        self.assertIn("_developer_connection_ready(status)", by_role["send_gate"]["symbol"])
        self.assertIn("_developer_connection_ready(approval_status)", by_role["approval_gate"]["symbol"])
        self.assertIn("test_repository_disconnected_blocks_diff_approval",
                      by_role["regression_test"]["symbol"])
        self.assertNotEqual(by_role["readiness_helper"]["line"], by_role["render_gate"]["line"])
        self.assertTrue(all(item["line"] > 7105 for item in by_role.values()
                            if item["path"] == "web_app.py"))

    def test_repository_evidence_and_multi_file_dependencies_are_real(self):
        _, _, result = self.investigate(FLOW_QUESTION)
        analysis = result["developer_analysis"]
        paths = {item["path"].replace("\\", "/") for item in analysis["repository_evidence"]}
        self.assertIn("web_app.py", paths)
        self.assertIn("nina_message_service.py", paths)
        self.assertIn("personal_whatsapp_bridge/src/company_session_manager.js", paths)
        self.assertEqual(analysis["risks"]["classification"], "HIGH")
        by_role = {item["role"]: item["symbol"] for item in analysis["repository_evidence"]}
        self.assertIn("processCompanyMessageUpsert", by_role["bridge_intake"])
        self.assertIn("delivery_recipient=sender_jid", by_role["shared_nina_call"])
        self.assertNotIn("proposed_change", result)

    def test_insufficient_architecture_evidence_fails_closed(self):
        result = web_app._developer_investigation_answer("developer_status_diff_preview", [])
        self.assertEqual(result["answer"], "INSUFFICIENT ARCHITECTURE EVIDENCE")
        self.assertNotIn("developer_analysis", result)
        self.assertNotIn("proposed_change", result)

    def test_rendered_analysis_is_before_diff_and_marks_no_write(self):
        kind, jobs, _ = self.investigate(STATUS_QUESTION)
        investigation_id = "devinvest_brain_render"
        for job in jobs:
            job["arguments"].update({"investigation_id": investigation_id, "question": STATUS_QUESTION})
        with patch.object(web_app, "list_developer_jobs", return_value=jobs):
            rendered, _ = web_app._admin_developer_jobs_html()
        self.assertLess(rendered.index("DEVELOPER ANALYSIS"), rendered.index("DIFF PREVIEW"))
        self.assertIn("WRITE NOT EXECUTED", rendered)

    def test_analysis_never_uses_generic_web_research_or_writes(self):
        before = {
            path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
            for path in ("web_app.py", "developer_control.py", "nina_message_service.py")
        }
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create, \
             patch.object(web_app, "send_message_to_nina") as generic_nina:
            response = client.post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": STATUS_QUESTION},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(create.called)
        self.assertTrue(all(call.args[0] == "search_text" for call in create.call_args_list))
        generic_nina.assert_not_called()
        after = {
            path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
            for path in before
        }
        self.assertEqual(before, after)

    def test_one_nina_security_and_sprint5_write_boundaries_remain(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        self.assertIn("Write Access</small><b>Disabled", page)
        self.assertIn("Deploy Access</small><b>Disabled", page)
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
            self.agent.execute("write_text_file", {"path": "web_app.py", "text": "unsafe"})


if __name__ == "__main__":
    unittest.main()
