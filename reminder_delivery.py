"""ONE NINA active reminder delivery over existing Work Objects and channels."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from work_objects import (
    claim_due_reminder,
    finish_reminder_delivery,
    get_work_object,
    list_work_objects,
    update_work_object,
)


def utc_now():
    return datetime.now(timezone.utc)


def _linked_whatsapp_channel(reminder, channel):
    """Allow Web-origin routing only for a tenant-scoped linked contact."""
    try:
        from channel_connections import get_connection
        from contact_identity import get_contact
        contact = get_contact(reminder.origin_user_id, reminder.workspace_id)
        connection = get_connection(reminder.workspace_id, channel)
    except Exception:
        return False
    return channel in set(contact.get("channels") or ()) and (
        connection.get("status") == "connected"
    )


def delivery_channel(reminder):
    metadata = reminder.metadata if isinstance(reminder.metadata, dict) else {}
    preferred = str(metadata.get("preferred_channel") or "").strip().lower()
    if preferred in {"telegram", "web"}:
        return preferred
    if preferred in {"whatsapp_personal", "whatsapp_company"} and (
        reminder.origin_channel in {
            "personal_whatsapp", "whatsapp_personal",
            "company_whatsapp", "whatsapp_company",
        }
        or _linked_whatsapp_channel(reminder, preferred)
    ):
        return preferred
    if reminder.origin_channel == "telegram" and str(reminder.origin_user_id or "").isdigit():
        return "telegram"
    if reminder.origin_channel == "web" and reminder.origin_user_id:
        return "web"
    if reminder.origin_channel in {"personal_whatsapp", "whatsapp_personal"}:
        return "whatsapp_personal"
    if reminder.origin_channel in {"company_whatsapp", "whatsapp_company"}:
        return "whatsapp_company"
    return ""


def deliver_whatsapp(reminder, channel):
    """Send one claimed reminder through the existing Baileys bridge."""
    from personal_whatsapp import bridge_request

    metadata = reminder.metadata if isinstance(reminder.metadata, dict) else {}
    path = (
        "/v1/company/outbound"
        if channel == "whatsapp_company" else "/v1/outbound"
    )
    payload = {
        "workspace_id": str(reminder.workspace_id or "").strip(),
        "delivery_id": f"reminder:{reminder.object_id}",
        "text": f"⏰ Atgādinājums: {reminder.title.removeprefix('Atgādinājums: ').strip()}",
    }
    if channel == "whatsapp_company":
        payload["recipient_jid"] = str(
            metadata.get("whatsapp_recipient_jid") or ""
        ).strip()
    result = bridge_request(path, payload, timeout=15)
    if (
        not isinstance(result, dict)
        or not result.get("ok")
        or not str(result.get("message_id") or "").strip()
    ):
        raise RuntimeError("whatsapp_delivery_failed")
    return str(result.get("message_id") or "").strip()


def claim_next(worker_id="telegram-core", now=None):
    current = now or utc_now()
    return claim_due_reminder(
        worker_id,
        current.isoformat(timespec="seconds"),
        (current - timedelta(minutes=5)).isoformat(timespec="seconds"),
    )


def persist_web_delivery(reminder):
    """Persist one claimed Web reminder in the existing canonical Channel Layer."""
    from channel_layer import (
        create_outbound,
        ensure_web_connection,
        get_outbound_for_work_object,
        transition_delivery,
    )

    workspace_id = str(reminder.workspace_id or "").strip()
    contact_id = str(reminder.origin_user_id or "").strip()
    connection = ensure_web_connection(workspace_id, actor="reminder_scheduler")
    outbound = get_outbound_for_work_object(
        workspace_id, reminder.object_id, contact_id,
    )
    if outbound is None:
        text = f"⏰ Atgādinājums: {reminder.title.removeprefix('Atgādinājums: ').strip()}"
        outbound = create_outbound(
            workspace_id,
            connection.channel_connection_id,
            contact_id=contact_id,
            text_content=text,
            related_work_object_id=reminder.object_id,
            status="DRAFT",
            safe_metadata={
                "surface": "web_chat",
                "notification_type": "reminder",
                "conversation_id": f"contact:{contact_id}:web",
            },
            created_by="reminder_scheduler",
        )
    transitions = {
        "DRAFT": ("APPROVED", {}),
        "APPROVED": ("QUEUED", {}),
        "QUEUED": ("SENT", {"provider_confirmed": True}),
        "SENT": ("DELIVERED", {"delivery_receipt": True}),
    }
    while outbound.delivery_status in transitions:
        target, options = transitions[outbound.delivery_status]
        outbound = transition_delivery(
            workspace_id, outbound.message_id, target,
            actor="web_notification", **options,
        )
    return outbound


async def deliver_claimed(reminder, telegram_sender=None, now=None):
    current = now or utc_now()
    metadata = dict(reminder.metadata or {})
    token = str(metadata.get("claim_token") or "")
    channel = delivery_channel(reminder)
    if not channel:
        return finish_reminder_delivery(
            reminder.object_id, token, "awaiting_channel", error_code="no_delivery_channel",
        )
    if channel == "web":
        try:
            outbound = persist_web_delivery(reminder)
        except Exception as exc:
            return finish_reminder_delivery(
                reminder.object_id, token, "failed", channel="web",
                error_code=f"web_{type(exc).__name__.lower()}",
            )
        if outbound.delivery_status != "DELIVERED":
            return finish_reminder_delivery(
                reminder.object_id, token, "failed", channel="web",
                error_code="web_delivery_incomplete",
            )
        # Web Push is additive and best-effort. Its own delivery ledger records
        # failures; the canonical Web reminder must retain its successful state.
        try:
            from web_push import deliver_reminder_push
            deliver_reminder_push(reminder)
        except Exception:
            pass
        metadata.update({"unread": True, "channel_message_id": outbound.message_id})
        update_work_object(reminder.object_id, metadata=metadata)
        return finish_reminder_delivery(
            reminder.object_id, token, "delivered", channel="web",
            delivered_at=current.isoformat(timespec="seconds"),
        )
    if channel in {"whatsapp_personal", "whatsapp_company"}:
        try:
            message_id = deliver_whatsapp(reminder, channel)
        except Exception as exc:
            return finish_reminder_delivery(
                reminder.object_id, token, "failed", channel=channel,
                error_code=f"{channel}_{type(exc).__name__.lower()}",
            )
        metadata["whatsapp_message_id"] = message_id
        update_work_object(reminder.object_id, metadata=metadata)
        return finish_reminder_delivery(
            reminder.object_id, token, "delivered", channel=channel,
            delivered_at=current.isoformat(timespec="seconds"),
        )
    if telegram_sender is None:
        return finish_reminder_delivery(
            reminder.object_id, token, "failed", channel="telegram",
            error_code="telegram_sender_unavailable",
        )
    try:
        await telegram_sender(
            chat_id=int(reminder.origin_user_id),
            text=f"⏰ Atgādinājums: {reminder.title.removeprefix('Atgādinājums: ').strip()}",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        return finish_reminder_delivery(
            reminder.object_id, token, "failed", channel="telegram",
            error_code=f"telegram_{type(exc).__name__.lower()}",
        )
    return finish_reminder_delivery(
        reminder.object_id, token, "delivered", channel="telegram",
        delivered_at=current.isoformat(timespec="seconds"),
    )


async def process_due_reminders(telegram_sender=None, worker_id="telegram-core", now=None, limit=25):
    from nina_message_service import materialize_due_reminders

    current = now or utc_now()
    workspace_ids = {
        item.workspace_id for item in list_work_objects(limit=5000)
        if item.workspace_id
    }
    for workspace_id in workspace_ids:
        materialize_due_reminders(workspace_id, now=current)
    results = []
    for _ in range(max(1, min(int(limit), 100))):
        reminder = claim_next(worker_id=worker_id, now=current)
        if reminder is None:
            break
        results.append(await deliver_claimed(reminder, telegram_sender=telegram_sender, now=current))
    return results


def snooze_reminder(object_id, owner_id, planned_at):
    reminder = get_work_object(object_id)
    if not reminder or reminder.object_type != "reminder" or reminder.origin_user_id != str(owner_id):
        return None
    metadata = dict(reminder.metadata or {})
    history = list(metadata.get("delivery_history") or [])
    history.append({
        "planned_at": metadata.get("planned_at") or metadata.get("reminder_at"),
        "delivery_status": metadata.get("delivery_status"),
        "delivered_at": metadata.get("delivered_at", ""),
        "channel": metadata.get("channel", ""),
    })
    metadata.update({
        "planned_at": planned_at,
        "reminder_at": planned_at,
        "delivery_status": "snoozed",
        "unread": False,
        "delivery_history": history[-20:],
    })
    update_work_object(object_id, status="active", metadata=metadata)
    metadata["delivery_status"] = "scheduled"
    return update_work_object(object_id, metadata=metadata)


def complete_reminder(object_id, owner_id):
    reminder = get_work_object(object_id)
    if not reminder or reminder.object_type != "reminder" or reminder.origin_user_id != str(owner_id):
        return None
    metadata = dict(reminder.metadata or {})
    metadata.update({"delivery_status": "cancelled", "unread": False})
    return update_work_object(object_id, status="cancelled", metadata=metadata)
