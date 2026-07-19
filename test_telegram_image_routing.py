import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TELEGRAM_TOKEN", "123456:test-telegram-token")

import app


class FakeTelegramFile:
    async def download_to_memory(self, out):
        out.write(b"test-image-bytes")


class FakeBot:
    async def get_file(self, file_id):
        return FakeTelegramFile()


def photo_update(caption=""):
    photo = SimpleNamespace(file_id="photo-file", file_unique_id="photo-unique")
    message = SimpleNamespace(caption=caption, photo=[photo], media_group_id=None)
    return SimpleNamespace(effective_user=SimpleNamespace(id=101), message=message)


class TelegramImageRoutingTests(unittest.TestCase):
    def run_photo(self, caption="", vision="Redzu attēlā kaķi pie loga.", recent_object=None):
        reply = AsyncMock()
        context = SimpleNamespace(bot=FakeBot())
        patches = [
            patch.object(app, "build_vision_answer_from_openai", return_value=vision),
            patch.object(app, "v1151_vision_smart_reply", return_value="Attēlā redzu kaķi pie loga."),
            patch.object(app, "nina_latest_channel_work_context", return_value=recent_object),
            patch.object(app, "nina_append_photo_evidence", wraps=app.nina_append_photo_evidence),
            patch.object(app, "classify_channel_business_intake", return_value={"matched": False}),
            patch.object(app, "nina_save_forwarded_text_to_one_nina", return_value=None),
            patch.object(app, "v40_log_usage"),
            patch.object(app, "save_conversation_state"),
            patch.object(app, "ctx112_after_vision_answer"),
            patch.object(app, "safe_reply_text", new=reply),
        ]
        started = [item.start() for item in patches]
        try:
            asyncio.run(app.handle_photo(photo_update(caption), context))
            return {"reply": reply, "append": started[3], "classify": started[4], "save": started[5], "vision_context": started[8], "smart": started[1]}
        finally:
            for item in reversed(patches):
                item.stop()

    def test_plain_photo_uses_vision_even_with_recent_work_context(self):
        recent = SimpleNamespace(object_id="work-1", title="Recent work", metadata={})
        result = self.run_photo(recent_object=recent)
        result["append"].assert_not_called()
        result["classify"].assert_not_called()
        self.assertIn("kaķi", result["reply"].await_args.args[1])
        result["vision_context"].assert_called_once()

    def test_question_and_ocr_captions_use_vision(self):
        for caption in ("Kas ir šajā bildē?", "Ko tu redzi?", "Apraksti šo bildi.", "Izlasi tekstu no bildes."):
            with self.subTest(caption=caption):
                result = self.run_photo(caption=caption)
                result["save"].assert_not_called()
                result["append"].assert_not_called()
                self.assertIn("kaķi", result["reply"].await_args.args[1])

    def test_explicit_material_and_client_project_commands_use_work_path(self):
        work_object = SimpleNamespace(object_id="work-2", title="Client project", metadata={})
        for caption in ("Saglabā šo kā darba materiālu.", "Pievieno šo bildi klienta Jāņa projektam."):
            with self.subTest(caption=caption):
                with patch.object(app, "classify_channel_business_intake", return_value={"matched": True, "kind": "work_material"}), patch.object(app, "nina_save_forwarded_text_to_one_nina", return_value={"object": work_object}) as save, patch.object(app, "nina_append_photo_evidence", return_value=work_object) as append, patch.object(app, "nina_photo_context_answer", return_value="Materiāls saglabāts."), patch.object(app, "build_vision_answer_from_openai", return_value="Redzu darba foto."), patch.object(app, "v40_log_usage"), patch.object(app, "save_conversation_state"), patch.object(app, "safe_reply_text", new=AsyncMock()) as reply:
                    asyncio.run(app.handle_photo(photo_update(caption), SimpleNamespace(bot=FakeBot())))
                save.assert_called_once()
                append.assert_called_once()
                self.assertEqual(reply.await_args.args[1], "Materiāls saglabāts.")

    def test_vision_failure_is_honest_and_never_claims_material_attachment(self):
        fallback = app.build_no_vision_fallback(version="V115.2")
        result = self.run_photo(vision=fallback, recent_object=SimpleNamespace(object_id="work-3", title="Recent", metadata={}))
        result["append"].assert_not_called()
        result["smart"].assert_not_called()
        self.assertEqual(result["reply"].await_args.args[1], app.nina_vision_safe_fallback())
        self.assertNotIn("piesaist", result["reply"].await_args.args[1].lower())

    def test_explicit_intent_detector_is_high_confidence(self):
        self.assertFalse(app.nina_photo_has_explicit_material_intent("Ko tu redzi klienta bildē?"))
        self.assertFalse(app.nina_photo_has_explicit_material_intent("Forwarded photo"))
        self.assertTrue(app.nina_photo_has_explicit_material_intent("Attach this to the client project"))
        self.assertTrue(app.nina_photo_has_explicit_material_intent("Сохрани как рабочий документ"))


if __name__ == "__main__":
    unittest.main()
