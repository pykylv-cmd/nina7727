import hashlib
import hmac
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import channel_connections
import web_app
import whatsapp_channel
from cryptography.fernet import Fernet


class WhatsAppBusinessConnectionTests(unittest.TestCase):
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
        web_app.app.config.update(TESTING=True)
        cls.client = web_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        channel_connections.DATABASE_URL, channel_connections.DB_FILE, channel_connections.USE_POSTGRES = cls.original_db
        channel_connections._SCHEMA_READY = False
        try:
            os.unlink(cls.db_file)
        except OSError:
            pass

    def setUp(self):
        channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")

    def configure(self):
        return channel_connections.configure_whatsapp(
            web_app.NINA_WEB_WORKSPACE_ID,
            "phone_123",
            "business_456",
            "WHATSAPP_ACCESS_TOKEN_TEST",
            "WHATSAPP_VERIFY_TOKEN_TEST",
            "app_789",
            "WHATSAPP_APP_SECRET_TEST",
        )

    def provider(self, method, url, token, payload=None):
        self.assertEqual(token, "provider-access-secret")
        if "/phone_123?" in url:
            return {"id": "phone_123", "display_phone_number": "+371 20000000", "verified_name": "Nina Demo", "quality_rating": "GREEN"}
        if "/business_456/phone_numbers?" in url:
            return {"data": [{"id": "phone_123"}]}
        if "/business_456?" in url:
            return {"id": "business_456", "name": "Nina Business"}
        if url.endswith("/messages"):
            return {"messages": [{"id": "wamid.reply"}]}
        raise AssertionError(url)

    def onboarding_provider(self, method, url, token, payload=None):
        if "/oauth/access_token" in url:
            self.assertEqual(token, "")
            self.assertNotIn("provider-access-secret", url)
            self.assertNotIn("meta-app-secret", url)
            self.assertEqual(payload["code"], "one-time-code")
            return {"access_token": "provider-access-secret"}
        self.assertEqual(token, "provider-access-secret")
        if "/phone_123?" in url:
            return {"id": "phone_123", "display_phone_number": "+371 20000000", "verified_name": "Nina Demo", "quality_rating": "GREEN", "name_status": "APPROVED"}
        if "/business_456/phone_numbers?" in url:
            return {"data": [{"id": "phone_123"}]}
        if url.endswith("/business_456/subscribed_apps"):
            return {"success": True}
        raise AssertionError(url)

    def test_channels_languages_disconnected_and_secret_references(self):
        for lang in ("lv", "en", "ru"):
            self.assertEqual(self.client.get(f"/channels?lang={lang}").status_code, 200)
        configured = self.configure()
        self.assertEqual(configured["status"], "pending")
        refs = channel_connections.get_secret_references(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")
        self.assertEqual(refs["access_token"], "WHATSAPP_ACCESS_TOKEN_TEST")
        page = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertNotIn("provider-access-secret", page)
        self.assertNotIn("value='WHATSAPP_ACCESS_TOKEN_TEST'", page)

    def test_simple_connect_ui_hides_technical_configuration(self):
        for lang in ("lv", "en", "ru"):
            page = self.client.get(f"/channels?lang={lang}").get_data(as_text=True)
            self.assertEqual(self.client.get(f"/channels?lang={lang}").status_code, 200)
            self.assertIn("WhatsApp", page)
        page = self.client.get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Connect WhatsApp", page)
        for term in ("Phone Number ID", "Business Account ID", "Meta App ID", "Access Token", "Webhook verify-token", "App Secret reference"):
            self.assertNotIn(term, page)

    def test_onboarding_state_is_scoped_expiring_single_use(self):
        setup = channel_connections.create_whatsapp_onboarding_state("workspace_a", ttl_seconds=60)
        with open(self.db_file, "rb") as database_file:
            self.assertNotIn(setup["state"].encode(), database_file.read())
        self.assertIsNone(channel_connections.consume_whatsapp_onboarding_state(setup["state"], expected_workspace_id="workspace_b"))
        self.assertEqual(channel_connections.consume_whatsapp_onboarding_state(setup["state"], expected_workspace_id="workspace_a"), "workspace_a")
        self.assertIsNone(channel_connections.consume_whatsapp_onboarding_state(setup["state"]))
        expired = channel_connections.create_whatsapp_onboarding_state("workspace_c", ttl_seconds=60)
        from datetime import datetime, timedelta, timezone
        self.assertIsNone(channel_connections.consume_whatsapp_onboarding_state(expired["state"], now=datetime.now(timezone.utc) + timedelta(minutes=2)))

    def test_embedded_signup_callback_connects_only_after_provider_verification(self):
        key = Fernet.generate_key().decode()
        env = {
            "WHATSAPP_META_APP_ID": "app_789",
            "WHATSAPP_META_APP_SECRET": "meta-app-secret",
            "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID": "config_456",
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN": "verify-secret",
            "NINA_CHANNEL_CREDENTIAL_KEY": key,
        }
        with patch.dict(os.environ, env):
            started = self.client.post("/channels/whatsapp/start", json={"csrf_token": web_app._channel_csrf("whatsapp_start")})
            self.assertEqual(started.status_code, 200)
            state = started.get_json()["state"]
            self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "pending")
            complete = lambda *args: whatsapp_channel.complete_embedded_signup(*args, requester=self.onboarding_provider)
            with patch.object(web_app, "complete_embedded_signup", side_effect=complete):
                callback = self.client.post("/channels/whatsapp/callback", json={"csrf_token": web_app._channel_csrf("whatsapp_callback"), "state": state, "code": "one-time-code", "phone_number_id": "phone_123", "business_account_id": "business_456", "business_portfolio_id": "portfolio_789"})
        self.assertEqual(callback.status_code, 200)
        connected = channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")
        self.assertEqual(connected["status"], "connected")
        self.assertEqual(connected["metadata"]["display_phone_number"], "+371 20000000")
        self.assertIn("+371 20000000", self.client.get("/channels?lang=en").get_data(as_text=True))
        self.assertIsNone(channel_connections.consume_whatsapp_onboarding_state(state))
        with open(self.db_file, "rb") as database_file:
            self.assertNotIn(b"provider-access-secret", database_file.read())

    def test_invalid_callback_and_safe_reconnect(self):
        bad = self.client.post("/channels/whatsapp/callback", json={"csrf_token": web_app._channel_csrf("whatsapp_callback"), "state": "invalid", "code": "code"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "disconnected")
        env = {"WHATSAPP_META_APP_ID": "app_789", "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID": "config_456"}
        with patch.dict(os.environ, env):
            first = self.client.post("/channels/whatsapp/start", json={"csrf_token": web_app._channel_csrf("whatsapp_start")})
            self.assertEqual(first.status_code, 200)
            channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")
            second = self.client.post("/channels/whatsapp/start", json={"csrf_token": web_app._channel_csrf("whatsapp_start")})
            self.assertEqual(second.status_code, 200)

    def test_provider_failure_never_claims_connected(self):
        env = {"WHATSAPP_META_APP_ID": "app_789", "WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID": "config_456"}
        with patch.dict(os.environ, env):
            started = self.client.post("/channels/whatsapp/start", json={"csrf_token": web_app._channel_csrf("whatsapp_start")}).get_json()
        with patch.object(web_app, "complete_embedded_signup", side_effect=whatsapp_channel.WhatsAppProviderError("authorization_failed")):
            response = self.client.post("/channels/whatsapp/callback", json={"csrf_token": web_app._channel_csrf("whatsapp_callback"), "state": started["state"], "code": "bad-code", "phone_number_id": "phone_123", "business_account_id": "business_456"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "error")

    def test_secret_reference_validation_and_raw_token_not_persisted(self):
        with self.assertRaises(ValueError):
            channel_connections.configure_whatsapp("workspace", "phone_123", "business_456", "raw token", "VERIFY_REF")
        self.configure()
        with open(self.db_file, "rb") as database_file:
            self.assertNotIn(b"provider-access-secret", database_file.read())

    def test_successful_and_failed_meta_verification(self):
        self.configure()
        env = {"WHATSAPP_ACCESS_TOKEN_TEST": "provider-access-secret"}
        with patch.dict(os.environ, env):
            verified = whatsapp_channel.verify_whatsapp_connection(web_app.NINA_WEB_WORKSPACE_ID, requester=self.provider)
        self.assertEqual(verified["status"], "connected")
        self.assertEqual(verified["metadata"]["display_phone_number"], "+371 20000000")
        channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")
        self.configure()
        with patch.dict(os.environ, env):
            with self.assertRaises(whatsapp_channel.WhatsAppProviderError) as failure:
                whatsapp_channel.verify_whatsapp_connection(web_app.NINA_WEB_WORKSPACE_ID, requester=lambda *args: (_ for _ in ()).throw(whatsapp_channel.WhatsAppProviderError("credentials_or_provider_request_rejected", 401)))
        self.assertEqual(str(failure.exception), "credentials_or_provider_request_rejected")
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "error")

    def test_webhook_get_valid_and_invalid_verify_token(self):
        self.configure()
        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN_TEST": "verify-secret"}):
            valid = self.client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-secret&hub.challenge=12345")
            invalid = self.client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=12345")
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.get_data(as_text=True), "12345")
        self.assertEqual(invalid.status_code, 403)
        self.assertTrue(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["metadata"]["webhook_verified"])

    def payload(self):
        return {"object": "whatsapp_business_account", "entry": [{"id": "business_456", "changes": [{"field": "messages", "value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "+371 20000000", "phone_number_id": "phone_123"}, "messages": [{"from": "37121111111", "id": "wamid.inbound", "timestamp": "1", "type": "text", "text": {"body": "Create a task tomorrow"}}]}}]}]}

    def test_webhook_invalid_payload_and_valid_shared_routing_outbound(self):
        self.assertEqual(self.client.post("/webhooks/whatsapp", json={"bad": True}).status_code, 400)
        self.configure()
        channel_connections.update_whatsapp_verification(web_app.NINA_WEB_WORKSPACE_ID, True, {"provider_verified": True})
        raw = json.dumps(self.payload(), separators=(",", ":")).encode()
        app_secret = "app-signature-secret"
        signature = "sha256=" + hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"WHATSAPP_APP_SECRET_TEST": app_secret}), patch.object(web_app, "send_message_to_nina", return_value={"ok": True, "text": "Task created"}) as nina, patch.object(web_app, "send_whatsapp_message", return_value={"ok": True, "message_id": "wamid.reply"}) as outbound:
            response = self.client.post("/webhooks/whatsapp", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
        self.assertEqual(response.status_code, 200)
        nina.assert_called_once_with("Create a task tomorrow", workspace_id=web_app.NINA_WEB_WORKSPACE_ID, channel="whatsapp")
        outbound.assert_called_once_with(web_app.NINA_WEB_WORKSPACE_ID, "37121111111", "Task created")
        self.assertFalse(channel_connections.claim_channel_message(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp", "wamid.inbound"))

    def test_send_adapter_and_disconnect(self):
        self.configure()
        channel_connections.update_whatsapp_verification(web_app.NINA_WEB_WORKSPACE_ID, True)
        with patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN_TEST": "provider-access-secret"}):
            sent = whatsapp_channel.send_whatsapp_message(web_app.NINA_WEB_WORKSPACE_ID, "37121111111", "Hello", requester=self.provider)
        self.assertTrue(sent["ok"])
        channel_connections.disconnect(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")
        self.assertEqual(channel_connections.get_connection(web_app.NINA_WEB_WORKSPACE_ID, "whatsapp")["status"], "disconnected")


if __name__ == "__main__":
    unittest.main()
