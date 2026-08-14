import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_assignment
import managed_migrations
import persistence_backend
from platform_core import initialize_platform_runtime
from rolepack_system import initialize_rolepack_system
from worker_catalog import (
    get_workspace_worker,
    set_workspace_worker,
)


class WorkspaceAgentAssignmentV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "assignment.sqlite")
        self.backend_patch = patch.multiple(
            persistence_backend,
            HOSTED=False,
            USE_POSTGRES=False,
            DATABASE_URL="",
            DB_FILE=self.db_file,
        )
        self.backend_patch.start()
        managed_migrations.run_migrations()
        initialize_platform_runtime({
            key: (lambda: True) for key in (
                "persistence_backend", "deployment_compatibility",
                "work_objects", "contact_identity", "message_service",
                "channel_services", "rolepack_system",
                "ready_worker_catalog", "agent_assignment",
                "knowledge_vault", "universal_work_objects",
            )
        })
        initialize_rolepack_system()

    def tearDown(self):
        self.backend_patch.stop()
        self.temp_dir.cleanup()

    def test_assignment_persistence_and_single_active(self):
        first = agent_assignment.provision_workspace_assignment(
            "workspace_a", "office_manager", actor="owner",
            language="lv", timezone_name="Europe/Riga",
        )
        loaded = agent_assignment.get_workspace_assignment("workspace_a")
        self.assertEqual(loaded, first)
        self.assertEqual(loaded.status, "ACTIVE")
        self.assertEqual(loaded.language, "lv")
        conn = sqlite3.connect(self.db_file)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM nina_agent_assignments "
                "WHERE workspace_id=? AND status='active'",
                ("workspace_a",),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1)

    def test_worker_instance_is_stable_for_same_configuration(self):
        first = agent_assignment.provision_workspace_assignment(
            "workspace_a", "office_manager", actor="owner",
        )
        second = agent_assignment.sync_workspace_assignment(
            "workspace_a", "office_manager", actor="owner",
        )
        self.assertEqual(first.worker_instance_id, second.worker_instance_id)
        self.assertEqual(first.assignment_id, second.assignment_id)

    def test_worker_change_creates_controlled_new_instance(self):
        first = agent_assignment.provision_workspace_assignment(
            "workspace_a", "office_manager", actor="owner",
        )
        set_workspace_worker(
            "workspace_a", "sales_assistant", updated_by="owner",
        )
        second = agent_assignment.get_workspace_assignment("workspace_a")
        self.assertNotEqual(first.worker_instance_id, second.worker_instance_id)
        self.assertEqual(second.worker_key, "sales_assistant")
        self.assertEqual(second.status, "ACTIVE")

    def test_workspace_isolation_and_audit(self):
        one = agent_assignment.provision_workspace_assignment(
            "workspace_a", "office_manager", actor="owner_a",
        )
        two = agent_assignment.provision_workspace_assignment(
            "workspace_b", "personal_assistant", actor="owner_b",
        )
        self.assertNotEqual(one.worker_instance_id, two.worker_instance_id)
        events = agent_assignment.list_workspace_assignment_events(
            "workspace_a"
        )
        self.assertTrue(events)
        self.assertTrue(all(row[3] == "workspace_a" for row in events))
        self.assertEqual(
            agent_assignment.list_workspace_assignment_events("workspace_b")[0][3],
            "workspace_b",
        )

    def test_update_suspend_reactivate_archive_audit(self):
        original = agent_assignment.provision_workspace_assignment(
            "workspace_a", "office_manager", actor="owner",
        )
        updated = agent_assignment.update_workspace_assignment(
            "workspace_a", actor="owner", language="lv",
            timezone_name="Europe/Riga",
        )
        suspended = agent_assignment.transition_workspace_assignment(
            "workspace_a", "SUSPENDED", actor="owner",
        )
        active = agent_assignment.transition_workspace_assignment(
            "workspace_a", "ACTIVE", actor="owner",
        )
        archived = agent_assignment.transition_workspace_assignment(
            "workspace_a", "ARCHIVED", actor="owner",
        )
        self.assertEqual(original.worker_instance_id, updated.worker_instance_id)
        self.assertEqual(suspended.status, "SUSPENDED")
        self.assertEqual(active.status, "ACTIVE")
        self.assertEqual(archived.status, "ARCHIVED")
        event_types = {
            row[4] for row in
            agent_assignment.list_workspace_assignment_events("workspace_a")
        }
        self.assertTrue({
            "assignment_created", "assignment_updated",
            "assignment_activated", "assignment_suspended",
            "assignment_archived",
        }.issubset(event_types))

    def test_rolepack_and_worker_catalog_integration(self):
        set_workspace_worker(
            "workspace_a", "client_manager", updated_by="owner",
        )
        worker = get_workspace_worker("workspace_a")
        assignment = agent_assignment.get_workspace_assignment("workspace_a")
        self.assertEqual(worker.worker_id, assignment.worker_key)
        self.assertEqual(assignment.rolepack_version, "1.0.0")

    def test_migration_contract(self):
        conn = sqlite3.connect(self.db_file)
        try:
            columns = {
                row[1] for row in conn.execute(
                    "PRAGMA table_info(nina_agent_assignments)"
                )
            }
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            indexes = {
                row[1] for row in conn.execute(
                    "PRAGMA index_list(nina_agent_assignments)"
                )
            }
        finally:
            conn.close()
        self.assertTrue({
            "worker_instance_id", "workspace_id", "worker_key",
            "worker_version", "rolepack_version", "language", "timezone",
            "permissions_profile",
        }.issubset(columns))
        self.assertIn("nina_agent_assignment_events", tables)
        self.assertIn(
            "uq_nina_agent_assignments_active_workspace", indexes
        )


if __name__ == "__main__":
    unittest.main()
