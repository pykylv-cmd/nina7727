import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet


class ClientIdentityBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ.pop("DATABASE_URL", None)
        os.environ["NINA_DB_FILE"] = os.path.join(cls.tmp.name, "client-bridge.db")
        os.environ["NINA_CHANNEL_CREDENTIAL_KEY"] = Fernet.generate_key().decode()
        os.environ["NINA_CONTACT_IDENTITY_KEY"] = "contact-identity-test-key-at-least-32-bytes"
        os.environ["NINAOS_NUMBER_IDENTITY_KEY"] = "number-identity-test-key-at-least-32-bytes"
        os.environ["NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN"] = "bridge-test"
        os.environ["NINA_COMPANY_WHATSAPP_NUMBER"] = "+37120714711"
        os.environ["NINA_COMPANY_WHATSAPP_WORKSPACE"] = "ninaos_company"

        import contact_identity
        import client_identity
        import work_objects
        import task_engine
        import work_engine
        import nina_message_service
        import company_whatsapp
        import web_app

        cls.contacts = importlib.reload(contact_identity)
        cls.clients = importlib.reload(client_identity)
        cls.objects = importlib.reload(work_objects)
        importlib.reload(task_engine)
        cls.engine = importlib.reload(work_engine)
        cls.messages = importlib.reload(nina_message_service)
        cls.company = importlib.reload(company_whatsapp)
        cls.web = importlib.reload(web_app)
        cls.web.app.config.update(TESTING=True)
        cls.http = cls.web.app.test_client()
        cls.http.set_cookie(
            cls.web.ADMIN_COOKIE,
            cls.web.create_admin_session(cls.web._workspace_cookie_secret()),
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _contact(self, workspace, external):
        return self.contacts.resolve_contact_identity(
            workspace, "company_whatsapp", external,
            {"relationship_type": "client"},
        )

    def _inbound(self, workspace, sender, message_id, text):
        payload = {
            "workspace_id": workspace, "sender_jid": sender,
            "message_id": message_id, "text": text,
        }
        with self.web.app.test_request_context(
            "/internal/company-whatsapp/inbound", method="POST", json=payload
        ), patch.object(self.web, "_bridge_json", return_value=payload), patch.object(
            self.web, "accept_company_whatsapp_inbound", return_value=True
        ):
            return self.web.internal_company_whatsapp_inbound()

    def test_mapping_is_idempotent_tenant_scoped_and_survives_reload(self):
        first_contact = self._contact("tenant-a", "37120000001@s.whatsapp.net")
        first = self.clients.get_or_create_client_mapping("tenant-a", first_contact["contact_id"])
        repeated = self.clients.get_or_create_client_mapping("tenant-a", first_contact["contact_id"])
        second_contact = self._contact("tenant-a", "37120000002@s.whatsapp.net")
        second = self.clients.get_or_create_client_mapping("tenant-a", second_contact["contact_id"])
        other_contact = self._contact("tenant-b", "37120000001@s.whatsapp.net")
        other = self.clients.get_or_create_client_mapping("tenant-b", other_contact["contact_id"])

        self.assertEqual(first["canonical_client_id"], repeated["canonical_client_id"])
        self.assertEqual(len({
            first["canonical_client_id"], second["canonical_client_id"],
            other["canonical_client_id"],
        }), 3)
        reloaded = importlib.reload(self.clients)
        self.assertEqual(
            reloaded.get_client_mapping("tenant-a", first_contact["contact_id"])["canonical_client_id"],
            first["canonical_client_id"],
        )
        with self.assertRaises(ValueError):
            reloaded.get_or_create_client_mapping("tenant-b", first_contact["contact_id"])

    def test_company_task_uses_stable_client_and_ordinary_chat_creates_no_work(self):
        sender = "37121111111@s.whatsapp.net"
        before = len(self.objects.list_work_objects(workspace_id="ninaos_company", limit=1000))
        with patch.object(self.messages, "_openai_generate", return_value="Sveiki!"):
            self._inbound("ninaos_company", sender, "ordinary-1", "Sveiki")
        after_chat = len(self.objects.list_work_objects(workspace_id="ninaos_company", limit=1000))
        self.assertEqual(after_chat, before)

        self._inbound(
            "ninaos_company", sender, "task-1",
            "Izveido uzdevumu: rīt piezvanīt Pēterim.",
        )
        contact = self._contact("ninaos_company", sender)
        mapping = self.clients.get_client_mapping("ninaos_company", contact["contact_id"])
        tasks = self.objects.list_work_objects(
            workspace_id="ninaos_company", object_type="task", limit=1000
        )
        created = next(item for item in tasks if "Pēterim" in item.title)
        self.assertEqual(created.client_id, mapping["canonical_client_id"])
        self.assertEqual(created.origin_channel, "whatsapp_company")
        self.assertEqual(created.metadata["contact_id"], contact["contact_id"])

        self._inbound(
            "ninaos_company", sender, "task-2",
            "Izveido uzdevumu: šodien nosūtīt kopsavilkumu.",
        )
        latest_mapping = self.clients.get_client_mapping("ninaos_company", contact["contact_id"])
        self.assertEqual(latest_mapping["canonical_client_id"], mapping["canonical_client_id"])

        other_sender = "37123333333@s.whatsapp.net"
        self._inbound(
            "ninaos_company", other_sender, "task-other-1",
            "Izveido uzdevumu: rīt nosūtīt projekta ziņu.",
        )
        other_contact = self._contact("ninaos_company", other_sender)
        other_mapping = self.clients.get_client_mapping(
            "ninaos_company", other_contact["contact_id"]
        )
        self.assertNotEqual(
            other_mapping["canonical_client_id"], mapping["canonical_client_id"]
        )

    def test_clients_groups_same_work_truth_and_admin_shows_safe_link(self):
        contact = self._contact("ninaos_company", "37122222222@s.whatsapp.net")
        mapping = self.clients.get_or_create_client_mapping("ninaos_company", contact["contact_id"])
        client_id = mapping["canonical_client_id"]
        for object_type in ("estimate", "followup_task"):
            self.objects.create_work_object(
                object_type=object_type, title=f"Linked {object_type}",
                workspace_id="ninaos_company", client_id=client_id,
                source_key=f"client-bridge-test:{object_type}",
                origin_channel="whatsapp_company",
            )

        profiles = self.web.one_nina_client_work_map()
        profile = profiles[client_id.casefold()]
        visible_ids = {item.object_id for item in profile["objects"]}
        stored_ids = {
            item.object_id for item in self.objects.list_work_objects(
                workspace_id="ninaos_company", client_id=client_id, limit=100
            )
        }
        self.assertEqual(visible_ids, stored_ids)
        clients_page = self.http.get("/clients?lang=en").get_data(as_text=True)
        admin_page = self.http.get("/admin/clients?lang=en").get_data(as_text=True)
        self.assertIn(client_id, clients_page)
        self.assertIn(client_id, admin_page)
        self.assertNotIn("37122222222", clients_page)
        self.assertNotIn("37122222222", admin_page)
        self.assertFalse(any(
            item.object_type == "client"
            for item in self.objects.list_work_objects(
                workspace_id="ninaos_company", client_id=client_id, limit=100
            )
        ))


if __name__ == "__main__":
    unittest.main()
