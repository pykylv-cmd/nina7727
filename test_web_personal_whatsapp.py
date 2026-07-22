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
        self.client.get('/channels?lang=en')
        self.workspace=self.web._verified_workspace_cookie(self.client.get_cookie(self.web._WORKSPACE_COOKIE).value)
        self.p.disconnect_personal(self.workspace); self.c.disconnect(self.workspace,"whatsapp")
    def test_cards_are_separate_and_mobile_css_present(self):
        html=self.client.get('/channels?lang=en').get_data(as_text=True)
        self.assertIn('Personal WhatsApp',html); self.assertIn('WhatsApp Business',html); self.assertIn('@media(max-width:640px)',html)
        self.assertLess(html.index('Personal WhatsApp'),html.index('WhatsApp Business'))
    def test_connect_qr_status_and_linked(self):
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'status':'connecting'}):
            response=self.client.post('/channels/whatsapp-personal/connect?lang=en',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_connect')})
        self.assertEqual(response.status_code,302); self.assertEqual(self.c.get_connection(self.workspace,'whatsapp_personal')['status'],'pending')
        pair=self.p.create_pairing_session(self.workspace)
        auth={'Authorization':'Bearer bridge-test'}
        response=self.client.post('/internal/personal-whatsapp/linked',headers=auth,json={'workspace_id':self.workspace,'session_token':pair['session_token'],'identity':{'jid':'1@s.whatsapp.net','masked_identity':'***1'}})
        self.assertEqual(response.status_code,200); self.assertIn('Connected',self.client.get('/channels?lang=en').get_data(as_text=True))
    def test_qr_proxy_rejects_active_content(self):
        self.c.set_connection_for_test(self.workspace,'whatsapp_personal','pending')
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'status':'connecting','qr_svg':'<svg onload=alert(1)></svg>'}):
            self.assertEqual(self.client.get('/channels/whatsapp-personal/status').get_json()['qr_svg'],'')
    def test_inbound_same_nina_and_boundaries(self):
        pair=self.p.create_pairing_session(self.workspace); self.p.mark_connected(self.workspace,pair['session_token'],{'jid':'1@s.whatsapp.net'})
        auth={'Authorization':'Bearer bridge-test'}
        with patch.object(self.web,'send_message_to_nina',return_value={'text':'Nina reply'}) as send:
            ok=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':self.workspace,'message_id':'x1','chat_jid':'1@s.whatsapp.net','text':'hello','is_group':False})
            self.assertEqual(ok.get_json()['reply'],'Nina reply'); send.assert_called_once_with('hello',workspace_id=self.workspace,channel='whatsapp_personal')
            denied=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':self.workspace,'message_id':'x2','chat_jid':'2@s.whatsapp.net','text':'hello','is_group':False})
            self.assertFalse(denied.get_json()['accepted'])
    def test_disconnect_does_not_touch_business(self):
        self.c.set_connection_for_test(self.workspace,'whatsapp','connected',{'business_display_name':'Biz'})
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'ok':True}):
            r=self.client.post('/channels/whatsapp-personal/disconnect',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_disconnect')})
        self.assertEqual(r.status_code,302); self.assertEqual(self.c.get_connection(self.workspace,'whatsapp')['status'],'connected')
    def test_internal_api_requires_auth(self):
        self.assertEqual(self.client.post('/internal/personal-whatsapp/auth/load',json={'workspace_id':'x'}).status_code,401)
    def test_two_web_users_connect_status_and_disconnect_independently(self):
        client_a=self.web.app.test_client(); client_b=self.web.app.test_client()
        client_a.get('/channels?lang=en'); client_b.get('/channels?lang=en')
        workspace_a=self.web._verified_workspace_cookie(client_a.get_cookie(self.web._WORKSPACE_COOKIE).value)
        workspace_b=self.web._verified_workspace_cookie(client_b.get_cookie(self.web._WORKSPACE_COOKIE).value)
        self.assertNotEqual(workspace_a,workspace_b)
        calls=[]
        with patch.object(self.web,'personal_whatsapp_bridge_request',side_effect=lambda path,payload:calls.append((path,payload)) or {'status':'connecting'}):
            for client in (client_a,client_b):
                self.assertEqual(client.post('/channels/whatsapp-personal/connect',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_connect')}).status_code,302)
        self.assertEqual([value[1]['workspace_id'] for value in calls],[workspace_a,workspace_b])
        pair_a=self.p.create_pairing_session(workspace_a); pair_b=self.p.create_pairing_session(workspace_b)
        self.p.mark_connected(workspace_a,pair_a['session_token'],{'jid':'a@s.whatsapp.net'}); self.p.mark_connected(workspace_b,pair_b['session_token'],{'jid':'b@s.whatsapp.net'})
        self.assertIn('Connected',client_a.get('/channels?lang=en').get_data(as_text=True)); self.assertIn('Connected',client_b.get('/channels?lang=en').get_data(as_text=True))
        with patch.object(self.web,'personal_whatsapp_bridge_request',return_value={'ok':True}):
            client_a.post('/channels/whatsapp-personal/disconnect',data={'csrf_token':self.web._channel_csrf('whatsapp_personal_disconnect')})
        self.assertEqual(self.c.get_connection(workspace_a,'whatsapp_personal')['status'],'disconnected')
        self.assertEqual(self.c.get_connection(workspace_b,'whatsapp_personal')['status'],'connected')
    def test_forged_workspace_cookie_is_replaced(self):
        client=self.web.app.test_client(); client.set_cookie(self.web._WORKSPACE_COOKIE,'web_'+'a'*32+'.'+'0'*64)
        client.get('/channels')
        workspace=self.web._verified_workspace_cookie(client.get_cookie(self.web._WORKSPACE_COOKIE).value)
        self.assertRegex(workspace,r'^web_[a-f0-9]{32}$'); self.assertNotEqual(workspace,'web_'+'a'*32)
    def test_inbound_messages_use_their_linked_nina_workspace(self):
        auth={'Authorization':'Bearer bridge-test'}
        for workspace,jid in [('workspace-a','a@s.whatsapp.net'),('workspace-b','b@s.whatsapp.net')]:
            pair=self.p.create_pairing_session(workspace); self.p.mark_connected(workspace,pair['session_token'],{'jid':jid})
        with patch.object(self.web,'send_message_to_nina',side_effect=lambda text,workspace_id,channel:{'text':workspace_id}) as send:
            a=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':'workspace-a','message_id':'a1','chat_jid':'a@s.whatsapp.net','text':'hello','is_group':False})
            b=self.client.post('/internal/personal-whatsapp/inbound',headers=auth,json={'workspace_id':'workspace-b','message_id':'b1','chat_jid':'b@s.whatsapp.net','text':'hello','is_group':False})
        self.assertEqual(a.get_json()['reply'],'workspace-a'); self.assertEqual(b.get_json()['reply'],'workspace-b')
        self.assertEqual([call.kwargs['workspace_id'] for call in send.call_args_list],['workspace-a','workspace-b'])

if __name__=='__main__': unittest.main()
