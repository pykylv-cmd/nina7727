import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class RolePackWorkspaceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "rolepack.sqlite")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import autonomy_framework
        import execution_layer
        import initiative_engine
        import managed_migrations
        import reply_builder
        import rolepack_system
        import web_app
        import work_objects
        cls.autonomy = autonomy_framework
        cls.execution = execution_layer
        cls.initiative = initiative_engine
        cls.migrations = managed_migrations
        cls.reply = reply_builder
        cls.rolepacks = rolepack_system
        cls.web = web_app
        cls.work = work_objects
        cls.restore = bind_sqlite_database(
            cls.db_file, autonomy_framework, execution_layer,
            managed_migrations, rolepack_system, web_app, work_objects,
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
        for table in (
            "nina_rolepack_events", "nina_workspace_rolepacks",
            "nina_autonomy_events", "nina_autonomy_profiles",
            "nina_execution_events", "nina_executions",
            "nina_approval_events", "nina_approvals",
            "nina_work_object_events", "nina_work_objects",
        ):
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
        cur.close()
        conn.close()

    def select(self, rolepack_id, workspace=None, actor="owner-a"):
        return self.rolepacks.set_workspace_rolepack(
            workspace or self.workspace, rolepack_id, updated_by=actor,
        )

    def test_01_default_rolepack_is_office_manager(self):
        self.assertEqual(
            self.rolepacks.get_workspace_rolepack(
                self.workspace,
            ).rolepack_id,
            "office_manager",
        )

    def test_02_rolepack_persists(self):
        selected = self.select("sales_assistant")
        self.assertEqual(
            self.rolepacks.get_workspace_rolepack(
                self.workspace, create=False,
            ),
            selected,
        )

    def test_03_single_active_primary_rolepack(self):
        self.select("sales_assistant")
        self.select("client_manager")
        conn = self.work._connect()
        count = conn.execute(
            "SELECT COUNT(*) FROM nina_workspace_rolepacks "
            "WHERE workspace_id=?", (self.workspace,),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)
        self.assertEqual(
            self.rolepacks.active_rolepack(self.workspace).rolepack_id,
            "client_manager",
        )

    def test_04_change_is_audited(self):
        self.select("office_manager")
        self.select("sales_assistant", actor="owner-b")
        event = self.rolepacks.list_workspace_rolepack_events(
            self.workspace,
        )[0]
        self.assertEqual(
            event[2:6],
            (
                "rolepack_changed", "office_manager",
                "sales_assistant", "owner-b",
            ),
        )

    def test_05_identical_selection_does_not_duplicate_audit(self):
        self.select("office_manager")
        before = len(
            self.rolepacks.list_workspace_rolepack_events(self.workspace)
        )
        self.select("office_manager", actor="owner-b")
        self.assertEqual(
            len(self.rolepacks.list_workspace_rolepack_events(self.workspace)),
            before,
        )

    def test_06_workspace_isolation(self):
        self.select("sales_assistant")
        self.select("personal_assistant", workspace="other-workspace")
        self.assertEqual(
            self.rolepacks.active_rolepack(self.workspace).rolepack_id,
            "sales_assistant",
        )
        self.assertEqual(
            self.rolepacks.active_rolepack("other-workspace").rolepack_id,
            "personal_assistant",
        )

    def test_07_required_dashboard_rolepacks_exist(self):
        identifiers = {
            item.rolepack_id
            for item in self.rolepacks.list_rolepacks()
        }
        self.assertTrue({
            "office_manager", "sales_assistant",
            "client_manager", "personal_assistant",
        }.issubset(identifiers))

    def test_08_capabilities_are_declarative(self):
        office = self.rolepacks.get_rolepack("office_manager")
        self.assertIn("manage_tasks", office.capabilities)
        self.assertIn("prepare_replies", office.capabilities)
        self.assertNotIn("send_message", office.capabilities)

    def test_09_action_registry_is_declarative(self):
        remind = self.rolepacks.ACTION_REGISTRY.require("REMIND")
        self.assertEqual(
            (remind.risk_level, remind.executor, remind.status),
            ("low", "active_reminders", "active"),
        )

    def test_10_registry_replaces_execution_allowlist(self):
        self.assertEqual(
            self.execution.ALLOWLIST,
            self.rolepacks.executable_action_types(),
        )

    def test_11_personal_assistant_denies_follow_up(self):
        self.select("personal_assistant")
        definition, rolepack = self.rolepacks.action_for_workspace(
            self.workspace, "FOLLOW_UP",
        )
        self.assertIsNotNone(definition)
        self.assertIsNone(rolepack)

    def test_12_office_manager_allows_follow_up(self):
        self.select("office_manager")
        _, rolepack = self.rolepacks.action_for_workspace(
            self.workspace, "FOLLOW_UP",
        )
        self.assertEqual(rolepack.rolepack_id, "office_manager")

    def test_13_reply_builder_falls_back_to_no_action(self):
        self.select("personal_assistant")
        item = self.work.create_work_object(
            "followup_task", "Client follow-up", workspace_id=self.workspace,
            status="scheduled",
        )
        initiative = self.initiative.initiative_queue(
            self.workspace,
        )[0]
        self.assertEqual(initiative.work_object_id, item.object_id)
        reply = self.reply.ReplyBuilder.build(initiative)
        self.assertEqual(reply.suggested_action, "NO_ACTION")

    def test_14_autonomy_uses_action_registry_and_rolepack(self):
        self.select("personal_assistant")
        self.autonomy.set_mode(
            self.workspace, "AUTO", updated_by="owner-a",
        )
        approval = type("Approval", (), {
            "workspace_id": self.workspace, "status": "pending",
            "decision": "",
        })()
        reply = type("Reply", (), {"workspace_id": self.workspace})()
        result = self.autonomy.AutonomyFramework.evaluate(
            self.workspace, approval, reply, "FOLLOW_UP",
        )
        self.assertEqual((result.decision, result.reason), (
            "DENY", "rolepack_action_not_allowed",
        ))

    def test_15_execution_source_uses_action_registry(self):
        source = Path(self.execution.__file__).read_text(encoding="utf-8")
        self.assertIn("action_for_workspace(", source)
        self.assertNotIn(
            'frozenset({"REMIND", "NO_ACTION"})', source,
        )

    def test_16_dashboard_renders_rolepack_read_only(self):
        self.select("client_manager")
        body = self.web.app.test_client().get(
            "/dashboard",
        ).get_data(as_text=True)
        self.assertIn("Active RolePack", body)
        self.assertIn("Active: Client Manager", body)
        self.assertNotIn("Save RolePack", body)
        self.assertNotIn("action='/settings/rolepack'", body)

    def test_17_rolepack_post_uses_prg_and_persists(self):
        client = self.web.app.test_client()
        token = self.web._channel_csrf("rolepack:change")
        response = client.post(
            "/settings/rolepack",
            data={
                "rolepack_id": "sales_assistant",
                "csrf_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("rolepack_status=sales_assistant", response.location)
        self.assertEqual(
            self.rolepacks.active_rolepack(self.workspace).rolepack_id,
            "sales_assistant",
        )

    def test_18_rolepack_post_rejects_csrf(self):
        response = self.web.app.test_client().post(
            "/settings/rolepack",
            data={
                "rolepack_id": "sales_assistant",
                "csrf_token": "forged",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_19_invalid_rolepack_is_rejected_server_side(self):
        with self.assertRaises(self.rolepacks.RolePackError):
            self.select("forged_rolepack")

    def test_20_migration_tables_and_index_exist(self):
        conn = self.work._connect()
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        indexes = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        conn.close()
        self.assertTrue({
            "nina_workspace_rolepacks", "nina_rolepack_events",
        }.issubset(tables))
        self.assertIn("idx_nina_rolepack_events_workspace", indexes)


if __name__ == "__main__":
    unittest.main()
