import importlib, os, tempfile, unittest
from unittest.mock import patch
from cryptography.fernet import Fernet


class WebPersonalWhatsAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); os.environ.pop("DATABASE_URL",None); os.environ["NINA_DB_FILE"]=os.path.join(cls.tmp.name,"web.db")
        os.environ["NINA_CHANNEL_CREDENTIAL_KEY"]=Fernet.generate_key().decode(); os.environ["NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN"]="bridge-test"
        import channel_connections, personal_whatsapp, web_app
        cls.c=importlib.reload(channel_connections); cls.p=importlib.reload(personal_whatsapp); cls.web=importlib.reload(web_app); cls.client=cls.web.app.test_client()
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def setUp(self):
        self.p.disconnect_personal(self.web.NINA_WEB_WORKSPACE_ID); self.c.disconnect(self.web.NINA_WEB_WORKSPACE_ID,"whatsapp")
    def test_cards_are_separate_and_mobile_css_present(self):
        html=self.client.get('/channels?lang=en').get_data(as_text=True)
        self.assertIn('Personal WhatsApp',html); self.assertIn('WhatsApp Business',html); self.assertIn('@media(max-width:640px)',html)
        self.assertLess(html.index('Personal WhatsApp'),html.index('WhatsApp Business'))
    def test_connect_qr_status_and_linked(self):
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'status':'connecting'}):
            response=self.client.post('/channels/whatsapp-personal/connect?lang=en',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_connect')})
        self.assertEqual(response.status_code,302); self.assertEqual(self.c.get_connection(self.web.NINA_WEB_WORKSPACE_ID,'whatsapp_personal')['status'],'pending')
        pair=self.p.create_pairing_session(self.web.NINA_WEB_WORKSPACE_ID)
        auth={'Authorization':'Bearer bridge-test'}
        response=self.client.post('/internal/personal-whatsapp/linked',headers=auth,json={'workspace_id':self.web.NINA_WEB_WORKSPACE_ID,'session_token':pair['session_token'],'identity':{'jid':'1@s.whatsapp.net','masked_identity':'***1'}})
        self.assertEqual(response.status_code,200); self.assertIn('Connected',self.client.get('/channels?lang=en').get_data(as_text=True))
    def test_qr_proxy_rejects_active_content(self):
        self.c.set_connection_for_test(self.web.NINA_WEB_WORKSPACE_ID,'whatsapp_personal','pending')
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'status':'connecting','qr_svg':'<svg onload=alert(1)></svg>'}):
            self.assertEqual(self.client.get('/channels/whatsapp-personal/status').get_json()['qr_svg'],'')
    def test_inbound_same_nina_and_boundaries(self):
        pair=self.p.create_pairing_session(self.web.NINA_WEB_WORKSPACE_ID); self.p.mark_connected(self.web.NINA_WEB_WORKSPACE_ID,pair['session_token'],{'jid':'1@s.whatsapp.net'})
        auth={'Authorization':'Bearer bridge-test'}
        with patch.object(self.web,'send_message_to_nina',return_value={'text':'Nina reply'}) as send:
            ok=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':self.web.NINA_WEB_WORKSPACE_ID,'message_id':'x1','chat_jid':'1@s.whatsapp.net','text':'hello','is_group':False})
            self.assertEqual(ok.get_json()['reply'],'Nina reply'); send.assert_called_once_with('hello',workspace_id=self.web.NINA_WEB_WORKSPACE_ID,channel='whatsapp_personal')
            denied=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':self.web.NINA_WEB_WORKSPACE_ID,'message_id':'x2','chat_jid':'2@s.whatsapp.net','text':'hello','is_group':False})
            self.assertFalse(denied.get_json()['accepted'])
    def test_disconnect_does_not_touch_business(self):
        self.c.set_connection_for_test(self.web.NINA_WEB_WORKSPACE_ID,'whatsapp','connected',{'business_display_name':'Biz'})
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'ok':True}):
            r=self.client.post('/channels/whatsapp-personal/disconnect',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_disconnect')})
        self.assertEqual(r.status_code,302); self.assertEqual(self.c.get_connection(self.web.NINA_WEB_WORKSPACE_ID,'whatsapp')['status'],'connected')
    def test_internal_api_requires_auth(self):
        self.assertEqual(self.client.post('/internal/personal-whatsapp/auth/load',json={'workspace_id':'x'}).status_code,401)

if __name__=='__main__': unittest.main()
