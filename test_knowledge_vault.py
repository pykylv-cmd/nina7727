import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge_vault
import managed_migrations
import persistence_backend


class KnowledgeVaultFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp.name) / "vault.sqlite")
        self.backend = patch.multiple(
            persistence_backend, HOSTED=False, USE_POSTGRES=False,
            DATABASE_URL="", DB_FILE=self.db_file,
        )
        self.backend.start()
        managed_migrations.run_migrations()

    def tearDown(self):
        self.backend.stop()
        self.temp.cleanup()

    def create(self, workspace="workspace_a", **values):
        data = {
            "title": "Support hours",
            "content": "Support is available from 09:00 to 17:00.",
            "knowledge_type": "FACT",
            "source_type": "MANUAL",
            "source_reference": "Owner entry",
            "tags": ["support", "hours"],
            "created_by": "owner",
        }
        data.update(values)
        return knowledge_vault.create_knowledge_item(workspace, **data)


class KnowledgeVaultDomainTests(KnowledgeVaultFixture):
    def test_create_model_checksum_and_audit(self):
        item = self.create()
        self.assertEqual(item.status, "ACTIVE")
        self.assertEqual(item.version, 1)
        self.assertEqual(len(item.content_checksum), 64)
        self.assertEqual(
            knowledge_vault.list_knowledge_events("workspace_a")[0][3],
            "knowledge_created",
        )

    def test_required_and_closed_vocabularies(self):
        for field, value in (
            ("title", ""), ("content", ""),
            ("knowledge_type", "UNKNOWN"), ("source_type", "WEB"),
        ):
            with self.subTest(field=field), self.assertRaises(
                knowledge_vault.KnowledgeVaultValidationError
            ):
                self.create(**{field: value})
        with self.assertRaises(knowledge_vault.KnowledgeVaultValidationError):
            self.create(source_type="IMPORTED_TEXT", source_reference="")

    def test_all_types_and_statuses(self):
        for index, value in enumerate(sorted(knowledge_vault.KNOWLEDGE_TYPES)):
            self.create(title=f"Item {index}", knowledge_type=value)
        item = self.create(title="Archive")
        archived = knowledge_vault.archive_knowledge_item(
            "workspace_a", item.knowledge_id
        )
        self.assertEqual(archived.status, "ARCHIVED")

    def test_update_versions_idempotence_and_concurrency(self):
        item = self.create()
        unchanged = knowledge_vault.update_knowledge_item(
            "workspace_a", item.knowledge_id,
            expected_version=1, content=item.content,
        )
        self.assertEqual(unchanged.version, 1)
        changed = knowledge_vault.update_knowledge_item(
            "workspace_a", item.knowledge_id,
            expected_version=1, content="Support is available every weekday.",
        )
        self.assertEqual(changed.version, 2)
        self.assertEqual(
            [entry.version for entry in knowledge_vault.list_knowledge_versions(
                "workspace_a", item.knowledge_id
            )],
            [2, 1],
        )
        with self.assertRaises(knowledge_vault.KnowledgeVaultConflictError):
            knowledge_vault.update_knowledge_item(
                "workspace_a", item.knowledge_id,
                expected_version=1, content="Stale edit",
            )

    def test_archive_preserves_versions_and_default_search_excludes(self):
        item = self.create()
        knowledge_vault.update_knowledge_item(
            "workspace_a", item.knowledge_id, content="Version two"
        )
        knowledge_vault.archive_knowledge_item(
            "workspace_a", item.knowledge_id
        )
        self.assertEqual(
            len(knowledge_vault.list_knowledge_versions(
                "workspace_a", item.knowledge_id
            )),
            2,
        )
        self.assertEqual(knowledge_vault.list_tenant_knowledge("workspace_a"), ())
        self.assertEqual(
            len(knowledge_vault.list_tenant_knowledge(
                "workspace_a", status="ARCHIVED"
            )),
            1,
        )

    def test_search_title_content_type_tag_limit_and_stable_order(self):
        self.create(title="Alpine policy", knowledge_type="POLICY", tags=["alpine"])
        self.create(title="Billing", content="Alpine service price", knowledge_type="SERVICE")
        self.assertEqual(len(knowledge_vault.list_tenant_knowledge(
            "workspace_a", query="Alpine"
        )), 2)
        self.assertEqual(len(knowledge_vault.list_tenant_knowledge(
            "workspace_a", knowledge_type="POLICY"
        )), 1)
        self.assertEqual(len(knowledge_vault.list_tenant_knowledge(
            "workspace_a", tag="alpine"
        )), 1)
        first = knowledge_vault.list_tenant_knowledge(
            "workspace_a", query="Alpine", limit=1
        )
        second = knowledge_vault.list_tenant_knowledge(
            "workspace_a", query="Alpine", limit=1
        )
        self.assertEqual(first, second)

    def test_workspace_isolation_for_get_update_archive_search_and_audit(self):
        private = self.create("workspace_b", title="Private")
        operations = (
            lambda: knowledge_vault.get_knowledge_item(
                "workspace_a", private.knowledge_id
            ),
            lambda: knowledge_vault.update_knowledge_item(
                "workspace_a", private.knowledge_id, content="Guess"
            ),
            lambda: knowledge_vault.archive_knowledge_item(
                "workspace_a", private.knowledge_id
            ),
        )
        for operation in operations:
            with self.assertRaises(knowledge_vault.KnowledgeVaultNotFoundError):
                operation()
        self.assertEqual(
            knowledge_vault.list_tenant_knowledge(
                "workspace_a", query="Private"
            ),
            (),
        )
        self.assertEqual(
            knowledge_vault.list_knowledge_events("workspace_a"), ()
        )

    def test_audit_is_safe_and_secret_content_rejected(self):
        with self.assertRaises(knowledge_vault.KnowledgeVaultValidationError):
            self.create(content="api_key=do-not-store-this")
        item = self.create()
        knowledge_vault.update_knowledge_item(
            "workspace_a", item.knowledge_id, content="Safe update"
        )
        knowledge_vault.archive_knowledge_item(
            "workspace_a", item.knowledge_id
        )
        encoded = json.dumps(
            knowledge_vault.list_knowledge_events("workspace_a")
        ).casefold()
        self.assertNotIn("api_key", encoded)
        self.assertIn("knowledge_updated", encoded)
        self.assertIn("knowledge_archived", encoded)

    def test_worker_assignment_and_rolepack_changes_do_not_change_vault(self):
        import agent_assignment
        import worker_catalog
        from platform_core import initialize_platform_runtime
        initialize_platform_runtime({
            name: (lambda: True) for name in (
                "persistence_backend", "deployment_compatibility",
                "work_objects", "contact_identity", "message_service",
                "channel_services", "rolepack_system", "ready_worker_catalog",
                "agent_assignment", "knowledge_vault",
                "universal_work_objects",
            )
        })
        item = self.create()
        worker_catalog.set_workspace_worker(
            "workspace_a", "office_manager", updated_by="owner"
        )
        worker_catalog.set_workspace_worker(
            "workspace_a", "sales_assistant", updated_by="owner"
        )
        assignment = agent_assignment.get_workspace_assignment("workspace_a")
        self.assertEqual(assignment.status, "ACTIVE")
        self.assertEqual(
            knowledge_vault.get_knowledge_item(
                "workspace_a", item.knowledge_id
            ).content,
            item.content,
        )

    def test_migration_and_readiness(self):
        self.assertTrue(
            knowledge_vault.initialize_knowledge_vault(
                require_schema=True
            )["ok"]
        )
        conn = sqlite3.connect(self.db_file)
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            migrations = {
                row[0] for row in conn.execute(
                    "SELECT migration_identifier FROM nina_schema_migrations"
                )
            }
        finally:
            conn.close()
        self.assertTrue({
            "nina_knowledge_items", "nina_knowledge_versions",
            "nina_knowledge_events",
        }.issubset(tables))
        self.assertIn("0011_knowledge_vault_v1", migrations)
        managed_migrations.run_migrations()

    def test_readiness_is_false_without_complete_schema(self):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute("DROP TABLE nina_knowledge_events")
            conn.commit()
        finally:
            conn.close()
        self.assertFalse(
            knowledge_vault.initialize_knowledge_vault(require_schema=True)
        )


