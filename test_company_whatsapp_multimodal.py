import base64
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_runtime_support import (
    bind_sqlite_database,
    initialize_ready_web,
    install_test_environment,
)

install_test_environment()

class CompanyWhatsAppMultimodalTests(unittest.TestCase):
    def test_audio_uses_shared_transcription_then_nina_route(self):
        import nina_media_service as service
        with patch.object(service, "transcribe_audio_with_openai", return_value="Izveido uzdevumu"), \
             patch.object(service, "send_message_to_nina", return_value={"ok": True, "text": "Izveidots"}) as send:
            result = service.process_media_message(
                kind="audio", data=b"audio", mime_type="audio/ogg; codecs=opus",
                filename="voice.ogg", caption="", quoted_text="", workspace_id="ws",
                conversation_id="wa:ws:a", channel="whatsapp_company",
                origin_user_id="3712", message_id="m1", openai_client=Mock(),
            )
        self.assertEqual(result["text"], "Izveidots")
        self.assertEqual(send.call_args.args[0], "Izveido uzdevumu")

    def test_image_uses_shared_vision_and_shared_conversation_store(self):
        import nina_media_service as service
        with patch.object(service, "build_vision_answer_from_openai", return_value="Redzu projektu."), \
             patch.object(service, "save_channel_turn") as save:
            result = service.process_media_message(
                kind="image", data=b"image", mime_type="image/jpeg", filename="image.jpg",
                caption="Apraksti", quoted_text="", workspace_id="ws", conversation_id="wa:ws:a",
                channel="whatsapp_company", origin_user_id="3712", message_id="m2",
                openai_client=Mock(),
            )
        self.assertEqual(result["source"], "shared_vision")
        save.assert_called_once()

    def test_document_uses_shared_intake_and_canonical_work_store(self):
        import nina_media_service as service
        intake = {
            "ok": True, "fingerprint": "abc", "object_type": "document_case",
            "document_kind": "document", "extracted_text": "work", "facts": [],
            "acknowledgement": "Dokuments saņemts.",
        }
        with patch.object(service, "prepare_document_intake", return_value=intake), \
             patch.object(service, "save_or_get_work_object") as save_object, \
             patch.object(service, "save_channel_turn"):
            result = service.process_media_message(
                kind="document", data=b"doc", mime_type="text/plain", filename="work.txt",
                caption="", quoted_text="", workspace_id="ws", conversation_id="wa:ws:a",
                channel="whatsapp_company", origin_user_id="3712", message_id="m3",
                openai_client=Mock(),
            )
        self.assertEqual(result["source"], "shared_document_intake")
        self.assertEqual(save_object.call_args.kwargs["workspace_id"], "ws")
        self.assertEqual(save_object.call_args.kwargs["origin_channel"], "whatsapp_company")

    def test_validation_rejects_unsupported_and_oversized_media(self):
        import nina_media_service as service
        with self.assertRaises(service.MediaValidationError):
            service.validate_media("audio", "video/mp4", b"x")
        with self.assertRaises(service.MediaValidationError):
            service.validate_media("image", "image/jpeg", b"x" * (service.IMAGE_MAX_BYTES + 1))

    def test_web_endpoint_decodes_media_and_preserves_sender_conversation(self):
        old_db = os.environ.get("NINA_DB_FILE")
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            db_path = handle.name
        os.environ["NINA_DB_FILE"] = db_path
        try:
            import channel_connections
            import nina_message_service
            import web_app
            restore_database = bind_sqlite_database(
                db_path, channel_connections, nina_message_service
            )
            initialize_ready_web(web_app)
            payload = {
                "workspace_id": "ninaos_company", "message_id": "media-1",
                "sender_jid": "37120000001@s.whatsapp.net", "text": "",
                "media": {
                    "kind": "image", "mime_type": "image/jpeg", "filename": "image.jpg",
                    "caption": "", "size": 3, "data_base64": base64.b64encode(b"img").decode(),
                },
            }
            identity = {"workspace_id": "ninaos_company", "conversation_id": "wa:sender-a"}
            with web_app.app.test_request_context("/internal/company-whatsapp/inbound", method="POST", json=payload):
                with patch.object(web_app, "_bridge_json", return_value=payload), \
                     patch.object(web_app, "accept_company_whatsapp_inbound", return_value=True), \
                     patch.object(web_app, "resolve_ninaos_channel_identity", return_value=identity), \
                     patch.object(web_app, "process_media_message", return_value={"text": "vision"}) as process:
                    response = web_app.internal_company_whatsapp_inbound()
            self.assertEqual(response.get_json()["reply"], "vision")
            self.assertEqual(process.call_args.kwargs["conversation_id"], "wa:sender-a")
        finally:
            if "restore_database" in locals():
                restore_database()
            if old_db is None:
                os.environ.pop("NINA_DB_FILE", None)
            else:
                os.environ["NINA_DB_FILE"] = old_db
            try:
                os.unlink(db_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
