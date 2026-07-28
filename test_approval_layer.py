import inspect
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class ApprovalLayerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "approval.db")
        cls.env = patch.dict(
            os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file},
        )
        cls.env.start()
        import approval_layer
        import initiative_engine
        import managed_migrations
        import reply_builder
        import web_app
        import work_objects
        cls.approval = approval_layer
        cls.initiative = initiative_engine
        cls.migrations = managed_migrations
        cls.reply = reply_builder
        cls.web = web_app
        cls.work = work_objects
        cls.restore = bind_sqlite_database(
            cls.db_file, managed_migrations, work_objects, web_app,
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
        cur.execute("DELETE FROM nina_approval_events")
        cur.execute("DELETE FROM nina_approvals")
        cur.execute("DELETE FROM nina_work_objects")
        conn.commit()
        cur.close()
        conn.close()
        self.now = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)

    def candidate(self, workspace=None):
        workspace = workspace or self.workspace
        item = self.work.create_work_object(
            "task", "Approval controlled task", workspace_id=workspace,
            status="open", due_date=(self.now - timedelta(days=1)).isoformat(),
            client_id="client-a",
        )
        initiative = self.initiative.detect_initiatives(
            workspace, objects=[item], now=self.now,
        )[0]
        reply = self.reply.ReplyBuilder.build(initiative)
        record = self.approval.ensure_approval(
            workspace, initiative.initiative_id, reply.reply_id, item.object_id,
            now=self.now,
        )
        return item, initiative, reply, record

    def decide(self, decision, **values):
        item, initiative, reply, record = self.candidate()
        result = self.approval.decide(
            self.workspace, initiative.initiative_id, reply.reply_id, decision,
            decided_by="owner-a", now=self.now, **values,
        )
        return item, initiative, reply, record, result

    def event_count(self):
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nina_approval_events")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    def test_01_pending_approval_rendering(self):
        self.candidate()
        body = self.web.app.test_client().get("/dashboard").get_data(as_text=True)
        self.assertIn("Approval status: Pending", body)

    def test_02_approve_persistence(self):
        *_, result = self.decide("approved")
        self.assertEqual(result.status, "approved")

    def test_03_approve_after_refresh_stays_approved(self):
        _, initiative, reply, _, _ = self.decide("approved")
        self.web.app.test_client().get("/dashboard")
        saved = self.approval.get_approval(
            self.workspace, initiative.initiative_id, reply.reply_id,
        )
        self.assertEqual(saved.status, "approved")

    def test_04_approve_has_no_send_dependency(self):
        source = inspect.getsource(self.web.approval_decision)
        self.assertNotIn("send_message", source)
        self.assertNotIn("delivery", source)

    def test_05_approve_does_not_change_work_object(self):
        item, *_ = self.decide("approved")
        saved = self.work.get_work_object(item.object_id)
        self.assertEqual((saved.status, saved.updated_at), (item.status, item.updated_at))

    def test_06_dismiss_persistence(self):
        *_, result = self.decide("dismissed")
        self.assertEqual(result.decision, "dismissed")

    def test_07_dismissed_not_pending(self):
        self.decide("dismissed")
        self.assertEqual(
            self.approval.list_approvals(self.workspace, ("pending",)), (),
        )

    def test_08_snooze_one_hour(self):
        until = self.approval.snooze_one_hour(self.now)
        *_, result = self.decide("snoozed", snoozed_until=until)
        self.assertEqual(result.snoozed_until, until)

    def test_09_snoozed_before_deadline_not_active(self):
        self.decide(
            "snoozed", snoozed_until=self.approval.snooze_one_hour(self.now),
        )
        self.approval.wake_expired(
            self.workspace, now=self.now + timedelta(minutes=30),
        )
        self.assertEqual(
            self.approval.list_approvals(self.workspace)[0].status, "snoozed",
        )

    def test_10_snoozed_after_deadline_returns_pending(self):
        self.decide(
            "snoozed", snoozed_until=self.approval.snooze_one_hour(self.now),
        )
        count = self.approval.wake_expired(
            self.workspace, now=self.now + timedelta(hours=2),
        )
        self.assertEqual(count, 1)
        self.assertEqual(
            self.approval.list_approvals(self.workspace)[0].status, "pending",
        )

    def test_11_duplicate_post_is_idempotent(self):
        _, initiative, reply, _, first = self.decide("approved")
        before = self.event_count()
        second = self.approval.decide(
            self.workspace, initiative.initiative_id, reply.reply_id,
            "approved", decided_by="owner-a", now=self.now,
        )
        self.assertEqual((first, before), (second, self.event_count()))

    def test_12_duplicate_approval_prevention(self):
        _, initiative, reply, first = self.candidate()
        second = self.approval.ensure_approval(
            self.workspace, initiative.initiative_id, reply.reply_id,
            first.work_object_id, now=self.now,
        )
        self.assertEqual(first.approval_id, second.approval_id)
        self.assertEqual(len(self.approval.list_approvals(self.workspace)), 1)

    def test_13_workspace_isolation(self):
        self.candidate("workspace-b")
        self.assertEqual(self.approval.list_approvals(self.workspace), ())

    def test_14_forged_initiative_reply_rejected(self):
        with self.assertRaisesRegex(
            self.approval.ApprovalValidationError, "not_found",
        ):
            self.approval.decide(
                self.workspace, "forged", "forged", "approved",
                decided_by="owner-a",
            )

    def test_15_stale_candidate_not_rendered(self):
        item, *_ = self.candidate()
        self.work.update_work_object(item.object_id, status="done")
        body = self.web.app.test_client().get("/dashboard").get_data(as_text=True)
        self.assertNotIn(item.object_id + "</span><span class='muted'>Suggested", body)

    def test_16_invalid_decision_rejected(self):
        _, initiative, reply, _ = self.candidate()
        with self.assertRaises(self.approval.ApprovalValidationError):
            self.approval.decide(
                self.workspace, initiative.initiative_id, reply.reply_id,
                "execute", decided_by="owner-a",
            )

    def test_17_invalid_snooze_date_rejected(self):
        _, initiative, reply, _ = self.candidate()
        with self.assertRaises(self.approval.ApprovalValidationError):
            self.approval.decide(
                self.workspace, initiative.initiative_id, reply.reply_id,
                "snoozed", decided_by="owner-a",
                snoozed_until=(self.now - timedelta(seconds=1)).isoformat(),
                now=self.now,
            )

    def test_18_audit_fields(self):
        *_, result = self.decide(
            "approved", decision_reason="owner reviewed",
        )
        self.assertEqual(result.decided_by, "owner-a")
        self.assertEqual(result.decision_reason, "owner reviewed")
        self.assertTrue(result.decided_at)

    def test_19_approval_history_rendering(self):
        self.decide("approved")
        body = self.web.app.test_client().get("/dashboard").get_data(as_text=True)
        self.assertIn("Approval History", body)
        self.assertIn("Approved", body)

    def test_20_post_redirect_get(self):
        _, initiative, reply, _ = self.candidate()
        action = f"approval:approved:{reply.reply_id}"
        response = self.web.app.test_client().post(
            "/approvals/decision",
            data={
                "initiative_id": initiative.initiative_id,
                "reply_id": reply.reply_id,
                "decision": "approved",
                "csrf_token": self.web._channel_csrf(action),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    def test_21_initiative_regression(self):
        item, *_ = self.candidate()
        self.assertEqual(
            self.initiative.detect_initiatives(
                self.workspace, objects=[item], now=self.now,
            )[0].type,
            "overdue",
        )

    def test_22_reply_builder_regression(self):
        _, initiative, reply, _ = self.candidate()
        self.assertEqual(self.reply.ReplyBuilder.build(initiative), reply)

    def test_23_reminder_regression(self):
        self.work.create_work_object(
            "reminder", "Keep reminder", workspace_id=self.workspace,
            status="active",
        )
        self.decide("approved")
        reminders = self.work.list_work_objects(
            workspace_id=self.workspace, object_type="reminder",
        )
        self.assertEqual(len(reminders), 1)

    def test_24_planner_regression(self):
        item, initiative, reply, _ = self.candidate()
        from daily_planner import canonical_daily_work
        before = [entry.work_object_id for entry in canonical_daily_work(self.workspace)]
        self.approval.decide(
            self.workspace, initiative.initiative_id, reply.reply_id,
            "dismissed", decided_by="owner-a", now=self.now,
        )
        after = [entry.work_object_id for entry in canonical_daily_work(self.workspace)]
        self.assertEqual(before, after)
        self.assertIn(item.object_id, after)

    def test_25_web_core_runtime_boundary(self):
        source = inspect.getsource(self.web)
        self.assertNotIn("start_reminder_scheduler(", source)


if __name__ == "__main__":
    unittest.main()
