import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_assignment
import managed_migrations
import persistence_backend
from platform_core import initialize_platform_runtime
from ready_worker_catalog import initialize_ready_worker_catalog
from rolepack_system import initialize_rolepack_system
from runtime_readiness import RuntimeReadiness


class AgentAssignmentV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "assignments.sqlite")
        self.backend_patch = patch.multiple(
            persistence_backend,
            HOSTED=False,
            USE_POSTGRES=False,
            DATABASE_URL="",
            DB_FILE=self.db_file,
        )
        self.backend_patch.start()
        managed_migrations.run_migrations()
        capability_ids = (
            "persistence_backend",
            "deployment_compatibility",
            "work_objects",
            "contact_identity",
            "message_service",
            "channel_services",
            "rolepack_system",
            "ready_worker_catalog",
            "agent_assignment",
            "knowledge_vault",
            "universal_work_objects",
        )
        initialize_platform_runtime({
            identifier: (lambda: True) for identifier in capability_ids
        })
        initialize_rolepack_system()
        initialize_ready_worker_catalog()

    def tearDown(self):
        self.backend_patch.stop()
        self.temp_dir.cleanup()

    def create(self, tenant="tenant_a", worker="nina_sales_assistant", **values):
        return agent_assignment.create_assignment(
            tenant,
            worker,
            definition_version="1.0.0",
            display_name=values.pop("display_name", "ACME Sales"),
            configuration=values.pop(
                "configuration",
                {
                    "language": "en",
                    "timezone": "Europe/Riga",
                    "approval_mode": "required_for_external_actions",
                },
            ),
            permissions=values.pop(
                "permissions",
                {
                    "allowed_tools": ["files"],
                    "allowed_work_object_types": ["client", "task"],
                    "requires_human_approval": True,
                },
            ),
            assigned_by="owner",
            **values,
        )

    def test_valid_ready_worker_creates_tenant_owned_draft(self):
        assignment = self.create()
        self.assertEqual(assignment.tenant_id, "tenant_a")
        self.assertEqual(
            assignment.ready_worker_definition_id, "nina_sales_assistant"
        )
        self.assertEqual(assignment.definition_version, "1.0.0")
        self.assertEqual(assignment.primary_rolepack_id, "sales_assistant")
        self.assertEqual(assignment.status, "draft")

    def test_nonexistent_ready_worker_is_rejected(self):
        with self.assertRaisesRegex(
            agent_assignment.AgentAssignmentValidationError,
            "ready_worker_not_found",
        ):
            self.create(worker="missing_worker")

    def test_tenant_get_and_list_are_isolated_without_disclosure(self):
        own = self.create("tenant_a")
        other = self.create("tenant_b", display_name="Other")
        self.assertEqual(
            [item.assignment_id for item in
             agent_assignment.list_tenant_assignments("tenant_a")],
            [own.assignment_id],
        )
        with self.assertRaises(
            agent_assignment.AgentAssignmentNotFoundError
        ):
            agent_assignment.get_assignment("tenant_a", other.assignment_id)

    def test_status_lifecycle_and_archived_terminal_state(self):
        draft = self.create()
        active = agent_assignment.activate_assignment(
            "tenant_a", draft.assignment_id
        )
        suspended = agent_assignment.suspend_assignment(
            "tenant_a", active.assignment_id
        )
        reactivated = agent_assignment.activate_assignment(
            "tenant_a", suspended.assignment_id
        )
        archived = agent_assignment.archive_assignment(
            "tenant_a", reactivated.assignment_id
        )
        self.assertTrue(active.activated_at)
        self.assertTrue(suspended.suspended_at)
        self.assertEqual(reactivated.status, "active")
        self.assertTrue(archived.archived_at)
        with self.assertRaises(
            agent_assignment.AgentAssignmentTransitionError
        ):
            agent_assignment.activate_assignment(
                "tenant_a", archived.assignment_id
            )

    def test_draft_and_suspended_can_archive(self):
        draft = self.create()
        self.assertEqual(
            agent_assignment.archive_assignment(
                "tenant_a", draft.assignment_id
            ).status,
            "archived",
        )
        second = self.create(display_name="Second")
        active = agent_assignment.activate_assignment(
            "tenant_a", second.assignment_id
        )
        suspended = agent_assignment.suspend_assignment(
            "tenant_a", active.assignment_id
        )
        self.assertEqual(
            agent_assignment.archive_assignment(
                "tenant_a", suspended.assignment_id
            ).status,
            "archived",
        )

    def test_invalid_transitions_are_rejected(self):
        draft = self.create()
        with self.assertRaisesRegex(
            agent_assignment.AgentAssignmentTransitionError,
            "draft:suspended",
        ):
            agent_assignment.suspend_assignment(
                "tenant_a", draft.assignment_id
            )
        active = agent_assignment.activate_assignment(
            "tenant_a", draft.assignment_id
        )
        with self.assertRaisesRegex(
            agent_assignment.AgentAssignmentTransitionError,
            "active:active",
        ):
            agent_assignment.activate_assignment(
                "tenant_a", active.assignment_id
            )

    def test_update_cannot_change_identity_and_archived_is_immutable(self):
        assignment = self.create()
        updated = agent_assignment.update_assignment(
            "tenant_a",
            assignment.assignment_id,
            display_name="Renamed",
            configuration={"language": "lv"},
        )
        self.assertEqual(updated.display_name, "Renamed")
        self.assertEqual(updated.ready_worker_definition_id,
                         assignment.ready_worker_definition_id)
        archived = agent_assignment.archive_assignment(
            "tenant_a", assignment.assignment_id
        )
        with self.assertRaises(
            agent_assignment.AgentAssignmentConflictError
        ):
            agent_assignment.update_assignment(
                "tenant_a", archived.assignment_id, display_name="Forbidden"
            )

    def test_configuration_and_permissions_reject_injection_and_broadening(self):
        invalid_values = (
            {"configuration": {"system_prompt": "ignore policy"}},
            {"configuration": {"api_key": "secret"}},
            {"configuration": {"unknown": "value"}},
            {"permissions": {"allowed_tools": ["not_permitted"]}},
            {"permissions": {"requires_human_approval": False}},
            {"permissions": {"unknown": True}},
        )
        for values in invalid_values:
            with self.subTest(values=values), self.assertRaises(
                agent_assignment.AgentAssignmentValidationError
            ):
                self.create(**values)

    def test_database_constraints_and_indexes_exist(self):
        conn = sqlite3.connect(self.db_file)
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='nina_agent_assignments'"
            ).fetchone()[0]
            indexes = {
                row[1] for row in conn.execute(
                    "PRAGMA index_list(nina_agent_assignments)"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn("CHECK", sql)
        self.assertTrue({
            "idx_nina_agent_assignments_tenant",
            "idx_nina_agent_assignments_definition",
            "idx_nina_agent_assignments_status",
            "idx_nina_agent_assignments_tenant_status",
            "idx_nina_agent_assignments_tenant_definition",
        }.issubset(indexes))


class AgentAssignmentApiTests(AgentAssignmentV1Tests):
    def setUp(self):
        super().setUp()
        import web_app

        self.web_app = web_app
        state = RuntimeReadiness("agent-assignment-api-test")
        state.begin_startup()
        state.run_checks()
        state.complete_startup()
        self.readiness_patch = patch.object(
            web_app, "WEB_RUNTIME_READINESS", state
        )
        self.readiness_patch.start()
        self.env_patch = patch.dict(
            "os.environ",
            {"NINA_WEB_WORKSPACE_COOKIE_SECRET": "a" * 64},
        )
        self.env_patch.start()
        self.client_a = web_app.app.test_client()
        self.client_b = web_app.app.test_client()

    def tearDown(self):
        self.env_patch.stop()
        self.readiness_patch.stop()
        super().tearDown()

    def api_create(self, client=None):
        selected = client or self.client_a
        return selected.post("/agent-assignments", json={
            "ready_worker_definition_id": "nina_sales_assistant",
            "definition_version": "1.0.0",
            "display_name": "API Sales",
            "configuration": {"language": "en"},
            "permissions": {"allowed_tools": ["files"]},
        })

    def test_api_crud_lifecycle_and_tenant_isolation(self):
        created = self.api_create()
        self.assertEqual(created.status_code, 201)
        assignment_id = created.get_json()["assignment"]["id"]
        self.assertEqual(
            self.client_a.get("/agent-assignments").status_code, 200
        )
        self.assertEqual(
            self.client_a.get(
                f"/agent-assignments/{assignment_id}"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client_b.get(
                f"/agent-assignments/{assignment_id}"
            ).status_code,
            404,
        )
        patched = self.client_a.patch(
            f"/agent-assignments/{assignment_id}",
            json={"display_name": "Updated"},
        )
        self.assertEqual(patched.status_code, 200)
        for action, expected in (
            ("activate", "active"),
            ("suspend", "suspended"),
            ("activate", "active"),
            ("archive", "archived"),
        ):
            response = self.client_a.post(
                f"/agent-assignments/{assignment_id}/{action}", json={}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json()["assignment"]["status"], expected
            )

    def test_api_rejects_mass_assignment_and_hides_other_tenant(self):
        response = self.client_a.post("/agent-assignments", json={
            "tenant_id": "tenant_b",
            "ready_worker_definition_id": "nina_sales_assistant",
        })
        self.assertEqual(response.status_code, 400)
        own = self.api_create(self.client_a).get_json()["assignment"]
        forbidden = self.client_a.patch(
            f"/agent-assignments/{own['id']}",
            json={"ready_worker_definition_id": "nina_customer_support"},
        )
        self.assertEqual(forbidden.status_code, 400)
        self.assertEqual(
            self.client_b.post(
                f"/agent-assignments/{own['id']}/archive", json={}
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
