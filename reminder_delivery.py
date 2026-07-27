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


def delivery_channel(reminder):
    metadata = reminder.metadata if isinstance(reminder.metadata, dict) else {}
    preferred = str(metadata.get("preferred_channel") or "").strip().lower()
    if preferred in {"telegram", "web"}:
        return preferred
    if reminder.origin_channel == "telegram" and str(reminder.origin_user_id or "").isdigit():
        return "telegram"
    if reminder.origin_channel == "web" and reminder.origin_user_id:
        return "web"
    return ""


def claim_next(worker_id="telegram-core", now=None):
    current = now or utc_now()
    return claim_due_reminder(
        worker_id,
        current.isoformat(timespec="seconds"),
        (current - timedelta(minutes=5)).isoformat(timespec="seconds"),
    )


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
        metadata["unread"] = True
        update_work_object(reminder.object_id, metadata=metadata)
        return finish_reminder_delivery(
            reminder.object_id, token, "delivered", channel="web",
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
