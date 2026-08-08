import os
import unittest
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "router-v2-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "router-v2-admin-token-at-least-32")

import web_app


class DeveloperRouterV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_app.app.config.update(TESTING=True)

    def admin_client(self):
        client = web_app.app.test_client()
        client.set_cookie(web_app.ADMIN_COOKIE,
                          web_app.create_admin_session(web_app._workspace_cookie_secret()))
        return client

    def test_multiple_phrasings_resolve_to_same_intent(self):
        repository = (
            "Analizē repozitorija struktūru",
            "Explain the repo architecture",
            "Parādi projekta failu analīzi",
        )
        self.assertTrue(all("repository_analysis" in web_app._developer_intents(text)
                            for text in repository))
        ui = ("Analizē Developer Console UI", "Review the Developer Console status cards")
        self.assertTrue(all("ui_analysis" in web_app._developer_intents(text) for text in ui))

    def test_all_supported_intents_are_deterministically_recognized(self):
        examples = {
            "repository_analysis": "Analizē repo failus",
            "ui_analysis": "Review Developer Console UI",
            "architecture_analysis": "Izskaidro Company WhatsApp message flow",
            "risk_analysis": "Atrodi regresijas riskus šajā modulī",
            "code_search": "Atrodi kodā funkciju send_message_to_nina",
            "diff_request": "Sagatavo diff preview",
            "release_request": "Deployo apstiprināto release",
        }
        for expected, text in examples.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, web_app._developer_intents(text))

    def test_existing_brain_plans_follow_intent_resolution(self):
        variants = (
            "Atrodi kodā, kur tiek definēts send_message_to_nina",
            "Find the function definition send_message_to_nina in code",
        )
        for text in variants:
            kind, plan = web_app._developer_investigation_plan(text)
            self.assertEqual(kind, "send_message_definition")
            self.assertTrue(plan)
        kind, plan = web_app._developer_investigation_plan(
            "Izskaidro Company WhatsApp arhitektūras message flow un moduļus"
        )
        self.assertEqual(kind, "company_whatsapp_flow")
        self.assertTrue(plan)

    def test_release_intent_is_non_executable_and_uses_owner_approval_boundary(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Deployo šo release"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["notice"], "developer_release_requires_owner_approval")
        create.assert_not_called()

    def test_supported_but_underspecified_intent_requests_context(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Analizē arhitektūras riskus"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["notice"], "developer_intent_requires_context")
        create.assert_not_called()

    def test_unknown_remains_fail_closed_only_without_supported_intent(self):
        self.assertEqual(web_app._developer_intents("Sveika, Nina"), ())
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"), "message": "Sveika, Nina"},
            )
        self.assertEqual(response.get_json()["notice"], "unsupported_developer_command")
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