class KnowledgeVaultWebTests(KnowledgeVaultFixture):
    def setUp(self):
        super().setUp()
        import web_app
        self.web_app = web_app
        self.env = patch.dict(
            "os.environ", {"NINA_WEB_WORKSPACE_COOKIE_SECRET": "k" * 64}
        )
        self.env.start()
        self.workspace = patch.object(
            web_app, "current_workspace_id", return_value="workspace_a"
        )
        self.workspace.start()
        self.contact = patch.object(
            web_app,
            "current_web_contact",
            return_value={"contact_id": "contact_owner"},
        )
        self.contact.start()
        self.client = web_app.app.test_client()

    def tearDown(self):
        self.contact.stop()
        self.workspace.stop()
        self.env.stop()
        super().tearDown()

    def test_api_server_workspace_validation_and_permissions_registry(self):
        response = self.client.post("/knowledge-vault/items", json={
            "title": "API fact", "content": "Canonical information",
            "knowledge_type": "FACT", "source_type": "MANUAL",
            "tags": ["api"],
        })
        self.assertEqual(response.status_code, 201)
        item = response.get_json()["item"]
        self.assertNotIn("workspace_id", item)
        archived = self.client.post(
            f"/knowledge-vault/items/{item['knowledge_id']}/archive",
            json={},
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(
            self.client.get("/knowledge-vault/items").get_json()["items"], []
        )
        archived_items = self.client.get(
            "/knowledge-vault/items?status=ARCHIVED"
        ).get_json()["items"]
        self.assertEqual(
            [entry["knowledge_id"] for entry in archived_items],
            [item["knowledge_id"]],
        )
        self.assertEqual(
            self.client.post("/knowledge-vault/items", json={
                "workspace_id": "other", "title": "Attack",
                "content": "Bad", "knowledge_type": "FACT",
                "source_type": "MANUAL",
            }).status_code,
            400,
        )
        from permission_engine import get_permission_rule
        for permission in (
            "knowledge_read", "knowledge_write", "knowledge_archive",
            "knowledge_audit_view",
        ):
            self.assertIsNotNone(get_permission_rule(permission))

    def test_dashboard_render_csrf_prg_and_html_escape(self):
        item = self.create(
            title="<script>alert(1)</script>",
            content="<b>stored text is escaped</b>",
        )
        page = self.client.get("/dashboard")
        body = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Knowledge Vault", body)
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("action='/knowledge-vault/create'", body)
        rejected = self.client.post("/knowledge-vault/create", data={
            "title": "No CSRF", "content": "No", "knowledge_type": "FACT",
            "source_type": "MANUAL",
        })
        self.assertEqual(rejected.status_code, 403)
        token = self.web_app._channel_csrf(
            f"knowledge:archive:{item.knowledge_id}"
        )
        archived = self.client.post(
            f"/knowledge-vault/{item.knowledge_id}/archive",
            data={"csrf_token": token},
        )
        self.assertEqual(archived.status_code, 302)


if __name__ == "__main__":
    unittest.main()
