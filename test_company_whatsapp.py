import importlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet


class CompanyWhatsAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        os.environ.pop("DATABASE_URL",None)
        os.environ["NINA_DB_FILE"]=os.path.join(cls.tmp.name,"company.db")
        os.environ["NINA_CHANNEL_CREDENTIAL_KEY"]=Fernet.generate_key().decode()
        os.environ["NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN"]="bridge-test"
        os.environ["NINA_COMPANY_WHATSAPP_NUMBER"]="+37120714711"
        os.environ["NINA_COMPANY_WHATSAPP_WORKSPACE"]="ninaos_company"
        os.environ["NINAOS_NUMBER_IDENTITY_KEY"]="stable-company-identity-key"
        import channel_connections, personal_whatsapp, company_whatsapp, nina_message_service, ninaos_number, web_app
        cls.connections=importlib.reload(channel_connections)
        cls.personal=importlib.reload(personal_whatsapp)
        cls.company=importlib.reload(company_whatsapp)
        cls.service=importlib.reload(nina_message_service)
        cls.number=importlib.reload(ninaos_number)
        cls.web=importlib.reload(web_app)
        cls.web.app.config.update(TESTING=True)
        cls.client=cls.web.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.company.disconnect_company()
        self.personal.disconnect_personal("ninaos_company")

    def connect(self):
        pair=self.company.create_pairing_session()
        self.assertIsNotNone(self.company.mark_connected("ninaos_company",pair["session_token"],{"masked_identity":"*******4711"}))

    def test_auth_namespace_cannot_collide_with_personal(self):
        self.company.store_auth_record("ninaos_company","creds",{"kind":"company"})
        self.personal.store_auth_record("ninaos_company","creds",{"kind":"personal"})
        self.assertEqual(self.company.load_auth_records("ninaos_company")["creds"]["kind"],"company")
        self.assertEqual(self.personal.load_auth_records("ninaos_company")["creds"]["kind"],"personal")
        conn=sqlite3.connect(os.environ["NINA_DB_FILE"])
        tables={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertIn("nina_company_whatsapp_auth",tables)
        self.assertIn("nina_personal_whatsapp_auth",tables)

    def test_connect_status_disconnect_use_company_endpoints_only(self):
        calls=[]
        with patch.object(self.web,"personal_whatsapp_bridge_request",side_effect=lambda path,payload:calls.append((path,payload)) or {"status":"connecting"}):
            response=self.client.post("/channels/whatsapp-company/connect",data={"csrf_token":self.web._channel_csrf("whatsapp_company_connect")})
        self.assertEqual(response.status_code,302)
        self.assertEqual(calls[0][0],"/v1/company/sessions")
        self.assertEqual(self.connections.get_connection("ninaos_company","whatsapp_company")["status"],"pending")
        with patch.object(self.web,"personal_whatsapp_bridge_request",return_value={"ok":True}) as bridge:
            self.client.post("/channels/whatsapp-company/disconnect",data={"csrf_token":self.web._channel_csrf("whatsapp_company_disconnect")})
        bridge.assert_called_once_with("/v1/company/disconnect",{"workspace_id":"ninaos_company"})

    def test_two_external_senders_route_to_isolated_nina_context(self):
        self.connect()
        auth={"Authorization":"Bearer bridge-test"}
        with patch.object(self.web,"send_message_to_nina",return_value={"text":"Nina reply"}) as nina:
            for index,jid in enumerate(("37120000001@s.whatsapp.net","37120000002@s.whatsapp.net"),1):
                response=self.client.post("/internal/company-whatsapp/inbound",headers=auth,json={"workspace_id":"ninaos_company","message_id":f"m{index}","sender_jid":jid,"text":"hello"})
                self.assertTrue(response.get_json()["accepted"])
        first,second=nina.call_args_list
        self.assertNotEqual(first.kwargs["workspace_id"],second.kwargs["workspace_id"])
        self.assertNotEqual(first.kwargs["conversation_id"],second.kwargs["conversation_id"])
        self.assertEqual(first.kwargs["channel"],"whatsapp_company")

    def test_sender_context_does_not_leak(self):
        identity_a=self.number.resolve_channel_identity("whatsapp_company","ninaos_company","37120000001")
        identity_b=self.number.resolve_channel_identity("whatsapp_company","ninaos_company","37120000002")
        self.service.send_message_to_nina("anna-private",workspace_id=identity_a["workspace_id"],channel="whatsapp_company",conversation_id=identity_a["conversation_id"],generator=lambda prompt:"A")
        prompts=[]
        self.service.send_message_to_nina("janis-message",workspace_id=identity_b["workspace_id"],channel="whatsapp_company",conversation_id=identity_b["conversation_id"],generator=lambda prompt:prompts.append(prompt) or "B")
        self.assertNotIn("anna-private",prompts[0])

    def test_public_contact_uses_company_configuration_without_meta(self):
        with patch.dict(os.environ,{"NINAOS_NUMBERS_JSON":""}):
            contact=self.number.public_contact(self.number.primary_number())
            self.assertEqual(contact["whatsapp_url"],"https://wa.me/37120714711")
            page=self.client.get("/nina?lang=en").get_data(as_text=True)
            self.assertIn("Talk to Nina",page)
            self.assertIn("https://wa.me/37120714711",page)

    def test_internal_company_api_requires_bridge_auth_and_workspace(self):
        self.assertEqual(self.client.post("/internal/company-whatsapp/auth/load",json={"workspace_id":"ninaos_company"}).status_code,401)
        auth={"Authorization":"Bearer bridge-test"}
        self.assertEqual(self.client.post("/internal/company-whatsapp/auth/load",headers=auth,json={"workspace_id":"other"}).status_code,400)


if __name__=="__main__":
    unittest.main()
