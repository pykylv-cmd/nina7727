import sqlite3
import tempfile
import unittest
import re
from pathlib import Path
from unittest.mock import patch

import agent_assignment
import client_work_view
import daily_planner
import followup_engine
import managed_migrations
import knowledge_vault
import persistence_backend
import task_engine
import universal_work_objects as work
from platform_core import initialize_platform_runtime
from ready_worker_catalog import initialize_ready_worker_catalog
from rolepack_system import initialize_rolepack_system
from runtime_readiness import RuntimeReadiness


CAPABILITIES = (
    "persistence_backend", "deployment_compatibility", "work_objects",
    "contact_identity", "message_service", "channel_services",
    "rolepack_system", "ready_worker_catalog", "agent_assignment",
    "knowledge_vault", "universal_work_objects",
)


class UniversalWorkFixture(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "work.sqlite")
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
            identifier: (lambda: True) for identifier in CAPABILITIES
        })
        initialize_rolepack_system()
        initialize_ready_worker_catalog()

    def tearDown(self):
        self.backend_patch.stop()
        self.temp_dir.cleanup()

    def create(self, tenant="tenant_a", **values):
        defaults = {
            "object_type": "task",
            "title": "Prepare approved offer",
            "description": "Prepare the customer deliverable.",
            "priority": "normal",
            "source_type": "user",
            "source_reference": "manual",
            "metadata": {"tags": ["sales"]},
            "created_by": "owner",
        }
        defaults.update(values)
        return work.create_work_object(tenant, **defaults)

    def active_assignment(self, tenant="tenant_a"):
        return agent_assignment.activate_assignment(
            tenant,
            agent_assignment.create_assignment(
                tenant,
                "nina_sales_assistant",
                definition_version="1.0.0",
                display_name="Sales",
                configuration={"language": "en"},
                permissions={"allowed_tools": ["files"]},
                assigned_by="owner",
            ).assignment_id,
        )


