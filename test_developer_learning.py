import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_DB_DIR = tempfile.TemporaryDirectory()
os.environ["NINA_DB_FILE"] = str(Path(_DB_DIR.name) / "developer-learning.sqlite")
os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "developer-learning-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "developer-learning-admin-token-at-least-32")

import developer_control
import web_app
import test_developer_brain as developer_brain_fixture


class DeveloperLearningTests(unittest.TestCase):
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

    def lesson(self, **overrides):
        value = {
            "problem_pattern": "Developer Console readiness status drift",
            "affected_modules": ["web_app.py", "developer_control.py"],
            "root_cause": "Agent and Repository readiness checks were duplicated.",
            "attempted_solution": "Reuse _developer_connection_ready for every gate.",
            "outcome": "Focused tests passed and the patch remained fail-closed.",
            "failure_reason": "",
            "successful_pattern": "Use one shared readiness predicate.",
            "regression_risk": "LOW",
            "tests_that_caught_it": ["repository disconnected POST", "owner approval gate"],
            "architecture_rule": "ONE NINA owner actions share one server-side readiness policy.",
        }
        value.update(overrides)
        return value

    def source(self, suffix="verified"):
        return {"developer_job_id": "devjob_" + suffix, "approval_id": "devapproval_" + suffix}

    def test_only_verified_outcomes_become_lessons(self):
        stored = developer_control.record_verified_lesson(
            "successful_patch_tests", self.lesson(), self.source()
        )
        self.assertTrue(stored["lesson_id"].startswith("devlesson_"))
        self.assertEqual(stored["verification_type"], "successful_patch_tests")
        with self.assertRaisesRegex(ValueError, "outcome_unverified"):
            developer_control.record_verified_lesson(
                "speculative_draft", self.lesson(), self.source("guess")
            )
        self.assertEqual(len(developer_control.retrieve_relevant_lessons("readiness status")), 1)

    def test_failed_validation_and_rollback_are_stored_correctly(self):
        stored = developer_control.record_verified_lesson(
            "failed_validation_rollback",
            self.lesson(outcome="Validation failed and rollback completed.",
                        failure_reason="focused_validation_failed", successful_pattern=""),
            self.source("rollback"),
        )
        self.assertEqual(stored["failure_reason"], "focused_validation_failed")
        self.assertEqual(stored["verification_type"], "failed_validation_rollback")

    def test_speculative_or_abandoned_jobs_do_not_create_lessons(self):
        job_id = developer_control.create_job("search_text", {"query": "speculative", "path": "web_app.py"})
        job = developer_control.claim_job()
        self.assertEqual(job["job_id"], job_id)
        developer_control.complete_job(job_id, {"matches": []})
        self.assertEqual(developer_control.retrieve_relevant_lessons("speculative"), [])

    def test_successful_approved_patch_outcome_learns_automatically(self):
        context = {
            "problem_pattern": self.lesson()["problem_pattern"],
            "root_cause": self.lesson()["root_cause"],
            "attempted_solution": self.lesson()["attempted_solution"],
            "successful_pattern": self.lesson()["successful_pattern"],
            "regression_risk": "LOW",
            "tests_that_caught_it": self.lesson()["tests_that_caught_it"],
            "architecture_rule": self.lesson()["architecture_rule"],
        }
        created = developer_control.create_approved_patch_job(
            "devinvest_learning_success", "--- a/web_app.py\n+++ b/web_app.py\n",
            __import__("hashlib").sha256(b"--- a/web_app.py\n+++ b/web_app.py\n").hexdigest(),
            ["web_app.py"], {"web_app.py": "a" * 64}, {"py_compile": ["web_app.py"]},
            lesson_context=context,
        )
        job = developer_control.claim_job()
        developer_control.complete_job(job["job_id"], {
            "write_executed": True, "validation": {"checks": [{"returncode": 0}]},
        })
        lessons = developer_control.retrieve_relevant_lessons("readiness status", ["web_app.py"])
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["source_ids"]["approval_id"], created["approval_id"])

    def test_failed_approved_patch_records_verified_rollback_lesson(self):
        context = {
            "problem_pattern": self.lesson()["problem_pattern"],
            "root_cause": self.lesson()["root_cause"],
            "attempted_solution": self.lesson()["attempted_solution"],
            "regression_risk": "LOW",
            "tests_that_caught_it": self.lesson()["tests_that_caught_it"],
            "architecture_rule": self.lesson()["architecture_rule"],
        }
        patch_text = "--- a/web_app.py\n+++ b/web_app.py\n"
        developer_control.create_approved_patch_job(
            "devinvest_learning_failure", patch_text,
            __import__("hashlib").sha256(patch_text.encode()).hexdigest(),
            ["web_app.py"], {"web_app.py": "b" * 64}, {"py_compile": ["web_app.py"]},
            lesson_context=context,
        )
        job = developer_control.claim_job()
        developer_control.complete_job(job["job_id"], {}, "focused_validation_failed")
        lessons = developer_control.retrieve_relevant_lessons("readiness status", ["web_app.py"])
        self.assertEqual(lessons[0]["verification_type"], "failed_validation_rollback")
        self.assertEqual(lessons[0]["failure_reason"], "focused_validation_failed")

    def test_lesson_retrieval_is_relevant_and_deduplicated(self):
        first = developer_control.record_verified_lesson(
            "successful_patch_tests", self.lesson(), self.source("same")
        )
        second = developer_control.record_verified_lesson(
            "successful_patch_tests", self.lesson(), self.source("same")
        )
        developer_control.record_verified_lesson(
            "production_regression",
            self.lesson(problem_pattern="SS.lv field parsing", affected_modules=["web_research.py"],
                        root_cause="Structured vehicle fields were mapped from the wrong HTML rows.",
                        attempted_solution="Parse only labelled listing parameter rows.",
                        outcome="Production regression verified.", successful_pattern="",
                        architecture_rule="Verified market facts come only from fetched source HTML."),
            {"release_id": "release_search"},
        )
        self.assertEqual(first["lesson_id"], second["lesson_id"])
        lessons = developer_control.retrieve_relevant_lessons("Developer readiness", ["web_app.py"])
        self.assertEqual([item["lesson_id"] for item in lessons], [first["lesson_id"]])

    def test_current_repo_evidence_overrides_stale_lesson(self):
        developer_control.record_verified_lesson(
            "production_regression",
            self.lesson(affected_modules=["removed_status_module.py"],
                        outcome="Old status module regressed.", successful_pattern=""),
            {"release_id": "release_stale"},
        )
        developer_brain_fixture.DeveloperBrainTests.setUpClass()
        _, _, payload = developer_brain_fixture.DeveloperBrainTests().investigate(
            developer_brain_fixture.STATUS_QUESTION
        )
        lessons = payload["developer_analysis"]["Relevant previous lessons"]
        self.assertEqual(lessons[0]["current_repo_relevance"],
                         "NOT CONFIRMED; CURRENT REPO EVIDENCE TAKES PRECEDENCE")
        self.assertIn("_developer_connection_ready", payload["developer_analysis"]["chosen_solution"])

    def test_no_relevant_lesson_fails_closed_without_inventing_history(self):
        developer_brain_fixture.DeveloperBrainTests.setUpClass()
        _, _, payload = developer_brain_fixture.DeveloperBrainTests().investigate(
            developer_brain_fixture.STATUS_QUESTION
        )
        self.assertEqual(payload["developer_analysis"]["Relevant previous lessons"], ["None found."])

    def test_no_parallel_memory_and_owner_boundary_is_preserved(self):
        conn = developer_control._connect()
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'nina_developer%'"
            ).fetchall()}
            foreign = self.lesson()
            foreign["lesson_id"] = "devlesson_foreign"
            conn.execute(
                "INSERT INTO nina_developer_events "
                "(event_id,agent_id,job_id,event_type,safe_metadata_json,created_at) VALUES (?,?,?,?,?,?)",
                ("devevt_foreign", "another_owner", "", "developer_lesson_recorded",
                 json.dumps(foreign), "2026-01-01T00:00:00Z"),
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(tables, {"nina_developer_agents", "nina_developer_jobs", "nina_developer_events"})
        self.assertEqual(developer_control.retrieve_relevant_lessons("readiness"), [])

    def test_write_and_deploy_access_remain_disabled(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = client.get("/admin/developer").get_data(as_text=True)
        self.assertIn("Write Access</small><b>Disabled", page)
        self.assertIn("Deploy Access</small><b>Disabled", page)


if __name__ == "__main__":
    unittest.main()
