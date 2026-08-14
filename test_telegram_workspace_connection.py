import asyncio
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


_db_handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_FILE = _db_handle.name
_db_handle.close()
os.environ["DATABASE_URL"] = ""
os.environ["NINA_DB_FILE"] = TEST_DB_FILE
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TELEGRAM_TOKEN", "123456:test-telegram-token")

import app
import channel_connections


def update_for(user_id="101", chat_id="202", username="owner", full_name="Owner Name"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id, username=username, full_name=full_name),
        effective_chat=SimpleNamespace(id=chat_id),
    )


class TelegramWorkspaceConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        channel_connections.DATABASE_URL = ""
        channel_connections.DB_FILE = TEST_DB_FILE
        channel_connections.USE_POSTGRES = False
        channel_connections._SCHEMA_READY = False

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(TEST_DB_FILE)
        except OSError:
            pass

    def setUp(self):
        for workspace in ("workspace_start", "workspace_other", "workspace_cross"):
            channel_connections.disconnect(workspace, "telegram")

    def test_start_without_payload_preserves_default_behavior(self):
        update = update_for()
        context = SimpleNamespace(args=[])
        with patch.object(app, "nina_start_answer", return_value="existing-start") as default, patch.object(app, "referral_capture_welcome_answer") as referral, patch.object(app, "safe_reply_text", new=AsyncMock()) as reply:
            asyncio.run(app.start_command(update, context))
        default.assert_called_once_with("101")
        referral.assert_not_called()
        self.assertEqual(reply.await_args.args[1], "existing-start")

    def test_referral_payload_preserves_referral_behavior(self):
        update = update_for()
        context = SimpleNamespace(args=["NINA-12345"])
        with patch.object(app, "nina_start_answer") as default, patch.object(app, "referral_capture_welcome_answer", return_value="existing-referral") as referral, patch.object(app, "safe_reply_text", new=AsyncMock()) as reply:
            asyncio.run(app.start_command(update, context))
        referral.assert_called_once_with("101", "NINA-12345")
        default.assert_not_called()
        self.assertIn("existing-referral", reply.await_args.args[1])

    def test_valid_start_token_links_and_persists_identity(self):
        setup = channel_connections.create_telegram_token("workspace_start", "Nina7727_bot")
        update = update_for()
        with patch.object(app, "safe_reply_text", new=AsyncMock()) as reply:
            asyncio.run(app.start_command(update, SimpleNamespace(args=[setup["token"]])))
        saved = channel_connections.get_connection("workspace_start", "telegram")
        self.assertEqual(saved["status"], "connected")
        self.assertTrue(saved["token_used_at"])
        self.assertEqual(saved["metadata"]["telegram_user_id"], "101")
        self.assertEqual(saved["metadata"]["telegram_chat_id"], "202")
        self.assertEqual(saved["metadata"]["telegram_username"], "owner")
        self.assertEqual(saved["metadata"]["telegram_display_name"], "Owner Name")
        self.assertTrue(saved["metadata"]["linked_at"])
        self.assertIn("veiksmīgi savienots", reply.await_args.args[1])

    def test_consumed_expired_and_invalid_tokens_are_rejected(self):
        setup = channel_connections.create_telegram_token("workspace_start", "Nina7727_bot")
        first = channel_connections.consume_telegram_token(setup["token"], "101", "owner", "202", "Owner")
        self.assertIsNotNone(first)
        self.assertIsNone(channel_connections.consume_telegram_token(setup["token"], "101", "owner", "202", "Owner"))
        channel_connections.disconnect("workspace_start", "telegram")
        expired = channel_connections.create_telegram_token("workspace_start", "Nina7727_bot", ttl_seconds=60)
        self.assertIsNone(channel_connections.consume_telegram_token(expired["token"], "101", "owner", "202", "Owner", now=datetime.now(timezone.utc) + timedelta(minutes=2)))
        self.assertIsNone(channel_connections.consume_telegram_token("ninaos_invalid_payload", "101", "owner", "202", "Owner"))

    def test_cross_workspace_and_identity_reassignment_are_blocked(self):
        cross = channel_connections.create_telegram_token("workspace_cross", "Nina7727_bot")
        self.assertIsNone(channel_connections.consume_telegram_token(cross["token"], "101", "owner", "202", "Owner", expected_workspace_id="workspace_other"))
        self.assertEqual(channel_connections.get_connection("workspace_cross", "telegram")["status"], "pending")
        linked = channel_connections.consume_telegram_token(cross["token"], "101", "owner", "202", "Owner")
        self.assertIsNotNone(linked)
        with self.assertRaisesRegex(ValueError, "telegram_already_connected"):
            channel_connections.create_telegram_token("workspace_cross", "Nina7727_bot")
        other = channel_connections.create_telegram_token("workspace_other", "Nina7727_bot")
        self.assertIsNone(channel_connections.consume_telegram_token(other["token"], "101", "owner", "202", "Owner"))
        self.assertEqual(channel_connections.get_connection("workspace_other", "telegram")["status"], "pending")

    def test_prefixed_invalid_token_gets_safe_message_without_default_routing(self):
        update = update_for()
        invalid = "ninaos_" + "A" * 32
        with patch.object(app, "nina_start_answer") as default, patch.object(app, "referral_capture_welcome_answer") as referral, patch.object(app, "safe_reply_text", new=AsyncMock()) as reply:
            asyncio.run(app.start_command(update, SimpleNamespace(args=[invalid])))
        default.assert_not_called()
        referral.assert_not_called()
        self.assertIn("nav derīga", reply.await_args.args[1])

    def test_bot_token_is_absent_from_connection_persistence_and_output(self):
        setup = channel_connections.create_telegram_token("workspace_start", "Nina7727_bot")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            linked = channel_connections.consume_telegram_token(setup["token"], "101", "owner", "202", "Owner")
        self.assertIsNotNone(linked)
        provider_secret = os.environ["TELEGRAM_TOKEN"]
        self.assertNotIn(provider_secret, captured.getvalue())
        with open(TEST_DB_FILE, "rb") as database_file:
            self.assertNotIn(provider_secret.encode(), database_file.read())


if __name__ == "__main__":
    unittest.main()
