import sqlite3
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import billing_service
import managed_migrations
import persistence_backend
from billing_provider import ManualBillingProvider, NullBillingProvider


class BillingV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "billing.sqlite")
        self.backend_patch = patch.multiple(
            persistence_backend, HOSTED=False, USE_POSTGRES=False,
            DATABASE_URL="", DB_FILE=self.db_file,
        )
        self.backend_patch.start()
        managed_migrations.run_migrations()

    def tearDown(self):
        self.backend_patch.stop(); self.temp_dir.cleanup()

    def test_migration_and_readiness(self):
        conn = sqlite3.connect(self.db_file)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertTrue(billing_service.REQUIRED_TABLES.issubset(tables))
        self.assertTrue(billing_service.initialize_billing_service(require_schema=True)["ok"])

    def test_legacy_compatibility_is_idempotent_and_audited(self):
        first = billing_service.get_workspace_subscription("workspace_a")
        second = billing_service.get_workspace_subscription("workspace_a")
        self.assertEqual(first["subscription_id"], second["subscription_id"])
        self.assertEqual(first["source"], "grandfathered")
        self.assertEqual(len(billing_service.list_billing_events("workspace_a")), 1)

    def test_effective_resolution_override_precedes_plan(self):
        self.assertTrue(billing_service.check_entitlement("workspace_a", "core.access"))
        billing_service.set_override("workspace_a", "core.access", False)
        self.assertFalse(billing_service.check_entitlement("workspace_a", "core.access"))

    def test_usage_idempotency_and_tenant_isolation(self):
        one = billing_service.record_usage("workspace_a", "work_objects", idempotency_key="same")
        duplicate = billing_service.record_usage("workspace_a", "work_objects", idempotency_key="same")
        other = billing_service.record_usage("workspace_b", "work_objects", idempotency_key="same")
        self.assertTrue(one["recorded"]); self.assertFalse(duplicate["recorded"])
        self.assertEqual(other["quantity"], 1)
        self.assertEqual(billing_service.get_usage("workspace_a", "work_objects", "all", "all"), 1)

    def test_limit_check_and_plan_change_audit(self):
        billing_service.set_override("workspace_a", "limit.work_objects", 1)
        self.assertTrue(billing_service.check_limit("workspace_a", "work_objects")["allowed"])
        billing_service.record_usage("workspace_a", "work_objects", idempotency_key="one")
        self.assertFalse(billing_service.check_limit("workspace_a", "work_objects")["allowed"])
        changed = billing_service.change_workspace_plan("workspace_a", "legacy")
        self.assertEqual(changed["plan_id"], "plan_legacy")

    def test_provider_boundary_has_safe_null_and_manual_implementations(self):
        self.assertFalse(NullBillingProvider().create_customer("workspace_a").ok)
        self.assertTrue(ManualBillingProvider().create_customer("workspace_a").ok)

    def test_plan_lifecycle_entitlements_and_override_deactivation(self):
        plan = billing_service.create_plan("starter", "Starter", price_minor=900)
        billing_service.set_plan_entitlement(plan["plan_id"], "feature.chat", True)
        billing_service.change_workspace_plan("workspace_a", plan["plan_id"])
        self.assertTrue(billing_service.check_entitlement("workspace_a", "feature.chat"))
        billing_service.set_override("workspace_a", "feature.chat", False)
        self.assertFalse(billing_service.check_entitlement("workspace_a", "feature.chat"))
        self.assertTrue(billing_service.deactivate_override("workspace_a", "feature.chat"))
        self.assertTrue(billing_service.check_entitlement("workspace_a", "feature.chat"))
        self.assertEqual(billing_service.update_plan(plan["plan_id"], status="inactive")["status"], "inactive")


class BillingWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "b" * 64)
        import web_app
        cls.web_app = web_app
        cls.client = web_app.app.test_client()

    def test_client_billing_is_read_only_and_server_workspace_scoped(self):
        with patch.object(self.web_app, "_billing_summary", return_value="Billing summary") as summary:
            response = self.client.get("/billing?workspace_id=forged")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Billing summary", response.data)
        self.assertNotEqual(summary.call_args.args[0], "forged")
        self.assertFalse(summary.call_args.kwargs.get("admin", False))

    def test_admin_billing_requires_admin_and_csrf(self):
        with patch.object(self.web_app, "current_web_role", return_value="client"):
            self.assertEqual(self.client.get("/admin/billing").status_code, 403)
        with patch.object(self.web_app, "current_web_role", return_value="platform_admin"):
            response = self.client.post("/admin/billing/plan", data={"workspace_id":"workspace_a","plan_id":"legacy"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
