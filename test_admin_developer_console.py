import os
import unittest
from unittest.mock import patch

os.environ.setdefault("NINA_WEB_WORKSPACE_COOKIE_SECRET", "test-workspace-cookie-secret-at-least-32")
os.environ.setdefault("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN", "test-admin-bootstrap-token-at-least-32")

import web_app


class AdminDeveloperConsoleTests(unittest.TestCase):
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

    def test_unauthenticated_developer_console_is_denied(self):
        self.assertEqual(web_app.app.test_client().get("/admin/developer").status_code, 403)

    def test_authenticated_admin_can_open_developer_console(self):
        response = self.admin_client().get("/admin/developer?lang=en")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"NINA DEVELOPER", response.data)

    def test_developer_navigation_is_admin_only(self):
        admin_page = self.admin_client().get("/admin/channels?lang=en").get_data(as_text=True)
        self.assertIn("href='/admin/developer?lang=en'", admin_page)
        client = web_app.app.test_client()
        for route in ("/dashboard", "/channels", "/inbox", "/workers", "/tasks", "/clients",
                      "/projects", "/calendar", "/files", "/analytics", "/exchange"):
            with self.subTest(route=route):
                response = client.get(route + "?lang=en")
                self.assertNotIn("/admin/developer", response.get_data(as_text=True))

    def test_admin_subnav_fails_closed_outside_admin_context(self):
        with web_app.app.test_request_context("/dashboard?lang=en"), \
             patch.object(web_app, "current_web_role", return_value=web_app.CLIENT_ROLE):
            self.assertEqual(web_app._admin_subnav(), "")

    def test_client_workspace_session_cannot_open_developer_console(self):
        client = web_app.app.test_client()
        client.set_cookie(
            web_app._WORKSPACE_COOKIE,
            web_app._workspace_cookie_value("client_security_hotfix_test"),
        )
        self.assertEqual(client.get("/admin/developer").status_code, 403)

    def test_developer_statuses_are_fail_closed(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "not_connected", "repository": "not_connected"}):
            page = self.admin_client().get("/admin/developer?lang=en").get_data(as_text=True)
        for expected in (
            "Developer Console", "Online", "Local Developer Agent", "Not connected",
            "Repository", "AI Coding Model", "Not configured", "Write Access",
            "Deploy Access", "Disabled",
        ):
            self.assertIn(expected, page)
        self.assertIn("placeholder='Developer Agent is not connected' disabled", page)

    def test_repository_disconnected_blocks_diff_approval(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "not_connected"}), \
             patch.object(web_app, "create_developer_approval_job") as create:
            response = client.post("/admin/developer", data={
                "csrf_token": web_app._channel_csrf("developer:approve"),
                "action": "approve_diff", "investigation_id": "devinvest_test",
                "diff_hash": "0" * 64,
            })
        self.assertEqual(response.status_code, 409)
        create.assert_not_called()

    def test_repository_disconnected_blocks_direct_post(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "not_connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = client.post("/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Developer: paradi git status"})
        self.assertEqual(response.status_code, 409)
        create.assert_not_called()

    def test_connected_status_and_message_input_use_same_backend_state(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}):
            page = self.admin_client().get("/admin/developer?lang=en").get_data(as_text=True)
        self.assertIn("Local Developer Agent</small><b>Connected", page)
        self.assertIn("Repository</small><b>Connected", page)
        self.assertIn("id='developer-message' name='message' maxlength='2000' placeholder=''></textarea>", page)
        self.assertNotIn("Developer Agent is not connected", page)
        self.assertNotIn("type='submit' disabled", page)

    def test_send_only_renders_setup_notice_without_external_action(self):
        client = self.admin_client()
        with patch.object(web_app, "send_message_to_nina") as nina, \
             patch.object(web_app, "personal_whatsapp_bridge_request") as bridge:
            response = client.post(
                "/admin/developer?lang=en",
                data={
                    "csrf_token": web_app._channel_csrf("developer:send"),
                    "message": "Developer: show files",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Developer Agent vēl nav pieslēgts", response.get_data(as_text=True))
        nina.assert_not_called()
        bridge.assert_not_called()

    def test_existing_telegram_and_whatsapp_routes_remain_guarded(self):
        rules = {(rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"}))) for rule in web_app.app.url_map.iter_rules()}
        self.assertIn(("/channels/telegram/connect", ("POST",)), rules)
        self.assertIn(("/channels/whatsapp-company/connect", ("POST",)), rules)
        self.assertIn(("/channels/whatsapp-company/status", ("GET",)), rules)
        client = web_app.app.test_client()
        self.assertEqual(client.post("/channels/telegram/connect").status_code, 403)
        self.assertEqual(client.post("/channels/whatsapp-company/connect").status_code, 403)
        self.assertEqual(client.get("/channels/whatsapp-company/status").status_code, 403)

    def test_console_is_sticky_and_results_scroll_independently(self):
        page = self.admin_client().get("/admin/developer?lang=en").get_data(as_text=True)
        self.assertIn("class='card card-pad developer-console'", page)
        self.assertIn(".developer-console{position:sticky", page)
        self.assertIn("id='developer-results'", page)
        self.assertIn(".developer-results{max-height:52vh;overflow-y:auto", page)
        self.assertLess(page.index("id='developer-form'"), page.index("id='developer-results'"))

    def test_console_uses_ajax_and_restores_focus_and_result_scroll(self):
        page = self.admin_client().get("/admin/developer?lang=en").get_data(as_text=True)
        self.assertIn("form.addEventListener('submit'", page)
        self.assertIn("event.preventDefault()", page)
        self.assertIn("fetch(form.action", page)
        self.assertIn("fetch('/admin/developer?format=results'", page)
        self.assertIn("input.focus()", page)
        self.assertIn("results.scrollTop=results.scrollHeight", page)
        self.assertNotIn("window.location", page)

    def test_ajax_submit_queues_only_read_only_job(self):
        client = self.admin_client()
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job", return_value="devjob_test") as create:
            response = client.post(
                "/admin/developer",
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Developer: paradi projekta failus"},
                headers={"Accept": "application/json"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        create.assert_called_once_with("list_root", {})

    def test_connected_unsupported_command_is_not_misclassified_as_disconnected(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Developer: nezināma komanda"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["notice"], "unsupported_developer_command")
        self.assertNotEqual(response.get_json()["notice"], "agent_not_connected")
        create.assert_not_called()

    def test_actually_disconnected_agent_keeps_disconnected_error(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "not_connected", "repository": "not_connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"),
                      "message": "Developer: parādi projekta failus"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["notice"], "agent_not_connected")
        create.assert_not_called()

    def test_exact_status_cards_live_intent_routes_to_existing_investigation(self):
        command = (
            "Analizē Developer Console statusu kartītes. Atrodi vienu zema riska uzlabojumu, "
            "kas padara statusu saprotamāku. Pirms jebkādas izmaiņas parādi Developer Analysis, "
            "Quality Review un Diff Preview."
        )
        kind, steps = web_app._developer_investigation_plan(command)
        self.assertEqual(kind, "developer_status_diff_preview")
        self.assertTrue(steps)
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            response = self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"), "message": command},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(create.called)
        self.assertTrue(all(call.args[0] == "search_text" for call in create.call_args_list))

    def test_frontend_preserves_safe_backend_error_and_has_generic_fallback(self):
        page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        self.assertIn("failure.safeMessage=payload.message||payload.error||''", page)
        self.assertIn("error.safeMessage||'Developer command could not be completed.'", page)

    def test_write_and_deploy_access_remain_disabled_for_unsupported_command(self):
        with patch.object(web_app, "developer_connection_status",
                          return_value={"agent": "connected", "repository": "connected"}), \
             patch.object(web_app, "create_developer_job") as create:
            self.admin_client().post(
                "/admin/developer", headers={"Accept": "application/json"},
                data={"csrf_token": web_app._channel_csrf("developer:send"), "message": "unsupported"},
            )
            page = self.admin_client().get("/admin/developer").get_data(as_text=True)
        create.assert_not_called()
        self.assertIn("Write Access</small><b>Disabled", page)
        self.assertIn("Deploy Access</small><b>Disabled", page)

    def test_ajax_results_endpoint_remains_admin_only(self):
        denied = web_app.app.test_client().get(
            "/admin/developer?format=results", headers={"Accept": "application/json"}
        )
        self.assertEqual(denied.status_code, 403)
        allowed = self.admin_client().get(
            "/admin/developer?format=results", headers={"Accept": "application/json"}
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("html", allowed.get_json())

    def test_results_render_oldest_to_newest_for_bottom_scroll(self):
        newest = {"operation": "git_status", "status": "completed", "result": {"status": "newest"}}
        oldest = {"operation": "list_root", "status": "completed", "result": {"path": "oldest"}}
        with patch.object(web_app, "list_developer_jobs", return_value=[newest, oldest]):
            rendered, latest_status = web_app._admin_developer_jobs_html()
        self.assertLess(rendered.index("list_root"), rendered.index("git_status"))
        self.assertEqual(latest_status, "completed")


if __name__ == "__main__":
    unittest.main()
