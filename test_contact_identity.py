import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class ContactIdentityV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.tmp.name, "contacts.db")
        cls.env = patch.dict(os.environ, {
            "DATABASE_URL": "",
            "NINA_RUNTIME_ENV": "test",
            "NINA_DB_FILE": cls.db_file,
            "NINA_CONTACT_IDENTITY_KEY": "contact-test-key-at-least-32-characters",
        })
        cls.env.start()
        import contact_identity
        cls.identity = importlib.reload(contact_identity)
        cls.restore_database = bind_sqlite_database(cls.db_file, cls.identity)

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        cls.env.stop()
        cls.tmp.cleanup()

    def test_stable_company_telegram_and_web_resolution(self):
        for channel, external in (
            ("company_whatsapp", "37120000001@s.whatsapp.net"),
            ("telegram", "123456"),
            ("web", "web_" + "a" * 32),
        ):
            first = self.identity.resolve_contact_identity("tenant-a", channel, external)
            second = self.identity.resolve_contact_identity("tenant-a", channel, external)
            self.assertEqual(first["contact_id"], second["contact_id"])
            self.assertEqual(first["conversation_id"], second["conversation_id"])

    def test_people_tenants_and_channels_are_isolated(self):
        a = self.identity.resolve_contact_identity("tenant-a", "company_whatsapp", "person-a")
        b = self.identity.resolve_contact_identity("tenant-a", "company_whatsapp", "person-b")
        other_tenant = self.identity.resolve_contact_identity("tenant-b", "company_whatsapp", "person-a")
        other_channel = self.identity.resolve_contact_identity("tenant-a", "telegram", "person-a")
        self.assertEqual(len({a["contact_id"], b["contact_id"], other_tenant["contact_id"], other_channel["contact_id"]}), 4)

    def test_display_name_quality_precedence_and_last_seen(self):
        low = self.identity.resolve_contact_identity(
            "tenant-name", "telegram", "77",
            {"display_name": "Provider Name", "display_name_quality": 30},
        )
        high = self.identity.resolve_contact_identity(
            "tenant-name", "telegram", "77",
            {"display_name": "Confirmed Name", "display_name_quality": 90},
        )
        lower_again = self.identity.resolve_contact_identity(
            "tenant-name", "telegram", "77",
            {"display_name": "Low Quality", "display_name_quality": 10},
        )
        self.assertEqual(low["contact_id"], high["contact_id"])
        self.assertEqual(lower_again["display_name"], "Confirmed Name")
        self.assertTrue(lower_again["last_seen_at"])

    def test_link_claim_requires_explicit_verification_and_never_name_matching(self):
        source = self.identity.resolve_contact_identity("tenant-link", "telegram", "1", {"display_name": "Same"})
        target = self.identity.resolve_contact_identity("tenant-link", "company_whatsapp", "2", {"display_name": "Same"})
        self.assertNotEqual(source["contact_id"], target["contact_id"])
        claim = self.identity.create_contact_link_claim(
            "tenant-link", source["contact_id"], target["contact_id"], "one_time_code"
        )
        self.assertFalse(self.identity.verify_contact_link_claim("tenant-link", claim["claim_id"], False))
        self.assertTrue(self.identity.verify_contact_link_claim("tenant-link", claim["claim_id"], True))
        self.assertNotEqual(source["contact_id"], target["contact_id"])

    def test_compact_context_is_minimal_and_profile_isolated(self):
        a = self.identity.resolve_contact_identity(
            "tenant-context", "company_whatsapp", "a",
            {"display_name": "Jānis", "display_name_quality": 80, "language": "lv", "language_verified": True, "relationship_type": "client"},
        )
        b = self.identity.resolve_contact_identity(
            "tenant-context", "company_whatsapp", "b",
            {"display_name": "Anna", "display_name_quality": 80},
        )
        context_a = self.identity.compact_contact_context(a)
        context_b = self.identity.compact_contact_context(b)
        self.assertIn("Jānis", context_a)
        self.assertIn("Preferred language: lv", context_a)
        self.assertNotIn("Jānis", context_b)
        self.assertLessEqual(len(context_a), 500)

    def test_message_service_receives_only_selected_contact_context(self):
        import nina_message_service
        old_db = (nina_message_service.DATABASE_URL, nina_message_service.DB_FILE, nina_message_service.USE_POSTGRES)
        nina_message_service.DATABASE_URL = ""
        nina_message_service.DB_FILE = os.path.join(self.tmp.name, "messages.db")
        nina_message_service.USE_POSTGRES = False
        prompts = []
        try:
            result = nina_message_service.send_message_to_nina(
                "hello", workspace_id="tenant-prompt", channel="company_whatsapp",
                conversation_id="contact:test", contact_id="contact_selected",
                contact_context="Contact: Jānis", generator=lambda prompt: prompts.append(prompt) or "reply",
            )
        finally:
            nina_message_service.DATABASE_URL, nina_message_service.DB_FILE, nina_message_service.USE_POSTGRES = old_db
        self.assertTrue(result["ok"])
        self.assertIn("contact_selected", prompts[0])
        self.assertIn("Contact: Jānis", prompts[0])
        self.assertNotIn("Anna", prompts[0])

    def test_admin_contact_view_does_not_show_external_identity(self):
        import web_app
        initialize_ready_web(web_app)
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE, web_app.create_admin_session(web_app._workspace_cookie_secret()))
        with patch.object(web_app, "list_contacts", return_value=[{
            "contact_id": "contact_opaque", "workspace_id": "tenant",
            "display_name": "Jānis", "preferred_name": "", "channels": ["company_whatsapp"],
            "relationship_type": "client", "status": "active",
        }]):
            page = client.get("/admin/clients").get_data(as_text=True)
        self.assertIn("contact_opaque", page)
        self.assertNotIn("37120000001@s.whatsapp.net", page)


if __name__ == "__main__":
    unittest.main()
