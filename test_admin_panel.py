import os
import unittest
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "test-workspace-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "test-admin-bootstrap-token-at-least-32")

import web_app


class AdminPanelSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(
            web_app.ADMIN_COOKIE,
            web_app.create_admin_session(web_app._workspace_cookie_secret()),
        )
        return client

    def test_admin_can_open_channels_and_navigation_is_role_scoped(self):
        admin = self.admin_client()
        page = admin.get("/admin/channels?lang=en")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"NinaOS Company WhatsApp", page.data)
        self.assertIn(b">Admin<", page.data)
        client_page = web_app.app.test_client().get("/channels?lang=en")
        self.assertNotIn(b">Admin<", client_page.data)

    def test_clients_sidebar_link_is_role_aware(self):
        admin_page = self.admin_client().get("/admin/channels?lang=en").get_data(as_text=True)
        client_page = web_app.app.test_client().get("/channels?lang=en").get_data(as_text=True)

        self.assertIn("href='/admin/clients?lang=en'", admin_page)
        self.assertNotIn("href='/clients?lang=en'", admin_page)
        self.assertIn("href='/clients?lang=en'", client_page)
        self.assertNotIn("href='/admin/clients?lang=en'", client_page)

    def test_admin_company_connect_status_qr_and_disconnect(self):
        admin = self.admin_client()
        env = {
            "NINA_COMPANY_WHATSAPP_NUMBER": "+37120714711",
            "NINA_COMPANY_WHATSAPP_WORKSPACE": "ninaos_company",
        }
        with patch.dict(os.environ, env), \
             patch.object(web_app, "create_company_whatsapp_pairing", return_value={"session_token": "single-use"}), \
             patch.object(web_app, "personal_whatsapp_bridge_request", return_value={"status": "connecting"}) as bridge:
            response = admin.post(
                "/channels/whatsapp-company/connect",
                data={"csrf_token": web_app._channel_csrf("whatsapp_company_connect")},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(bridge.call_args.args[0], "/v1/company/sessions")

        with patch.dict(os.environ, env), \
             patch.object(web_app, "get_connection", return_value={"status": "pending", "metadata": {}}), \
             patch.object(web_app, "company_whatsapp_pairing_is_active", return_value=True), \
             patch.object(web_app, "personal_whatsapp_bridge_request", return_value={"status": "connecting", "qr_svg": "<svg></svg>"}):
            status = admin.get("/channels/whatsapp-company/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()["qr_svg"], "<svg></svg>")
        self.assertIn("no-store", status.headers["Cache-Control"])

        with patch.dict(os.environ, env), \
             patch.object(web_app, "personal_whatsapp_bridge_request", return_value={"ok": True}), \
             patch.object(web_app, "disconnect_company_whatsapp") as disconnect:
            response = admin.post(
                "/channels/whatsapp-company/disconnect",
                data={"csrf_token": web_app._channel_csrf("whatsapp_company_disconnect")},
            )
        self.assertEqual(response.status_code, 302)
        disconnect.assert_called_once_with("ninaos_company")

    def test_client_and_anonymous_cannot_reach_admin_controls_or_pairing_qr(self):
        client = web_app.app.test_client()
        for method, route in (
            ("get", "/admin/channels"),
            ("post", "/channels/whatsapp-company/connect"),
            ("get", "/channels/whatsapp-company/status"),
            ("post", "/channels/whatsapp-company/disconnect"),
            ("post", "/channels/whatsapp-personal/connect"),
            ("get", "/channels/whatsapp-personal/status"),
            ("post", "/channels/telegram/connect"),
            ("post", "/channels/whatsapp/start"),
        ):
            self.assertEqual(getattr(client, method)(route).status_code, 403)

    def test_client_channels_are_product_facing_only(self):
        with patch.dict(os.environ, {"NINA_COMPANY_WHATSAPP_NUMBER": "+37120714711"}):
            page = web_app.app.test_client().get("/channels?lang=en").get_data(as_text=True)
        self.assertIn("Talk to Nina", page)
        self.assertIn("href='/nina?lang=en'", page)
        for forbidden in (
            "Connect company phone", "Disconnect", "Linked Devices",
            "bridge", "workspace_id", "qr_svg", "NinaOS Company WhatsApp",
            "WhatsApp", "wa.me", "/nina/contact-qr.svg", "/nina/contact.vcf",
        ):
            self.assertNotIn(forbidden, page)

    def test_client_web_chat_does_not_expose_platform_contact_or_messages(self):
        with patch.dict(os.environ, {"NINA_COMPANY_WHATSAPP_NUMBER": "+37120714711"}):
            page = web_app.app.test_client().get("/nina?lang=en").get_data(as_text=True)
        self.assertNotIn("wa.me", page)
        self.assertNotIn("/nina/contact-qr.svg", page)
        self.assertNotIn("/nina/contact.vcf", page)
        self.assertNotIn("NinaOS Company WhatsApp", page)

    def test_channel_layer_uses_signed_client_workspace_and_denies_management(self):
        client = web_app.app.test_client()
        workspace_id = "web_" + "a" * 32
        client.set_cookie(
            web_app._WORKSPACE_COOKIE,
            web_app._workspace_cookie_value(workspace_id),
        )
        with patch.object(web_app, "list_layer_connections", return_value=()) as listed:
            response = client.get("/channel-layer/connections")
        self.assertEqual(response.status_code, 200)
        listed.assert_called_once_with(workspace_id, limit=100)

        with patch.object(web_app, "create_layer_connection") as create:
            response = client.post(
                "/channel-layer/create",
                data={"csrf_token": web_app._channel_csrf("channel:create")},
            )
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_cross_workspace_connection_id_is_fail_closed(self):
        client = web_app.app.test_client()
        client.set_cookie(
            web_app._WORKSPACE_COOKIE,
            web_app._workspace_cookie_value("web_" + "b" * 32),
        )
        with patch.object(web_app, "update_layer_connection") as update:
            response = client.post(
                "/channel-layer/platform-connection/disconnect",
                data={
                    "csrf_token": web_app._channel_csrf(
                        "channel:disconnect:platform-connection"
                    )
                },
            )
        self.assertEqual(response.status_code, 403)
        update.assert_not_called()

    def test_public_contact_qr_is_distinct_from_private_pairing_status(self):
        client = web_app.app.test_client()
        with patch.dict(os.environ, {"NINA_COMPANY_WHATSAPP_NUMBER": "+37120714711"}):
            public_qr = client.get("/nina/contact-qr.svg")
        self.assertEqual(public_qr.status_code, 200)
        self.assertIn("image/svg+xml", public_qr.content_type)
        self.assertEqual(client.get("/channels/whatsapp-company/status").status_code, 403)
        self.assertNotEqual("/nina/contact-qr.svg", "/channels/whatsapp-company/status")

    def test_forged_role_and_workspace_cookies_do_not_grant_admin(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE, "platform_admin:9999999999." + "0" * 64)
        client.set_cookie(web_app._WORKSPACE_COOKIE, "web_" + "a" * 32 + "." + "0" * 64)
        self.assertEqual(client.get("/admin/channels").status_code, 403)
        self.assertEqual(client.get("/channels/whatsapp-company/status").status_code, 403)

    def test_bootstrap_token_issues_admin_session_without_exposing_token(self):
        token = "test-admin-bootstrap-token-at-least-32"
        with patch.dict(os.environ, {"NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN": token}):
            client = web_app.app.test_client()
            response = client.post("/admin/login", data={"bootstrap_token": token})
            self.assertEqual(response.status_code, 302)
            cookie = client.get_cookie(web_app.ADMIN_COOKIE)
            self.assertIsNotNone(cookie)
            self.assertNotIn(token, cookie.value)
            self.assertEqual(client.get("/admin/channels").status_code, 200)

    def test_bootstrap_login_normalizes_input_and_disables_browser_autofill(self):
        token = "TempAdmin2026!"
        with patch.dict(os.environ, {"NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN": token}):
            client = web_app.app.test_client()
            page = client.get("/admin/login?lang=en")
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"name='bootstrap_token'", page.data)
            self.assertIn(b"autocomplete='off'", page.data)
            self.assertIn(b"autocapitalize='none'", page.data)
            self.assertIn(b"spellcheck='false'", page.data)
            response = client.post(
                "/admin/login?lang=en",
                data={"bootstrap_token": f"  {token}  "},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/admin/channels?lang=en")
            self.assertEqual(client.get("/admin/channels?lang=en").status_code, 200)

    def test_invalid_bootstrap_login_redirects_to_fresh_empty_form(self):
        token = "test-admin-bootstrap-token-at-least-32"
        with patch.dict(os.environ, {"NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN": token}):
            client = web_app.app.test_client()
            response = client.post(
                "/admin/login?lang=en",
                data={"bootstrap_token": "stale-invalid-token"},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/admin/login?lang=en&notice=invalid")
            page = client.get(response.headers["Location"])
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Invalid admin access token. Please try again.", page.data)
            self.assertIn(b"name='bootstrap_token'", page.data)
            self.assertNotIn(b"value='stale-invalid-token'", page.data)
            self.assertIsNone(client.get_cookie(web_app.ADMIN_COOKIE))


if __name__ == "__main__":
    unittest.main()
