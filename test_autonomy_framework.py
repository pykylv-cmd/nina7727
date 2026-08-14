import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class AutonomyFrameworkV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "autonomy.sqlite")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import approval_layer
        import autonomy_framework
        import execution_layer
        import managed_migrations
        import web_app
        import work_objects
        cls.approval = approval_layer
        cls.autonomy = autonomy_framework
        cls.execution = execution_layer
        cls.migrations = managed_migrations
        cls.web = web_app
        cls.work = work_objects
        cls.restore = bind_sqlite_database(
            cls.db_file, approval_layer, autonomy_framework, execution_layer,
            managed_migrations, web_app, work_objects,
        )
        managed_migrations.run_migrations()
        initialize_ready_web(web_app)
        cls.workspace = web_app.NINA_WEB_WORKSPACE_ID

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_autonomy_events")
        cur.execute("DELETE FROM nina_autonomy_profiles")
        conn.commit()
        cur.close()
        conn.close()

    def context(self, *, approved=False, workspace=None):
        workspace = workspace or self.workspace
        status = "approved" if approved else "pending"
        decision = "approved" if approved else ""
        approval = SimpleNamespace(
            workspace_id=workspace, status=status, decision=decision,
        )
        reply = SimpleNamespace(workspace_id=workspace)
        return approval, reply

    def evaluate(self, mode, action, *, approved=False):
        self.autonomy.set_mode(
            self.workspace, mode, updated_by="owner-a",
        )
        approval, reply = self.context(approved=approved)
        return self.autonomy.AutonomyFramework.evaluate(
            self.workspace, approval, reply, action,
        )

    def test_01_manual_requires_approval(self):
        self.assertEqual(
            self.evaluate("MANUAL", "REMIND").decision,
            "REQUIRE_APPROVAL",
        )

    def test_02_suggest_requires_approval(self):
        self.assertEqual(
            self.evaluate("SUGGEST", "NO_ACTION").decision,
            "REQUIRE_APPROVAL",
        )

    def test_03_semi_auto_remind_allows(self):
        self.assertEqual(self.evaluate("SEMI_AUTO", "REMIND").decision, "ALLOW")

    def test_04_semi_auto_no_action_allows(self):
        self.assertEqual(
            self.evaluate("SEMI_AUTO", "NO_ACTION").decision, "ALLOW",
        )

    def test_05_semi_auto_follow_up_requires_approval(self):
        self.assertEqual(
            self.evaluate("SEMI_AUTO", "FOLLOW_UP").decision,
            "REQUIRE_APPROVAL",
        )

    def test_06_semi_auto_check_in_requires_approval(self):
        self.assertEqual(
            self.evaluate("SEMI_AUTO", "CHECK_IN").decision,
            "REQUIRE_APPROVAL",
        )

    def test_07_semi_auto_ask_for_update_requires_approval(self):
        self.assertEqual(
            self.evaluate("SEMI_AUTO", "ASK_FOR_UPDATE").decision,
            "REQUIRE_APPROVAL",
        )

    def test_08_auto_remind_allows(self):
        self.assertEqual(self.evaluate("AUTO", "REMIND").decision, "ALLOW")

    def test_09_auto_no_action_allows(self):
        self.assertEqual(self.evaluate("AUTO", "NO_ACTION").decision, "ALLOW")

    def test_10_auto_does_not_expand_allowlist(self):
        self.assertEqual(
            self.evaluate("AUTO", "FOLLOW_UP").decision,
            "REQUIRE_APPROVAL",
        )

    def test_11_human_approval_allows_manual_execution(self):
        self.assertEqual(
            self.evaluate("MANUAL", "REMIND", approved=True).decision,
            "ALLOW",
        )

    def test_12_unknown_action_is_unsupported(self):
        self.assertEqual(
            self.evaluate("AUTO", "SEND_MESSAGE").decision, "UNSUPPORTED",
        )

    def test_13_workspace_mismatch_denied(self):
        self.autonomy.set_mode(
            self.workspace, "AUTO", updated_by="owner-a",
        )
        approval, reply = self.context(workspace="other-workspace")
        result = self.autonomy.AutonomyFramework.evaluate(
            self.workspace, approval, reply, "REMIND",
        )
        self.assertEqual(result.decision, "DENY")

    def test_14_profile_persistence(self):
        saved = self.autonomy.set_mode(
            self.workspace, "SEMI_AUTO", updated_by="owner-a",
        )
        self.assertEqual(
            self.autonomy.get_profile(self.workspace, create=False), saved,
        )

    def test_15_default_profile_is_manual(self):
        self.assertEqual(
            self.autonomy.get_profile(self.workspace).mode, "MANUAL",
        )

    def test_16_mode_change_audit(self):
        self.autonomy.set_mode(
            self.workspace, "MANUAL", updated_by="owner-a",
        )
        self.autonomy.set_mode(
            self.workspace, "AUTO", updated_by="owner-b",
        )
        latest = self.autonomy.list_events(self.workspace)[0]
        self.assertEqual(latest[3:6], ("MANUAL", "AUTO", "owner-b"))

    def test_17_duplicate_profile_prevention(self):
        first = self.autonomy.set_mode(
            self.workspace, "MANUAL", updated_by="owner-a",
        )
        second = self.autonomy.set_mode(
            self.workspace, "MANUAL", updated_by="owner-b",
        )
        self.assertEqual(first, second)
        conn = self.work._connect()
        count = conn.execute(
            "SELECT COUNT(*) FROM nina_autonomy_profiles "
            "WHERE workspace_id=?", (self.workspace,),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_18_workspace_profiles_are_isolated(self):
        self.autonomy.set_mode(
            self.workspace, "AUTO", updated_by="owner-a",
        )
        self.autonomy.set_mode(
            "other-workspace", "SUGGEST", updated_by="owner-b",
        )
        self.assertEqual(
            self.autonomy.get_profile(self.workspace).mode, "AUTO",
        )
        self.assertEqual(
            self.autonomy.get_profile("other-workspace").mode, "SUGGEST",
        )

    def test_19_dashboard_renders_mode_settings(self):
        self.autonomy.set_mode(
            self.workspace, "SEMI_AUTO", updated_by="owner-a",
        )
        body = self.web.app.test_client().get(
            "/dashboard",
        ).get_data(as_text=True)
        self.assertIn("Workspace Settings", body)
        self.assertIn("Autonomy Mode", body)
        self.assertRegex(body, r"value='SEMI_AUTO' selected")

    def test_20_mode_post_uses_prg_and_persists(self):
        client = self.web.app.test_client()
        body = client.get("/dashboard").get_data(as_text=True)
        token = re.search(
            r"action='/settings/autonomy'.*?name='csrf_token' value='([^']+)'",
            body, re.S,
        ).group(1)
        response = client.post(
            "/settings/autonomy",
            data={"mode": "AUTO", "csrf_token": token},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("autonomy_status=AUTO", response.location)
        self.assertEqual(
            self.autonomy.get_profile(self.workspace).mode, "AUTO",
        )

    def test_21_mode_post_rejects_csrf(self):
        response = self.web.app.test_client().post(
            "/settings/autonomy",
            data={"mode": "AUTO", "csrf_token": "forged"},
        )
        self.assertEqual(response.status_code, 403)

    def test_22_refresh_does_not_duplicate_profile_or_audit(self):
        client = self.web.app.test_client()
        client.get("/dashboard")
        before = len(self.autonomy.list_events(self.workspace))
        client.get("/dashboard")
        self.assertEqual(len(self.autonomy.list_events(self.workspace)), before)

    def test_23_migration_tables_exist(self):
        conn = self.work._connect()
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        self.assertTrue({
            "nina_autonomy_profiles", "nina_autonomy_events",
        }.issubset(tables))

    def test_24_execution_integration_calls_policy(self):
        source = Path(self.execution.__file__).read_text(encoding="utf-8")
        self.assertIn("AutonomyFramework.evaluate(", source)

    def test_25_no_channel_scheduler_or_llm_dependency(self):
        source = Path(self.autonomy.__file__).read_text(
            encoding="utf-8",
        ).lower()
        for forbidden in (
            "telegram", "whatsapp", "send_message", "scheduler", "openai",
        ):
            self.assertNotIn(forbidden, source)
