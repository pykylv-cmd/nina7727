import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "repository-understanding-cookie-secret-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "repository-understanding-admin-token-32")

import nina_developer_agent
import web_app


class DeveloperRepositoryUnderstandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)
        cls.agent = nina_developer_agent.ReadOnlyDeveloperAgent(Path(__file__).resolve().parent)

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        return client

    def evidence_jobs(self, question):
        kind, plan = web_app._developer_investigation_plan(question)
        jobs = []
        for role, query, path in plan:
            result = self.agent.execute("search_text", {"query": query, "path": path})
            jobs.append({"status": "completed", "result": result,
                         "arguments": {"evidence_role": role, "investigation_kind": kind}})
        return kind, jobs

    def test_owner_only_access_is_preserved(self):
        self.assertEqual(web_app.app.test_client().get("/admin/developer?format=results").status_code, 403)
        self.assertEqual(self.admin_client().get("/admin/developer?format=results").status_code, 200)

    def test_real_repository_evidence_retrieval_finds_main_definition(self):
        kind, jobs = self.evidence_jobs("Kur tiek definēts send_message_to_nina?")
        answer = web_app._developer_investigation_answer(kind, jobs)
        self.assertIn("nina_message_service.py", answer["answer"])
        self.assertTrue(any("def send_message_to_nina" in item["symbol"] for item in answer["evidence"]))

    def test_multi_file_company_whatsapp_investigation(self):
        kind, jobs = self.evidence_jobs(
            "Izskaidro Company WhatsApp message flow no ienākošās ziņas līdz Nina reply."
        )
        answer = web_app._developer_investigation_answer(kind, jobs)
        paths = {item["path"].replace("\\", "/") for item in answer["evidence"]}
        self.assertIn("web_app.py", paths)
        self.assertIn("nina_message_service.py", paths)
        self.assertIn("personal_whatsapp_bridge/src/company_session_manager.js", paths)
        self.assertIn("messages.upsert", answer["answer"])

    def test_insufficient_evidence_fails_without_guessing(self):
        answer = web_app._developer_investigation_answer("company_whatsapp_flow", [])
        self.assertIn("insufficient", answer["answer"])
        self.assertIn("missing_evidence", answer)
        self.assertNotIn("→", answer["answer"])

    def test_investigation_plan_uses_only_existing_read_only_operations(self):
        for question in (
            "Kur tiek definēts send_message_to_nina?",
            "Izskaidro Company WhatsApp message flow no ienākošās ziņas līdz Nina reply.",
            'Kāpēc "Developer:" pieprasījums agrāk varēja nonākt Web Research?',
        ):
            _, plan = web_app._developer_investigation_plan(question)
            self.assertTrue(plan)
            self.assertTrue(all(query and path for _, query, path in plan))
        with self.assertRaisesRegex(nina_developer_agent.DeveloperAgentError, "operation_not_allowed"):
            self.agent.execute("write_text_file", {"path": "web_app.py", "text": "unsafe"})

    def test_repository_question_never_uses_generic_web_research_path(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create, \
             patch.object(web_app, "send_message_to_nina") as generic_nina:
            response = client.post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": 'Kāpēc "Developer:" pieprasījums agrāk varēja nonākt Web Research?'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(create.called)
        self.assertTrue(all(call.args[0] == "search_text" for call in create.call_args_list))
        generic_nina.assert_not_called()

    def test_disconnected_agent_fails_safely(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "not_connected", "repository": "not_connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = client.post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Kur tiek definēts send_message_to_nina?"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["ok"])
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
