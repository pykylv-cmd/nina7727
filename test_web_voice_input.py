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

    def test_voice_task_command_persists_canonical_task(self):
        transcript = "Izveido uzdevumu: rīt piezvanīt Jānim par piedāvājumu."
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
        self.assertIn("piezvanīt Jānim par piedāvājumu", tasks[0].title)
        self.assertEqual(tasks[0].due_date, "tomorrow")
        self.assertEqual(tasks[0].origin_channel, "web")

    def test_transcription_temporary_file_is_deleted(self):
        captured_path = []

        class Transcriptions:
            def create(self, **kwargs):
                captured_path.append(kwargs["file"].name)
                return "temporary cleanup"

        client = type(
            "Client",
            (),
            {"audio": type("Audio", (), {"transcriptions": Transcriptions()})()},
        )()
        result = voice_engine.transcribe_audio_with_openai(
            client,
            b"audio",
            filename="voice.webm",
            language_hint="en",
            force_language=False,
        )
        self.assertEqual(result, "temporary cleanup")
        self.assertEqual(len(captured_path), 1)
        self.assertFalse(os.path.exists(captured_path[0]))

    def test_customer_chat_has_no_internal_architecture_terms(self):
        body = self.client.get("/nina?lang=en").get_data(as_text=True)
        for term in ("ONE NINA", "Work Objects", "Work Engine", "Task Engine", "Debug"):
            self.assertNotIn(term, body)


if __name__ == "__main__":
    unittest.main()
