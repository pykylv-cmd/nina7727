import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class WebPushTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "web-push.sqlite")
        cls.env = patch.dict(os.environ, {
            "DATABASE_URL": "", "NINA_DB_FILE": cls.db_file,
            "NINA_WEB_PUSH_VAPID_PUBLIC_KEY": "public-key",
            "NINA_WEB_PUSH_VAPID_PRIVATE_KEY": "private-key",
            "NINA_WEB_PUSH_VAPID_SUBJECT": "mailto:ops@example.test",
        })
        cls.env.start()
        import persistence_backend
        import channel_connections
        import contact_identity
        import work_objects
        import managed_migrations
        cls.modules = (persistence_backend, channel_connections, contact_identity, work_objects)
        cls.restore = bind_sqlite_database(cls.db_file, *cls.modules)
        managed_migrations.run_migrations()
        cls.work = work_objects

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        conn = sqlite3.connect(self.db_file)
        for table in ("nina_web_push_events", "nina_web_push_deliveries", "nina_web_push_subscriptions"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit(); conn.close()

    @staticmethod
    def subscription(endpoint="https://push.example.test/device-a"):
        return {"endpoint": endpoint, "keys": {"p256dh": "p" * 32, "auth": "a" * 16}}

    def test_subscription_create_update_idempotence_and_encryption(self):
        import web_push
        first = web_push.register_subscription("workspace-a", "contact-a", self.subscription())
        second = web_push.register_subscription("workspace-a", "contact-a", self.subscription(), "Browser")
        self.assertEqual(first["subscription_id"], second["subscription_id"])
        conn = sqlite3.connect(self.db_file)
        row = conn.execute("SELECT encrypted_subscription_json,user_agent_safe,status FROM nina_web_push_subscriptions").fetchone()
        conn.close()
        self.assertNotIn("push.example.test", row[0])
        self.assertEqual(row[1:], ("Browser", "ACTIVE"))

    def test_cross_workspace_owner_conflict_and_unsubscribe_scope(self):
        import web_push
        web_push.register_subscription("workspace-a", "contact-a", self.subscription())
        with self.assertRaises(web_push.WebPushConflictError):
            web_push.register_subscription("workspace-b", "contact-b", self.subscription())
        self.assertFalse(web_push.unsubscribe("workspace-a", "contact-b", self.subscription()["endpoint"]))
        self.assertTrue(web_push.unsubscribe("workspace-a", "contact-a", self.subscription()["endpoint"]))

    def test_one_push_per_reminder_subscription_and_two_devices(self):
        import web_push
        web_push.register_subscription("workspace-a", "contact-a", self.subscription())
        web_push.register_subscription("workspace-a", "contact-a", self.subscription("https://push.example.test/device-b"))
        reminder = type("Reminder", (), {"workspace_id": "workspace-a", "origin_user_id": "contact-a", "object_id": "reminder-1", "title": "Reminder: walk dog"})()
        sent = []
        sender = lambda subscription, payload: sent.append((subscription, payload))
        first = web_push.deliver_reminder_push(reminder, sender=sender)
        second = web_push.deliver_reminder_push(reminder, sender=sender)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(sent), 2)
        self.assertEqual([item["status"] for item in second], ["DELIVERED", "DELIVERED"])
        self.assertTrue(all(item[1]["url"] == "/nina" for item in sent))

    def test_different_reminders_have_distinct_notification_tags(self):
        import web_push
        web_push.register_subscription("workspace-a", "contact-a", self.subscription())
        sent = []
        sender = lambda subscription, payload: sent.append(payload)
        reminder_one = type("Reminder", (), {"workspace_id": "workspace-a", "origin_user_id": "contact-a", "object_id": "reminder-one", "title": "First reminder"})()
        reminder_two = type("Reminder", (), {"workspace_id": "workspace-a", "origin_user_id": "contact-a", "object_id": "reminder-two", "title": "Second reminder"})()
        web_push.deliver_reminder_push(reminder_one, sender=sender)
        web_push.deliver_reminder_push(reminder_two, sender=sender)
        self.assertEqual(len(sent), 2)
        self.assertNotEqual(sent[0]["tag"], sent[1]["tag"])
        self.assertEqual(sent[0]["tag"], "nina-reminder-reminder-one")
        self.assertEqual(sent[1]["tag"], "nina-reminder-reminder-two")

    def test_invalid_endpoint_is_deactivated_and_failure_is_safe(self):
        import web_push
        web_push.register_subscription("workspace-a", "contact-a", self.subscription())
        reminder = type("Reminder", (), {"workspace_id": "workspace-a", "origin_user_id": "contact-a", "object_id": "reminder-2", "title": "Reminder"})()
        class Gone(Exception):
            response = type("Response", (), {"status_code": 410})()
        result = web_push.deliver_reminder_push(reminder, sender=lambda *_: (_ for _ in ()).throw(Gone("secret endpoint")))
        self.assertEqual(result[0]["status"], "FAILED")
        conn = sqlite3.connect(self.db_file)
        row = conn.execute("SELECT status,failure_code FROM nina_web_push_subscriptions").fetchone()
        events = conn.execute("SELECT safe_metadata_json FROM nina_web_push_events").fetchall()
        conn.close()
        self.assertEqual(row, ("EXPIRED", "endpoint_invalid"))
        self.assertNotIn("secret endpoint", json.dumps(events))

    def test_optional_readiness_does_not_claim_availability(self):
        import web_push
        with patch.dict(os.environ, {"NINA_WEB_PUSH_VAPID_PUBLIC_KEY": "", "NINA_WEB_PUSH_VAPID_PRIVATE_KEY": "", "NINA_WEB_PUSH_VAPID_SUBJECT": ""}):
            status = web_push.readiness_status()
        self.assertFalse(status["configured"])
        self.assertFalse(status["available"])


class WebPushSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import web_app
        cls.web = web_app

    def test_manifest_and_service_worker_contract(self):
        client = self.web.app.test_client()
        manifest = client.get("/manifest.webmanifest")
        worker = client.get("/service-worker.js")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.get_json()["start_url"], "/nina")
        self.assertEqual(manifest.get_json()["scope"], "/")
        self.assertEqual(worker.headers["Service-Worker-Allowed"], "/")
        self.assertIn("clients.openWindow('/nina')", worker.get_data(as_text=True))
        self.assertIn("renotify: true", worker.get_data(as_text=True))
        self.assertIn("vibrate: [200, 100, 200]", worker.get_data(as_text=True))
        self.assertIn("data.tag || ('nina-reminder-' + Date.now())", worker.get_data(as_text=True))

    def test_permission_ui_and_anonymous_mutation(self):
        with self.web.app.test_request_context("/nina"):
            body = self.web.nina_chat_body([])
        self.assertIn("Enable notifications", body)
        self.assertIn("Notification.requestPermission()", body)
        self.assertIn("navigator.serviceWorker.ready", body)
        self.assertIn("pushManager.subscribe", body)
        self.assertIn("/nina/push/subscribe", body)
        self.assertIn("handlerAttached", body)
        self.assertNotIn("enable.disabled = true", body)
        client = self.web.app.test_client()
        response = client.post("/nina/push/subscribe", json={"subscription": {}})
        self.assertEqual(response.status_code, 403)

    def test_route_uses_server_contact_and_requires_csrf(self):
        client = self.web.app.test_client()
        browser_id = "web_" + "a" * 32
        client.set_cookie(self.web._WORKSPACE_COOKIE, self.web._workspace_cookie_value(browser_id))
        payload = {"subscription": {"endpoint": "https://push.example.test/a", "keys": {"p256dh": "p" * 32, "auth": "a" * 16}}, "workspace_id": "attacker", "contact_id": "attacker"}
        with patch.object(self.web, "resolve_contact_identity", return_value={"contact_id": "contact-server"}), patch("web_push.configuration_status", return_value={"available": True}), patch("web_push.register_subscription", return_value={"subscription_id": "wps_1", "status": "ACTIVE"}) as register:
            denied = client.post("/nina/push/subscribe", json=payload)
            allowed = client.post("/nina/push/subscribe", json=payload, headers={"X-CSRF-Token": self.web._channel_csrf("web-push:subscribe")})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(register.call_args.args[0], self.web.NINA_WEB_WORKSPACE_ID)
        self.assertNotEqual(register.call_args.args[1], "attacker")


if __name__ == "__main__":
    unittest.main()
