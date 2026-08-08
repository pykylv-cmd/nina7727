import os
import unittest
from pathlib import Path

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "target-resolver-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "target-resolver-admin-secret-at-least-32")

import nina_developer_agent
import web_app


class DeveloperTargetResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)
        cls.agent = nina_developer_agent.ReadOnlyDeveloperAgent(Path(__file__).resolve().parent)

    def investigate(self, question):
        kind, plan = web_app._developer_investigation_plan(question)
        jobs = []
        for role, query, path in plan:
            jobs.append({
                "status": "completed",
                "result": self.agent.execute("search_text", {"query": query, "path": path}),
                "arguments": {
                    "evidence_role": role, "investigation_kind": kind, "question": question,
                },
            })
        return kind, plan, web_app._developer_investigation_answer(kind, jobs)

    def test_inbox_target_uses_real_inbox_evidence_not_developer_console(self):
        kind, _, payload = self.investigate("Analizē Inbox arhitektūru. Neko nemaini.")
        self.assertEqual(kind, "target_architecture_analysis")
        self.assertEqual(payload["developer_analysis"]["resolved_targets"], ["Inbox"])
        symbols = " ".join(item["symbol"] for item in payload["evidence"])
        self.assertIn("def inbox", symbols)
        self.assertIn("channel_hub_body", symbols)
        self.assertNotIn("admin_developer", symbols)
        self.assertNotIn("proposed_change", payload)

    def test_tasks_target_uses_route_view_and_canonical_work_evidence(self):
        kind, _, payload = self.investigate("Analizē Tasks arhitektūru. Neko nemaini.")
        self.assertEqual(kind, "target_architecture_analysis")
        self.assertEqual(payload["developer_analysis"]["resolved_targets"], ["Tasks"])
        symbols = " ".join(item["symbol"] for item in payload["evidence"])
        self.assertIn("def tasks", symbols)
        self.assertIn("tasks_body", symbols)
        self.assertIn("one_nina_list_work_objects", symbols)

    def test_client_context_and_memory_are_explicit_multi_target_evidence(self):
        kind, _, payload = self.investigate(
            "Analizē Client Context un Memory saistību. Neko nemaini."
        )
        self.assertEqual(kind, "target_architecture_analysis")
        self.assertEqual(payload["developer_analysis"]["resolved_targets"],
                         ["Client Context", "Memory"])
        paths = {item["path"].replace("\\", "/") for item in payload["evidence"]}
        self.assertIn("client_identity.py", paths)
        self.assertIn("memory_intelligence.py", paths)

    def test_multiple_unrelated_targets_require_clarification(self):
        resolution = web_app._resolve_developer_targets("Analizē Inbox Tasks arhitektūru")
        self.assertEqual(resolution["status"], "ambiguous")
        kind, plan = web_app._developer_investigation_plan("Analizē Inbox Tasks arhitektūru")
        self.assertEqual((kind, plan), ("", ()))

    def test_missing_target_evidence_fails_closed(self):
        payload = web_app._developer_investigation_answer("target_architecture_analysis", [{
            "status": "completed", "result": {"matches": []},
            "arguments": {"evidence_role": "target_0_discovery", "question": "Analizē Inbox"},
        }])
        self.assertEqual(payload["answer"], "TARGET NOT PROVEN")
        self.assertFalse(payload["write_executed"])


if __name__ == "__main__":
    unittest.main()
