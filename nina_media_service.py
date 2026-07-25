"""Channel-neutral media intake over NinaOS shared voice, vision and document truth."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

from document_intake import prepare_document_intake
from nina_message_service import (
    generate_with_nina,
    save_channel_turn,
    send_message_to_nina,
)
from vision_engine import build_vision_answer_from_openai
from voice_engine import transcribe_audio_with_openai
from work_objects import save_or_get_work_object

AUDIO_MAX_BYTES = 16 * 1024 * 1024
IMAGE_MAX_BYTES = 10 * 1024 * 1024
DOCUMENT_MAX_BYTES = 20 * 1024 * 1024

ALLOWED_AUDIO_MIMES = {
    "audio/aac", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/opus",
    "audio/wav", "audio/webm", "audio/x-m4a",
}
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_MIMES = {
    "application/csv", "application/json", "application/pdf", "application/rtf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/xml", "text/csv", "text/html", "text/markdown", "text/plain",
    "text/rtf", "text/xml",
}


class MediaValidationError(ValueError):
    pass


def _base_mime(value: str) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _context_text(text: str, quoted_text: str) -> str:
    text = str(text or "").strip()
    quoted = str(quoted_text or "").strip()[:1000]
    return f"Citētā ziņa: {quoted}\n\n{text}" if quoted else text


def validate_media(kind: str, mime_type: str, data: bytes) -> str:
    mime = _base_mime(mime_type)
    limits = {"audio": AUDIO_MAX_BYTES, "image": IMAGE_MAX_BYTES, "document": DOCUMENT_MAX_BYTES}
    allowed = {"audio": ALLOWED_AUDIO_MIMES, "image": ALLOWED_IMAGE_MIMES, "document": ALLOWED_DOCUMENT_MIMES}
    if kind not in limits or not data:
        raise MediaValidationError("empty_or_unknown_media")
    if len(data) > limits[kind]:
        raise MediaValidationError("media_too_large")
    if mime not in allowed[kind]:
        raise MediaValidationError("unsupported_media_type")
    return mime


def process_media_message(
    *,
    kind: str,
    data: bytes,
    mime_type: str,
    filename: str,
    caption: str,
    quoted_text: str,
    workspace_id: str,
    conversation_id: str,
    channel: str,
    origin_user_id: str,
    message_id: str,
    openai_client: Any = None,
) -> Dict[str, Any]:
    mime = validate_media(kind, mime_type, data)
    if openai_client is None:
        from openai import OpenAI
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        openai_client = OpenAI(api_key=api_key)

    if kind == "audio":
        transcript = transcribe_audio_with_openai(
            openai_client, data, filename=filename or "voice.ogg", mime_type=mime,
            language_hint="", force_language=False, model="gpt-4o-transcribe",
        )
        if not str(transcript or "").strip():
            raise RuntimeError("audio_transcription_failed")
        return send_message_to_nina(
            _context_text(transcript, quoted_text), workspace_id=workspace_id,
            channel=channel, conversation_id=conversation_id,
        )

    if kind == "image":
        answer = build_vision_answer_from_openai(openai_client, data, caption=_context_text(caption, quoted_text))
        answer = str(answer or "").replace("\n\nVersija: V23.0", "").strip()
        if not answer:
            raise RuntimeError("image_understanding_failed")
        save_channel_turn(
            workspace_id, _context_text(caption or "[Attēls]", quoted_text), answer,
            conversation_id=conversation_id, channel=channel,
        )
        return {"ok": True, "text": answer, "source": "shared_vision", "channel": channel}

    intake = prepare_document_intake(
        file_bytes=data, filename=filename or "document", mime_type=mime,
        generator=generate_with_nina,
    )
    if not intake.get("ok"):
        raise MediaValidationError(str(intake.get("error") or "document_intake_failed"))
    fingerprint = str(intake.get("fingerprint") or hashlib.sha256(data).hexdigest())
    title = str(filename or "document")[:240]
    metadata = {
        "source": "canonical_channel_document_intake_v1",
        "intake_kind": "document",
        "caption": str(caption or "")[:1000],
        "document_content": {
            "filename": title,
            "mime_type": mime,
            "document_kind": intake.get("document_kind"),
            "fingerprint_sha256": fingerprint,
            "extraction_method": intake.get("extraction_method"),
            "text_chars": intake.get("text_chars"),
            "truncated": bool(intake.get("truncated")),
            "source_text": str(intake.get("extracted_text") or "")[:30000],
            "grounded_facts": list(intake.get("facts") or []),
        },
    }
    save_or_get_work_object(
        object_type=str(intake.get("object_type") or "document_case"),
        title=title,
        source_key=f"{channel}:{workspace_id}:{message_id}",
        workspace_id=workspace_id,
        linked_files=[fingerprint],
        metadata=metadata,
        origin_channel=channel,
        origin_user_id=origin_user_id,
    )
    answer = str(intake.get("acknowledgement") or "Dokumentu saņēmu un piesaistīju darba kontekstam.").strip()
    save_channel_turn(
        workspace_id, _context_text(f"[Dokuments] {title}", quoted_text), answer,
        conversation_id=conversation_id, channel=channel,
    )
    return {"ok": True, "text": answer, "source": "shared_document_intake", "channel": channel}
