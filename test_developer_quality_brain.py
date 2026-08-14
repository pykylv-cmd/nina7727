import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "quality-brain-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "quality-brain-admin-token-at-least-32")

import nina_developer_agent
import web_app
import test_developer_brain as developer_brain_fixture


class DeveloperQualityBrainTests(unittest.TestCase):
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

    def approved_payload(self):
        developer_brain_fixture.DeveloperBrainTests.setUpClass()
        _, jobs, payload = developer_brain_fixture.DeveloperBrainTests().investigate(
            developer_brain_fixture.STATUS_QUESTION
        )
        return jobs, payload

    def test_quality_review_is_after_diff_and_before_owner_approval(self):
        jobs, payload = self.approved_payload()
        investigation_id = "devinvest_quality_order"
        for job in jobs:
            job["arguments"].update({"investigation_id": investigation_id})
        with patch.object(web_app, "list_developer_jobs", return_value=jobs):
            rendered, _ = web_app._admin_developer_jobs_html()
        self.assertLess(rendered.index("DIFF PREVIEW"), rendered.index("QUALITY REVIEW"))
        self.assertLess(rendered.index("QUALITY REVIEW"), rendered.index("Approve &amp; Apply Locally"))
        self.assertEqual(payload["quality_review"]["Verdict"], "APPROVE FOR OWNER REVIEW")

    def test_quality_review_checks_required_dimensions_and_real_evidence(self):
        _, payload = self.approved_payload()
        review = payload["quality_review"]
        for field in (
            "Architecture", "ONE NINA", "Regression Risk", "Security", "Data Integrity",
            "Test Plan", "Smaller Safe Alternative", "Assumptions Supported By Evidence",
            "Repository Evidence", "Cross-Runtime Review", "Duplicate Logic Review",
            "Backward Compatibility", "Verdict",
        ):
            self.assertIn(field, review)
        self.assertEqual(review["Architecture"], "PASS")
        self.assertEqual(review["ONE NINA"], "PASS")
        self.assertTrue(all(item["path"] and item["line"] for item in review["Repository Evidence"]))

    def test_blocked_security_or_one_nina_proposal_has_no_approval(self):
        jobs, payload = self.approved_payload()
        payload["proposed_change"] = dict(payload["proposed_change"])
        payload["proposed_change"]["diff"] = "-@platform_admin_required\n+second_nina = True"
        payload["quality_review"] = web_app._developer_quality_review(
            payload["developer_analysis"], payload["proposed_change"], payload["evidence"]
        )
        self.assertEqual(payload["quality_review"]["Verdict"], "BLOCK")
        investigation_id = "devinvest_quality_block"
        for job in jobs:
            job["arguments"].update({"investigation_id": investigation_id})
        with patch.object(web_app, "list_developer_jobs", return_value=jobs), \
             patch.object(web_app, "_developer_investigation_answer", return_value=payload):
            rendered, _ = web_app._admin_developer_jobs_html()
        self.assertNotIn("Approve &amp; Apply Locally", rendered)
        self.assertIn("Owner approval unavailable: BLOCK", rendered)

    def test_blocked_proposal_is_rejected_server_side(self):
        jobs, payload = self.approved_payload()
        payload["proposed_change"] = dict(payload["proposed_change"])
        payload["proposed_change"]["diff"] = "-@platform_admin_required"
        investigation_id = "devinvest_quality_post_block"
        for job in jobs:
            job["arguments"].update({"investigation_id": investigation_id})
        with patch.object(web_app, "list_developer_jobs", return_value=jobs), \
             patch.object(web_app, "_developer_investigation_answer", return_value=payload), \
             patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_approval_job") as create:
            response = self.admin_client().post("/admin/developer", data={
                "action": "approve_diff", "investigation_id": investigation_id,
                "diff_hash": hashlib.sha256(payload["proposed_change"]["diff"].encode()).hexdigest(),
                "csrf_token": web_app._channel_csrf("developer:approve"),
            })
        self.assertEqual(response.status_code, 409)
        create.assert_not_called()

    def test_insufficient_test_plan_requires_revision_and_new_review(self):
        _, payload = self.approved_payload()
        proposal = dict(payload["proposed_change"])
        proposal["focused_tests"] = []
        first = web_app._developer_quality_review(payload["developer_analysis"], proposal, payload["evidence"])
        self.assertEqual(first["Verdict"], "REVISE PROPOSAL")
        self.assertTrue(first["Revision Required"])
        proposal["focused_tests"] = ["owner-only approval", "repository disconnected approval"]
        second = web_app._developer_quality_review(payload["developer_analysis"], proposal, payload["evidence"])
        self.assertEqual(second["Verdict"], "APPROVE FOR OWNER REVIEW")
        self.assertFalse(second["Revision Required"])

    def test_missing_repository_evidence_blocks(self):
        _, payload = self.approved_payload()
        review = web_app._developer_quality_review(
            payload["developer_analysis"], payload["proposed_change"], []
        )
        self.assertEqual(review["Architecture"], "FAIL")
        self.assertEqual(review["Verdict"], "BLOCK")

    def test_review_does_not_write_repository(self):
        _, payload = self.approved_payload()
        paths = [self.root / "web_app.py", self.root / "developer_control.py"]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        web_app._developer_quality_review(
            payload["developer_analysis"], payload["proposed_change"], payload["evidence"]
        )
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(before, after)

    def test_write_and_deploy_access_remain_disabled(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        self.assertIn("Write Access</small><b>Disabled", page)
        self.assertIn("Deploy Access</small><b>Disabled", page)


if __name__ == "__main__":
    unittest.main()
