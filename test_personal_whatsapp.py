import importlib, json, os, tempfile, unittest
from unittest.mock import patch

from cryptography.fernet import Fernet


class PersonalWhatsAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.old = dict(os.environ)
        os.environ.pop("DATABASE_URL", None); os.environ["NINA_DB_FILE"] = os.path.join(self.tmp.name, "db.sqlite")
        os.environ["NINA_CHANNEL_CREDENTIAL_KEY"] = Fernet.generate_key().decode(); os.environ["NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN"] = "internal-test-token"
        import channel_connections, personal_whatsapp
        importlib.reload(channel_connections); self.p = importlib.reload(personal_whatsapp)
    def tearDown(self): os.environ.clear(); os.environ.update(self.old); self.tmp.cleanup()
    def test_pairing_is_scoped_expires_and_consumes(self):
        pair = self.p.create_pairing_session("a")
        self.assertTrue(self.p.validate_pairing_session("a", pair["session_token"]))
        self.assertFalse(self.p.validate_pairing_session("b", pair["session_token"]))
        from datetime import datetime, timezone, timedelta
        self.assertFalse(self.p.validate_pairing_session("a", pair["session_token"], now=datetime.now(timezone.utc)+timedelta(hours=1)))
        self.assertIsNotNone(self.p.mark_connected("a", pair["session_token"], {"jid":"1@s.whatsapp.net","masked_identity":"***01"}))
        self.assertFalse(self.p.validate_pairing_session("a", pair["session_token"]))
    def test_auth_is_encrypted_and_restart_loads(self):
        self.p.store_auth_record("a", "creds", {"secret":"value"})
        import sqlite3
        conn=sqlite3.connect(os.environ["NINA_DB_FILE"]); row=conn.execute("select encrypted_value from nina_personal_whatsapp_auth").fetchone()[0]; conn.close()
        self.assertTrue(row.startswith("enc:v1:")); self.assertNotIn("value", row)
        self.p=importlib.reload(self.p)
        self.assertEqual(self.p.load_auth_records("a")["creds"]["secret"], "value")
    def test_self_chat_only_dedupe_groups_and_disconnect(self):
        pair=self.p.create_pairing_session("a"); self.p.mark_connected("a",pair["session_token"],{"jid":"1@s.whatsapp.net"})
        self.assertTrue(self.p.accept_inbound("a","m1","1@s.whatsapp.net","hello")); self.assertFalse(self.p.accept_inbound("a","m1","1@s.whatsapp.net","hello"))
        self.assertFalse(self.p.accept_inbound("a","m2","2@s.whatsapp.net","hello")); self.assertFalse(self.p.accept_inbound("a","m3","1@g.us","hello",True))
        self.p.store_auth_record("a","creds",{"x":1}); self.p.disconnect_personal("a")
        self.assertEqual(self.p.load_auth_records("a"),{}); self.assertFalse(self.p.accept_inbound("a","m4","1@s.whatsapp.net","hello"))
    def test_business_separate(self):
        import channel_connections as c
        c.set_connection_for_test("a","whatsapp","connected",{"business_display_name":"Biz"})
        self.p.disconnect_personal("a")
        self.assertEqual(c.get_connection("a","whatsapp")["status"],"connected")
    def test_bridge_auth(self):
        self.assertTrue(self.p.authorize_bridge("Bearer internal-test-token")); self.assertFalse(self.p.authorize_bridge("Bearer no"))

if __name__ == "__main__": unittest.main()
