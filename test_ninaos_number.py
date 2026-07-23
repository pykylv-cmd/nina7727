import hashlib
import hmac
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet


class NinaOSNumberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.tmp.name, "ninaos-number.db")
        cls.config = [{
            "key": "lv-primary",
            "display_number": "+37120714711",
            "phone_number_id": "official_phone_1",
            "workspace_id": "ninaos_public_lv",
            "region": "LV",
            "name": "Nina",
            "access_token_env": "NINAOS_NUMBER_LV_ACCESS_TOKEN",
            "app_secret_env": "NINAOS_NUMBER_LV_APP_SECRET",
            "verify_token_env": "NINAOS_NUMBER_LV_VERIFY_TOKEN",
            "primary": True,
        }]
        cls.env = {
            "NINAOS_NUMBERS_JSON": json.dumps(cls.config),
            "NINAOS_NUMBER_IDENTITY_KEY": "test-identity-key-with-stable-entropy",
            "NINAOS_NUMBER_LV_ACCESS_TOKEN": "provider-token",
            "NINAOS_NUMBER_LV_APP_SECRET": "signature-secret",
            "NINAOS_NUMBER_LV_VERIFY_TOKEN": "verify-secret",
            "NINA_CHANNEL_CREDENTIAL_KEY": Fernet.generate_key().decode(),
            "NINA_DB_FILE": cls.db_file,
        }
        cls.env_patch = patch.dict(os.environ, cls.env)
        cls.env_patch.start()
        import channel_connections, nina_message_service, ninaos_number, web_app
        cls.connection_db = (channel_connections.DATABASE_URL, channel_connections.DB_FILE, channel_connections.USE_POSTGRES)
        cls.message_db = (nina_message_service.DATABASE_URL, nina_message_service.DB_FILE, nina_message_service.USE_POSTGRES)
        channel_connections.DATABASE_URL = ""
        channel_connections.DB_FILE = cls.db_file
        channel_connections.USE_POSTGRES = False
        channel_connections._SCHEMA_READY = False
        nina_message_service.DATABASE_URL = ""
        nina_message_service.DB_FILE = cls.db_file
        nina_message_service.USE_POSTGRES = False
        cls.connections = channel_connections
        cls.service = nina_message_service
        cls.number = importlib.reload(ninaos_number)
        cls.web = web_app
        cls.web.app.config.update(TESTING=True)
        cls.client = cls.web.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.connections.DATABASE_URL, cls.connections.DB_FILE, cls.connections.USE_POSTGRES = cls.connection_db
        cls.connections._SCHEMA_READY = False
        cls.service.DATABASE_URL, cls.service.DB_FILE, cls.service.USE_POSTGRES = cls.message_db
        cls.env_patch.stop()
        cls.tmp.cleanup()

    def payload(self, sender, message_id, text):
        return {
            "object": "whatsapp_business_account",
            "entry": [{"id": "official_business", "changes": [{"field": "messages", "value": {
                "messaging_product": "whatsapp",
                "metadata": {"display_phone_number": "+37120714711", "phone_number_id": "official_phone_1"},
                "messages": [{"from": sender, "id": message_id, "type": "text", "text": {"body": text}}],
            }}]}],
        }

    def signed(self, payload):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        signature = "sha256=" + hmac.new(b"signature-secret", raw, hashlib.sha256).hexdigest()
        return raw, signature

    def test_official_configuration_and_web_entry_points(self):
        configured = self.number.primary_number()
        self.assertEqual(configured["display_number"], "+37120714711")
        self.assertEqual(self.number.whatsapp_url(configured), "https://wa.me/37120714711")
        page = self.client.get("/nina?lang=en").get_data(as_text=True)
        self.assertIn("Talk to Nina", page)
        self.assertIn("https://wa.me/37120714711", page)
        self.assertIn("/nina/contact.vcf", page)
        self.assertEqual(self.client.get("/nina/contact.vcf").status_code, 200)
        self.assertEqual(self.client.get("/nina/contact-qr.svg").status_code, 200)

    def test_number_is_configuration_not_routing_constant(self):
        source = Path(self.number.__file__).read_text(encoding="utf-8")
        self.assertNotIn("37120714711", source)
        with patch.dict(os.environ, {"NINAOS_NUMBERS_JSON": json.dumps([{**self.config[0], "display_number": "+14155550123", "region": "US"}])}):
            self.assertEqual(self.number.primary_number("US")["display_number"], "+14155550123")

    def test_two_people_have_isolated_identity_and_memory(self):
        number = self.number.primary_number()
        person_a = self.number.resolve_sender_identity(number, "37120000001")
        person_b = self.number.resolve_sender_identity(number, "37120000002")
        self.assertNotEqual(person_a["workspace_id"], person_b["workspace_id"])
        self.assertNotEqual(person_a["conversation_id"], person_b["conversation_id"])
        self.service.send_message_to_nina(
            "alpha-private-context",
            workspace_id=person_a["workspace_id"],
            channel=self.number.CHANNEL,
            conversation_id=person_a["conversation_id"],
            generator=lambda prompt: "A reply",
        )
        prompts = []
        self.service.send_message_to_nina(
            "hello from B",
            workspace_id=person_b["workspace_id"],
            channel=self.number.CHANNEL,
            conversation_id=person_b["conversation_id"],
            generator=lambda prompt: prompts.append(prompt) or "B reply",
        )
        self.assertNotIn("alpha-private-context", prompts[0])

    def test_webhook_routes_reply_to_origin_and_deduplicates_outbound_echo(self):
        payload_a = self.payload("37120000001", "wamid.person-a", "Hello from A")
        payload_b = self.payload("37120000002", "wamid.person-b", "Hello from B")
        calls = []
        sends = []
        with patch.object(self.web, "send_message_to_nina", side_effect=lambda text, **kwargs: calls.append((text, kwargs)) or {"text": "Nina reply"}), patch.object(
            self.web, "send_ninaos_number_reply", side_effect=lambda number, recipient, text: sends.append((recipient, text)) or {"ok": True}
        ):
            for payload in (payload_a, payload_b):
                raw, signature = self.signed(payload)
                response = self.client.post("/webhooks/whatsapp", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
                self.assertEqual(response.status_code, 200)
            raw, signature = self.signed(payload_a)
            duplicate = self.client.post("/webhooks/whatsapp", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
        self.assertEqual(duplicate.get_json()["processed"], 0)
        self.assertEqual([recipient for recipient, _ in sends], ["37120000001", "37120000002"])
        self.assertNotEqual(calls[0][1]["workspace_id"], calls[1][1]["workspace_id"])
        self.assertNotEqual(calls[0][1]["conversation_id"], calls[1][1]["conversation_id"])

    def test_webhook_verification_uses_official_number_token(self):
        response = self.client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-secret&hub.challenge=official")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "official")

    def test_outbound_delivery_status_cannot_create_a_reply_loop(self):
        payload = {"object": "whatsapp_business_account", "entry": [{"id": "official_business", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "+37120714711", "phone_number_id": "official_phone_1"},
            "statuses": [{"id": "wamid.outbound", "status": "delivered", "recipient_id": "37120000001"}],
        }}]}]}
        raw, signature = self.signed(payload)
        with patch.object(self.web, "send_message_to_nina") as nina, patch.object(self.web, "send_ninaos_number_reply") as outbound:
            response = self.client.post("/webhooks/whatsapp", data=raw, content_type="application/json", headers={"X-Hub-Signature-256": signature})
        self.assertEqual(response.status_code, 400)
        nina.assert_not_called()
        outbound.assert_not_called()


if __name__ == "__main__":
    unittest.main()
