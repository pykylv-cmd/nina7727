from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict

CHANNEL_CONTENT_VERSION = "Canonical Channel Content V1"


def _clean(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class CanonicalChannelContent:
    channel: str
    owner_user_id: str
    event_id: str
    content_type: str
    text: str = ""
    caption: str = ""
    filename: str = ""
    mime_type: str = ""
    media_id: str = ""
    media_unique_id: str = ""
    sender_name: str = ""
    forwarded: bool = False
    received_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_channel_content(
    *,
    channel: str,
    owner_user_id: str,
    event_id: str,
    content_type: str,
    text: str = "",
    caption: str = "",
    filename: str = "",
    mime_type: str = "",
    media_id: str = "",
    media_unique_id: str = "",
    sender_name: str = "",
    forwarded: bool = False,
    received_at: str = "",
) -> CanonicalChannelContent:
    """Normalize channel payload metadata before shared ONE NINA work handling.

    This envelope is transport-normalization only. It is not a second business truth.
    Persistent business truth remains in nina_work_objects.
    """
    normalized_channel = _clean(channel).lower()
    normalized_type = _clean(content_type).lower()
    if not normalized_channel:
        raise ValueError("channel is required")
    if not _clean(owner_user_id):
        raise ValueError("owner_user_id is required")
    if not _clean(event_id):
        raise ValueError("event_id is required")
    if normalized_type not in {"text", "photo", "document", "audio", "location"}:
        raise ValueError(f"unsupported content_type: {normalized_type}")

    return CanonicalChannelContent(
        channel=normalized_channel,
        owner_user_id=_clean(owner_user_id),
        event_id=_clean(event_id),
        content_type=normalized_type,
        text=_clean(text),
        caption=_clean(caption),
        filename=_clean(filename),
        mime_type=_clean(mime_type).lower(),
        media_id=_clean(media_id),
        media_unique_id=_clean(media_unique_id),
        sender_name=_clean(sender_name),
        forwarded=bool(forwarded),
        received_at=_clean(received_at) or datetime.now(timezone.utc).isoformat(),
    )


def canonical_channel_source_key(content: CanonicalChannelContent) -> str:
    return f"channel:{content.channel}:{content.owner_user_id}:event:{content.event_id}"