class UniversalWorkDomainTests(UniversalWorkFixture):
    def test_create_get_list_and_tenant_isolation(self):
        own = self.create("tenant_a")
        other = self.create("tenant_b", title="Other private work")
        self.assertEqual(own.status, "draft")
        self.assertEqual(
            [item.work_object_id for item in work.list_work_objects("tenant_a")],
            [own.work_object_id],
        )
        operations = (
            lambda: work.get_work_object("tenant_a", other.work_object_id),
            lambda: work.update_work_object(
                "tenant_a", other.work_object_id, title="Guess"
            ),
            lambda: work.transition_work_object(
                "tenant_a", other.work_object_id, "open"
            ),
            lambda: work.archive_work_object(
                "tenant_a", other.work_object_id
            ),
        )
        for operation in operations:
            with self.assertRaises(work.UniversalWorkNotFoundError):
                operation()

    def test_closed_types_priorities_sources_and_due_date(self):
        for object_type in sorted(work.OBJECT_TYPES):
            self.create(title=f"type {object_type}", object_type=object_type)
        for priority in sorted(work.PRIORITIES):
            self.create(title=f"priority {priority}", priority=priority)
        valid = self.create(due_at="2026-08-01T10:00:00+03:00")
        self.assertTrue(valid.due_at.endswith("+00:00"))
        invalid = (
            {"object_type": "channel_task"},
            {"source_type": "email"},
            {"due_at": "tomorrow"},
            {"due_at": "2026-08-01T10:00:00"},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(
                work.UniversalWorkValidationError
            ):
                self.create(**values)

    def test_full_lifecycle_completed_cancelled_and_archived(self):
        item = self.create()
        for status in ("open", "in_progress", "waiting", "in_progress", "completed", "archived"):
            item = work.transition_work_object(
                "tenant_a", item.work_object_id, status
            )
        self.assertTrue(item.started_at)
        self.assertTrue(item.completed_at)
        self.assertTrue(item.archived_at)
        with self.assertRaises(work.UniversalWorkTransitionError):
            work.transition_work_object(
                "tenant_a", item.work_object_id, "open"
            )
        with self.assertRaises(work.UniversalWorkConflictError):
            work.update_work_object(
                "tenant_a", item.work_object_id, title="Forbidden"
            )
        cancelled = work.transition_work_object(
            "tenant_a", self.create(title="Cancel").work_object_id, "cancelled"
        )
        self.assertTrue(cancelled.cancelled_at)
        self.assertEqual(
            work.archive_work_object(
                "tenant_a", cancelled.work_object_id
            ).status,
            "archived",
        )

    def test_invalid_transitions_are_rejected(self):
        item = self.create()
        for target in ("completed", "archived", "blocked", "in_progress"):
            with self.subTest(target=target), self.assertRaises(
                work.UniversalWorkTransitionError
            ):
                work.transition_work_object(
                    "tenant_a", item.work_object_id, target
                )

    def test_assignment_same_tenant_active_and_unassign(self):
        assignment = self.active_assignment("tenant_a")
        item = self.create()
        assigned = work.assign_work_object(
            "tenant_a", item.work_object_id, assignment.assignment_id
        )
        self.assertEqual(
            assigned.assigned_agent_assignment_id, assignment.assignment_id
        )
        self.assertEqual(
            work.unassign_work_object(
                "tenant_a", item.work_object_id
            ).assigned_agent_assignment_id,
            "",
        )
        other = self.active_assignment("tenant_b")
        with self.assertRaises(work.UniversalWorkNotFoundError):
            work.assign_work_object(
                "tenant_a", item.work_object_id, other.assignment_id
            )
        archived = agent_assignment.archive_assignment(
            "tenant_a", assignment.assignment_id
        )
        with self.assertRaises(work.UniversalWorkConflictError):
            work.assign_work_object(
                "tenant_a", item.work_object_id, archived.assignment_id
            )
        with self.assertRaises(work.UniversalWorkNotFoundError):
            work.assign_work_object(
                "tenant_a", item.work_object_id, "asg_missing"
            )

    def test_parent_same_tenant_self_and_cycle_protection(self):
        parent = self.create(title="Parent")
        child = self.create(title="Child")
        linked = work.attach_parent(
            "tenant_a", child.work_object_id, parent.work_object_id
        )
        self.assertEqual(linked.parent_work_object_id, parent.work_object_id)
        self.assertEqual(
            [item.work_object_id for item in work.list_children(
                "tenant_a", parent.work_object_id
            )],
            [child.work_object_id],
        )
        with self.assertRaises(work.UniversalWorkValidationError):
            work.attach_parent(
                "tenant_a", parent.work_object_id, parent.work_object_id
            )
        with self.assertRaises(work.UniversalWorkValidationError):
            work.attach_parent(
                "tenant_a", parent.work_object_id, child.work_object_id
            )
        other = self.create("tenant_b", title="Other parent")
        with self.assertRaises(work.UniversalWorkNotFoundError):
            work.attach_parent(
                "tenant_a", child.work_object_id, other.work_object_id
            )
        self.assertEqual(
            work.detach_parent(
                "tenant_a", child.work_object_id
            ).parent_work_object_id,
            "",
        )

    def test_metadata_description_and_identity_boundaries(self):
        invalid = (
            {"description": "x" * (work.MAX_DESCRIPTION_BYTES + 1)},
            {"metadata": {"tenant_id": "other"}},
            {"metadata": {"api_key": "secret"}},
            {"metadata": {"a": {"b": {"c": {"d": {"e": 1}}}}}},
            {"metadata": {"blob": "x" * (work.MAX_METADATA_BYTES + 1)}},
        )
        for values in invalid:
            with self.subTest(values=list(values)), self.assertRaises(
                work.UniversalWorkValidationError
            ):
                self.create(**values)

    def test_search_filters_pagination_and_sql_injection(self):
        self.create("tenant_a", title="Alpine offer", priority="urgent")
        self.create("tenant_a", title="Billing task", description="Alpine")
        self.create("tenant_b", title="Alpine private")
        self.assertEqual(
            len(work.list_work_objects(
                "tenant_a", query="Alpine", limit=100
            )),
            2,
        )
        self.assertEqual(
            work.list_work_objects(
                "tenant_a", query="' OR 1=1 --", limit=100
            ),
            (),
        )
        with self.assertRaises(work.UniversalWorkValidationError):
            work.list_work_objects("tenant_a", limit=101)

    def test_audit_events_capture_lifecycle_and_assignment(self):
        assignment = self.active_assignment()
        item = self.create()
        work.transition_work_object("tenant_a", item.work_object_id, "open")
        work.assign_work_object(
            "tenant_a", item.work_object_id, assignment.assignment_id
        )
        events = work.list_work_events("tenant_a", item.work_object_id)
        self.assertEqual(
            [event["event_type"] for event in events],
            ["work_object_created", "updated", "assigned"],
        )

    def test_workspace_contract_knowledge_and_assignment_references(self):
        assignment = self.active_assignment()
        knowledge = knowledge_vault.create_knowledge_item(
            "tenant_a",
            title="Service policy",
            content="Respond within one business day.",
            knowledge_type="POLICY",
            source_type="MANUAL",
            created_by="owner",
        )
        item = self.create(
            object_type="CLIENT_REQUEST",
            priority="CRITICAL",
            owner_assignment_id=assignment.assignment_id,
            worker_instance_id="worker_instance_sales",
            knowledge_refs=[knowledge.knowledge_id],
            source_channel="web",
        )
        self.assertEqual(item.object_type, "request")
        self.assertEqual(item.priority, "critical")
        self.assertEqual(item.owner_assignment_id, assignment.assignment_id)
        self.assertEqual(item.worker_instance_id, "worker_instance_sales")
        self.assertEqual(item.knowledge_refs, (knowledge.knowledge_id,))
        self.assertEqual(item.source_channel, "web")
        self.assertEqual(item.updated_by, "owner")
        with self.assertRaises(work.UniversalWorkNotFoundError):
            self.create(knowledge_refs=["knowledge_missing"])
        with self.assertRaises(work.UniversalWorkNotFoundError):
            self.create(
                owner_assignment_id=self.active_assignment(
                    "tenant_b"
                ).assignment_id
            )

    def test_existing_modules_are_canonical_adapters(self):
        task = task_engine.create_canonical_task("tenant_a", "Task adapter")
        followup = followup_engine.create_canonical_followup(
            "tenant_a", "Follow-up adapter"
        )
        planner = daily_planner.canonical_daily_work("tenant_a")
        client = self.create(client_id="client_1", title="Client work")
        client_items = client_work_view.canonical_client_work(
            "tenant_a", "client_1"
        )
        self.assertEqual(
            {item.work_object_id for item in planner},
            {task.work_object_id, followup.work_object_id},
        )
        self.assertEqual(
            [item.work_object_id for item in client_items],
            [client.work_object_id],
        )

    def test_migration_adopts_existing_data_and_adds_indexes(self):
        conn = sqlite3.connect(self.db_file)
        try:
            columns = {
                row[1] for row in conn.execute(
                    "PRAGMA table_info(nina_work_objects)"
                ).fetchall()
            }
            indexes = {
                row[1] for row in conn.execute(
                    "PRAGMA index_list(nina_work_objects)"
                ).fetchall()
            }
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertTrue({
            "assigned_agent_assignment_id", "parent_work_object_id",
            "description", "owner_type", "source_type", "due_at",
            "completed_at", "archived_at", "created_by",
            "owner_assignment_id", "worker_instance_id",
            "knowledge_refs_json", "source_channel", "updated_by",
            "closed_at",
        }.issubset(columns))
        self.assertTrue({
            "idx_nina_work_objects_workspace_status",
            "idx_nina_work_objects_workspace_type",
            "idx_nina_work_objects_workspace_assignment",
            "idx_nina_work_objects_workspace_due",
            "idx_nina_work_objects_workspace_parent",
            "idx_nina_work_objects_workspace_owner",
            "idx_nina_work_objects_workspace_created",
            "idx_nina_work_objects_workspace_worker",
        }.issubset(indexes))
        self.assertIn("nina_work_object_events", tables)
        self.assertTrue(work.initialize_universal_work_objects(require_schema=True))

    def test_readiness_fails_closed_without_0012_schema(self):
        incomplete = str(Path(self.temp_dir.name) / "incomplete.sqlite")
        conn = sqlite3.connect(incomplete)
        conn.execute(
            "CREATE TABLE nina_work_objects "
            "(object_id TEXT, workspace_id TEXT, object_type TEXT, "
            "title TEXT, status TEXT)"
        )
        conn.commit()
        conn.close()
        with patch.multiple(
            persistence_backend,
            HOSTED=False,
            USE_POSTGRES=False,
            DATABASE_URL="",
            DB_FILE=incomplete,
        ):
            self.assertFalse(
                work.initialize_universal_work_objects(require_schema=True)
            )


class UniversalWorkApiTests(UniversalWorkFixture):
    def setUp(self):
        super().setUp()
        import web_app

        self.web_app = web_app
        state = RuntimeReadiness("universal-work-api-test")
        state.begin_startup()
        state.run_checks()
        state.complete_startup()
        self.readiness_patch = patch.object(
            web_app, "WEB_RUNTIME_READINESS", state
        )
        self.readiness_patch.start()
        self.env_patch = patch.dict(
            "os.environ", {"NINA_WEB_WORKSPACE_COOKIE_SECRET": "a" * 64}
        )
        self.env_patch.start()
        self.client_a = web_app.app.test_client()
        self.client_b = web_app.app.test_client()

    def tearDown(self):
        self.env_patch.stop()
        self.readiness_patch.stop()
        super().tearDown()

    def test_dashboard_work_objects_csrf_prg_and_rendering(self):
        page = self.client_a.get("/dashboard")
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Work Objects", body)
        self.assertIn("Create Work Object", body)
        self.assertEqual(
            self.client_a.post(
                "/work-objects/create-form",
                data={"title": "No CSRF", "object_type": "TASK"},
            ).status_code,
            403,
        )
        with patch.object(
            self.web_app,
            "current_web_contact",
            return_value={"contact_id": "contact_owner"},
        ):
            created = self.client_a.post(
                "/work-objects/create-form",
                data={
                    "csrf_token": self.web_app._channel_csrf("work:create"),
                    "title": "Dashboard canonical work",
                    "description": "Created through PRG.",
                    "object_type": "TASK",
                    "priority": "HIGH",
                },
            )
        self.assertEqual(created.status_code, 302)
        dashboard = self.client_a.get("/dashboard").get_data(as_text=True)
        self.assertIn("Dashboard canonical work", dashboard)
        self.assertIn(">Edit</summary>", dashboard)
        object_id = re.search(
            r"/work-objects/(wo_[A-Za-z0-9]+)/update-form", dashboard
        ).group(1)
        with patch.object(
            self.web_app,
            "current_web_contact",
            return_value={"contact_id": "contact_owner"},
        ):
            updated = self.client_a.post(
                f"/work-objects/{object_id}/update-form",
                data={
                    "csrf_token": self.web_app._channel_csrf(
                        f"work:update:{object_id}"
                    ),
                    "title": "Dashboard edited work",
                    "description": "Edited through PRG.",
                },
            )
        self.assertEqual(updated.status_code, 302)
        self.assertIn(
            "Dashboard edited work",
            self.client_a.get("/dashboard").get_data(as_text=True),
        )

    def api_create(self, client=None, **values):
        payload = {
            "object_type": "task",
            "title": "API work",
            "priority": "high",
            "source_type": "web",
            "metadata": {"tags": ["api"]},
        }
        payload.update(values)
        return (client or self.client_a).post("/work-objects", json=payload)

    def test_api_crud_lifecycle_and_tenant_isolation(self):
        created = self.api_create()
        self.assertEqual(created.status_code, 201)
        object_id = created.get_json()["work_object"]["id"]
        self.assertEqual(
            self.client_b.get(f"/work-objects/{object_id}").status_code, 404
        )
        self.assertEqual(
            self.client_b.patch(
                f"/work-objects/{object_id}", json={"title": "Guess"}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client_a.patch(
                f"/work-objects/{object_id}", json={"title": "Updated"}
            ).status_code,
            200,
        )
        for target in ("open", "in_progress", "completed", "archived"):
            response = self.client_a.post(
                f"/work-objects/{object_id}/transition",
                json={"status": target},
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client_b.post(
                f"/work-objects/{object_id}/archive", json={}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client_a.get(
                "/work-objects?query=Updated&limit=10&offset=0"
            ).status_code,
            200,
        )

    def test_api_rejects_mass_assignment_and_filter_abuse(self):
        forbidden = (
            {"tenant_id": "tenant_b"}, {"work_object_id": "chosen"},
            {"created_by": "admin"}, {"status": "completed"},
            {"completed_at": "2026-01-01T00:00:00Z"},
            {"archived_at": "2026-01-01T00:00:00Z"},
        )
        for extra in forbidden:
            with self.subTest(extra=extra):
                self.assertEqual(self.api_create(**extra).status_code, 400)
        self.assertEqual(
            self.client_a.get("/work-objects?limit=1000").status_code, 400
        )
        self.assertEqual(
            self.client_a.post(
                "/work-objects", data="{bad", content_type="application/json"
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
