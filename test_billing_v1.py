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

    def test_atomic_reservation_allows_below_limit_denies_at_limit_and_deduplicates(self):
        billing_service.set_override("workspace_a", "limit.workers", 1)
        first = billing_service.reserve_usage(
            "workspace_a", "workers", "request_one",
            source_type="agent_assignment",
        )
        duplicate = billing_service.reserve_usage(
            "workspace_a", "workers", "request_one",
            source_type="agent_assignment",
        )
        self.assertTrue(first["recorded"])
        self.assertFalse(duplicate["recorded"])
        with self.assertRaises(billing_service.BillingLimitError):
            billing_service.reserve_usage(
                "workspace_a", "workers", "request_two",
                source_type="agent_assignment",
            )
        self.assertEqual(billing_service.get_usage("workspace_a", "workers", "all", "all"), 1)

    def test_subscription_assignment_status_change_and_override_removal_are_audited(self):
        plan = billing_service.create_plan("team", "Team")
        assigned = billing_service.change_workspace_plan("workspace_a", plan["plan_id"])
        self.assertEqual(assigned["plan_id"], plan["plan_id"])
        changed = billing_service.set_subscription_status("workspace_a", "suspended")
        self.assertEqual(changed["status"], "suspended")
        self.assertEqual(billing_service.get_workspace_subscription("workspace_a")["status"], "suspended")
        billing_service.set_override("workspace_a", "limit.channels", 2)
        self.assertTrue(billing_service.deactivate_override("workspace_a", "limit.channels"))
        kinds = {row[1] for row in billing_service.list_billing_events("workspace_a")}
        self.assertTrue({"plan_changed", "subscription_status_changed", "entitlement_override_deactivated"}.issubset(kinds))

    def test_usage_invoice_and_event_lists_are_workspace_scoped(self):
        billing_service.record_usage("workspace_a", "channels", idempotency_key="a")
        billing_service.record_usage("workspace_b", "channels", idempotency_key="b")
        billing_service.get_workspace_subscription("workspace_a")
        self.assertEqual(len(billing_service.list_usage("workspace_a")), 1)
        self.assertEqual(billing_service.list_usage("workspace_a")[0][4], "")
        self.assertEqual(billing_service.list_invoices("workspace_a"), ())
        self.assertTrue(billing_service.list_billing_events("workspace_a"))

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

    def test_admin_render_includes_usage_invoices_events_and_write_controls(self):
        subscription = {"plan_id":"plan_legacy","status":"active","source":"grandfathered"}
        plan = {"plan_id":"plan_legacy","display_name":"Grandfathered"}
        with patch.multiple(self.web_app,
            get_workspace_subscription=lambda _w: subscription,
            list_plans=lambda **_k: (plan,),
            get_effective_entitlements=lambda _w: {"limit.workers": 2},
            list_usage=lambda _w: (("workers",1,"count","agent_assignment","a","now"),),
            list_invoices=lambda _w: (),
            list_billing_events=lambda _w: (("e","plan_changed","platform_admin","{}","now"),)):
            body = self.web_app._billing_summary("workspace_a", admin=True)
        for text in ("Subscription status", "Remove override", "Usage", "Invoices / payments", "Billing events"):
            self.assertIn(text, body)

    def test_structured_limit_denial_for_assignment_creation(self):
        with patch.object(self.web_app, "_billing_reserve", side_effect=billing_service.BillingLimitError("billing_limit_reached")):
            response = self.client.post("/agent-assignments", json={"ready_worker_definition_id":"worker", "display_name":"Worker"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["error"], "billing_limit_reached")

    def test_enforcement_denies_knowledge_work_and_channel_creation_only(self):
        denial = billing_service.BillingLimitError("billing_limit_reached")
        with patch.object(self.web_app, "_billing_reserve", side_effect=denial), patch.object(self.web_app, "_knowledge_permission", return_value=True):
            knowledge = self.client.post("/knowledge-vault/items", json={"title":"Title", "content":"Content"})
        self.assertEqual(knowledge.status_code, 429)
        self.assertEqual(knowledge.get_json()["metric"], "knowledge_items")
        with patch.object(self.web_app, "_billing_reserve", side_effect=denial):
            work = self.client.post("/work-objects", json={"object_type":"task", "title":"Task"})
        self.assertEqual(work.status_code, 429)
        self.assertEqual(work.get_json()["metric"], "work_objects")
        with patch.object(self.web_app, "_billing_reserve", side_effect=denial), patch.object(self.web_app, "_channel_permission", return_value=True), patch.object(self.web_app, "_valid_channel_csrf", return_value=True), patch.object(self.web_app, "disconnect_channel") as disconnect:
            channel = self.client.post("/channel-layer/create", data={"channel_type":"email"})
        self.assertEqual(channel.status_code, 302)
        disconnect.assert_not_called()

    def test_admin_login_regression_and_client_admin_isolation(self):
        with patch.object(self.web_app, "verify_bootstrap_token", return_value=True):
            response = self.client.post("/admin/login", data={"bootstrap_token":" valid "})
        self.assertEqual(response.status_code, 302)
        self.assertIn("nina_platform_admin=", response.headers.get("Set-Cookie", ""))
        with patch.object(self.web_app, "current_web_role", return_value="client"):
            self.assertEqual(self.client.get("/admin/billing").status_code, 403)


if __name__ == "__main__":
    unittest.main()
