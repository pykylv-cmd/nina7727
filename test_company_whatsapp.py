import importlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()


class CompanyWhatsAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db_file=os.path.join(cls.tmp.name,"company.db")
        cls.env=patch.dict(os.environ,{
            "DATABASE_URL":"",
            "NINA_RUNTIME_ENV":"test",
            "NINA_DB_FILE":cls.db_file,
            "NINA_CHANNEL_CREDENTIAL_KEY":Fernet.generate_key().decode(),
            "NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN":"bridge-test",
            "NINA_COMPANY_WHATSAPP_NUMBER":"+37120714711",
            "NINA_COMPANY_WHATSAPP_WORKSPACE":"ninaos_company",
            "NINAOS_NUMBER_IDENTITY_KEY":"stable-company-identity-key",
        })
        cls.env.start()
        import channel_connections, personal_whatsapp, company_whatsapp, nina_message_service, ninaos_number, web_app
        cls.connections=importlib.reload(channel_connections)
        cls.personal=importlib.reload(personal_whatsapp)
        cls.company=importlib.reload(company_whatsapp)
        cls.service=importlib.reload(nina_message_service)
        cls.number=importlib.reload(ninaos_number)
        cls.web=importlib.reload(web_app)
        cls.restore_database=bind_sqlite_database(
            cls.db_file, cls.connections, cls.personal, cls.company, cls.service
        )
        initialize_ready_web(cls.web)
        cls.web.app.config.update(TESTING=True)
        cls.client=cls.web.app.test_client()
        cls.client.set_cookie(
            cls.web.ADMIN_COOKIE,
            cls.web.create_admin_session(cls.web._workspace_cookie_secret()),
        )

    @classmethod
    def tearDownClass(cls):
        cls.restore_database()
        cls.env.stop()
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

    def test_saved_auth_is_restorable_and_runtime_state_survives_restart(self):
        self.company.store_auth_record("ninaos_company", "creds", {"registered": True, "noiseKey": {"private": "encrypted"}})
        self.company.store_auth_record("ninaos_company", "key:session:one", {"value": "incremental"})
        pair = self.company.create_pairing_session()
        self.company.mark_connected("ninaos_company", pair["session_token"], {"masked_identity": "*******4711"})

        self.assertEqual(self.company.list_connected_workspaces(), ["ninaos_company"])
        auth = {"Authorization": "Bearer bridge-test"}
        loaded = self.client.post(
            "/internal/company-whatsapp/auth/load", headers=auth, json={"workspace_id": "ninaos_company"}
        ).get_json()["records"]
        self.assertTrue(loaded["creds"]["registered"])
        self.assertEqual(loaded["key:session:one"]["value"], "incremental")

        reconnecting = self.client.post(
            "/internal/company-whatsapp/runtime-state",
            headers=auth,
            json={"workspace_id": "ninaos_company", "state": "reconnecting"},
        )
        self.assertEqual(reconnecting.status_code, 200)
        self.assertEqual(self.connections.get_connection("ninaos_company", "whatsapp_company")["status"], "pending")
        self.assertEqual(self.company.list_connected_workspaces(), ["ninaos_company"])
        invalid = self.client.post(
            "/internal/company-whatsapp/runtime-state",
            headers=auth,
            json={"workspace_id": "ninaos_company", "state": "invalid_auth"},
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(self.connections.get_connection("ninaos_company", "whatsapp_company")["status"], "error")
        self.assertEqual(self.company.list_connected_workspaces(), [])

    def test_reconnecting_status_is_not_mistaken_for_expired_pairing(self):
        self.company.store_auth_record("ninaos_company", "creds", {"registered": True})
        self.connections.set_connection_for_test(
            "ninaos_company", "whatsapp_company", "pending",
            {"mode": "company_external", "runtime_state": "reconnecting"},
        )
        with patch.object(self.web, "personal_whatsapp_bridge_request", return_value={"status": "connecting"}):
            response = self.client.get("/channels/whatsapp-company/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "connecting")
        self.assertEqual(
            self.connections.get_connection("ninaos_company", "whatsapp_company")["status"], "pending"
        )
        self.assertEqual(self.company.list_connected_workspaces(), ["ninaos_company"])

    def test_auth_survives_python_reload_and_wrong_key_is_diagnostic(self):
        self.company.store_auth_record("ninaos_company", "creds", {"registered": True})
        self.connections.set_connection_for_test("ninaos_company", "whatsapp_company", "connected", {})
        restored = importlib.reload(self.company)
        records, healthy = restored.load_auth_records_with_diagnostics("ninaos_company")
        self.assertTrue(records["creds"]["registered"])
        self.assertEqual(healthy["error_class"], "")
        with patch.dict(os.environ, {"NINA_CHANNEL_CREDENTIAL_KEY": Fernet.generate_key().decode()}):
            records, broken = restored.load_auth_records_with_diagnostics("ninaos_company")
            self.assertEqual(records, {})
            self.assertEqual(broken["error_class"], "invalid_auth")
            self.assertGreater(broken["invalid_record_count"], 0)

    def test_admin_system_exposes_only_safe_company_restoration_diagnostics(self):
        self.company.store_auth_record("ninaos_company", "creds", {"registered": True})
        self.connections.set_connection_for_test("ninaos_company", "whatsapp_company", "connected", {})
        with patch.object(
            self.web, "personal_whatsapp_bridge_request",
            return_value={"restoration_state": "connected", "last_error_class": "", "last_connected_at": "2026-01-01T00:00:00Z"},
        ):
            page = self.client.get("/admin/system?lang=en").get_data(as_text=True)
        self.assertIn("Bridge reachable", page)
        self.assertIn("Runtime environment", page)
        self.assertIn("Persistence backend", page)
        self.assertIn("PostgreSQL URL source", page)
        self.assertIn("Database reachable", page)
        self.assertIn("Database identity", page)
        self.assertIn("Contact Identity rows", page)
        self.assertIn("Client Mapping rows", page)
        self.assertIn("Company auth rows", page)
        self.assertIn("Company persisted channel status", page)
        self.assertIn("Work Object rows", page)
        self.assertIn("Stored auth records", page)
        self.assertIn("Restoration state", page)
        self.assertNotIn("registered", page)
        self.assertNotIn("NINA_CHANNEL_CREDENTIAL_KEY", page)

    def test_only_logged_out_runtime_state_requires_new_qr(self):
        self.connections.set_connection_for_test("ninaos_company", "whatsapp_company", "connected", {})
        invalid = self.company.mark_runtime_state("ninaos_company", "invalid_auth")
        self.assertFalse(invalid["metadata"]["qr_required"])
        logged_out = self.company.mark_runtime_state("ninaos_company", "logged_out")
        self.assertTrue(logged_out["metadata"]["qr_required"])

    def test_persisted_auth_restores_even_after_prior_error_status(self):
        self.company.store_auth_record("ninaos_company", "creds", {"registered": True})
        self.company.store_auth_record("ninaos_company", "key:session:one", {"value": "saved"})
        self.connections.set_connection_for_test(
            "ninaos_company", "whatsapp_company", "error", {"error_code": "pairing_expired"}
        )
        self.assertEqual(self.company.list_connected_workspaces(), ["ninaos_company"])
        auth = {"Authorization": "Bearer bridge-test"}
        active = self.client.post("/internal/company-whatsapp/active", headers=auth, json={})
        self.assertEqual(active.get_json()["workspace_ids"], ["ninaos_company"])
        loaded = self.client.post(
            "/internal/company-whatsapp/auth/load", headers=auth, json={"workspace_id": "ninaos_company"}
        )
        self.assertEqual(loaded.status_code, 200)
        self.assertTrue(loaded.get_json()["records"]["creds"]["registered"])
        self.assertEqual(loaded.get_json()["diagnostics"]["result_class"], "loaded")

    def test_auth_load_outcomes_and_explicit_disconnect_eligibility(self):
        auth = {"Authorization": "Bearer bridge-test"}
        missing = self.client.post(
            "/internal/company-whatsapp/auth/load", headers=auth, json={"workspace_id": "ninaos_company"}
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["error"], "no_auth_records")

        self.company.store_auth_record("ninaos_company", "creds", {"registered": True})
        self.connections.set_connection_for_test("ninaos_company", "whatsapp_company", "error", {})
        self.assertEqual(self.company.list_connected_workspaces(), ["ninaos_company"])
        self.company.disconnect_company("ninaos_company")
        self.assertEqual(self.company.list_connected_workspaces(), [])
        self.assertEqual(self.company.load_auth_records("ninaos_company"), {})


if __name__=="__main__":
    unittest.main()
