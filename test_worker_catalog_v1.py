import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class ReadyWorkerCatalogV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "workers.sqlite")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import managed_migrations
        import rolepack_system
        import web_app
        import worker_catalog
        import work_objects
        cls.migrations = managed_migrations
        cls.rolepacks = rolepack_system
        cls.web = web_app
        cls.catalog = worker_catalog
        cls.restore = bind_sqlite_database(
            cls.db_file, managed_migrations, rolepack_system,
            web_app, worker_catalog, work_objects,
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
        conn = self.migrations.persistence_backend.connect()
        cur = conn.cursor()
        for table in (
            "nina_worker_events", "nina_workspace_workers",
            "nina_rolepack_events", "nina_workspace_rolepacks",
        ):
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
        cur.close()
        conn.close()

    def select(self, worker_id, workspace=None, actor="owner-a"):
        return self.catalog.set_workspace_worker(
            workspace or self.workspace, worker_id, updated_by=actor,
        )

    def test_01_canonical_worker_model(self):
        item = self.catalog.get_worker("office_manager")
        for field in (
            "worker_id", "key", "display_name", "description", "status",
            "version", "icon", "created_at", "updated_at",
            "primary_rolepack", "secondary_rolepacks",
            "supported_channels", "supported_capabilities",
            "supported_actions", "default_autonomy_mode",
            "required_permissions",
        ):
            self.assertTrue(hasattr(item, field), field)

    def test_02_required_builtins(self):
        self.assertEqual(
            {item.worker_id for item in self.catalog.list_workers()},
            {
                "office_manager", "sales_assistant", "client_manager",
                "personal_assistant", "general_nina",
            },
        )

    def test_03_worker_content_is_composed_from_rolepacks(self):
        worker = self.catalog.get_worker("client_manager")
        role = self.rolepacks.get_rolepack("client_manager")
        self.assertEqual(worker.primary_rolepack, role.rolepack_id)
        self.assertEqual(
            set(worker.supported_capabilities), set(role.capabilities)
        )
        self.assertEqual(
            set(worker.supported_actions), set(role.allowed_actions)
        )
        self.assertEqual(
            set(worker.required_permissions),
            set(role.required_permissions),
        )

    def test_04_general_nina_composes_multiple_rolepacks(self):
        worker = self.catalog.get_worker("general_nina")
        self.assertEqual(worker.primary_rolepack, "office_manager")
        self.assertEqual(
            worker.secondary_rolepacks,
            (
                "sales_assistant", "client_manager",
                "personal_assistant",
            ),
        )
        expected = set()
        for rolepack_id in worker.rolepacks:
            expected.update(
                self.rolepacks.get_rolepack(rolepack_id).capabilities
            )
        self.assertEqual(set(worker.supported_capabilities), expected)

    def test_05_default_worker_preserves_matching_rolepack(self):
        self.rolepacks.set_workspace_rolepack(
            self.workspace, "sales_assistant", updated_by="owner-a",
        )
        selected = self.catalog.get_workspace_worker(self.workspace)
        self.assertEqual(selected.worker_id, "sales_assistant")

    def test_06_worker_persists(self):
        self.select("client_manager")
        selected = self.catalog.get_workspace_worker(
            self.workspace, create=False,
        )
        self.assertEqual(selected.worker_id, "client_manager")
        self.assertEqual(selected.worker_version, "1.0.0")

    def test_07_single_active_worker_per_workspace(self):
        self.select("sales_assistant")
        self.select("personal_assistant")
        conn = self.migrations.persistence_backend.connect()
        count = conn.execute(
            "SELECT COUNT(*) FROM nina_workspace_workers "
            "WHERE workspace_id=?",
            (self.workspace,),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_08_worker_change_audit(self):
        self.select("sales_assistant")
        self.select("client_manager", actor="owner-b")
        events = self.catalog.list_workspace_worker_events(self.workspace)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][2], "worker_changed")
        self.assertEqual(events[0][3], "sales_assistant")
        self.assertEqual(events[0][4], "client_manager")
        self.assertEqual(events[0][5], "owner-b")

    def test_09_duplicate_selection_is_idempotent(self):
        first = self.select("office_manager")
        second = self.select("office_manager")
        self.assertEqual(first, second)
        self.assertEqual(
            len(self.catalog.list_workspace_worker_events(self.workspace)), 1
        )

    def test_10_workspace_isolation(self):
        self.select("sales_assistant", "workspace-a")
        self.select("personal_assistant", "workspace-b")
        self.assertEqual(
            self.catalog.get_workspace_worker(
                "workspace-a", create=False,
            ).worker_id,
            "sales_assistant",
        )
        self.assertEqual(
            self.catalog.get_workspace_worker(
                "workspace-b", create=False,
            ).worker_id,
            "personal_assistant",
        )
        self.assertEqual(
            len(self.catalog.list_workspace_worker_events("workspace-a")), 1
        )

    def test_11_worker_activates_primary_rolepack(self):
        self.select("client_manager")
        role = self.rolepacks.get_workspace_rolepack(
            self.workspace, create=False,
        )
        self.assertEqual(role.rolepack_id, "client_manager")

    def test_12_general_nina_activates_primary_rolepack(self):
        self.select("general_nina")
        role = self.rolepacks.get_workspace_rolepack(
            self.workspace, create=False,
        )
        self.assertEqual(role.rolepack_id, "office_manager")

    def test_13_worker_and_rolepack_audit_share_actor(self):
        self.select("personal_assistant", actor="owner-z")
        worker_event = self.catalog.list_workspace_worker_events(
            self.workspace,
        )[0]
        role_event = self.rolepacks.list_workspace_rolepack_events(
            self.workspace,
        )[0]
        self.assertEqual(worker_event[5], "owner-z")
        self.assertEqual(role_event[5], "owner-z")

    def test_14_invalid_worker_is_rejected_server_side(self):
        with self.assertRaisesRegex(
            self.catalog.WorkerNotFoundError, "worker_not_found"
        ):
            self.select("forged_worker")
        self.assertIsNone(
            self.catalog.get_workspace_worker(
                self.workspace, create=False,
            )
        )

    def test_15_default_autonomy_is_configuration_only(self):
        for worker in self.catalog.list_workers():
            self.assertEqual(worker.default_autonomy_mode, "MANUAL")
        source = Path("worker_catalog.py").read_text(encoding="utf-8")
        self.assertNotIn("set_autonomy_mode(", source)

    def test_16_dashboard_renders_worker_dropdown_and_composition(self):
        self.select("general_nina")
        client = self.web.app.test_client()
        response = client.get("/dashboard")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Worker", body)
        for label in (
            "Office Manager", "Sales Assistant", "Client Manager",
            "Personal Assistant", "General Nina",
        ):
            self.assertIn(label, body)
        self.assertIn("RolePack composition", body)
        self.assertIn("Worker Instance ID", body)
        self.assertIn("<b>Status:</b> ACTIVE", body)
        self.assertIn("<b>Language:</b>", body)
        self.assertIn("<b>Timezone:</b>", body)
        self.assertIn("<b>Version:</b>", body)
        self.assertNotIn("action='/settings/rolepack'", body)

    def test_17_worker_post_uses_prg_and_persists(self):
        client = self.web.app.test_client()
        body = client.get("/dashboard").get_data(as_text=True)
        token = re.search(
            r"action='/settings/worker'>[\s\S]*?"
            r"name='csrf_token' value='([^']+)'",
            body,
        ).group(1)
        response = client.post(
            "/settings/worker",
            data={
                "worker_id": "sales_assistant",
                "csrf_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("worker_status=sales_assistant", response.location)
        self.assertEqual(
            self.catalog.get_workspace_worker(
                self.workspace, create=False,
            ).worker_id,
            "sales_assistant",
        )

    def test_18_worker_post_rejects_csrf(self):
        response = self.web.app.test_client().post(
            "/settings/worker",
            data={
                "worker_id": "sales_assistant",
                "csrf_token": "forged",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(
            self.catalog.get_workspace_worker(
                self.workspace, create=False,
            )
        )

    def test_19_post_cannot_select_another_workspace(self):
        client = self.web.app.test_client()
        body = client.get("/dashboard").get_data(as_text=True)
        token = re.search(
            r"action='/settings/worker'>[\s\S]*?"
            r"name='csrf_token' value='([^']+)'",
            body,
        ).group(1)
        response = client.post(
            "/settings/worker",
            data={
                "worker_id": "client_manager",
                "workspace_id": "workspace-attacker",
                "csrf_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(
            self.catalog.get_workspace_worker(
                "workspace-attacker", create=False,
            )
        )

    def test_20_migration_tables_and_index_exist(self):
        conn = self.migrations.persistence_backend.connect()
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
        self.assertIn("nina_workspace_workers", tables)
        self.assertIn("nina_worker_events", tables)
        self.assertIn("idx_nina_worker_events_workspace", indexes)


if __name__ == "__main__":
    unittest.main()
