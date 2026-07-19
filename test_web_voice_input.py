import io
import os
import tempfile
import unittest
from unittest.mock import patch

import nina_message_service
import voice_engine
import web_app
import work_objects


class WebVoiceInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "voice.sqlite")
        cls.original_work_db = (
            work_objects.DATABASE_URL,
            work_objects.DB_FILE,
            work_objects.USE_POSTGRES,
        )
        cls.original_message_db = (
            nina_message_service.DATABASE_URL,
            nina_message_service.DB_FILE,
            nina_message_service.USE_POSTGRES,
        )
        cls.env = patch.dict(
            os.environ,
            {
                "DATABASE_URL": "",
                "NINA_DB_FILE": cls.db_file,
                "OPENAI_API_KEY": "test-placeholder",
            },
        )
        cls.env.start()
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        nina_message_service.DATABASE_URL = ""
        nina_message_service.DB_FILE = cls.db_file
        nina_message_service.USE_POSTGRES = False

    @classmethod
    def tearDownClass(cls):
        work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES = cls.original_work_db
        work_objects._SCHEMA_READY = False
        (
            nina_message_service.DATABASE_URL,
            nina_message_service.DB_FILE,
            nina_message_service.USE_POSTGRES,
        ) = cls.original_message_db
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        work_objects.ensure_work_objects_schema()
        connection = work_objects._connect()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM nina_work_objects")
        connection.commit()
        cursor.close()
        connection.close()
        self.client = web_app.app.test_client()

    def test_nina_get_works_in_supported_languages(self):
        labels = {"lv": "Gatavs", "en": "Ready", "ru": "Готово"}
        for lang, label in labels.items():
            response = self.client.get(f"/nina?lang={lang}")
            self.assertEqual(response.status_code, 200)
            body = response.get_data(as_text=True)
            self.assertIn(label, body)
            self.assertIn("id='voice-start'", body)

    def test_existing_typed_post_is_unchanged(self):
        with patch.object(web_app, "send_message_to_nina") as send:
            response = self.client.post("/nina?lang=en", data={"message": "Hello"})
        self.assertEqual(response.status_code, 302)
        send.assert_called_once_with(
            "Hello", workspace_id=web_app.NINA_WEB_WORKSPACE_ID, channel="web"
        )

    def test_voice_rejects_empty_file(self):
        response = self.client.post(
            "/nina/voice?lang=lv",
            data={"audio": (io.BytesIO(b""), "voice.webm", "audio/webm"), "lang": "lv"},
        )
        self.assertEqual(response.status_code, 400)

    def test_voice_rejects_unsupported_mime(self):
        response = self.client.post(
            "/nina/voice?lang=en",
            data={"audio": (io.BytesIO(b"not audio"), "voice.txt", "text/plain")},
        )
        self.assertEqual(response.status_code, 415)

    def test_successful_transcription_uses_existing_message_service(self):
        with patch.object(web_app, "_transcribe_web_voice", return_value="Recognized text"), \
             patch.object(web_app, "send_message_to_nina") as send:
            response = self.client.post(
                "/nina/voice?lang=en",
                data={"audio": (io.BytesIO(b"audio"), "voice.webm", "audio/webm"), "lang": "en"},
            )
        self.assertEqual(response.status_code, 200)
        send.assert_called_once_with(
            "Recognized text", workspace_id=web_app.NINA_WEB_WORKSPACE_ID, channel="web"
        )

    def test_web_uses_accuracy_model_and_actual_mime(self):
        with patch.object(voice_engine, "transcribe_audio_with_openai", return_value="Exact text") as transcribe, \
             patch.object(web_app, "transcribe_audio_with_openai", transcribe), \
             patch("openai.OpenAI"):
            result = web_app._transcribe_web_voice(
                b"audio", "voice.webm", "audio/webm;codecs=opus", "lv"
            )
        self.assertEqual(result, "Exact text")
        kwargs = transcribe.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-4o-transcribe")
        self.assertEqual(kwargs["mime_type"], "audio/webm;codecs=opus")
        self.assertEqual(kwargs["language_hint"], "lv")
        self.assertFalse(kwargs["force_language"])

    def test_mime_to_extension_mapping(self):
        cases = {
            "audio/webm": ".webm",
            "audio/webm;codecs=opus": ".webm",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
        }
        for mime_type, expected in cases.items():
            self.assertEqual(
                voice_engine.audio_suffix_for_mime(mime_type, "wrong.ogg"), expected
            )

    def test_language_hints_are_neutral_and_multilingual(self):
        for language, name in {"lv": "Latvian", "en": "English", "ru": "Russian"}.items():
            prompt = voice_engine.transcription_context_prompt(language)
            self.assertIn(name, prompt)
            self.assertIn("do not translate", prompt)
            self.assertIn("izveido uzdevumu", prompt)
            self.assertIn("create task", prompt)
            self.assertIn("создай задачу", prompt)

    def test_telegram_transcription_defaults_remain_compatible(self):
        captured = {}

        class Transcriptions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return "Telegram text"

        client = type(
            "Client",
            (),
            {"audio": type("Audio", (), {"transcriptions": Transcriptions()})()},
        )()
        result = voice_engine.transcribe_audio_with_openai(client, b"audio", "voice.ogg")
        self.assertEqual(result, "Telegram text")
        self.assertEqual(captured["model"], "whisper-1")
        self.assertEqual(captured["language"], "lv")
        self.assertNotIn("prompt", captured)

    def test_voice_task_command_persists_canonical_task(self):
        transcript = "Izveido uzdevumu: rīt piezvanīt Pēterim."
        with patch.object(web_app, "_transcribe_web_voice", return_value=transcript):
            response = self.client.post(
                "/nina/voice?lang=lv",
                data={"audio": (io.BytesIO(b"audio"), "voice.webm", "audio/webm"), "lang": "lv"},
            )
        self.assertEqual(response.status_code, 200)
        tasks = work_objects.list_work_objects(
            workspace_id=web_app.NINA_WEB_WORKSPACE_ID, object_type="task"
        )
        self.assertEqual(len(tasks), 1)
        self.assertIn("piezvanīt Pēterim", tasks[0].title)
        self.assertEqual(tasks[0].due_date, "tomorrow")
        self.assertEqual(tasks[0].origin_channel, "web")

    def test_transcription_temporary_file_is_deleted(self):
        captured_paths = []

        class Transcriptions:
            def create(self, **kwargs):
                captured_paths.append(kwargs["file"].name)
                return "Izveido uzdevumu: rīt piezvanīt Pēterim."

        client = type(
            "Client",
            (),
            {"audio": type("Audio", (), {"transcriptions": Transcriptions()})()},
        )()
        for mime_type, suffix in (
            ("audio/webm", ".webm"),
            ("audio/webm;codecs=opus", ".webm"),
            ("audio/ogg", ".ogg"),
            ("audio/mp4", ".m4a"),
        ):
            result = voice_engine.transcribe_audio_with_openai(
                client,
                b"audio",
                filename="voice.bin",
                language_hint="en",
                force_language=False,
                model="gpt-4o-transcribe",
                mime_type=mime_type,
            )
            self.assertEqual(result, "Izveido uzdevumu: rīt piezvanīt Pēterim.")
            self.assertTrue(captured_paths[-1].endswith(suffix))
            self.assertFalse(os.path.exists(captured_paths[-1]))

    def test_diagnostic_logs_exclude_secrets_and_transcription(self):
        spoken = "Private spoken words sk-spoken-secret"
        with patch.object(web_app, "_transcribe_web_voice", return_value=spoken), \
             patch.object(web_app, "send_message_to_nina"), \
             self.assertLogs(web_app.logger, level="INFO") as captured:
            response = self.client.post(
                "/nina/voice?lang=ru",
                data={
                    "audio": (io.BytesIO(b"audio bytes"), "voice.webm", "audio/webm;codecs=opus"),
                    "lang": "ru",
                },
            )
        self.assertEqual(response.status_code, 200)
        logs = "\n".join(captured.output)
        self.assertIn("mime=audio/webm;codecs=opus", logs)
        self.assertIn("bytes=11", logs)
        self.assertIn("model=gpt-4o-transcribe", logs)
        self.assertIn("language_hint=ru", logs)
        self.assertIn(f"chars={len(spoken)}", logs)
        self.assertNotIn(spoken, logs)
        self.assertNotIn("test-placeholder", logs)
        self.assertNotIn("sk-spoken-secret", logs)

    def test_transcription_failure_is_logged_without_exception_details(self):
        with patch.object(
            web_app,
            "_transcribe_web_voice",
            side_effect=RuntimeError("private provider response sk-secret"),
        ), self.assertLogs(web_app.logger, level="INFO") as captured:
            response = self.client.post(
                "/nina/voice?lang=lv",
                data={"audio": (io.BytesIO(b"audio"), "voice.webm", "audio/webm")},
            )
        self.assertEqual(response.status_code, 502)
        logs = "\n".join(captured.output)
        self.assertIn("success=False", logs)
        self.assertNotIn("private provider response", logs)
        self.assertNotIn("sk-secret", logs)

    def test_customer_chat_has_no_internal_architecture_terms(self):
        body = self.client.get("/nina?lang=en").get_data(as_text=True)
        for term in ("ONE NINA", "Work Objects", "Work Engine", "Task Engine", "Debug"):
            self.assertNotIn(term, body)


if __name__ == "__main__":
    unittest.main()
