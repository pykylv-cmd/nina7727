import io
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

import channel_connections
import web_app


class ChannelConnectionsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_file = handle.name
        handle.close()
        cls.original_db = (channel_connections.DATABASE_URL, channel_connections.DB_FILE, channel_connections.USE_POSTGRES)
        channel_connections.DATABASE_URL = ""
        channel_connections.DB_FILE = cls.db_file
        channel_connections.USE_POSTGRES = False
        channel_connections._SCHEMA_READY = False
        cls.restore_database = bind_sqlite_database(
            cls.db_file, channel_connections
        )
        initialize_ready_web(web_app)
        web_app.app.config.update(TESTING=True)
        cls.client = web_app.app.test_client()
        cls.public_client = web_app.app.test_client()
        cls.client.set_cookie(
            web_app.ADMIN_COOKIE,
            web_app.create_admin_session(web_app._workspace_cookie_secret()),
        )

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        channel_connections.DATABASE_URL, channel_connections.DB_FILE, channel_connections.USE_POSTGRES = cls.original_db
        channel_connections._SCHEMA_READY = False
        try:
            os.unlink(cls.db_file)
        except OSError:
            pass

    def setUp(self):
        channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "telegram")
        channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")

    def csrf(self, action):
        return web_app._channel_csrf(action)

    def test_channels_loads_languages_and_web_is_active(self):
        for lang in ("lv", "en", "ru"):
            response = self.public_client.get(f"/channels?lang={lang}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Web", response.data)
            self.assertIn(b"connection-status active", response.data)

    def test_telegram_disconnected_and_connected_rendering(self):
        client_page = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Available", client_page)
        self.assertIn("Open Telegram", client_page)
        self.assertNotIn("connection-status disconnected", client_page)
        admin_page = self.client.get("/admin/channels?lang=en").get_data(as_text=True)
        self.assertIn("connection-status disconnected", admin_page)
        channel_connections.set_connection_for_test(web_app.NINA_WEB_WORKSPACE_ID, "telegram", "connected", {"bot_username": "Nina7727_bot"})
        client_page = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Available", client_page)
        self.assertIn("Open Telegram", client_page)
        self.assertNotIn("connection-status connected", client_page)
        admin_page = self.client.get("/admin/channels?lang=en").get_data(as_text=True)
        self.assertIn("connection-status connected", admin_page)
        self.assertIn("@Nina7727_bot", admin_page)

    def test_telegram_token_is_workspace_scoped_single_use_and_expiring(self):
        setup = channel_connections.create_telegram_token("workspace_a", "Nina7727_bot", ttl_seconds=60)
        self.assertEqual(channel_connections.get_connection("workspace_b", "telegram")["status"], "disconnected")
        linked = channel_connections.consume_telegram_token(setup["token"], "123", "owner", "456", "Owner")
        self.assertEqual(linked["workspace_id"], "workspace_a")
        self.assertIsNone(channel_connections.consume_telegram_token(setup["token"], "123", "owner", "456", "Owner"))
        expired = channel_connections.create_telegram_token("workspace_c", "Nina7727_bot", ttl_seconds=60)
        future = datetime.now(timezone.utc) + timedelta(minutes=2)
        self.assertIsNone(channel_connections.consume_telegram_token(expired["token"], now=future))

    def test_telegram_provider_secret_never_appears_in_html(self):
        secret = "telegram-provider-secret-never-render"
        with patch.dict(os.environ, {"TELEGRAM_TOKEN": secret, "TELEGRAM_BOT_USERNAME": "Nina7727_bot"}):
            page = self.public_client.get("/channels?lang=en").get_data(as_text=True)
        self.assertNotIn(secret, page)

    def test_telegram_connect_and_disconnect_are_csrf_protected_posts(self):
        self.assertEqual(self.client.get("/channels/telegram/connect").status_code, 405)
        self.assertEqual(self.client.post("/channels/telegram/connect", data={}).status_code, 400)
        response = self.client.post("/channels/telegram/connect?lang=en", data={"csrf_token": self.csrf("telegram_connect")})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"https://t.me/Nina7727_bot?start=", response.data)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "telegram")["status"], "pending")
        response = self.client.post("/channels/telegram/disconnect?lang=en", data={"csrf_token": self.csrf("telegram_disconnect")})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "telegram")["status"], "disconnected")

    def test_web_changes_from_pending_to_connected_after_telegram_consumes_token(self):
        setup = channel_connections.create_telegram_token(web_app.NINA_WEB_WORKSPACE_ID, "Nina7727_bot")
        self.assertEqual(
            channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "telegram")["status"],
            "pending",
        )
        pending = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Available", pending)
        self.assertIn("Open Telegram", pending)
        self.assertNotIn("connection-status pending", pending)
        pending_admin = self.client.get("/admin/channels?lang=en").get_data(as_text=True)
        self.assertIn("connection-status pending", pending_admin)
        linked = channel_connections.consume_telegram_token(setup["token"], "101", "owner", "202", "Owner Name")
        self.assertIsNotNone(linked)
        self.assertEqual(
            channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "telegram")["status"],
            "connected",
        )
        connected = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Available", connected)
        self.assertIn("Open Telegram", connected)
        self.assertNotIn("connection-status connected", connected)
        self.assertNotIn("Owner Name", connected)
        self.assertNotIn(setup["token"], connected)
        connected_admin = self.client.get("/admin/channels?lang=en").get_data(as_text=True)
        self.assertIn("connection-status connected", connected_admin)
        self.assertIn("Owner Name", connected_admin)
        self.assertNotIn(setup["token"], connected_admin)

    def test_whatsapp_customer_connect_is_simple_and_secure(self):
        with patch.dict(os.environ, {"NINA_COMPANY_WHATSAPP_NUMBER": "+37120714711"}):
            page = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Open WhatsApp", page)
        self.assertRegex(page, r"href='https://wa\.me/\d+'")
        self.assertNotIn("Connect WhatsApp", page)
        for label in ("Phone Number ID", "Business Account ID", "Access token secret reference", "Meta App Secret reference"):
            self.assertNotIn(label, page)
        self.assertEqual(self.client.post("/channels/whatsapp/start", json={}).status_code, 400)
        env = {"WHATSAPP_META_APP_ID": "app_789", "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID": "config_456"}
        with patch.dict(os.environ, env):
            response = self.client.post("/channels/whatsapp/start", json={"csrf_token": self.csrf("whatsapp_start")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "pending")
        disconnected = self.client.post("/channels/whatsapp/disconnect?lang=en", data={"csrf_token": self.csrf("whatsapp_disconnect")})
        self.assertEqual(disconnected.status_code, 302)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "disconnected")

    def test_existing_chat_voice_tasks_and_clients_are_unaffected(self):
        with patch.object(web_app, "load_web_conversation", return_value=[]), patch.object(web_app, "send_message_to_nina") as send:
            self.assertEqual(self.client.get("/nina?lang=en").status_code, 200)
            self.assertEqual(self.client.post("/nina?lang=en", data={"message": "Hello"}).status_code, 302)
            self.assertEqual(send.call_args.args[0], "Hello")
            self.assertTrue(send.call_args.kwargs["contact_id"].startswith("contact_"))
        with patch.object(web_app, "_transcribe_web_voice", return_value="Create task tomorrow"), patch.object(web_app, "send_message_to_nina") as send:
            response = self.client.post("/nina/voice?lang=en", data={"audio": (io.BytesIO(b"voice"), "voice.webm", "audio/webm"), "lang": "en"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(send.call_args.args[0], "Create task tomorrow")
            self.assertTrue(send.call_args.kwargs["contact_id"].startswith("contact_"))
        self.assertEqual(self.client.get("/tasks?lang=en").status_code, 200)
        self.assertEqual(self.client.get("/clients?lang=en").status_code, 200)

    def test_customer_channels_page_has_no_internal_terms(self):
        page = self.public_client.get("/channels?lang=en").get_data(as_text=True).lower()
        for term in ("one nina", "work objects", "work engine", "web_app.py", "version"):
            self.assertNotIn(term, page)


if __name__ == "__main__":
    unittest.main()
