import inspect
import os
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class ExecutionLayerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "execution.sqlite")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import approval_layer
        import execution_layer
        import initiative_engine
        import managed_migrations
        import reply_builder
        import web_app
        import work_objects
        cls.approval = approval_layer
        cls.execution = execution_layer
        cls.initiative = initiative_engine
        cls.migrations = managed_migrations
        cls.reply = reply_builder
        cls.web = web_app
        cls.work = work_objects
        cls.restore = bind_sqlite_database(
            cls.db_file, approval_layer, execution_layer, managed_migrations,
            work_objects, web_app,
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
            "nina_execution_events", "nina_executions",
            "nina_approval_events", "nina_approvals",
            "nina_work_object_events", "nina_work_objects",
        ):
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
        cur.close()
        conn.close()
        self.now = datetime.now(timezone.utc).replace(microsecond=0)

    def candidate(self, *, workspace=None, action="REMIND", approval_status="approved"):
        workspace = workspace or self.workspace
        if action == "FOLLOW_UP":
            item = self.work.create_work_object(
                "followup_task", "Execution follow-up", workspace_id=workspace,
                status="open", origin_channel="web",
                origin_user_id="contact-a",
            )
        else:
            item = self.work.create_work_object(
                "task", "Execution reminder", workspace_id=workspace,
                status="open",
                due_date=(self.now + timedelta(days=1)).isoformat(),
                origin_channel="web", origin_user_id="contact-a",
            )
        initiative = self.initiative.initiative_queue(
            workspace, limit=100,
        )[0]
        reply = self.reply.ReplyBuilder.build(initiative)
        approval = self.approval.ensure_approval(
            workspace, initiative.initiative_id, reply.reply_id,
            item.object_id,
        )
        if approval_status != "pending":
            decision = {
                "approved": "approved",
                "dismissed": "dismissed",
                "snoozed": "snoozed",
            }[approval_status]
            values = {}
            if decision == "snoozed":
                values["snoozed_until"] = (
                    self.now + timedelta(hours=1)
                ).isoformat()
            approval = self.approval.decide(
                workspace, initiative.initiative_id, reply.reply_id, decision,
                decided_by="owner-a", **values,
            )
        return item, initiative, reply, approval

    def execute(self, approval, **values):
        return self.execution.execute_approved(
            approval.workspace_id, approval.approval_id, "owner-a", **values,
        )

    def reminders(self, workspace=None):
        return self.work.list_work_objects(
            workspace_id=workspace or self.workspace,
            object_type="reminder",
        )

    def events(self, execution_id):
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT event_type,previous_status,new_status,safe_metadata "
            "FROM nina_execution_events WHERE execution_id=? "
            "ORDER BY created_at,event_id",
            (execution_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    def no_action(self, approval, reply):
        return patch.object(
            self.execution.ReplyBuilder, "build",
            return_value=replace(reply, suggested_action="NO_ACTION"),
        )

    def test_01_approved_remind_executes(self):
        *_, approval = self.candidate()
        self.assertEqual(self.execute(approval).status, "succeeded")

    def test_02_remind_creates_one_canonical_active_reminder(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        reminders = self.reminders()
        self.assertEqual(len(reminders), 1)
        self.assertEqual((reminders[0].status, result.result_type), ("active", "reminder"))

    def test_03_reminder_preserves_source_work_object(self):
        item, *_, approval = self.candidate()
        result = self.execute(approval)
        self.assertEqual(
            self.work.get_work_object(result.result_reference).metadata[
                "source_work_object_id"
            ],
            item.object_id,
        )

    def test_04_reminder_preserves_workspace(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        self.assertEqual(
            self.work.get_work_object(result.result_reference).workspace_id,
            self.workspace,
        )

    def test_05_reminder_time_is_future(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        planned = self.work.get_work_object(result.result_reference).metadata["planned_at"]
        self.assertGreater(datetime.fromisoformat(planned), self.now)

    def test_06_delivery_history_starts_empty(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        reminder = self.work.get_work_object(result.result_reference)
        self.assertEqual(reminder.metadata["delivery_history"], [])

    def test_07_repeat_execute_creates_no_second_reminder(self):
        *_, approval = self.candidate()
        first = self.execute(approval)
        second = self.execute(approval)
        self.assertEqual(first, second)
        self.assertEqual(len(self.reminders()), 1)

    def test_08_parallel_execute_creates_no_second_reminder(self):
        *_, approval = self.candidate()
        entered = threading.Event()
        release = threading.Event()
        original = self.execution._create_reminder

        def delayed(*args, **kwargs):
            entered.set()
            release.wait(5)
            return original(*args, **kwargs)

        results = []
        with patch.object(self.execution, "_create_reminder", side_effect=delayed):
            first = threading.Thread(
                target=lambda: results.append(self.execute(approval)),
            )
            first.start()
            self.assertTrue(entered.wait(5))
            results.append(self.execute(approval))
            release.set()
            first.join(5)
        self.assertEqual(len(self.reminders()), 1)
        self.assertEqual(len({
            item.execution_id for item in results
        }), 1)

    def test_09_no_action_succeeds(self):
        *_, reply, approval = self.candidate()
        with self.no_action(approval, reply):
            result = self.execute(approval)
        self.assertEqual((result.status, result.result_type), ("succeeded", "no_action"))

    def test_10_no_action_has_no_other_mutations(self):
        item, _, reply, approval = self.candidate()
        before = self.work.get_work_object(item.object_id)
        with self.no_action(approval, reply):
            self.execute(approval)
        after = self.work.get_work_object(item.object_id)
        self.assertEqual(before, after)
        self.assertEqual(self.reminders(), [])

    def test_11_follow_up_is_unsupported(self):
        *_, approval = self.candidate(action="FOLLOW_UP")
        result = self.execute(approval)
        self.assertEqual((result.status, result.error_code), ("unsupported", "unsupported_action"))

    def test_12_check_in_is_unsupported(self):
        _, _, reply, approval = self.candidate()
        with patch.object(
            self.execution.ReplyBuilder, "build",
            return_value=replace(reply, suggested_action="CHECK_IN"),
        ):
            result = self.execute(approval)
        self.assertEqual(result.status, "unsupported")

    def test_13_ask_for_update_is_unsupported(self):
        _, _, reply, approval = self.candidate()
        with patch.object(
            self.execution.ReplyBuilder, "build",
            return_value=replace(reply, suggested_action="ASK_FOR_UPDATE"),
        ):
            result = self.execute(approval)
        self.assertEqual(result.error_code, "unsupported_action")

    def test_14_pending_approval_rejected(self):
        *_, approval = self.candidate(approval_status="pending")
        with self.assertRaisesRegex(self.execution.ExecutionError, "approval_not_approved"):
            self.execute(approval)

    def test_15_dismissed_approval_rejected(self):
        *_, approval = self.candidate(approval_status="dismissed")
        with self.assertRaisesRegex(self.execution.ExecutionError, "approval_not_approved"):
            self.execute(approval)

    def test_16_snoozed_approval_rejected(self):
        *_, approval = self.candidate(approval_status="snoozed")
        with self.assertRaisesRegex(self.execution.ExecutionError, "approval_not_approved"):
            self.execute(approval)

    def test_17_forged_approval_rejected(self):
        with self.assertRaisesRegex(self.execution.ExecutionError, "approval_not_found"):
            self.execution.execute_approved(
                self.workspace, "approval_forged", "owner-a",
            )

    def test_18_cross_workspace_rejected(self):
        *_, approval = self.candidate()
        with self.assertRaisesRegex(self.execution.ExecutionError, "approval_not_found"):
            self.execution.execute_approved(
                "other-workspace", approval.approval_id, "owner-a",
            )

    def test_19_forged_action_is_ignored(self):
        *_, approval = self.candidate()
        response = self.post_execute(approval, action="FOLLOW_UP")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.execution.get_execution(
            self.workspace, approval.approval_id,
        ).action_type, "REMIND")

    def test_20_forged_work_object_is_ignored(self):
        *_, approval = self.candidate()
        self.post_execute(approval, work_object_id="forged")
        execution = self.execution.get_execution(
            self.workspace, approval.approval_id,
        )
        self.assertEqual(execution.work_object_id, approval.work_object_id)

    def test_21_forged_reminder_time_is_ignored(self):
        *_, approval = self.candidate()
        self.post_execute(approval, reminder_at="2000-01-01T00:00:00Z")
        reminder = self.reminders()[0]
        self.assertGreater(
            datetime.fromisoformat(reminder.metadata["planned_at"]), self.now,
        )

    def test_22_stale_initiative_rejected(self):
        item, *_, approval = self.candidate()
        self.work.update_work_object(item.object_id, status="done")
        with self.assertRaisesRegex(self.execution.ExecutionError, "stale_initiative"):
            self.execute(approval)

    def test_23_stale_reply_rejected(self):
        _, _, reply, approval = self.candidate()
        with patch.object(
            self.execution.ReplyBuilder, "build",
            return_value=replace(reply, reply_id="reply:stale"),
        ):
            with self.assertRaisesRegex(self.execution.ExecutionError, "stale_reply"):
                self.execute(approval)

    def test_24_stale_work_object_rejected(self):
        item, *_, approval = self.candidate()
        conn = self.work._connect()
        conn.execute("DELETE FROM nina_work_objects WHERE object_id=?", (item.object_id,))
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(self.execution.ExecutionError, "stale_work_object"):
            self.execute(approval)

    def test_25_execution_persists(self):
        *_, approval = self.candidate()
        created = self.execute(approval)
        self.assertEqual(
            self.execution.get_execution(
                self.workspace, approval.approval_id,
            ),
            created,
        )

    def test_26_execution_audit_events(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        self.assertEqual(
            [row[0] for row in self.events(result.execution_id)],
            ["execution_created", "execution_started", "execution_succeeded"],
        )

    def test_27_status_transitions_are_controlled(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        transitions = [(row[1], row[2]) for row in self.events(result.execution_id)]
        self.assertEqual(
            transitions,
            [("", "pending"), ("pending", "processing"), ("processing", "succeeded")],
        )

    def test_28_failed_reminder_does_not_succeed(self):
        *_, approval = self.candidate()
        with patch.object(
            self.execution, "_create_reminder",
            side_effect=RuntimeError("secret detail"),
        ):
            result = self.execute(approval)
        self.assertEqual((result.status, result.error_code), ("failed", "reminder_creation_failed"))
        self.assertNotIn("secret detail", result.error_summary)

    def test_29_response_retry_returns_existing_result(self):
        *_, approval = self.candidate()
        first = self.execute(approval)
        second = self.execute(approval, idempotency_key="response-retry")
        self.assertEqual(first, second)
        self.assertEqual(len(self.reminders()), 1)

    def post_execute(self, approval, **forged):
        data = {
            "approval_id": approval.approval_id,
            "csrf_token": self.web._channel_csrf(
                f"execution:run:{approval.approval_id}"
            ),
            **forged,
        }
        return self.web.app.test_client().post("/executions/run", data=data)

    def test_30_post_redirect_get(self):
        *_, approval = self.candidate()
        response = self.post_execute(approval)
        self.assertEqual(response.status_code, 302)
        self.assertIn("execution_status=succeeded", response.headers["Location"])

    def test_31_dashboard_execution_rendering(self):
        *_, approval = self.candidate()
        body = self.web.app.test_client().get("/dashboard").get_data(as_text=True)
        self.assertIn("Execution", body)
        self.assertIn("Execute", body)
        self.assertIn(approval.approval_id, body)

    def test_32_refresh_does_not_execute_again(self):
        *_, approval = self.candidate()
        self.post_execute(approval)
        client = self.web.app.test_client()
        client.get("/dashboard")
        client.get("/dashboard")
        self.assertEqual(len(self.reminders()), 1)

    def test_33_approval_regression(self):
        *_, approval = self.candidate()
        self.execute(approval)
        saved = self.approval.get_approval_by_id(
            self.workspace, approval.approval_id,
        )
        self.assertEqual((saved.status, saved.decision), ("approved", "approved"))

    def test_34_reply_builder_regression(self):
        _, initiative, reply, _ = self.candidate()
        self.assertEqual(self.reply.ReplyBuilder.build(initiative), reply)

    def test_35_initiative_regression(self):
        _, initiative, _, _ = self.candidate()
        self.assertEqual(
            self.initiative.initiative_queue(self.workspace)[0].initiative_id,
            initiative.initiative_id,
        )

    def test_36_active_reminder_regression(self):
        *_, approval = self.candidate()
        result = self.execute(approval)
        reminder = self.work.get_work_object(result.result_reference)
        self.assertEqual(reminder.metadata["delivery_status"], "scheduled")
        self.assertEqual(reminder.metadata["attempt_count"], 0)

    def test_37_planner_regression(self):
        item, *_, approval = self.candidate()
        from daily_planner import canonical_daily_work
        before = [row.work_object_id for row in canonical_daily_work(self.workspace)]
        self.execute(approval)
        after = [row.work_object_id for row in canonical_daily_work(self.workspace)]
        self.assertIn(item.object_id, before)
        self.assertIn(item.object_id, after)

    def test_38_workspace_isolation_regression(self):
        self.candidate(workspace="other-workspace")
        *_, approval = self.candidate()
        self.execute(approval)
        self.assertEqual(len(self.reminders("other-workspace")), 0)

    def test_39_managed_migration_contract(self):
        identifiers = [item.identifier for item in self.migrations.MIGRATIONS]
        self.assertIn("0006_execution_layer_v1", identifiers)
        self.assertLess(
            identifiers.index("0006_execution_layer_v1"),
            identifiers.index("0007_autonomy_framework_v1"),
        )

    def test_40_web_core_runtime_boundary(self):
        source = inspect.getsource(self.web.execution_run)
        self.assertNotIn("scheduler", source)
        self.assertNotIn("send_", source)
        self.assertNotIn("telegram", source.lower())


if __name__ == "__main__":
    unittest.main()
