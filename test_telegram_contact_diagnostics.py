import ast
import asyncio
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

import app
import channel_connections
import contact_identity


class TelegramContactDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.tmp.name, "telegram-contact.sqlite")
        cls.env = patch.dict(os.environ, {
            "DATABASE_URL": "", "NINA_RUNTIME_ENV": "test", "NINA_DB_FILE": cls.db_file,
            "NINA_CONTACT_IDENTITY_KEY": "telegram-contact-test-key-at-least-32-bytes",
        })
        cls.env.start()
        cls.restore = bind_sqlite_database(cls.db_file, channel_connections, contact_identity)

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.env.stop()
        cls.tmp.cleanup()

    def setUp(self):
        channel_connections.ensure_schema()
        contact_identity.ensure_schema()
        connection = sqlite3.connect(self.db_file)
        connection.execute("DELETE FROM nina_channel_connections WHERE channel='telegram'")
        connection.commit()
        connection.close()

    @staticmethod
    def update(user_id="101", chat_id="201", text="hello"):
        message = SimpleNamespace(text=text, reply_text=AsyncMock())
        return SimpleNamespace(
            effective_user=SimpleNamespace(id=user_id, full_name="Test User", username="test", language_code="lv"),
            effective_chat=SimpleNamespace(id=chat_id), message=message,
        )

    @staticmethod
    def diagnostics(buffer):
        return [json.loads(line) for line in buffer.getvalue().splitlines() if line.startswith("{")]

    def link(self, workspace="workspace-one", user_id="101", chat_id="201"):
        channel_connections.set_connection_for_test(
            workspace, "telegram", "connected",
            {"telegram_user_id": user_id, "telegram_chat_id": chat_id},
        )

    def test_linked_contact_resolves_with_safe_reason_codes(self):
        self.link()
        output = io.StringIO()
        with redirect_stdout(output):
            contact = app.resolve_telegram_contact(self.update())
        self.assertTrue(contact["contact_id"])
        events = self.diagnostics(output)
        self.assertEqual(events[-1]["reason_code"], "telegram_contact_resolved")
        rendered = output.getvalue()
        self.assertNotIn("101", rendered)
        self.assertNotIn("201", rendered)
        self.assertNotIn("hello", rendered)
        self.assertNotIn(os.environ["NINA_CONTACT_IDENTITY_KEY"], rendered)

    def test_missing_and_ambiguous_workspace_fail_closed(self):
        for setup, expected in (
            (lambda: None, "telegram_workspace_not_found"),
            (lambda: (self.link("workspace-a"), self.link("workspace-b")), "telegram_workspace_ambiguous"),
        ):
            with self.subTest(expected=expected):
                setup()
                output = io.StringIO()
                with redirect_stdout(output):
                    result = app.resolve_telegram_contact(self.update())
                self.assertIsNone(result)
                self.assertEqual(self.diagnostics(output)[-1]["reason_code"], expected)
                connection = sqlite3.connect(self.db_file)
                connection.execute("DELETE FROM nina_channel_connections WHERE channel='telegram'")
                connection.commit()
                connection.close()

    def test_identity_configuration_and_persistence_errors_are_classified(self):
        self.link()
        for error, expected in (
            (RuntimeError("contact_identity_key_missing"), "telegram_identity_config_missing"),
            (sqlite3.OperationalError("database unavailable"), "telegram_contact_persistence_error"),
        ):
            with self.subTest(expected=expected), patch.object(app, "resolve_contact_identity", side_effect=error):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertIsNone(app.resolve_telegram_contact(self.update()))
                event = self.diagnostics(output)[-1]
                self.assertEqual(event["reason_code"], expected)
                self.assertEqual(event["exception_class"], type(error).__name__)

    def test_text_and_audio_share_fail_closed_resolver_while_image_divergence_is_explicit(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        voice_calls_reply = any(
            isinstance(node, ast.Await) and "reply(voice_update, context)" in ast.unparse(node)
            for node in ast.walk(functions["handle_voice"])
        )
        self.assertTrue(voice_calls_reply)
        reply_source = ast.unparse(functions["reply"])
        self.assertIn("contact = resolve_telegram_contact(update, context)", reply_source)
        self.assertIn("if not contact", reply_source)
        photo_source = ast.unparse(functions["handle_photo"])
        self.assertIn("resolve_telegram_contact(update, context)", photo_source)
        self.assertNotIn("if not contact", photo_source)

    def test_existing_fail_closed_reply_is_unchanged(self):
        update = self.update()
        with patch.object(app, "resolve_telegram_contact", return_value=None):
            asyncio.run(app.reply(update, SimpleNamespace(chat_data={})))
        sent = update.message.reply_text.await_args.args[0]
        self.assertIn("Nevar", sent)
        self.assertIn("Telegram", sent)

    def test_paired_text_reaches_shared_one_nina_route_without_demo_fallback(self):
        self.link()
        update = self.update(text="Sveika, Nina")
        captured = {}

        def route(envelope):
            captured["envelope"] = envelope
            return {"text": "Kopīgā Nina atbild."}

        with patch.object(app, "route_nina_message", side_effect=route):
            asyncio.run(app.reply(update, SimpleNamespace(chat_data={})))
        envelope = captured["envelope"]
        self.assertEqual(envelope.workspace_id, "workspace-one")
        self.assertEqual(envelope.channel, "telegram")
        self.assertTrue(envelope.contact_id)
        self.assertEqual(update.message.reply_text.await_args.args[0], "Kopīgā Nina atbild.")

    def test_paired_audio_transcript_reaches_same_shared_one_nina_route(self):
        self.link()

        class TelegramFile:
            async def download_to_memory(self, out):
                out.write(b"voice-bytes")

        bot = SimpleNamespace(get_file=AsyncMock(return_value=TelegramFile()))
        real_reply = AsyncMock()
        message = SimpleNamespace(
            text=None, caption=None,
            voice=SimpleNamespace(file_id="voice-file"), audio=None, document=None,
            reply_text=real_reply,
        )
        update = SimpleNamespace(
            effective_user=SimpleNamespace(
                id="101", full_name="Test User", username="test", language_code="lv"
            ),
            effective_chat=SimpleNamespace(id="201"), message=message,
        )
        captured = {}

        def route(envelope):
            captured["envelope"] = envelope
            return {"text": "Audio sasniedza kopīgo Ninu."}

        with (
            patch.object(app, "transcribe_audio_with_openai", return_value="Sveika, Nina"),
            patch.object(app, "cleanup_voice_transcript", return_value="Sveika, Nina"),
            patch.object(app, "route_nina_message", side_effect=route),
            patch.object(app, "v40_log_usage"),
            patch.object(app, "save_conversation_state"),
        ):
            asyncio.run(app.handle_voice(update, SimpleNamespace(bot=bot, chat_data={})))
        envelope = captured["envelope"]
        self.assertEqual(envelope.workspace_id, "workspace-one")
        self.assertEqual(envelope.channel, "telegram")
        self.assertEqual(envelope.text, "Sveika, Nina")
        self.assertEqual(real_reply.await_args.args[0], "Audio sasniedza kopīgo Ninu.")

    def test_pairing_metadata_round_trip_resolves_exact_workspace(self):
        setup = channel_connections.create_telegram_token(
            "round-trip-workspace", "Nina7727_bot", ttl_seconds=60,
        )
        linked = channel_connections.consume_telegram_token(
            setup["token"], "777", "owner", "888", "Owner",
        )
        self.assertEqual(linked["status"], "connected")
        resolution = channel_connections.telegram_workspace_resolution("777", "888")
        self.assertEqual(resolution["workspace_id"], "round-trip-workspace")
        self.assertEqual(resolution["reason_code"], "telegram_workspace_resolved")

    def test_source_contains_no_demo_workspace_fallback_in_canonical_contact_route(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name: ast.unparse(node)
            for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertNotIn("demo_small_business", functions["resolve_telegram_contact"])
        self.assertNotIn(
            "contact.get('workspace_id') or 'demo_small_business'", functions["reply"]
        )
        self.assertIn("contact.get('workspace_id') or ''", functions["reply"])


if __name__ == "__main__":
    unittest.main()
