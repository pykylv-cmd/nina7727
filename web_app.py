# web_app.py
# NinaOS Web App V51.6.2 — ONE NINA UI SPACING FIX
# Web service start command: python web_app.py
# Telegram service start command stays: python app.py

import json
import logging
import os
import hashlib
import hmac
import secrets
import re
from datetime import datetime
from urllib.parse import quote_plus, unquote_plus
from flask import Flask, Response, jsonify, redirect, request
from nina_message_service import WORKSPACE_ID as NINA_WEB_WORKSPACE_ID, load_web_conversation, send_message_to_nina
from voice_engine import transcribe_audio_with_openai
from channel_connections import claim_channel_message, consume_whatsapp_onboarding_state, create_telegram_token, create_whatsapp_onboarding_state, disconnect as disconnect_channel, get_connection, update_whatsapp_verification
from whatsapp_channel import (
    WhatsAppProviderError,
    complete_embedded_signup,
    embedded_signup_public_config,
    parse_inbound_text,
    resolve_webhook_verification,
    resolve_workspace_for_phone_number,
    send_whatsapp_message,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

# ONE NINA V51.3 — shared canonical Work Object read bridge.
# Web does not classify Telegram text here. It reads the same persistent
# nina_work_objects objects that app.py writes through work_objects.py.
try:
    from work_objects import (
        list_work_objects as one_nina_list_work_objects,
        persistence_health as one_nina_work_persistence_health,
        WORK_OBJECTS_VERSION as ONE_NINA_WORK_OBJECTS_VERSION,
    )
    ONE_NINA_WORK_READ_READY = True
except Exception as e:
    print("V51.8.1 ONE NINA work_objects base import error:", repr(e))
    ONE_NINA_WORK_OBJECTS_VERSION = "Persistent Work Objects nav pieslēgts"
    ONE_NINA_WORK_READ_READY = False

    def one_nina_list_work_objects(*args, **kwargs):
        return []

    def one_nina_work_persistence_health():
        return {"ok": False, "error": "Persistent Work Objects nav pieslēgts"}

try:
    from work_objects import canonical_action_result as one_nina_canonical_action_result
except Exception as e:
    print("V51.8.1 canonical action reader compatibility mode:", repr(e))

    def one_nina_canonical_action_result(obj, action_key):
        metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
        actions = metadata.get("canonical_actions")
        if not isinstance(actions, dict):
            return {}
        result = actions.get(str(action_key or "").strip())
        return dict(result) if isinstance(result, dict) else {}

try:
    from work_engine import (
        prepare_canonical_estimate_draft as one_nina_prepare_estimate_draft,
        decide_canonical_estimate_draft as one_nina_decide_estimate_draft,
        ESTIMATE_ACTION_KEY as ONE_NINA_ESTIMATE_ACTION_KEY,
        WORK_ENGINE_VERSION as ONE_NINA_WORK_ENGINE_VERSION,
    )
    ONE_NINA_ESTIMATE_ACTION_READY = True
except Exception as e:
    print("V51.8.1 ONE NINA estimate action import error:", repr(e))
    ONE_NINA_ESTIMATE_ACTION_KEY = "estimate_draft_v1"
    ONE_NINA_WORK_ENGINE_VERSION = "Work Engine nav pieslēgts"
    ONE_NINA_ESTIMATE_ACTION_READY = False

    def one_nina_prepare_estimate_draft(*args, **kwargs):
        return {"ok": False, "error": "estimate_action_unavailable"}

    def one_nina_decide_estimate_draft(*args, **kwargs):
        return {"ok": False, "error": "estimate_approval_unavailable"}

WEB_APP_VERSION = "Web App V51.8.1 — ONE NINA Estimate Approval V1 Release-Safe"
app = Flask(__name__)
_CHANNEL_CSRF_SECRET = secrets.token_bytes(32)
WEB_VOICE_MAX_BYTES = 10 * 1024 * 1024
WEB_VOICE_TRANSCRIPTION_MODEL = "gpt-4o-transcribe"
WEB_VOICE_MIME_TYPES = {
    "audio/aac", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav",
    "audio/webm", "audio/x-m4a", "audio/x-wav", "video/webm",
}

# V47.1 safe workspace-object surface polish.
# This writes only safe web workspace-object snapshots into memory_backups and does NOT touch Telegram app.py.
# Telegram remains its own runtime; web_app.py only reads/surfaces shared intake/work data.
WORKSPACE_ACTION_PREVIEWS = []
# V51.2 SAFETY FIX: verified Telegram client mappings are unique by normalized client and chat_id.
# Owner approval decisions are saved safely into memory_backups with source='web_thread_approval_state'.
# This avoids losing Approve/Hold/Reject after web reload/redeploy without touching app.py.
THREAD_WORKFLOW_STATES = {}
THREAD_WORKFLOW_STATES_LOADED = False
WORKSPACE_OBJECT_CACHE = {}
WORKSPACE_OBJECT_CACHE_LOADED = False
LAST_VOICE_INTAKE_PREVIEW = None
DRAFT_REVIEW_STATES = {}
DRAFT_REVIEW_STATES_LOADED = False
TELEGRAM_SEND_PREP_STATES = {}
TELEGRAM_SEND_PREP_STATES_LOADED = False
TELEGRAM_RECIPIENT_STATES = {}
TELEGRAM_RECIPIENT_STATES_LOADED = False
TELEGRAM_CLIENT_CONTACT_MAPPINGS = {}
TELEGRAM_CLIENT_CONTACT_MAPPINGS_LOADED = False


# =========================================================
# V51.4 — ONE NINA canonical Work Object product surface
# =========================================================

def one_nina_canonical_work_objects(limit=200):
    """Read active production Work Objects from the shared ONE NINA layer."""
    if not ONE_NINA_WORK_READ_READY:
        return []
    try:
        raw_objects = one_nina_list_work_objects(
            workspace_id="demo_small_business",
            limit=max(1, min(int(limit or 200) * 4, 4000)),
        )
        production_objects = []
        for obj in raw_objects:
            metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
            source_key = str(getattr(obj, "source_key", "") or "")
            is_demo = (
                metadata.get("demo") is True
                or str(metadata.get("source") or "") == "demo_seed"
                or source_key.startswith("demo:")
            )
            if is_demo:
                continue
            production_objects.append(obj)
            if len(production_objects) >= max(1, min(int(limit or 200), 1000)):
                break
        return production_objects
    except Exception as e:
        print("V51.4 PRODUCTION CLEANUP canonical work read error:", repr(e))
        return []


def one_nina_estimate_action_html(obj):
    """Web renders and triggers the canonical estimate action; it owns no work truth."""
    if str(getattr(obj, "object_type", "") or "").strip().lower() != "estimate":
        return ""

    result = one_nina_canonical_action_result(obj, ONE_NINA_ESTIMATE_ACTION_KEY)
    draft_text = str((result or {}).get("draft_text") or "").strip()
    approval_state = str((result or {}).get("approval_state") or "").strip().lower()
    object_id = str(getattr(obj, "object_id", "") or "").strip()

    if not draft_text:
        if not ONE_NINA_ESTIMATE_ACTION_READY or not object_id:
            return "<div class='safe-note'>Estimate action is unavailable.</div>"
        return (
            f"<form method='post' action='{q('/work-objects/' + quote_plus(object_id) + '/estimate-draft')}' style='margin-top:12px'>"
            "<button class='btn primary' type='submit'>Prepare estimate draft</button>"
            "</form>"
        )

    state_label = {
        "pending": "PENDING APPROVAL",
        "approved": "APPROVED",
        "hold": "HOLD",
        "rejected": "REJECTED",
    }.get(approval_state, approval_state.upper() or "PREPARED")

    controls = ""
    if object_id and approval_state != "approved":
        controls = (
            "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-top:10px'>"
            f"<form method='post' action='{q('/work-objects/' + quote_plus(object_id) + '/estimate-approval/approve')}'><button class='btn primary' type='submit'>Approve</button></form>"
            f"<form method='post' action='{q('/work-objects/' + quote_plus(object_id) + '/estimate-approval/hold')}'><button class='btn' type='submit'>Hold</button></form>"
            f"<form method='post' action='{q('/work-objects/' + quote_plus(object_id) + '/estimate-approval/reject')}'><button class='btn' type='submit'>Reject</button></form>"
            "</div>"
        )

    return (
        "<div class='preview-box' style='margin-top:12px'>"
        "<b>Estimate draft — prepared by ONE NINA</b>"
        f"<span class='muted'>{html_escape(state_label)}</span>"
        f"<div class='muted' style='white-space:pre-wrap;margin-top:8px'>{html_escape(draft_text)}</div>"
        f"{controls}"
        "<div class='safe-note'>Draft and approval state are saved on this same canonical estimate Work Object.</div>"
        "</div>"
    )


def one_nina_work_object_rows(limit=20, empty_text="No canonical work objects yet."):
    objects = one_nina_canonical_work_objects(limit=limit)
    if not objects:
        return (
            "<div class='row'><div>"
            f"<b>{html_escape(empty_text)}</b>"
            "<span class='muted'>nina_work_objects</span>"
            "</div><span class='pill'>idle</span></div>"
        )
    rows = []
    for obj in objects[:limit]:
        metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
        raw_text = str(metadata.get("raw_text") or "")
        source_key = str(getattr(obj, "source_key", "") or "")
        client_id = str(getattr(obj, "client_id", "") or "")
        due_date = str(getattr(obj, "due_date", "") or "")
        origin_channel = str(getattr(obj, "origin_channel", "") or "")
        details = [
            str(getattr(obj, "object_type", "") or "work"),
            str(getattr(obj, "status", "") or "open"),
            str(getattr(obj, "priority", "") or "normal"),
        ]
        if client_id:
            details.append(client_id)
        if due_date:
            details.append(due_date)
        if origin_channel:
            details.append(origin_channel)
        evidence = raw_text or source_key or str(getattr(obj, "object_id", "") or "")
        if len(evidence) > 220:
            evidence = evidence[:217] + "..."
        action_html = one_nina_estimate_action_html(obj)
        rows.append(
            "<div class='row'><div style='flex:1'>"
            f"<b>{html_escape(getattr(obj, 'title', '') or 'Canonical Work Object')}</b>"
            f"<span class='muted'>{html_escape(' · '.join(details))}</span>"
            f"<span class='muted'>{html_escape(evidence)}</span>"
            f"{action_html}"
            "</div><span class='pill'>ONE NINA</span></div>"
        )
    return "".join(rows)


def one_nina_work_kpis_html():
    objects = one_nina_canonical_work_objects(limit=1000)
    clients = {
        str(getattr(obj, "client_id", "") or "").strip().lower()
        for obj in objects
        if str(getattr(obj, "client_id", "") or "").strip()
    }
    telegram_items = [
        obj for obj in objects
        if str(getattr(obj, "origin_channel", "") or "").strip().lower() == "telegram"
    ]
    health = one_nina_work_persistence_health()
    backend = str(health.get("backend") or "persistent DB")
    return (
        "<div class='kpis'>"
        + kpi_card("Canonical work", len(objects), {"text": "ONE NINA", "href": "/tasks"})
        + kpi_card("Telegram intake", len(telegram_items), {"text": "shared work truth", "href": "/tasks"})
        + kpi_card("Canonical clients", len(clients), {"text": "work-linked", "href": "/clients"})
        + kpi_card("Persistence", "OK" if health.get("ok") else "ERROR", {"text": backend, "href": "/tasks"})
        + "</div>"
    )


def one_nina_work_surface_html(limit=20):
    health = one_nina_work_persistence_health()
    status = "persistent truth connected" if health.get("ok") else "persistent truth unavailable"
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>ONE NINA Canonical Work Objects</div>"
        f"{one_nina_work_kpis_html()}<br>"
        f"<div class='list'>{one_nina_work_object_rows(limit=limit)}</div>"
        "<div class='safe-note'>"
        "V51.4 LABEL FIX: Web reads nina_work_objects through the shared work_objects.py service. "
        "The web surface does not infer task type, client or meaning from Telegram text in this section. "
        f"Status: {html_escape(status)} · {html_escape(ONE_NINA_WORK_OBJECTS_VERSION)}."
        "</div></section><br>"
    )


# =========================================================
# V51.5 — ONE NINA CLIENT LINK V1
# =========================================================

def one_nina_normalize_client_name(value):
    return " ".join(str(value or "").strip().split())


def one_nina_client_work_map(limit=2000):
    """Group the SAME canonical Work Objects by client_id.

    This is a view only. It creates no client work copy, thread snapshot or
    second work object.
    """
    grouped = {}
    for obj in one_nina_canonical_work_objects(limit=limit):
        client_name = one_nina_normalize_client_name(
            getattr(obj, "client_id", "") or ""
        )
        if not client_name:
            continue

        key = client_name.casefold()
        if key not in grouped:
            grouped[key] = {
                "name": client_name,
                "objects": [],
                "types": {},
                "channels": set(),
            }

        entry = grouped[key]
        entry["objects"].append(obj)

        object_type = str(getattr(obj, "object_type", "") or "work")
        entry["types"][object_type] = entry["types"].get(object_type, 0) + 1

        channel = str(getattr(obj, "origin_channel", "") or "").strip()
        if channel:
            entry["channels"].add(channel)

    for entry in grouped.values():
        entry["objects"].sort(
            key=lambda obj: (
                str(getattr(obj, "updated_at", "") or ""),
                str(getattr(obj, "created_at", "") or ""),
            ),
            reverse=True,
        )

    return grouped


def one_nina_find_client_profile(client_name):
    wanted = one_nina_normalize_client_name(client_name).casefold()
    return one_nina_client_work_map().get(wanted)


def one_nina_client_rows(empty_text="No canonical clients yet."):
    profiles = one_nina_client_work_map()
    if not profiles:
        return (
            "<div class='row'><div>"
            f"<b>{html_escape(empty_text)}</b>"
            "<span class='muted'>No client-linked canonical work objects.</span>"
            "</div><span class='pill'>idle</span></div>"
        )

    rows = ""
    for _, profile in sorted(
        profiles.items(),
        key=lambda item: item[1]["name"].casefold(),
    ):
        objects = profile["objects"]
        type_summary = " · ".join(
            f"{object_type}: {count}"
            for object_type, count in sorted(profile["types"].items())
        )
        channel_summary = " + ".join(sorted(profile["channels"])) or "NinaOS"
        latest_titles = " | ".join(
            str(getattr(obj, "title", "") or "")
            for obj in objects[:3]
            if str(getattr(obj, "title", "") or "").strip()
        )
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(profile['name'])}</b>"
            f"<span class='muted'>canonical work: {len(objects)} · {html_escape(type_summary)}</span>"
            f"<span class='muted'>{html_escape(latest_titles or channel_summary)}</span>"
            "</div>"
            f"<a class='pill' href='{q('/clients/' + _client_profile_slug(profile['name']))}'>Open client profile</a>"
            "</div>"
        )
    return rows


def one_nina_business_details(obj):
    """Read already-extracted canonical business_details.

    V51.6 must not parse raw Telegram text. Extraction belongs to the shared
    work_objects.py V2.2 layer.
    """
    metadata = (
        obj.metadata
        if isinstance(getattr(obj, "metadata", None), dict)
        else {}
    )
    details = metadata.get("business_details")
    return dict(details) if isinstance(details, dict) else {}


def one_nina_business_detail_value(details, key, fallback=""):
    value = (details or {}).get(key)
    if value in (None, ""):
        return fallback
    return str(value).strip()


def one_nina_business_amount_label(details):
    amount = (details or {}).get("amount")
    currency = one_nina_business_detail_value(details, "currency")
    if amount in (None, ""):
        return ""

    amount_text = str(amount).strip()
    if amount_text.endswith(".0"):
        amount_text = amount_text[:-2]

    return f"{amount_text} {currency}".strip()


def one_nina_business_detail_rows_for_object(obj):
    """Render canonical business fields only from metadata.business_details."""
    details = one_nina_business_details(obj)
    if not details:
        return ""

    fields = []
    subject = one_nina_business_detail_value(details, "subject")
    amount = one_nina_business_amount_label(details)
    due_context = one_nina_business_detail_value(details, "due_context")
    start_context = one_nina_business_detail_value(details, "start_context")
    client_name = one_nina_business_detail_value(details, "client_name")

    if subject:
        fields.append(("Work subject", subject))
    if amount:
        fields.append(("Amount", amount))
    if due_context:
        fields.append(("Offer / due context", due_context))
    if start_context:
        fields.append(("Work start", start_context))
    if client_name:
        fields.append(("Client", client_name))

    if not fields:
        return ""

    return (
        "<div class='list'>"
        + "".join(
            "<div class='row'><div>"
            f"<b>{html_escape(label)}</b>"
            f"<span class='muted'>{html_escape(value)}</span>"
            "</div><span class='pill'>canonical</span></div>"
            for label, value in fields
        )
        + "</div>"
    )


def one_nina_client_business_detail_cards(profile):
    objects = (profile or {}).get("objects") or []
    if not objects:
        return ""

    cards = []
    for obj in objects:
        details = one_nina_business_details(obj)
        if not details:
            continue

        subject = one_nina_business_detail_value(
            details,
            "subject",
            str(getattr(obj, "title", "") or "Canonical Work Object"),
        )
        amount = one_nina_business_amount_label(details)
        object_type = str(getattr(obj, "object_type", "") or "work")
        status = str(getattr(obj, "status", "") or "open")
        due_context = one_nina_business_detail_value(details, "due_context")
        start_context = one_nina_business_detail_value(details, "start_context")
        channel = str(getattr(obj, "origin_channel", "") or "NinaOS")

        summary_parts = [object_type, status]
        if amount:
            summary_parts.append(amount)
        if due_context:
            summary_parts.append(f"due: {due_context}")
        if start_context:
            summary_parts.append(f"start: {start_context}")
        if channel:
            summary_parts.append(channel)

        cards.append(
            "<section class='card card-pad'>"
            "<div class='section-title'>Canonical Business Details</div>"
            "<div class='list'>"
            "<div class='row'><div>"
            f"<b>{html_escape(subject)}</b>"
            f"<span class='muted'>{html_escape(' · '.join(summary_parts))}</span>"
            "</div><span class='pill'>ONE NINA</span></div>"
            "</div><br>"
            f"{one_nina_business_detail_rows_for_object(obj)}"
            f"{one_nina_estimate_action_html(obj)}"
            "<div class='safe-note'>"
            "V51.6 renders metadata.business_details already extracted by shared work_objects.py V2.2. "
            "Web does not parse or re-extract Telegram text."
            "</div>"
            "</section><br>"
        )

    return "".join(cards)


def one_nina_client_object_rows(profile, empty_text="No canonical client work yet."):
    objects = (profile or {}).get("objects") or []
    if not objects:
        return (
            "<div class='row'><div>"
            f"<b>{html_escape(empty_text)}</b>"
            "<span class='muted'>nina_work_objects</span>"
            "</div><span class='pill'>idle</span></div>"
        )

    rows = ""
    for obj in objects:
        metadata = (
            obj.metadata
            if isinstance(getattr(obj, "metadata", None), dict)
            else {}
        )
        raw_text = str(metadata.get("raw_text") or "").strip()
        business_details = one_nina_business_details(obj)
        business_subject = one_nina_business_detail_value(business_details, "subject")
        business_amount = one_nina_business_amount_label(business_details)
        business_due = one_nina_business_detail_value(business_details, "due_context")
        business_start = one_nina_business_detail_value(business_details, "start_context")
        object_type = str(getattr(obj, "object_type", "") or "work")
        status = str(getattr(obj, "status", "") or "open")
        priority = str(getattr(obj, "priority", "") or "normal")
        due_date = str(getattr(obj, "due_date", "") or "")
        channel = str(getattr(obj, "origin_channel", "") or "")
        source_key = str(getattr(obj, "source_key", "") or "")

        details = [object_type, status, priority]
        if due_date:
            details.append(due_date)
        if channel:
            details.append(channel)

        canonical_business_summary = " · ".join(
            value
            for value in [
                business_subject,
                business_amount,
                f"due: {business_due}" if business_due else "",
                f"start: {business_start}" if business_start else "",
            ]
            if value
        )
        evidence = canonical_business_summary or raw_text or source_key or str(
            getattr(obj, "object_id", "") or ""
        )
        if len(evidence) > 320:
            evidence = evidence[:317] + "..."

        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(getattr(obj, 'title', '') or 'Canonical Work Object')}</b>"
            f"<span class='muted'>{html_escape(' · '.join(details))}</span>"
            f"<span class='muted'>{html_escape(evidence)}</span>"
            "</div>"
            "<span class='pill'>ONE NINA</span>"
            "</div>"
        )
    return rows


def one_nina_client_kpis_html(profile):
    objects = (profile or {}).get("objects") or []
    types = (profile or {}).get("types") or {}
    channels = (profile or {}).get("channels") or set()
    return (
        "<div class='kpis'>"
        + kpi_card("Canonical work", len(objects), {"text": "same objects", "href": "/tasks"})
        + kpi_card("Estimates", types.get("estimate", 0), {"text": "client-linked", "href": "/tasks"})
        + kpi_card("Follow-ups", types.get("followup_task", 0), {"text": "client-linked", "href": "/tasks"})
        + kpi_card("Channels", len(channels), {"text": "shared Nina context", "href": "/clients"})
        + "</div>"
    )

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def html_escape(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def current_language():
    lang = (request.args.get("lang") or "en").strip().lower()
    return lang if lang in ["en", "lv", "ru"] else "en"


def q(path):
    return f"{path}?lang={current_language()}"


def tx(key, lang=None):
    lang = lang or current_language()
    d = {
        "talk_to_nina": {"en": "Talk to Nina", "lv": "Runā ar Ninu", "ru": "Поговорить с Ниной"},
        "search": {"en": "Search anything...", "lv": "Meklēt jebko...", "ru": "Искать..."},
        "dashboard": {"en": "Dashboard", "lv": "Panelis", "ru": "Панель"},
        "workers": {"en": "Workers", "lv": "Darbinieki", "ru": "Работники"},
        "tasks": {"en": "Tasks", "lv": "Uzdevumi", "ru": "Задачи"},
        "clients": {"en": "Clients", "lv": "Klienti", "ru": "Клиенты"},
        "projects": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "calendar": {"en": "Calendar", "lv": "Kalendārs", "ru": "Календарь"},
        "files": {"en": "Files", "lv": "Faili", "ru": "Файлы"},
        "analytics": {"en": "Analytics", "lv": "Analītika", "ru": "Аналитика"},
        "exchange": {"en": "Exchange", "lv": "Birža", "ru": "Биржа"},
        "good_morning": {"en": "Good morning, Katrin 👋", "lv": "Labrīt, Katrin 👋", "ru": "Доброе утро, Katrin 👋"},
        "workspace_today": {
            "en": "Here’s what needs attention in your NinaOS workspace today.",
            "lv": "Šeit ir tas, kam šodien jāpievērš uzmanība NinaOS darba vidē.",
            "ru": "Вот что сегодня требует внимания в рабочем пространстве NinaOS.",
        },
        "hero_line": {
            "en": "One Platform. Unlimited AI Workers.<br>For every business. Everywhere.",
            "lv": "Viena platforma. Neierobežoti AI darbinieki.<br>Katram biznesam. Visur.",
            "ru": "Одна платформа. Неограниченные AI-работники.<br>Для любого бизнеса. Везде.",
        },
        "open_work": {"en": "Open Work Queue", "lv": "Atvērt darbu rindu", "ru": "Открыть задачи"},
        "explore": {"en": "Explore Exchange", "lv": "Apskatīt biržu", "ru": "Открыть биржу"},
        "global": {"en": "Global AI Workforce", "lv": "Globālais AI darbaspēks", "ru": "Глобальная AI-команда"},
        "connected": {"en": "Connected. Intelligent. Tireless.", "lv": "Savienots. Gudrs. Nenogurstošs.", "ru": "Связано. Умно. Без усталости."},
        "your_workers": {"en": "Your AI Workforce", "lv": "Tavi AI darbinieki", "ru": "Твои AI-работники"},
        "recent": {"en": "Recent Activity", "lv": "Pēdējā aktivitāte", "ru": "Последняя активность"},
        "snapshot": {"en": "Workspace Snapshot", "lv": "Darba vides pārskats", "ru": "Снимок рабочей среды"},
        "tasks_today": {"en": "Tasks Today", "lv": "Šodienas uzdevumi", "ru": "Задачи сегодня"},
        "followups": {"en": "Follow-ups", "lv": "Atkārtoti kontakti", "ru": "Повторные контакты"},
        "invoices": {"en": "Invoices", "lv": "Rēķini", "ru": "Счета"},
        "projects_kpi": {"en": "Projects", "lv": "Projekti", "ru": "Проекты"},
        "open_work_label": {"en": "Open work", "lv": "Atvērts darbs", "ru": "Открытая работа"},
        "need_attention": {"en": "Need attention", "lv": "Jāpievērš uzmanība", "ru": "Требует внимания"},
        "finance": {"en": "Finance", "lv": "Finanses", "ru": "Финансы"},
        "active": {"en": "Active", "lv": "Aktīvs", "ru": "Активно"},
        "view_global": {"en": "View Global Network →", "lv": "Skatīt globālo tīklu →", "ru": "Смотреть глобальную сеть →"},
        "crm": {"en": "CRM", "lv": "CRM", "ru": "CRM"},
        "ai_workforce": {"en": "AI workforce", "lv": "AI darbinieki", "ru": "AI-команда"},
        "estimates": {"en": "Estimates", "lv": "Tāmes", "ru": "Сметы"},
        "in_progress": {"en": "In progress", "lv": "Procesā", "ru": "В работе"},
        "due_sent": {"en": "Due / sent", "lv": "Termiņš / nosūtīts", "ru": "К оплате / отправлено"},
        "tasks_sub": {"en": "Live task and follow-up queue from NinaOS workspace.", "lv": "Dzīvā uzdevumu un atkārtoto kontaktu rinda no NinaOS darba vides.", "ru": "Живая очередь задач и повторных контактов из NinaOS."},
        "clients_sub": {"en": "CRM workspace for client work, follow-ups, estimates and invoices.", "lv": "CRM darba vide klientiem, follow-upiem, tāmēm un rēķiniem.", "ru": "CRM для клиентов, повторных контактов, смет и счетов."},
        "projects_sub": {"en": "Project operations view with linked client work.", "lv": "Projektu darba skats ar piesaistītiem klientu darbiem.", "ru": "Проектный вид с привязанной клиентской работой."},
        "workers_sub": {"en": "AI workforce control surface.", "lv": "AI darbinieku vadības panelis.", "ru": "Панель управления AI-работниками."},
        "exchange_sub": {"en": "AI Workers Marketplace — preview catalog.", "lv": "AI darbinieku birža — kataloga priekšskatījums.", "ru": "Маркетплейс AI-работников — предпросмотр каталога."},
        "calendar_sub": {"en": "Schedule and due work preview.", "lv": "Grafika un termiņu darba priekšskatījums.", "ru": "Расписание и задачи по срокам."},
        "files_sub": {"en": "Document workspace for client and project files.", "lv": "Dokumentu darba vide klientu un projektu failiem.", "ru": "Документы клиентов и проектов."},
        "analytics_sub": {"en": "Operational workspace analytics preview.", "lv": "Darba vides operatīvās analītikas priekšskatījums.", "ru": "Операционная аналитика рабочей среды."},
        "open_work_action": {"en": "Open work", "lv": "Atvērt darbus", "ru": "Открыть работу"},
        "view_details": {"en": "View Details", "lv": "Skatīt detaļas", "ru": "Подробнее"},
        "today": {"en": "today", "lv": "šodien", "ru": "сегодня"},
        "attention": {"en": "attention", "lv": "uzmanība", "ru": "внимание"},
        "office_manager": {"en": "Nina Office Manager", "lv": "Nina Office Manager", "ru": "Nina Office Manager"},
        "worker_detail_sub": {"en": "Main desktop control center for the first ready AI worker.", "lv": "Galvenais vadības centrs pirmajam gatavajam AI darbiniekam.", "ru": "Главный центр управления первым готовым AI-работником."},
        "role_stack": {"en": "Role Stack", "lv": "Lomu steks", "ru": "Стек ролей"},
        "approval_required": {"en": "Approval Required", "lv": "Vajadzīgs apstiprinājums", "ru": "Требуется подтверждение"},
        "allowed_tools": {"en": "Allowed Tools", "lv": "Atļautie rīki", "ru": "Разрешённые инструменты"},
        "memory_scopes": {"en": "Memory Scopes", "lv": "Atmiņas zonas", "ru": "Области памяти"},
        "permissions": {"en": "Permissions", "lv": "Atļaujas", "ru": "Права"},
        "worker_summary": {"en": "Worker Summary", "lv": "Darbinieka pārskats", "ru": "Сводка работника"},
        "linked_work": {"en": "Linked Work", "lv": "Piesaistītie darbi", "ru": "Связанная работа"},
        "quick_actions": {"en": "Quick Actions", "lv": "Ātrās darbības", "ru": "Быстрые действия"},
        "ask_nina": {"en": "Ask Nina", "lv": "Jautāt Ninai", "ru": "Спросить Нину"},
        "new_task": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_client": {"en": "Follow-up Client", "lv": "Sazināties ar klientu", "ru": "Повторно связаться"},
        "create_estimate": {"en": "Create Estimate Draft", "lv": "Izveidot tāmes melnrakstu", "ru": "Создать черновик сметы"},
        "create_invoice": {"en": "Create Invoice Admin Record", "lv": "Izveidot rēķina ierakstu", "ru": "Создать запись счёта"},
        "upload_document": {"en": "Upload Document", "lv": "Augšupielādēt dokumentu", "ru": "Загрузить документ"},
        "open_office_manager": {"en": "Open Office Manager", "lv": "Atvērt Office Manager", "ru": "Открыть Office Manager"},
        "action_panels": {"en": "Action Panels", "lv": "Darbību paneļi", "ru": "Панели действий"},
        "task_panel": {"en": "Task Panel", "lv": "Uzdevumu panelis", "ru": "Панель задач"},
        "followup_panel": {"en": "Follow-up Panel", "lv": "Follow-up panelis", "ru": "Панель повторных контактов"},
        "estimate_panel": {"en": "Estimate Panel", "lv": "Tāmju panelis", "ru": "Панель смет"},
        "invoice_panel": {"en": "Invoice Panel", "lv": "Rēķinu panelis", "ru": "Панель счетов"},
        "document_panel": {"en": "Document Panel", "lv": "Dokumentu panelis", "ru": "Панель документов"},
        "approval_queue": {"en": "Approval Queue", "lv": "Apstiprinājumu rinda", "ru": "Очередь подтверждений"},
        "create_task_hint": {"en": "Create and organize daily work.", "lv": "Izveido un sakārto dienas darbus.", "ru": "Создать и организовать работу дня."},
        "followup_hint": {"en": "Track repeated client contact.", "lv": "Sekot atkārtotai klientu saziņai.", "ru": "Отслеживать повторный контакт с клиентом."},
        "estimate_hint": {"en": "Draft offers and estimates.", "lv": "Sagatavot piedāvājumus un tāmes.", "ru": "Готовить предложения и сметы."},
        "invoice_hint": {"en": "Track sent and due invoice records.", "lv": "Sekot nosūtītiem un termiņa rēķiniem.", "ru": "Отслеживать счета и сроки оплаты."},
        "document_hint": {"en": "Link client and project documents.", "lv": "Piesaistīt klientu un projektu dokumentus.", "ru": "Привязать документы клиентов и проектов."},
        "approval_hint": {"en": "Owner confirmation before sensitive actions.", "lv": "Īpašnieka apstiprinājums pirms svarīgām darbībām.", "ru": "Подтверждение владельца перед важными действиями."},
        "open_panel": {"en": "Open Panel", "lv": "Atvērt paneli", "ru": "Открыть панель"},
        "no_approvals": {"en": "No approvals waiting.", "lv": "Nav gaidošu apstiprinājumu.", "ru": "Нет ожидающих подтверждений."},
        "next_step": {"en": "Next step", "lv": "Nākamais solis", "ru": "Следующий шаг"},
        "work_console": {"en": "Work Console", "lv": "Darba konsole", "ru": "Рабочая консоль"},
        "today_queue": {"en": "Today Queue", "lv": "Šodienas rinda", "ru": "Очередь на сегодня"},
        "followups_due": {"en": "Follow-ups Due", "lv": "Follow-up termiņi", "ru": "Повторные контакты"},
        "finance_queue": {"en": "Finance Queue", "lv": "Finanšu rinda", "ru": "Финансовая очередь"},
        "documents": {"en": "Documents", "lv": "Dokumenti", "ru": "Документы"},
        "pending_items": {"en": "Pending Items", "lv": "Gaidošie darbi", "ru": "Ожидающие элементы"},
        "owner_control": {"en": "Owner Control", "lv": "Īpašnieka kontrole", "ru": "Контроль владельца"},
        "worker_status": {"en": "Worker Status", "lv": "Darbinieka statuss", "ru": "Статус работника"},
        "active_worker": {"en": "Active worker", "lv": "Aktīvs darbinieks", "ru": "Активный работник"},
        "data_source": {"en": "Data source", "lv": "Datu avots", "ru": "Источник данных"},
        "no_items": {"en": "No items yet.", "lv": "Pagaidām nav ierakstu.", "ru": "Пока нет элементов."},
        "status_ready": {"en": "Ready", "lv": "Gatavs", "ru": "Готов"},
        "system_safe": {"en": "Safe mode", "lv": "Drošais režīms", "ru": "Безопасный режим"},
        "open_tasks": {"en": "Open tasks", "lv": "Atvērt uzdevumus", "ru": "Открыть задачи"},
        "open_clients": {"en": "Open clients", "lv": "Atvērt klientus", "ru": "Открыть клиентов"},
        "open_files": {"en": "Open files", "lv": "Atvērt failus", "ru": "Открыть файлы"},
        "console_sub": {"en": "What Nina Office Manager is handling right now.", "lv": "Ko Nina Office Manager šobrīd apstrādā.", "ru": "Что сейчас обрабатывает Nina Office Manager."},
        "action_center": {"en": "Action Center", "lv": "Darbību centrs", "ru": "Центр действий"},
        "action_center_sub": {"en": "Create operational work from the Office Manager console.", "lv": "Izveido operatīvos darbus no Office Manager konsoles.", "ru": "Создать рабочие элементы из консоли Office Manager."},
        "task_title": {"en": "Task title", "lv": "Uzdevuma nosaukums", "ru": "Название задачи"},
        "client_name": {"en": "Client name", "lv": "Klienta vārds", "ru": "Имя клиента"},
        "project_name": {"en": "Project name", "lv": "Projekta nosaukums", "ru": "Название проекта"},
        "amount": {"en": "Amount", "lv": "Summa", "ru": "Сумма"},
        "due_date": {"en": "Due date", "lv": "Termiņš", "ru": "Срок"},
        "notes": {"en": "Notes", "lv": "Piezīmes", "ru": "Заметки"},
        "priority": {"en": "Priority", "lv": "Prioritāte", "ru": "Приоритет"},
        "normal": {"en": "Normal", "lv": "Normāla", "ru": "Обычный"},
        "high": {"en": "High", "lv": "Augsta", "ru": "Высокий"},
        "submit_preview": {"en": "Save Preview", "lv": "Saglabāt priekšskatījumu", "ru": "Сохранить предпросмотр"},
        "safe_note": {"en": "V43.4 safe mode: approved previews are surfaced as real workspace work across Dashboard, Tasks and Office Manager. Postgres write bridge comes next.", "lv": "V43.4 drošais režīms: apstiprināti preview darbi redzami kā īsti darba vides darbi Dashboard, Uzdevumos un Office Manager. Postgres bridge nāks nākamais.", "ru": "V43.4 безопасный режим: подтверждённые preview задачи видны как реальные рабочие элементы в Dashboard, Tasks и Office Manager. Postgres bridge — следующий."},
        "created_preview": {"en": "Preview created", "lv": "Priekšskatījums izveidots", "ru": "Предпросмотр создан"},
        "form_type": {"en": "Form type", "lv": "Formas tips", "ru": "Тип формы"},
        "new_task_form": {"en": "New Task", "lv": "Jauns uzdevums", "ru": "Новая задача"},
        "followup_form": {"en": "Follow-up Client", "lv": "Follow-up klientam", "ru": "Повторный контакт"},
        "estimate_form": {"en": "Estimate Draft", "lv": "Tāmes melnraksts", "ru": "Черновик сметы"},
        "invoice_form": {"en": "Invoice Admin Record", "lv": "Rēķina ieraksts", "ru": "Запись счёта"},
        "saved_to_workspace": {"en": "Saved to workspace preview", "lv": "Saglabāts darba vides priekšskatījumā", "ru": "Сохранено в предпросмотр рабочего пространства"},
        "workspace_object": {"en": "Workspace object", "lv": "Darba objekts", "ru": "Рабочий объект"},
        "object_type": {"en": "Object type", "lv": "Objekta tips", "ru": "Тип объекта"},
        "object_id": {"en": "Object ID", "lv": "Objekta ID", "ru": "ID объекта"},
        "status": {"en": "Status", "lv": "Statuss", "ru": "Статус"},
        "preview_queue": {"en": "Preview Queue", "lv": "Priekšskatījumu rinda", "ru": "Очередь предпросмотра"},
        "workspace_preview_queue": {"en": "Workspace Preview Queue", "lv": "Darba vides priekšskatījumu rinda", "ru": "Очередь предпросмотра рабочего пространства"},
        "all_workspace_work": {"en": "All Workspace Work", "lv": "Visi darba vides darbi", "ru": "Вся рабочая очередь"},
        "source_preview": {"en": "web preview", "lv": "web priekšskatījums", "ru": "web предпросмотр"},
        "source_database": {"en": "database", "lv": "datu bāze", "ru": "база данных"},
        "source_demo": {"en": "demo data", "lv": "demo dati", "ru": "демо данные"},
        "source_workspace": {"en": "workspace", "lv": "darba vide", "ru": "рабочее пространство"},
        "preview_approval_layer": {"en": "Preview Approval Layer", "lv": "Priekšskatījumu apstiprināšanas slānis", "ru": "Слой подтверждения предпросмотра"},
        "approval_state": {"en": "Approval state", "lv": "Apstiprinājuma statuss", "ru": "Статус подтверждения"},
        "pending_approval": {"en": "pending approval", "lv": "gaida apstiprinājumu", "ru": "ожидает подтверждения"},
        "approved_preview": {"en": "approved preview", "lv": "apstiprināts preview", "ru": "предпросмотр подтверждён"},
        "held_preview": {"en": "held preview", "lv": "aizturēts preview", "ru": "предпросмотр удержан"},
        "rejected_preview": {"en": "rejected preview", "lv": "noraidīts preview", "ru": "предпросмотр отклонён"},
        "approve": {"en": "Approve", "lv": "Apstiprināt", "ru": "Подтвердить"},
        "hold": {"en": "Hold", "lv": "Aizturēt", "ru": "Удержать"},
        "reject": {"en": "Reject", "lv": "Noraidīt", "ru": "Отклонить"},
        "approved_safe_note": {"en": "Approved in safe preview only. DB write is still disabled.", "lv": "Apstiprināts tikai drošajā priekšskatījumā. DB rakstīšana vēl ir izslēgta.", "ru": "Подтверждено только в безопасном предпросмотре. Запись в DB всё ещё отключена."},
        "approval_workspace_bridge": {"en": "Approval → Workspace Queue Bridge", "lv": "Apstiprinājums → darba rindas bridge", "ru": "Подтверждение → рабочая очередь"},
        "approved_workspace_queue": {"en": "Approved Workspace Queue", "lv": "Apstiprinātā darba rinda", "ru": "Подтверждённая рабочая очередь"},
        "held_preview_queue": {"en": "Held Preview Queue", "lv": "Aizturēto preview rinda", "ru": "Удержанные preview"},
        "rejected_preview_log": {"en": "Rejected Preview Log", "lv": "Noraidīto preview žurnāls", "ru": "Журнал отклонённых preview"},
        "pending_or_held": {"en": "Pending / held approvals", "lv": "Gaida / aizturēti apstiprinājumi", "ru": "Ожидает / удержано"},
        "approved_work_note": {"en": "Approved preview work is now promoted into the active workspace surfaces, but still not written to Postgres.", "lv": "Apstiprinātais preview darbs tagad ir pacelts aktīvajās darba virsmās, bet vēl nav rakstīts Postgres.", "ru": "Подтверждённая preview работа поднята в активные рабочие поверхности, но ещё не записана в Postgres."},
        "real_task_surface_bridge": {"en": "Preview → Real Task Surface Bridge", "lv": "Preview → īstā darba virsmas bridge", "ru": "Preview → мост реальной рабочей поверхности"},
        "active_workspace_queue": {"en": "Active Workspace Queue", "lv": "Aktīvā darba rinda", "ru": "Активная рабочая очередь"},
        "inbox": {"en": "Inbox", "lv": "Ienākošie", "ru": "Входящие"},
        "channel_hub": {"en": "Channel Hub", "lv": "Kanālu centrs", "ru": "Центр каналов"},
        "channel_hub_sub": {"en": "One modern intake layer for voice, WhatsApp, Telegram, files and client work.", "lv": "Viena moderna ienākošā darba kārta balsij, WhatsApp, Telegram, failiem un klientu darbiem.", "ru": "Единый современный слой входящей работы для голоса, WhatsApp, Telegram, файлов и клиентов."},
        "voice_command": {"en": "Voice Command", "lv": "Balss komanda", "ru": "Голосовая команда"},
        "voice_command_hint": {"en": "Say it once. Nina turns it into client work, tasks, documents and approvals.", "lv": "Pasaki vienreiz. Nina to pārvērš klienta darbā, uzdevumos, dokumentos un apstiprinājumos.", "ru": "Скажи один раз. Nina превращает это в клиентскую работу, задачи, документы и подтверждения."},
        "connected_channels": {"en": "Connected Channels", "lv": "Savienotie kanāli", "ru": "Подключённые каналы"},
        "whatsapp_business": {"en": "WhatsApp Business", "lv": "WhatsApp Business", "ru": "WhatsApp Business"},
        "telegram_channel": {"en": "Telegram", "lv": "Telegram", "ru": "Telegram"},
        "email_channel": {"en": "Email", "lv": "E-pasts", "ru": "Почта"},
        "files_channel": {"en": "Files / scans", "lv": "Faili / skeni", "ru": "Файлы / сканы"},
        "modern_intake": {"en": "Modern Work Intake", "lv": "Moderna darba ievade", "ru": "Современный приём работы"},
        "client_timeline": {"en": "Client Timeline", "lv": "Klienta laika līnija", "ru": "Лента клиента"},
        "owner_send_back": {"en": "Send Back to Client", "lv": "Nosūtīt atpakaļ klientam", "ru": "Отправить клиенту"},
        "ai_auto_prepare": {"en": "AI Auto-Prepare", "lv": "AI automātiskā sagatavošana", "ru": "AI автоподготовка"},
        "owner_approval_gate": {"en": "Owner Approval Gate", "lv": "Īpašnieka apstiprinājuma vārti", "ru": "Подтверждение владельца"},
        "voice_intake_form": {"en": "Voice Intake Form", "lv": "Balss darba ievade", "ru": "Форма голосового ввода"},
        "voice_intake_hint": {"en": "Paste or type what the owner/client said. Nina converts it into a safe preview work object.", "lv": "Ielīmē vai ieraksti, ko īpašnieks/klients pateica. Nina to pārvērš drošā darba priekšskatījumā.", "ru": "Вставь или напиши, что сказал владелец/клиент. Nina превратит это в безопасный preview-объект."},
        "voice_text": {"en": "Voice text", "lv": "Balss teksts", "ru": "Текст голоса"},
        "source_channel": {"en": "Source channel", "lv": "Avota kanāls", "ru": "Канал источника"},
        "nina_prepare": {"en": "Nina, prepare work", "lv": "Nina, sagatavo darbu", "ru": "Nina, подготовь работу"},
        "voice_preview_created": {"en": "Voice intake preview created", "lv": "Balss ievades priekšskatījums izveidots", "ru": "Preview из голосового ввода создан"},
        "voice_safe_note": {"en": "V50.0 safe mode: saved client send-back drafts now collect in a global Outbox / Send Center for owner review. Web still reads existing Telegram memory; only safe workspace-object snapshots are written.", "lv": "V50.0 drošais režīms: klienta profilos tagad tiek sagatavoti droši WhatsApp, Telegram un e-pasta melnrakstu priekšskatījumi. Web joprojām lasa esošo Telegram atmiņu; rakstīti tiek tikai droši workspace-object snapshoti.", "ru": "Безопасный режим V45.2: web читает существующую память Telegram и task backups. Новая запись в DB — позже."},
        "detected_intent": {"en": "Detected intent", "lv": "Atpazītais nodoms", "ru": "Распознанное намерение"},
        "twenty_second_century": {"en": "22nd-century work surface: clients speak, send photos and documents; Nina organizes the work.", "lv": "22. gadsimta darba virsma: klienti runā, sūta bildes un dokumentus; Nina sakārto darbu.", "ru": "Рабочая поверхность 22 века: клиенты говорят, отправляют фото и документы; Nina организует работу."},
    }
    return d.get(key, {}).get(lang) or d.get(key, {}).get("en") or key


def object_to_dict(obj):
    if isinstance(obj, dict):
        data = dict(obj)
    else:
        data = {
            "object_id": getattr(obj, "object_id", ""),
            "object_type": getattr(obj, "object_type", ""),
            "title": getattr(obj, "title", ""),
            "status": getattr(obj, "status", ""),
            "priority": getattr(obj, "priority", "normal"),
            "client_id": getattr(obj, "client_id", ""),
            "project_id": getattr(obj, "project_id", ""),
            "due_date": getattr(obj, "due_date", ""),
            "metadata": getattr(obj, "metadata", {}) or {},
        }
    data.setdefault("metadata", {})
    return data


def build_clients_from_objects(objects):
    clients = {}
    for obj in objects:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_name") or obj.get("client_id") or ""
        if not name:
            continue
        clients.setdefault(name, {"name": name, "objects": [], "followups": 0, "estimates": 0, "invoices": 0, "projects": 0})
        clients[name]["objects"].append(obj)
        t = obj.get("object_type")
        if t == "followup_task":
            clients[name]["followups"] += 1
        if t in ["estimate", "offer"]:
            clients[name]["estimates"] += 1
        if t == "invoice":
            clients[name]["invoices"] += 1
        if t == "project":
            clients[name]["projects"] += 1
    if not clients:
        clients["Demo Client"] = {"name": "Demo Client", "objects": [], "followups": 1, "estimates": 1, "invoices": 1, "projects": 1}
    return list(clients.values())


def load_live_objects_from_app_db():
    objects = []
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
    if not database_url:
        return objects
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        queries = [
            "SELECT id, title, status, priority, client, deadline, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
            "SELECT id, title, status, priority, client_name, due_date, raw_text, followup FROM tasks ORDER BY id DESC LIMIT 100",
        ]
        rows = []
        for query in queries:
            try:
                cur.execute(query)
                rows = cur.fetchall()
                break
            except Exception:
                conn.rollback()
        for row in rows:
            object_id, title, status, priority, client, due, raw_text, followup = row
            obj_type = "followup_task" if bool(followup) else "task"
            objects.append({
                "object_id": f"db_task_{object_id}",
                "object_type": obj_type,
                "title": title or raw_text or "Untitled task",
                "status": status or "open",
                "priority": priority or "normal",
                "client_id": client or "",
                "project_id": "",
                "due_date": due or "",
                "metadata": {"client_name": client or "", "owner": "Telegram Nina", "source": "database"},
            })
        cur.close()
        conn.close()
    except Exception:
        return []
    return objects



def infer_work_type_from_text(text, fallback="task"):
    low = (text or "").lower()
    if any(w in low for w in ["tāme", "tame", "estimate", "quote", "offer", "piedāvāj", "piedavaj"]):
        return "estimate"
    if any(w in low for w in ["rēķin", "rekin", "invoice", "bill"]):
        return "invoice"
    if any(w in low for w in ["piezvan", "atgādin", "atgadin", "follow", "sazin", "pajaut", "uzrakst", "atsūti", "atsuti"]):
        return "followup_task"
    if any(w in low for w in ["dokuments", "document", "pdf", "bilde", "foto", "scan", "skens"]):
        return "document_intake"
    return fallback or "task"


def telegram_intake_demo_items():
    """V45 demo/safe fallback: shows the intended sync shape when DB has no Telegram rows yet."""
    now = datetime.utcnow().isoformat() + "Z"
    demo = [
        {
            "object_id": "telegram_sync_demo_voice_1",
            "object_type": "estimate",
            "title": "Telegram voice: sagatavot tāmi vannas istabas remontam",
            "status": "synced_preview",
            "priority": "normal",
            "client_id": "Klients",
            "project_id": "",
            "due_date": "",
            "metadata": {
                "client_name": "Klients",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram voice",
                "intake_kind": "voice_transcript",
                "raw_text": "Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp.",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
        {
            "object_id": "telegram_sync_demo_followup_2",
            "object_type": "followup_task",
            "title": "Telegram intake: piektdien jāpajautā Andrim par atbildi",
            "status": "synced_preview",
            "priority": "normal",
            "client_id": "Andris",
            "project_id": "",
            "due_date": "friday",
            "metadata": {
                "client_name": "Andris",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram text/voice",
                "intake_kind": "followup_capture",
                "raw_text": "piektdien jāpajautā Andrim par atbildi",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
        {
            "object_id": "telegram_sync_demo_doc_3",
            "object_type": "document_intake",
            "title": "Telegram files/photos: klienta objekta bildes un dokumenti",
            "status": "document_intake",
            "priority": "normal",
            "client_id": "Klients",
            "project_id": "",
            "due_date": "",
            "metadata": {
                "client_name": "Klients",
                "owner": "Telegram Nina",
                "source": "telegram_intake_sync",
                "source_channel": "Telegram photo/document",
                "intake_kind": "document_photo_intake",
                "raw_text": "Photos, scans and PDFs should be stored under the client workspace.",
                "storage_target": "NinaOS client workspace",
                "approval_state": "pending_approval",
                "db_write": False,
                "synced_at": now,
            },
        },
    ]
    return demo





def extract_client_name_from_text(text):
    raw = str(text or "")
    lower = raw.lower()
    patterns = [
        r"\b(?:andrim|andri)\b",
        r"\b(?:klientam|klients|klientei)\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž-]{2,})",
        r"\b(?:client|customer)\s+([A-Z][\w-]{2,})",
    ]
    if "andri" in lower or "andrim" in lower:
        return "Andris"
    try:
        import re
        for pat in patterns[1:]:
            m = re.search(pat, raw)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return ""


def _first_value(row, keys, default=""):
    for key in keys:
        if key in row and row.get(key) not in [None, ""]:
            return row.get(key)
    return default



def db_url_info():
    """Return the first usable Postgres connection URL and rich env diagnostics.

    Railway can expose database URLs under different names depending on whether
    the variable was added manually, referenced from Postgres, or generated by
    a plugin. This helper is intentionally broad and read-only. It never prints
    secret values, only the source key and a masked URL.
    """
    candidates = [
        "DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_PRIVATE_URL",
        "POSTGRES_PUBLIC_URL",
        "DATABASE_PRIVATE_URL",
        "DATABASE_PUBLIC_URL",
        "PGURL",
        "PG_URL",
        "RAILWAY_DATABASE_URL",
        "RAILWAY_POSTGRES_URL",
        "POSTGRES_CONNECTION_URL",
        "DATABASE_CONNECTION_URL",
    ]

    found = []
    for key in candidates:
        value = os.environ.get(key)
        if value:
            found.append({"key": key, "safe": mask_db_url(value), "length": len(value)})

    # Also expose names of relevant env keys so we can debug Railway without leaking values.
    relevant_env_keys = sorted([
        k for k in os.environ.keys()
        if any(token in k.upper() for token in ["DATABASE", "POSTGRES", "PG", "RAILWAY"])
    ])

    url = ""
    source = ""
    if found:
        # Prefer DATABASE_URL when it exists, otherwise use the first available candidate.
        preferred = next((x for x in found if x["key"] == "DATABASE_URL"), found[0])
        source = preferred["key"]
        url = os.environ.get(source) or ""

    return {
        "url": url,
        "source": source,
        "safe": mask_db_url(url),
        "found": found,
        "relevant_env_keys": relevant_env_keys,
    }


def _db_url():
    return db_url_info().get("url") or ""


def _json_dumps_safe(obj):
    try:
        import json
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj or "")


def _json_loads_safe(text, default=None):
    try:
        import json
        value = json.loads(str(text or ""))
        return value if value is not None else default
    except Exception:
        return default


def load_persistent_thread_workflow_states_from_db(limit=500):
    """V47.1: load owner approval decisions from existing memory_backups.

    This avoids a new migration while preserving state across web reload/redeploy.
    Records are append-only; latest record wins per object_id.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_thread_approval_state", int(limit or 500)),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
        states = {}
        for row in rows:
            payload = _json_loads_safe(row[0], {})
            if not isinstance(payload, dict):
                continue
            object_id = str(payload.get("object_id") or "").strip()
            state = str(payload.get("approval_state") or "").strip()
            if object_id and state and object_id not in states:
                states[object_id] = state
        return states
    except Exception as e:
        print("V47.1 load persistent thread states error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def ensure_thread_workflow_states_loaded():
    """Lazy-load persisted thread workflow states once per web runtime."""
    global THREAD_WORKFLOW_STATES_LOADED, THREAD_WORKFLOW_STATES
    if THREAD_WORKFLOW_STATES_LOADED:
        return
    THREAD_WORKFLOW_STATES_LOADED = True
    try:
        persisted = load_persistent_thread_workflow_states_from_db()
        if persisted:
            THREAD_WORKFLOW_STATES.update(persisted)
    except Exception as e:
        print("V47.1 ensure_thread_workflow_states_loaded error:", repr(e))


def save_persistent_thread_workflow_state_to_db(object_id, approval_state, decision=""):
    """V47.1: append owner approval decision into memory_backups.

    This is the first safe persistence step for web owner decisions. It does not
    mutate Telegram task memory and does not create final work objects yet.
    """
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url"
    object_id = str(object_id or "").strip()
    approval_state = str(approval_state or "").strip()
    if not object_id or not approval_state:
        return False, "missing_object_id_or_state"
    payload = {
        "type": "thread_approval_state",
        "version": "V47.1",
        "object_id": object_id,
        "approval_state": approval_state,
        "decision": decision or approval_state,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "approval_state_only",
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_thread_approval_state"),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "saved"
    except Exception as e:
        print("V47.1 save persistent thread state error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200]


def load_persistent_workspace_objects_from_db(limit=800):
    """V47.1: load approved thread -> workspace object snapshots.

    Still uses memory_backups to avoid a migration while creating a stable work-object
    surface that survives reload/redeploy. Latest object per source_thread_id wins.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_workspace_object", int(limit or 800)),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
        objects = {}
        for row in rows:
            payload = _json_loads_safe(row[0], {})
            if not isinstance(payload, dict):
                continue
            source_thread_id = str(payload.get("source_thread_id") or payload.get("object_id") or "").strip()
            obj = payload.get("workspace_object") if isinstance(payload.get("workspace_object"), dict) else payload
            if source_thread_id and source_thread_id not in objects:
                objects[source_thread_id] = obj
        return objects
    except Exception as e:
        print("V47.1 load persistent workspace objects error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def ensure_workspace_object_cache_loaded():
    global WORKSPACE_OBJECT_CACHE_LOADED, WORKSPACE_OBJECT_CACHE
    if WORKSPACE_OBJECT_CACHE_LOADED:
        return
    WORKSPACE_OBJECT_CACHE_LOADED = True
    try:
        WORKSPACE_OBJECT_CACHE.update(load_persistent_workspace_objects_from_db())
    except Exception as e:
        print("V47.1 ensure workspace object cache error:", repr(e))


def workspace_object_type_from_thread(thread):
    meta = (thread or {}).get("metadata", {}) if isinstance((thread or {}).get("metadata"), dict) else {}
    family = str(meta.get("thread_family") or (thread or {}).get("object_type") or "task").lower()
    title = str((thread or {}).get("title") or "").lower()
    if "estimate" in family or "offer" in family or "tāme" in title or "piedāvāj" in title:
        return "estimate"
    if "invoice" in family or "rēķin" in title:
        return "invoice"
    if "document" in family or "photo" in family or "file" in family or "dok" in title:
        return "document_intake"
    if "follow" in family or "pajaut" in title or "zvan" in title or "atgādin" in title:
        return "followup_task"
    return "task"


def build_workspace_object_from_thread(thread):
    """V47.1: convert an approved client work thread into a stable workspace object."""
    thread = _with_thread_state(thread or {})
    meta = dict(thread.get("metadata", {}) if isinstance(thread.get("metadata"), dict) else {})
    source_thread_id = str(thread.get("object_id") or meta.get("source_thread_id") or "thread")
    object_type = workspace_object_type_from_thread(thread)
    client_name = meta.get("thread_client") or thread.get("client_id") or "Workspace"
    title = str(thread.get("title") or "Approved workspace work").strip()
    workspace_object_id = "workspace_object_" + source_thread_id
    source_badges = meta.get("source_badges") or []
    if isinstance(source_badges, str):
        source_badges = [source_badges]
    evidence = meta.get("thread_evidence_titles") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    return {
        "object_id": workspace_object_id,
        "object_type": object_type,
        "title": title,
        "status": "open",
        "priority": thread.get("priority") or "normal",
        "client_id": client_name if client_name != "Workspace" else "",
        "project_id": "",
        "due_date": meta.get("deadline") or "",
        "metadata": {
            "client_name": client_name,
            "source": "approved_thread_workspace_object",
            "source_channel": "Telegram / NinaOS Web",
            "source_thread_id": source_thread_id,
            "source_thread_title": title,
            "approval_state": "approved",
            "created_from": "telegram_memory_bridge",
            "workspace_object_state": "active",
            "thread_items_count": meta.get("thread_items_count") or 1,
            "source_badges": source_badges,
            "evidence_titles": evidence[:8],
            "storage_target": "NinaOS workspace objects",
            "db_write_scope": "workspace_object_snapshot",
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
    }


def save_workspace_object_to_db(source_thread_id, workspace_object):
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url"
    payload = {
        "type": "workspace_object_snapshot",
        "version": "V47.1",
        "source_thread_id": source_thread_id,
        "workspace_object": workspace_object,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "workspace_object_snapshot",
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_workspace_object"),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "saved"
    except Exception as e:
        print("V47.1 save workspace object error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200]


def ensure_workspace_object_for_thread(thread):
    ensure_workspace_object_cache_loaded()
    source_thread_id = str((thread or {}).get("object_id") or "").strip()
    if not source_thread_id:
        return None
    if source_thread_id in WORKSPACE_OBJECT_CACHE:
        return WORKSPACE_OBJECT_CACHE[source_thread_id]
    obj = build_workspace_object_from_thread(thread)
    saved, _status = save_workspace_object_to_db(source_thread_id, obj)
    if saved:
        WORKSPACE_OBJECT_CACHE[source_thread_id] = obj
    return obj


def approved_workspace_object_items():
    """Return real workspace-object surface items for approved threads.

    Approved thread state is V46.2 persistence. V47.1 adds the next safe layer:
    a stable workspace object snapshot for Tasks, Dashboard and Office Manager.
    """
    ensure_workspace_object_cache_loaded()
    items = []
    for thread in approved_client_thread_items():
        obj = ensure_workspace_object_for_thread(thread)
        if obj:
            items.append(obj)
    return items


def load_real_intake_events_from_db(limit=50):
    """V45.1/V45.2 compatibility: read future shared intake_events table if it exists.

    This remains read-only. V45.2 does not require intake_events yet because app.py
    already stores useful Telegram work memory in memory_backups and conversation_state.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'intake_events'
        """)
        columns = [r[0] for r in cur.fetchall()]
        if not columns:
            cur.close()
            conn.close()
            return []

        order_col = "created_at" if "created_at" in columns else ("id" if "id" in columns else columns[0])
        cur.execute(f"SELECT * FROM intake_events ORDER BY {order_col} DESC LIMIT %s", (int(limit),))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for idx, row in enumerate(rows):
            raw_text = _first_value(row, ["raw_text", "message_text", "transcript", "text", "body", "content", "caption"], "")
            title = _first_value(row, ["title", "summary", "subject"], "") or str(raw_text or "Incoming Telegram intake")[:140]
            source_channel = _first_value(row, ["source_channel", "channel", "source", "platform"], "Telegram")
            event_type = _first_value(row, ["event_type", "intake_kind", "kind", "type", "content_type"], "telegram_intake")
            client_name = _first_value(row, ["client_name", "client", "customer_name", "contact_name", "sender_name"], "")
            priority = _first_value(row, ["priority"], "normal") or "normal"
            status = _first_value(row, ["status", "state"], "synced_preview") or "synced_preview"
            approval_state = _first_value(row, ["approval_state", "approval", "owner_state"], "pending_approval") or "pending_approval"
            object_type = _first_value(row, ["object_type", "work_type"], "") or infer_work_type_from_text(str(title) + " " + str(raw_text), "task")
            file_name = _first_value(row, ["file_name", "filename", "document_name", "attachment_name"], "")
            if file_name and object_type == "task":
                object_type = "document_intake"
            object_id = _first_value(row, ["object_id", "event_id", "id"], f"intake_event_{idx}")
            created_at = _first_value(row, ["created_at", "timestamp", "received_at"], "")
            if created_at:
                created_at = str(created_at)
            meta = {
                "client_name": client_name,
                "owner": "Telegram Nina",
                "source": "real_intake_store",
                "source_channel": source_channel,
                "intake_kind": event_type,
                "raw_text": raw_text,
                "file_name": file_name,
                "storage_target": "NinaOS client workspace",
                "approval_state": approval_state,
                "db_read": True,
                "db_write_by_web": False,
                "synced_at": now,
                "created_at": created_at,
            }
            objects.append({
                "object_id": f"intake_event_{object_id}",
                "object_type": object_type,
                "title": title or "Incoming Telegram intake",
                "status": status,
                "priority": priority,
                "client_id": client_name,
                "project_id": _first_value(row, ["project_id", "project_name"], ""),
                "due_date": _first_value(row, ["due_date", "deadline"], ""),
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def _row_get(row, index, default=""):
    try:
        return row[index]
    except Exception:
        return default


def load_existing_task_engine_memory_from_db(limit=80):
    """V45.2: read the existing app.py task memory store.

    app.py already saves detected tasks/follow-ups as JSON into memory_backups
    with source='task_engine'. Web should bridge to that before inventing a new table.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2, json
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, backup_text, created_at
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
        """, ("task_engine", int(limit)))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            backup_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            backup_text = _row_get(row, 2) or ""
            created_at = str(_row_get(row, 3) or "")
            try:
                obj = json.loads(str(backup_text)) if backup_text else {}
                if not isinstance(obj, dict):
                    obj = {"title": str(backup_text)}
            except Exception:
                obj = {"title": str(backup_text)}

            title = obj.get("title") or obj.get("raw_text") or obj.get("text") or "Telegram task memory"
            obj_type = obj.get("object_type") or obj.get("type") or infer_work_type_from_text(str(title) + " " + str(obj.get("raw_text", "")), "task")
            if obj.get("followup") or obj.get("is_followup") or "follow" in str(obj_type).lower():
                obj_type = "followup_task"
            client_name = obj.get("client") or obj.get("client_name") or obj.get("contact") or obj.get("person") or ""
            due_date = obj.get("deadline") or obj.get("due_date") or obj.get("date") or ""
            priority = obj.get("priority") or "normal"
            status = obj.get("status") or "synced_preview"
            meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            meta.update({
                "client_name": client_name or meta.get("client_name", ""),
                "owner": "Telegram Nina",
                "source": "existing_task_memory",
                "source_channel": "Telegram",
                "intake_kind": "task_engine_memory",
                "raw_text": obj.get("raw_text") or obj.get("text") or title,
                "storage_target": "memory_backups/source=task_engine",
                "approval_state": meta.get("approval_state") or "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "memory_backup_id": str(backup_id or ""),
                "created_at": created_at,
                "synced_at": now,
            })
            objects.append({
                "object_id": f"task_memory_{backup_id}",
                "object_type": obj_type,
                "title": title,
                "status": status,
                "priority": priority,
                "client_id": client_name or "",
                "project_id": obj.get("project_id") or obj.get("project") or "",
                "due_date": due_date,
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def load_existing_voice_photo_state_from_db(limit=80):
    """V45.2: read voice/photo records already saved by app.py in conversation_state."""
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, user_text, nina_text, intent, topic, created_at
            FROM conversation_state
            WHERE user_text LIKE %s OR user_text LIKE %s OR intent IN (%s, %s)
            ORDER BY id DESC
            LIMIT %s
        """, ("[VOICE]%", "[PHOTO]%", "voice_transcript", "photo", int(limit)))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for row in rows:
            state_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            user_text = str(_row_get(row, 2) or "")
            nina_text = str(_row_get(row, 3) or "")
            intent = str(_row_get(row, 4) or "")
            topic = str(_row_get(row, 5) or "")
            created_at = str(_row_get(row, 6) or "")

            is_voice = user_text.startswith("[VOICE]") or intent == "voice_transcript" or topic == "voice"
            is_photo = user_text.startswith("[PHOTO]") or intent == "photo" or topic == "vision"
            clean_text = user_text.replace("[VOICE]", "", 1).replace("[PHOTO]", "", 1).strip()
            if not clean_text:
                clean_text = "Telegram voice/photo intake"
            obj_type = "document_intake" if is_photo else infer_work_type_from_text(clean_text, "task")
            title_prefix = "Telegram voice" if is_voice else ("Telegram photo/document" if is_photo else "Telegram message")
            meta = {
                "client_name": "",
                "owner": "Telegram Nina",
                "source": "existing_conversation_state",
                "source_channel": "Telegram voice" if is_voice else ("Telegram photo/vision" if is_photo else "Telegram"),
                "intake_kind": "voice_transcript" if is_voice else ("photo_vision" if is_photo else "conversation_state"),
                "raw_text": clean_text,
                "nina_text": nina_text[:600],
                "storage_target": "conversation_state",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "conversation_state_id": str(state_id or ""),
                "created_at": created_at,
                "synced_at": now,
            }
            objects.append({
                "object_id": f"conversation_state_{state_id}",
                "object_type": obj_type,
                "title": f"{title_prefix}: {clean_text[:110]}",
                "status": "synced_preview",
                "priority": "normal",
                "client_id": "",
                "project_id": "",
                "due_date": "",
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []




def load_recent_conversation_state_from_db(limit=80):
    """V45.3: read recent Telegram conversation_state, not only voice/photo.

    app.py saves many Telegram routes into conversation_state with intents/topics such as
    human_mode, work_layer, followup, web_surface, task/work replies etc. A fresh Telegram
    message may be stored here even when it is not [VOICE] or [PHOTO].
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, user_id, user_text, nina_text, intent, topic, created_at
            FROM conversation_state
            ORDER BY id DESC
            LIMIT %s
        """, (int(limit),))
        rows = cur.fetchall() or []
        cur.close()
        conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        skipped_prefixes = ("/start", "health", "admin", "premium", "stripe")
        for row in rows:
            state_id = _row_get(row, 0)
            user_id = _row_get(row, 1)
            user_text = str(_row_get(row, 2) or "").strip()
            nina_text = str(_row_get(row, 3) or "")
            intent = str(_row_get(row, 4) or "")
            topic = str(_row_get(row, 5) or "")
            created_at = str(_row_get(row, 6) or "")
            if not user_text:
                continue
            lower = user_text.lower().strip()
            if lower.startswith(skipped_prefixes):
                continue

            is_voice = user_text.startswith("[VOICE]") or intent == "voice_transcript" or topic == "voice"
            is_photo = user_text.startswith("[PHOTO]") or intent == "photo" or topic == "vision"
            clean_text = user_text.replace("[VOICE]", "", 1).replace("[PHOTO]", "", 1).strip()
            if not clean_text:
                continue

            obj_type = "document_intake" if is_photo else infer_work_type_from_text(clean_text, "task")
            # Mark likely client/follow-up work more usefully.
            if any(x in clean_text.lower() for x in ["pajautā", "pajauta", "piezvani", "atgādini", "atgadini", "follow"]):
                obj_type = "followup_task"
            if any(x in clean_text.lower() for x in ["tāme", "tami", "estimate", "quote", "piedāvāj"]):
                obj_type = "estimate"

            source_channel = "Telegram voice" if is_voice else ("Telegram photo/vision" if is_photo else "Telegram text")
            intake_kind = "voice_transcript" if is_voice else ("photo_vision" if is_photo else (intent or topic or "telegram_text"))
            meta = {
                "client_name": extract_client_name_from_text(clean_text),
                "owner": "Telegram Nina",
                "source": "existing_conversation_state_recent",
                "source_channel": source_channel,
                "intake_kind": intake_kind,
                "raw_text": clean_text,
                "nina_text": nina_text[:600],
                "storage_target": "conversation_state/recent",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "telegram_user_id": str(user_id or ""),
                "conversation_state_id": str(state_id or ""),
                "created_at": created_at,
                "synced_at": now,
            }
            objects.append({
                "object_id": f"conversation_recent_{state_id}",
                "object_type": obj_type,
                "title": f"Telegram: {clean_text[:120]}",
                "status": "synced_preview",
                "priority": "normal",
                "client_id": meta.get("client_name", ""),
                "project_id": "",
                "due_date": "",
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def load_existing_tasks_table_from_db(limit=80):
    """V45.3: read existing app.py tasks table when present.

    Some app versions write Telegram tasks/follow-ups into a tasks table instead of only
    memory_backups. The schema has changed over time, so this reads columns dynamically.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tasks'
        """)
        columns = [r[0] for r in cur.fetchall()]
        if not columns:
            cur.close(); conn.close(); return []
        order_col = "id" if "id" in columns else ("created_at" if "created_at" in columns else columns[0])
        cur.execute(f"SELECT * FROM tasks ORDER BY {order_col} DESC LIMIT %s", (int(limit),))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        cur.close(); conn.close()

        objects = []
        now = datetime.utcnow().isoformat() + "Z"
        for idx, row in enumerate(rows):
            raw_text = _first_value(row, ["raw_text", "text", "body", "message", "description"], "")
            title = _first_value(row, ["title", "task_title", "name"], "") or str(raw_text or "Telegram task")[:140]
            client_name = _first_value(row, ["client", "client_name", "contact", "person"], "") or extract_client_name_from_text(str(title) + " " + str(raw_text))
            is_followup = bool(_first_value(row, ["followup", "is_followup"], False))
            obj_type = "followup_task" if is_followup else infer_work_type_from_text(str(title) + " " + str(raw_text), "task")
            task_id = _first_value(row, ["id", "task_id", "object_id"], idx)
            meta = {
                "client_name": client_name,
                "owner": "Telegram Nina",
                "source": "existing_tasks_table",
                "source_channel": "Telegram",
                "intake_kind": "tasks_table",
                "raw_text": raw_text or title,
                "storage_target": "tasks",
                "approval_state": "synced_from_existing_memory",
                "db_read": True,
                "db_write_by_web": False,
                "task_table_id": str(task_id or ""),
                "created_at": str(_first_value(row, ["created_at", "created"], "")),
                "synced_at": now,
            }
            objects.append({
                "object_id": f"tasks_table_{task_id}",
                "object_type": obj_type,
                "title": title,
                "status": _first_value(row, ["status", "state"], "synced_preview") or "synced_preview",
                "priority": _first_value(row, ["priority"], "normal") or "normal",
                "client_id": client_name,
                "project_id": _first_value(row, ["project", "project_id", "project_name"], ""),
                "due_date": _first_value(row, ["deadline", "due_date", "date"], ""),
                "metadata": meta,
            })
        return objects
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


def _canonical_text_key(value):
    """V45.3: stable key for deduping the same Telegram work across task_memory, voice and conversation_state."""
    raw = str(value or "").strip().lower()
    for prefix in ["[voice]", "[photo]", "telegram voice:", "telegram intake:", "telegram files/photos:"]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
    # Normalize common Latvian chars lightly while keeping readable text.
    replacements = {
        "ā":"a", "č":"c", "ē":"e", "ģ":"g", "ī":"i", "ķ":"k", "ļ":"l", "ņ":"n", "š":"s", "ū":"u", "ž":"z",
        "ä":"a", "ö":"o", "ü":"u"
    }
    raw = "".join(replacements.get(ch, ch) for ch in raw)
    import re
    raw = re.sub(r"[^a-z0-9€]+", " ", raw).strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw[:180]


def _source_badge_for_obj(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or "workspace"
    kind = meta.get("intake_kind") or obj.get("object_type") or "work"
    if source == "existing_task_memory":
        return "Task Memory"
    if source == "existing_conversation_state":
        if "voice" in str(kind).lower():
            return "Voice"
        if "photo" in str(kind).lower() or "vision" in str(kind).lower():
            return "Photo"
        return "Conversation"
    if source == "telegram_intake_sync":
        return "Telegram"
    if source == "real_intake_store":
        return "Intake Store"
    if source == "existing_tasks_table":
        return "Tasks Table"
    return str(source).replace("_", " ").title()


def _rank_intake_obj(obj):
    """Higher number wins as the canonical visible card."""
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or ""
    obj_type = obj.get("object_type") or ""
    score = 0
    if source == "existing_task_memory":
        score += 100
    if source == "existing_tasks_table":
        score += 90
    if source == "real_intake_store":
        score += 80
    if source == "existing_conversation_state":
        score += 50
    if source == "telegram_intake_sync":
        score += 20
    if obj_type in ["followup_task", "estimate", "invoice", "document_intake"]:
        score += 10
    if meta.get("client_name") or obj.get("client_id"):
        score += 5
    return score


def dedupe_and_unify_intake_items(items, limit=30):
    """V45.3: collapse repeated Telegram memory rows into one clean Inbox card.

    app.py currently writes the same real work to more than one memory layer:
    - memory_backups source=task_engine;
    - conversation_state text/voice/photo;
    - optional tasks/intake tables.

    Web should show one useful work card and preserve the evidence as source badges,
    not flood the owner with duplicates.
    """
    groups = {}
    order = []
    for obj in items or []:
        if not isinstance(obj, dict):
            continue
        meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
        title = obj.get("title") or meta.get("raw_text") or meta.get("transcript_text") or "Telegram intake work"
        client = meta.get("client_name") or obj.get("client_id") or ""
        # Use title+client as the primary dedup identity; do not use object_id because every DB row has a different one.
        key = _canonical_text_key(client) + "|" + _canonical_text_key(title)
        if not key.strip("|"):
            key = str(obj.get("object_id") or title)
        badge = _source_badge_for_obj(obj)
        if key not in groups:
            copy = dict(obj)
            copy["metadata"] = meta
            meta["source_badges"] = [badge]
            meta["dedup_count"] = 1
            meta["dedup_sources"] = [str(obj.get("object_id") or badge)]
            meta["unified_card"] = True
            groups[key] = copy
            order.append(key)
            continue
        current = groups[key]
        current_meta = current.get("metadata", {}) if isinstance(current.get("metadata"), dict) else {}
        current_badges = list(current_meta.get("source_badges") or [])
        if badge and badge not in current_badges:
            current_badges.append(badge)
        current_meta["source_badges"] = current_badges
        current_meta["dedup_count"] = int(current_meta.get("dedup_count") or 1) + 1
        ds = list(current_meta.get("dedup_sources") or [])
        obj_id = str(obj.get("object_id") or badge)
        if obj_id not in ds:
            ds.append(obj_id)
        current_meta["dedup_sources"] = ds[:12]
        # Prefer the strongest object as the visible card, but keep dedup metadata.
        if _rank_intake_obj(obj) > _rank_intake_obj(current):
            replacement = dict(obj)
            replacement_meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            replacement_meta.update({
                "source_badges": current_badges,
                "dedup_count": current_meta.get("dedup_count"),
                "dedup_sources": current_meta.get("dedup_sources"),
                "unified_card": True,
            })
            replacement["metadata"] = replacement_meta
            groups[key] = replacement
        else:
            current["metadata"] = current_meta
    unified = [groups[k] for k in order if k in groups]
    # newest/highest ranked first when possible
    unified.sort(key=lambda o: (_rank_intake_obj(o), str((o.get("metadata") or {}).get("created_at") or "")), reverse=True)
    return unified[:int(limit or 30)]


def _thread_family_for_obj(obj):
    """V45.4 FIX: classify related NinaOS work into broad thread families.

    Important polish:
    - Follow-up wording must not become a document thread just because the card has photo/voice evidence.
    - Estimate/offer wording wins over generic document/photo words.
    - Only real document/photo-only intake stays in the documents family.
    """
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    text = " ".join([
        str(obj.get("title") or ""),
        str(meta.get("raw_text") or ""),
        str(meta.get("transcript_text") or ""),
        str(meta.get("caption") or ""),
        str(obj.get("object_type") or ""),
    ]).lower()
    obj_type = str(obj.get("object_type") or "").lower()

    followup_terms = [
        "follow", "pajaut", "atgādin", "atgadin", "zvana", "zvanīt", "zvanit",
        "raksti", "uzraksti", "atbild", "sazin", "piezvan", "jāpajaut", "japajaut",
    ]
    estimate_terms = ["tāme", "tame", "estimate", "piedāvāj", "piedavaj", "offer", "quote", "€", "eur"]
    invoice_terms = ["rēķin", "rekin", "invoice"]
    document_terms = ["foto", "photo", "bild", "image", "pdf", "dok", "document", "scan", "skan", "fails", "file"]

    has_followup = obj_type == "followup_task" or any(x in text for x in followup_terms)
    has_estimate = obj_type in ["estimate", "offer"] or any(x in text for x in estimate_terms)
    has_invoice = obj_type == "invoice" or any(x in text for x in invoice_terms)
    has_document = obj_type == "document_intake" or any(x in text for x in document_terms)

    # Business intent wins over attachment/evidence hints.
    if has_estimate:
        return "estimate"
    if has_invoice:
        return "invoice"
    if has_followup:
        return "followup"
    if has_document:
        return "documents"
    return "task"


def _thread_client_for_obj(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    client = meta.get("client_name") or obj.get("client_id") or ""
    title = str(obj.get("title") or meta.get("raw_text") or "")
    if not client:
        # Small practical Latvian client extraction fallback for existing task memory.
        import re
        m = re.search(r"\b(?:Andrim|Andri|Andris)\b", title, flags=re.IGNORECASE)
        if m:
            client = "Andris"
    return str(client or "Workspace").strip() or "Workspace"


def _thread_sort_time(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return str(meta.get("created_at") or meta.get("synced_at") or "")


def build_client_work_threads(items, limit=20):
    """V45.4: group deduplicated intake cards into client work threads.

    This is intentionally read-only. It does not mutate Postgres or app.py.
    Several similar Andris follow-ups become one follow-up thread with evidence count/source badges.
    """
    groups = {}
    order = []
    for obj in items or []:
        if not isinstance(obj, dict):
            continue
        client = _thread_client_for_obj(obj)
        family = _thread_family_for_obj(obj)
        key = _canonical_text_key(client) + "|" + family
        if key not in groups:
            meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
            meta["thread_client"] = client
            meta["thread_family"] = family
            meta["thread_items_count"] = 1
            meta["thread_evidence_titles"] = [str(obj.get("title") or "Telegram work")[:140]]
            meta["thread_latest_at"] = _thread_sort_time(obj)
            badges = list(meta.get("source_badges") or [])
            badge = _source_badge_for_obj(obj)
            if badge and badge not in badges:
                badges.append(badge)
            meta["source_badges"] = badges[:6]
            thread_obj = dict(obj)
            thread_obj["metadata"] = meta
            thread_obj["object_id"] = "client_thread_" + key.replace("|", "_")[:120]
            thread_obj["client_id"] = client
            # Human-friendly title for the thread.
            label = {
                "followup": "Follow-up thread",
                "estimate": "Estimate / offer thread",
                "invoice": "Invoice thread",
                "documents": "Document intake thread",
                "task": "Task thread",
            }.get(family, "Work thread")
            if client != "Workspace":
                thread_obj["title"] = f"{client} — {label}"
            else:
                thread_obj["title"] = label
            groups[key] = thread_obj
            order.append(key)
            continue

        current = groups[key]
        cm = current.get("metadata", {}) if isinstance(current.get("metadata"), dict) else {}
        cm["thread_items_count"] = int(cm.get("thread_items_count") or 1) + 1
        ev = list(cm.get("thread_evidence_titles") or [])
        t = str(obj.get("title") or "Telegram work")[:140]
        if t and t not in ev:
            ev.append(t)
        cm["thread_evidence_titles"] = ev[:8]
        # Merge source badges.
        badges = list(cm.get("source_badges") or [])
        for b in (obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}).get("source_badges", []) or []:
            if b and b not in badges:
                badges.append(b)
        b = _source_badge_for_obj(obj)
        if b and b not in badges:
            badges.append(b)
        cm["source_badges"] = badges[:6]
        if _thread_sort_time(obj) > str(cm.get("thread_latest_at") or ""):
            cm["thread_latest_at"] = _thread_sort_time(obj)
        # Prefer canonical visible details from strongest work object.
        if _rank_intake_obj(obj) > _rank_intake_obj(current):
            replacement = dict(current)
            replacement["object_type"] = obj.get("object_type") or current.get("object_type")
            replacement["status"] = obj.get("status") or current.get("status")
            replacement["priority"] = obj.get("priority") or current.get("priority")
            replacement["metadata"] = cm
            groups[key] = replacement
        else:
            current["metadata"] = cm

    threads = [groups[k] for k in order if k in groups]
    threads.sort(key=lambda o: (_rank_intake_obj(o), str((o.get("metadata") or {}).get("thread_latest_at") or "")), reverse=True)
    return threads[:int(limit or 20)]


def load_client_work_threads():
    return build_client_work_threads(load_existing_telegram_intake_sync(), limit=20)



def thread_workflow_state(obj):
    """V47.1: approval state for client work threads.

    Threads are read from existing app.py memory, while owner decisions are
    persisted in memory_backups with source='web_thread_approval_state'.
    """
    ensure_thread_workflow_states_loaded()
    object_id = str((obj or {}).get("object_id") or "")
    meta = (obj or {}).get("metadata", {}) if isinstance((obj or {}).get("metadata"), dict) else {}
    return THREAD_WORKFLOW_STATES.get(object_id) or meta.get("thread_approval_state") or "pending_approval"


def apply_thread_approval(object_id, decision):
    ensure_thread_workflow_states_loaded()
    decision = (decision or "").strip().lower()
    if decision not in ["approve", "hold", "reject"]:
        return None
    state_map = {"approve": "approved", "hold": "hold", "reject": "rejected"}
    new_state = state_map[decision]
    object_id = str(object_id or "").strip()
    if not object_id:
        return None
    THREAD_WORKFLOW_STATES[object_id] = new_state
    saved, save_status = save_persistent_thread_workflow_state_to_db(object_id, new_state, decision=decision)
    return {
        "object_id": object_id,
        "approval_state": new_state,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "persistent": bool(saved),
        "save_status": save_status,
    }


def _with_thread_state(obj):
    obj = dict(obj or {})
    meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
    state = thread_workflow_state(obj)
    meta["approval_state"] = state
    meta["thread_approval_state"] = state
    meta["workspace_queue_state"] = "active_approved_thread" if state == "approved" else state
    meta["db_write"] = False
    obj["metadata"] = meta
    if state == "approved":
        obj["status"] = "open"
    if state == "rejected":
        obj["status"] = "rejected"
    return obj


def client_threads_by_state(state=None):
    threads = [_with_thread_state(o) for o in load_client_work_threads()]
    if state is None:
        return threads
    if isinstance(state, (list, tuple, set)):
        allowed = set(state)
        return [o for o in threads if thread_workflow_state(o) in allowed]
    return [o for o in threads if thread_workflow_state(o) == state]


def approved_client_thread_items():
    return client_threads_by_state("approved")

def active_workspace_work_rows(limit=8, empty_text=None, include_preview=True):
    """V47.1: render approved threads as workspace objects across web surfaces."""
    lang = current_language()
    empty_text = empty_text or tx("no_items", lang)
    workspace_objects = approved_workspace_object_items()[:int(limit or 8)]
    approved_previews = approved_preview_items()[:int(limit or 8)] if include_preview else []
    if not workspace_objects and not approved_previews:
        return f"<div class='row'><div><b>{html_escape(empty_text)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    if workspace_objects:
        rows += work_object_rows(workspace_objects, empty_text="", limit=limit, show_source=True, show_approval=True)
    if approved_previews:
        rows += work_object_rows(approved_previews, empty_text="", limit=limit, show_source=True, show_approval=True)
    return rows


def approved_workspace_object_count():
    try:
        return len(approved_workspace_object_items())
    except Exception:
        return 0


def send_back_candidate_items():
    """V47.1: client-facing approved objects that can later be sent back to clients."""
    candidates = []
    for obj in approved_workspace_object_items():
        t = (obj.get("object_type") or "").lower()
        client = ((obj.get("metadata") or {}).get("client_name") or obj.get("client_id") or "").strip()
        if client and client.lower() != "workspace":
            candidates.append(obj)
            continue
        if t in ["estimate", "invoice", "document_intake", "followup_task"]:
            candidates.append(obj)
    return candidates


def workspace_object_surface_rows(limit=8, empty_text=None):
    lang = current_language()
    return work_object_rows(approved_workspace_object_items(), empty_text=empty_text or tx("no_items", lang), limit=limit, show_source=True, show_approval=True)


def send_back_candidate_rows(limit=8, empty_text=None):
    lang = current_language()
    return work_object_rows(send_back_candidate_items(), empty_text=empty_text or tx("no_items", lang), limit=limit, show_source=True, show_approval=True)


def client_workspace_objects_map():
    grouped = {}
    for obj in approved_workspace_object_items():
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = (meta.get("client_name") or obj.get("client_id") or "Workspace").strip() or "Workspace"
        grouped.setdefault(name, []).append(obj)
    return grouped


def client_workspace_surface_rows(empty_text=None):
    lang = current_language()
    grouped = client_workspace_objects_map()
    if not grouped:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for name, items in sorted(grouped.items(), key=lambda kv: kv[0].lower()):
        types = {}
        for obj in items:
            t = obj.get("object_type") or "work"
            types[t] = types.get(t, 0) + 1
        summary = " · ".join(f"{k}: {v}" for k, v in sorted(types.items()))
        preview_titles = " | ".join((o.get("title") or "") for o in items[:3])
        more = f" | +{len(items)-3} more" if len(items) > 3 else ""
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(name)}</b>"
            f"<span class='muted'>{html_escape(summary)} · {html_escape(preview_titles + more)}</span>"
            "</div>"
            f"<a class='pill' href='{q('/tasks')}'>workspace objects</a></div>"
        )
    return rows


def _client_profile_slug(name):
    try:
        from urllib.parse import quote_plus
        return quote_plus(str(name or "Workspace"))
    except Exception:
        return str(name or "Workspace").replace(" ", "+")


def _client_from_slug(slug):
    try:
        from urllib.parse import unquote_plus
        return unquote_plus(str(slug or "Workspace"))
    except Exception:
        return str(slug or "Workspace").replace("+", " ")


def client_workspace_profiles_map():
    """V48.0: one profile per client, combining threads, approved objects and send-back candidates."""
    profiles = {}

    def profile(name):
        clean = (str(name or "Workspace").strip() or "Workspace")
        profiles.setdefault(clean, {
            "name": clean,
            "threads": [],
            "workspace_objects": [],
            "send_back": [],
            "followups": 0,
            "estimates": 0,
            "documents": 0,
            "tasks": 0,
            "latest_titles": [],
            "sources": set(),
        })
        return profiles[clean]

    for thread in client_threads_by_state():
        meta = thread.get("metadata", {}) if isinstance(thread.get("metadata"), dict) else {}
        name = meta.get("thread_client") or thread.get("client_id") or "Workspace"
        pr = profile(name)
        pr["threads"].append(thread)
        ttype = (meta.get("thread_type") or thread.get("object_type") or "").lower()
        if "follow" in ttype:
            pr["followups"] += 1
        elif "estimate" in ttype or "offer" in ttype:
            pr["estimates"] += 1
        elif "document" in ttype or "photo" in ttype:
            pr["documents"] += 1
        else:
            pr["tasks"] += 1
        if thread.get("title"):
            pr["latest_titles"].append(thread.get("title"))
        for src in (meta.get("source_labels") or []):
            pr["sources"].add(str(src))

    for obj in approved_workspace_object_items():
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_id") or "Workspace"
        pr = profile(name)
        pr["workspace_objects"].append(obj)
        otype = (obj.get("object_type") or "").lower()
        if "follow" in otype:
            pr["followups"] += 1
        elif "estimate" in otype or "offer" in otype:
            pr["estimates"] += 1
        elif "document" in otype or "photo" in otype:
            pr["documents"] += 1
        else:
            pr["tasks"] += 1
        if obj.get("title"):
            pr["latest_titles"].append(obj.get("title"))
        for src in (meta.get("source_labels") or []):
            pr["sources"].add(str(src))

    for obj in send_back_candidate_items():
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        name = meta.get("client_name") or obj.get("client_id") or "Workspace"
        profile(name)["send_back"].append(obj)

    return profiles


def client_profile_rows(empty_text=None):
    lang = current_language()
    profiles = client_workspace_profiles_map()
    if not profiles:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for name, pr in sorted(profiles.items(), key=lambda kv: kv[0].lower()):
        summary = (
            f"threads: {len(pr['threads'])} · work objects: {len(pr['workspace_objects'])} · "
            f"send-back: {len(pr['send_back'])} · follow-ups: {pr['followups']} · estimates: {pr['estimates']} · docs: {pr['documents']}"
        )
        preview = " | ".join([x for x in pr.get("latest_titles", []) if x][:3])
        sources = " + ".join(sorted(pr.get("sources") or [])) or "NinaOS memory"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(name)}</b>"
            f"<span class='muted'>{html_escape(summary)}</span>"
            f"<span class='muted'>{html_escape(preview or sources)}</span>"
            "</div>"
            f"<a class='pill' href='{q('/clients/' + _client_profile_slug(name))}'>Open client profile</a></div>"
        )
    return rows


def _sendback_channel_label(channel):
    ch = (channel or "whatsapp").strip().lower()
    if ch in ["telegram", "tg"]:
        return "Telegram"
    if ch in ["email", "mail"]:
        return "Email"
    return "WhatsApp"


def _safe_sendback_object_id(item):
    raw = (item or {}).get("object_id") or ((item or {}).get("metadata") or {}).get("source_thread_id") or (item or {}).get("title") or "sendback"
    return _client_profile_slug(str(raw))


def find_sendback_item_for_client(profile, object_key):
    candidates = (profile or {}).get("send_back") or []
    if not candidates:
        return None
    key = (object_key or "").strip().lower()
    for item in candidates:
        if _safe_sendback_object_id(item).lower() == key:
            return item
    return candidates[0]


def build_sendback_draft_preview(client_name, item, channel):
    channel_label = _sendback_channel_label(channel)
    title = (item or {}).get("title") or "Client work"
    object_type = (item or {}).get("object_type") or "work"
    meta = (item or {}).get("metadata") if isinstance((item or {}).get("metadata"), dict) else {}
    evidence = " + ".join(meta.get("source_labels") or []) or meta.get("source") or "NinaOS memory"
    client = client_name or meta.get("client_name") or "Client"
    if channel_label == "Email":
        subject = f"Update about {title}"
        body = (
            f"Hi {client},\n\n"
            f"I prepared the next update for: {title}.\n"
            f"Type: {object_type}.\n\n"
            "Please review the details and tell me if you want any changes before I send the final version.\n\n"
            "Best,\nNinaOS"
        )
        return {"channel": channel_label, "title": title, "subject": subject, "body": body, "evidence": evidence}
    greeting = f"Sveiks, {client}!" if client and client != "Workspace" else "Sveiki!"
    if channel_label == "Telegram":
        body = (
            f"{greeting}\n\n"
            f"Sagatavoju darba atjauninājumu: {title}.\n"
            f"Tips: {object_type}.\n"
            "Pārbaudu vēlreiz pirms nosūtīšanas, lai viss ir pareizi."
        )
    else:
        body = (
            f"{greeting} Sagatavoju atjauninājumu par: {title}. "
            f"Tips: {object_type}. Pārbaudu pirms nosūtīšanas, lai viss ir korekti."
        )
    return {"channel": channel_label, "title": title, "subject": "", "body": body, "evidence": evidence}



def sendback_draft_key(client_name, item, channel):
    client_slug = _client_profile_slug(client_name or "Workspace")
    obj_key = _safe_sendback_object_id(item or {})
    channel_key = (channel or "whatsapp").strip().lower()
    if channel_key not in ["whatsapp", "telegram", "email"]:
        channel_key = "whatsapp"
    return f"{client_slug}:{obj_key}:{channel_key}"


def load_persistent_sendback_drafts_from_db(client_name=None, limit=500):
    """V50.0: load saved send-back draft previews from memory_backups.

    This persists owner-prepared drafts without sending anything and without
    touching Telegram app.py. Latest draft wins per draft_key.
    """
    database_url = _db_url()
    if not database_url:
        return []
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_sendback_draft", int(limit or 500)),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
        client_slug = _client_profile_slug(client_name or "") if client_name else ""
        seen = set()
        drafts = []
        for row in rows:
            payload = _json_loads_safe(row[0], {})
            if not isinstance(payload, dict):
                continue
            draft_key = str(payload.get("draft_key") or "")
            if not draft_key or draft_key in seen:
                continue
            if client_slug and str(payload.get("client_slug") or "") != client_slug:
                continue
            seen.add(draft_key)
            payload["saved_at"] = str(payload.get("saved_at") or row[1] or "")
            payload["db_id"] = row[2]
            drafts.append(payload)
        return drafts
    except Exception as e:
        print("V50.0 load sendback drafts error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []


# =========================
# V50.0 Send-back Review Workspace
# =========================

def load_persistent_draft_review_states_from_db(limit=500):
    """Load owner review decisions for send-back drafts.

    Safe scope: reads memory_backups/source=web_sendback_review_state.
    Latest decision wins per draft_key.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_sendback_review_state", int(limit or 500)),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        states = {}
        for text, created_at, row_id in rows:
            payload = _json_loads_safe(text)
            if not isinstance(payload, dict):
                continue
            key = str(payload.get("draft_key") or "")
            if not key or key in states:
                continue
            payload["created_at"] = str(payload.get("created_at") or created_at or "")
            payload["db_id"] = row_id
            states[key] = payload
        return states
    except Exception as e:
        print("V51.0 load draft review states error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def ensure_draft_review_states_loaded():
    global DRAFT_REVIEW_STATES_LOADED, DRAFT_REVIEW_STATES
    if DRAFT_REVIEW_STATES_LOADED:
        return
    DRAFT_REVIEW_STATES = load_persistent_draft_review_states_from_db(limit=800)
    DRAFT_REVIEW_STATES_LOADED = True


def load_draft_review_history_from_db(limit=1500):
    """V51.2 STATE RECOVERY FIX: load review history per draft_key.

    Unlike the normal latest-state reader, this preserves enough history to
    recover a previously approved draft when a legacy/stale reset record was
    written after Telegram send preparation had already been persisted.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_sendback_review_state", int(limit or 1500)),
        )
        rows = cur.fetchall() or []
        cur.close()
        conn.close()
        history = {}
        for text, created_at, row_id in rows:
            payload = _json_loads_safe(text, {})
            if not isinstance(payload, dict):
                continue
            key = str(payload.get("draft_key") or "")
            if not key:
                continue
            payload = dict(payload)
            payload["created_at"] = str(payload.get("created_at") or created_at or "")
            payload["db_id"] = row_id
            history.setdefault(key, []).append(payload)
        return history
    except Exception as e:
        print("V51.2 STATE RECOVERY FIX load review history error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def _review_payload_state(payload):
    payload = payload or {}
    return str(payload.get("review_state") or payload.get("approval_state") or "draft_saved")


def _recover_effective_review_state(draft_key, latest_state, prep_state, recipient_state, review_history):
    """Recover the highest valid persisted workflow stage for one draft.

    Safety rule: needs_edit and rejected are explicit owner decisions and always
    win. A legacy draft_saved/reset can be ignored only when the same draft has
    a historical approved_for_send record AND a later workflow layer already
    proves send preparation or recipient resolution exists.
    """
    latest_state = str(latest_state or "draft_saved")
    if latest_state in ("needs_edit", "rejected", "approved_for_send"):
        return latest_state, False, "latest_review_state"

    history = review_history.get(str(draft_key or ""), []) or []
    had_approved = any(_review_payload_state(p) == "approved_for_send" for p in history)
    advanced_state_exists = (
        str(prep_state or "") == "telegram_send_prepared"
        or str(recipient_state or "") in ("recipient_unresolved", "recipient_resolved")
    )
    latest_payload = history[0] if history else {}
    latest_decision = str(latest_payload.get("decision") or "").lower()

    if had_approved and advanced_state_exists and latest_state == "draft_saved":
        # This specifically repairs legacy/stale Return-to-review query replays
        # that reset review state while send-prep remained persisted.
        return "approved_for_send", True, f"recovered_from_{latest_decision or 'draft_saved'}"

    return latest_state, False, "latest_review_state"


def draft_review_state(draft):
    ensure_draft_review_states_loaded()
    key = str((draft or {}).get("draft_key") or "")
    saved_default = (draft or {}).get("approval_state") or "draft_saved"
    state_payload = DRAFT_REVIEW_STATES.get(key) or {}
    return state_payload.get("review_state") or state_payload.get("approval_state") or saved_default


def save_draft_review_state_to_db(draft_key, review_state, decision=""):
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url"
    draft_key = str(draft_key or "").strip()
    if not draft_key:
        return False, "missing_draft_key"
    review_state = str(review_state or "draft_saved")
    payload = {
        "type": "sendback_draft_review_state",
        "version": "V51.2",
        "draft_key": draft_key,
        "review_state": review_state,
        "approval_state": review_state,
        "decision": decision or review_state,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "sendback_review_state_only",
        "safe_mode": True,
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_sendback_review_state"),
        )
        conn.commit()
        cur.close()
        conn.close()
        DRAFT_REVIEW_STATES[draft_key] = payload
        return True, "saved"
    except Exception as e:
        print("V51.0 save draft review state error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200]


def apply_draft_review_decision(draft_key, decision):
    ensure_draft_review_states_loaded()
    decision = (decision or "").strip().lower()
    state_map = {
        "approve": "approved_for_send",
        "edit": "needs_edit",
        "reject": "rejected",
        "reset": "draft_saved",
    }
    if decision not in state_map:
        return None
    review_state = state_map[decision]
    ok, status = save_draft_review_state_to_db(draft_key, review_state, decision=decision)
    return {
        "draft_key": draft_key,
        "review_state": review_state,
        "decision": decision,
        "persistent": bool(ok),
        "save_status": status,
    }


def load_persistent_telegram_send_prep_states_from_db(limit=500):
    """V51.2: load safe Telegram send preparation states.

    Safe scope: reads memory_backups/source=web_telegram_send_prep.
    Latest record wins per draft_key. This does not send anything.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_telegram_send_prep", int(limit or 500)),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        states = {}
        for text, created_at, row_id in rows:
            payload = _json_loads_safe(text)
            if not isinstance(payload, dict):
                continue
            key = str(payload.get("draft_key") or "")
            if not key or key in states:
                continue
            payload["created_at"] = str(payload.get("created_at") or created_at or "")
            payload["db_id"] = row_id
            states[key] = payload
        return states
    except Exception as e:
        print("V51.1 load telegram send prep states error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def ensure_telegram_send_prep_states_loaded():
    global TELEGRAM_SEND_PREP_STATES_LOADED, TELEGRAM_SEND_PREP_STATES
    if TELEGRAM_SEND_PREP_STATES_LOADED:
        return
    TELEGRAM_SEND_PREP_STATES = load_persistent_telegram_send_prep_states_from_db(limit=800)
    TELEGRAM_SEND_PREP_STATES_LOADED = True


def telegram_send_prep_state(draft):
    ensure_telegram_send_prep_states_loaded()
    key = str((draft or {}).get("draft_key") or "")
    payload = TELEGRAM_SEND_PREP_STATES.get(key) or {}
    return payload.get("send_prep_state") or payload.get("status") or "not_prepared"


def save_telegram_send_prep_to_db(draft_key, action="prepare"):
    """V51.2: create a safe Telegram send action preview.

    This only stores a send-prep record. It does not call Telegram APIs and it does not
    send any message to a client.
    """
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url"
    draft_key = str(draft_key or "").strip()
    if not draft_key:
        return False, "missing_draft_key"
    ensure_draft_review_states_loaded()
    ensure_telegram_send_prep_states_loaded()
    payload = {
        "type": "telegram_send_prep",
        "version": "V51.2",
        "draft_key": draft_key,
        "channel": "Telegram",
        "send_prep_state": "telegram_send_prepared",
        "status": "prepared_not_sent",
        "decision": action or "prepare",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "telegram_send_prep_only",
        "safe_mode": True,
        "sent": False,
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_telegram_send_prep"),
        )
        conn.commit()
        cur.close()
        conn.close()
        TELEGRAM_SEND_PREP_STATES[draft_key] = payload
        return True, "prepared"
    except Exception as e:
        print("V51.1 save telegram send prep error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200]


def apply_telegram_send_prep(draft_key):
    ok, status = save_telegram_send_prep_to_db(draft_key, action="prepare_telegram_send")
    return {
        "draft_key": draft_key,
        "send_prep_state": "telegram_send_prepared" if ok else "prep_failed",
        "persistent": bool(ok),
        "save_status": status,
    }



def _normalize_client_key(value):
    """Stable client identity key: case/space insensitive."""
    return " ".join(str(value or "").strip().lower().split())


def _mapping_is_active(payload):
    return bool(
        isinstance(payload, dict)
        and payload.get("verified") is True
        and str(payload.get("mapping_state") or "verified").lower() not in ("inactive", "revoked", "deleted")
    )


def load_persistent_telegram_client_contact_mappings_from_db(limit=500):
    """Load latest mapping state per normalized client.

    Latest record wins. Inactive/revoked records suppress older verified mappings.
    Active duplicate chat_ids remain visible for diagnostics but are blocked from
    recipient resolution by telegram_mapping_conflicts().
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_telegram_client_contact_mapping", int(limit or 500)),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        latest = {}
        for text, created_at, row_id in rows:
            payload = _json_loads_safe(text)
            if not isinstance(payload, dict):
                continue
            client_key = _normalize_client_key(payload.get("normalized_client_key") or payload.get("client_name"))
            if not client_key or client_key in latest:
                continue
            payload["normalized_client_key"] = client_key
            payload["created_at"] = str(payload.get("created_at") or created_at or "")
            payload["db_id"] = row_id
            latest[client_key] = payload
        return {k: v for k, v in latest.items() if _mapping_is_active(v)}
    except Exception as e:
        print("V51.2 SAFETY load client contact mappings error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def _reload_telegram_client_contact_mappings():
    global TELEGRAM_CLIENT_CONTACT_MAPPINGS_LOADED, TELEGRAM_CLIENT_CONTACT_MAPPINGS
    TELEGRAM_CLIENT_CONTACT_MAPPINGS = load_persistent_telegram_client_contact_mappings_from_db(limit=1200)
    TELEGRAM_CLIENT_CONTACT_MAPPINGS_LOADED = True
    return TELEGRAM_CLIENT_CONTACT_MAPPINGS


def ensure_telegram_client_contact_mappings_loaded():
    global TELEGRAM_CLIENT_CONTACT_MAPPINGS_LOADED
    if not TELEGRAM_CLIENT_CONTACT_MAPPINGS_LOADED:
        _reload_telegram_client_contact_mappings()


def telegram_mapping_conflicts():
    """Return chat_id -> sorted client keys when an active id has multiple owners."""
    ensure_telegram_client_contact_mappings_loaded()
    owners = {}
    for client_key, payload in TELEGRAM_CLIENT_CONTACT_MAPPINGS.items():
        chat_id = str(payload.get("telegram_chat_id") or "").strip()
        if chat_id:
            owners.setdefault(chat_id, []).append(client_key)
    return {chat_id: sorted(keys) for chat_id, keys in owners.items() if len(set(keys)) > 1}


def telegram_client_contact_mapping(client_name):
    ensure_telegram_client_contact_mappings_loaded()
    key = _normalize_client_key(client_name)
    payload = TELEGRAM_CLIENT_CONTACT_MAPPINGS.get(key) or {}
    if not payload:
        return {}
    chat_id = str(payload.get("telegram_chat_id") or "").strip()
    if chat_id in telegram_mapping_conflicts():
        return {}  # ambiguous mappings are never eligible for sending
    return payload


def _valid_telegram_chat_id(value):
    raw = str(value or "").strip()
    if not raw:
        return False
    if raw.startswith("-"):
        return raw[1:].isdigit() and len(raw[1:]) >= 5
    return raw.isdigit() and len(raw) >= 5


def save_telegram_client_contact_mapping_to_db(client_name, chat_id, verified=False, note=""):
    """Persist one unique verified client → Telegram chat_id mapping.

    A chat_id already owned by another active normalized client is rejected.
    Saving a new id for the same normalized client intentionally replaces that
    client's prior mapping because latest record wins.
    """
    database_url = _db_url()
    client_name = " ".join(str(client_name or "").strip().split())
    client_key = _normalize_client_key(client_name)
    chat_id = str(chat_id or "").strip()
    if not database_url:
        return False, "missing_database_url", {}
    if not client_key:
        return False, "missing_client_name", {}
    if not _valid_telegram_chat_id(chat_id):
        return False, "invalid_chat_id", {}
    if not verified:
        return False, "verification_required", {}

    current = _reload_telegram_client_contact_mappings()
    conflicting_clients = [
        key for key, mapping in current.items()
        if key != client_key and str(mapping.get("telegram_chat_id") or "").strip() == chat_id
    ]
    if conflicting_clients:
        return False, "chat_id_conflict", {
            "client_name": client_name,
            "normalized_client_key": client_key,
            "telegram_chat_id": chat_id,
            "conflicting_clients": conflicting_clients,
        }

    payload = {
        "type": "telegram_client_contact_mapping",
        "version": "V51.2 SAFETY FIX",
        "client_name": client_name,
        "normalized_client_key": client_key,
        "telegram_chat_id": chat_id,
        "mapping_state": "verified",
        "verified": True,
        "verification_method": "owner_manual_confirmation",
        "note": str(note or "").strip()[:500],
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "client_contact_mapping_only",
        "safe_mode": True,
        "sent": False,
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_telegram_client_contact_mapping"),
        )
        conn.commit()
        cur.close()
        conn.close()
        _reload_telegram_client_contact_mappings()
        return True, "mapping_saved", payload
    except Exception as e:
        print("V51.2 SAFETY save client contact mapping error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200], payload


def deactivate_telegram_client_contact_mapping_to_db(client_name, note=""):
    """Write an inactive latest-state record for one normalized client."""
    database_url = _db_url()
    client_key = _normalize_client_key(client_name)
    if not database_url:
        return False, "missing_database_url", {}
    if not client_key:
        return False, "missing_client_name", {}
    current = _reload_telegram_client_contact_mappings()
    existing = current.get(client_key) or {}
    if not existing:
        return False, "mapping_not_found", {}
    payload = {
        "type": "telegram_client_contact_mapping",
        "version": "V51.2 SAFETY FIX",
        "client_name": existing.get("client_name") or str(client_name or "").strip(),
        "normalized_client_key": client_key,
        "telegram_chat_id": str(existing.get("telegram_chat_id") or ""),
        "mapping_state": "inactive",
        "verified": False,
        "verification_method": "owner_manual_deactivation",
        "note": str(note or "Owner deactivated mapping").strip()[:500],
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "client_contact_mapping_only",
        "safe_mode": True,
        "sent": False,
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s)",
            ("__web__", _json_dumps_safe(payload), "web_telegram_client_contact_mapping"),
        )
        conn.commit()
        cur.close()
        conn.close()
        _reload_telegram_client_contact_mappings()
        return True, "mapping_deactivated", payload
    except Exception as e:
        print("V51.2 SAFETY deactivate mapping error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200], payload


def telegram_contact_mapping_form_html():
    ensure_telegram_client_contact_mappings_loaded()
    conflicts = telegram_mapping_conflicts()
    rows = []
    for client_key, m in sorted(TELEGRAM_CLIENT_CONTACT_MAPPINGS.items()):
        chat_id = str(m.get("telegram_chat_id") or "")
        is_conflict = chat_id in conflicts
        state_label = "CONFLICT — blocked" if is_conflict else "verified unique"
        action = q('/outbox')
        sep = '&' if '?' in action else '?'
        deactivate_href = (
            f"{action}{sep}contact_action=deactivate_mapping"
            f"&client_name={quote_plus(str(m.get('client_name') or client_key))}"
        )
        rows.append(
            f"<div class='row'><div><b>{html_escape(m.get('client_name') or client_key)}</b>"
            f"<span class='muted'>Telegram chat_id: {html_escape(chat_id)}</span>"
            f"<span class='muted'>{html_escape(state_label)} · normalized: {html_escape(client_key)}</span></div>"
            f"<div><span class='pill'>{html_escape('blocked' if is_conflict else 'verified')}</span> "
            f"<a class='pill' href='{deactivate_href}'>Deactivate</a></div></div>"
        )
    mapping_rows = "".join(rows) or (
        "<div class='row'><div><b>No verified Telegram client mappings yet.</b>"
        "<span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    )
    conflict_note = ""
    if conflicts:
        items = "; ".join(f"{cid}: {', '.join(keys)}" for cid, keys in sorted(conflicts.items()))
        conflict_note = (
            "<div class='safe-note' style='margin-top:12px'><b>Safety conflict:</b> the same chat_id is assigned to multiple clients: "
            + html_escape(items)
            + ". These mappings are blocked until incorrect mappings are deactivated.</div>"
        )
    action = q('/outbox')
    return (
        "<section class='card card-pad'><div class='section-title'>Telegram Client Contact Mapping</div>"
        "<div class='safe-note'>One Telegram chat_id may belong to only one normalized client. Andris / andris are treated as the same client. Saving a new id for the same client replaces the old mapping; conflicts are rejected. No message is sent.</div><br>"
        f"<form method='get' action='{action}'>"
        f"<input type='hidden' name='lang' value='{html_escape(current_language())}'>"
        "<input type='hidden' name='contact_action' value='save_mapping'>"
        "<div class='form-grid'>"
        "<label>Client name<input name='client_name' placeholder='Andris' required></label>"
        "<label>Telegram chat_id<input name='telegram_chat_id' placeholder='123456789' required></label>"
        "<label>Verification note<input name='mapping_note' placeholder='Confirmed by owner / client'></label>"
        "</div>"
        "<label style='display:block;margin-top:12px'><input type='checkbox' name='verified' value='yes' required> I confirm this Telegram chat_id belongs to this client.</label>"
        "<button class='pill' type='submit' style='margin-top:12px'>Save verified mapping</button>"
        "</form><br><div class='section-title'>Verified mappings</div><div class='list'>" + mapping_rows + "</div>"
        + conflict_note
        + "<div class='safe-note'>V51.2 SAFETY FIX: unique mapping, normalized client identity, conflict blocking and manual deactivation are active. Real sending remains disabled.</div></section><br>"
    )


def outbox_contact_mapping_banner_html():
    status = (request.args.get("mapping_status") or "").strip()
    client_name = (request.args.get("mapping_client") or "").strip()
    conflict_owner = (request.args.get("mapping_conflict_owner") or "").strip()
    if not status:
        return ""
    labels = {
        "mapping_saved": "Telegram client mapping saved",
        "mapping_deactivated": "Telegram client mapping deactivated",
        "chat_id_conflict": "Mapping blocked: chat_id already belongs to another client",
        "mapping_not_found": "Mapping not found",
        "verification_required": "Owner verification is required",
        "invalid_chat_id": "Invalid Telegram chat_id",
    }
    label = labels.get(status, "Telegram client mapping not saved")
    detail = client_name
    if conflict_owner:
        detail += " · existing owner: " + conflict_owner
    return (
        "<section class='card card-pad'><div class='section-title'>Telegram contact mapping</div>"
        f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(detail)}</span></div><span class='pill'>{html_escape(status)}</span></div>"
        "<div class='safe-note'>No Telegram message was sent.</div></section><br>"
    )


def load_persistent_telegram_recipient_states_from_db(limit=500):
    """V51.2: load safe Telegram recipient resolution states.

    Reads only memory_backups/source=web_telegram_recipient_resolution.
    No Telegram API call is made. Latest record wins per draft_key.
    """
    database_url = _db_url()
    if not database_url:
        return {}
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT backup_text, created_at, id
            FROM memory_backups
            WHERE source = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            ("web_telegram_recipient_resolution", int(limit or 500)),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        states = {}
        for text, created_at, row_id in rows:
            payload = _json_loads_safe(text)
            if not isinstance(payload, dict):
                continue
            key = str(payload.get("draft_key") or "")
            if not key or key in states:
                continue
            payload["created_at"] = str(payload.get("created_at") or created_at or "")
            payload["db_id"] = row_id
            states[key] = payload
        return states
    except Exception as e:
        print("V51.1 load telegram recipient states error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {}


def ensure_telegram_recipient_states_loaded():
    global TELEGRAM_RECIPIENT_STATES_LOADED, TELEGRAM_RECIPIENT_STATES
    if TELEGRAM_RECIPIENT_STATES_LOADED:
        return
    TELEGRAM_RECIPIENT_STATES = load_persistent_telegram_recipient_states_from_db(limit=800)
    TELEGRAM_RECIPIENT_STATES_LOADED = True


def telegram_recipient_state(draft):
    ensure_telegram_recipient_states_loaded()
    key = str((draft or {}).get("draft_key") or "")
    payload = TELEGRAM_RECIPIENT_STATES.get(key) or {}
    return payload.get("recipient_state") or "recipient_not_checked"


def _recipient_candidate_from_draft(draft):
    draft = draft or {}
    mapping = telegram_client_contact_mapping(draft.get("client_name") or "")
    if mapping.get("verified") and mapping.get("telegram_chat_id"):
        return str(mapping.get("telegram_chat_id")), "verified_client_contact_mapping"
    for key in ("telegram_chat_id", "recipient_chat_id", "client_chat_id", "chat_id"):
        value = draft.get(key)
        if value not in (None, ""):
            return str(value), key
    return "", ""


def save_telegram_recipient_resolution_to_db(draft):
    """Create a safe recipient-resolution record; never sends a message."""
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url", {}
    draft = draft or {}
    draft_key = str(draft.get("draft_key") or "").strip()
    if not draft_key:
        return False, "missing_draft_key", {}
    ensure_telegram_recipient_states_loaded()
    chat_id, chat_id_source = _recipient_candidate_from_draft(draft)
    resolved = bool(chat_id)
    payload = {
        "type": "telegram_recipient_resolution",
        "version": "V51.2",
        "draft_key": draft_key,
        "client_name": draft.get("client_name") or "Workspace",
        "channel": "Telegram",
        "recipient_state": "recipient_resolved" if resolved else "recipient_unresolved",
        "telegram_chat_id": chat_id or None,
        "chat_id_source": chat_id_source or None,
        "resolution_note": "Recipient chat_id found in draft metadata." if resolved else "No Telegram chat_id is linked to this client yet.",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "recipient_resolution_only",
        "safe_mode": True,
        "sent": False,
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_telegram_recipient_resolution"),
        )
        conn.commit()
        cur.close()
        conn.close()
        TELEGRAM_RECIPIENT_STATES[draft_key] = payload
        return True, payload["recipient_state"], payload
    except Exception as e:
        print("V51.1 save telegram recipient resolution error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200], payload


def apply_telegram_recipient_resolution(draft_key):
    drafts = global_outbox_draft_items(limit=500)
    draft = next((d for d in drafts if str(d.get("draft_key") or "") == str(draft_key or "")), None)
    if not draft:
        return {"draft_key": draft_key, "recipient_state": "draft_not_found", "persistent": False}
    ok, status, payload = save_telegram_recipient_resolution_to_db(draft)
    return {
        "draft_key": draft_key,
        "recipient_state": payload.get("recipient_state") or status,
        "telegram_chat_id": payload.get("telegram_chat_id"),
        "persistent": bool(ok),
        "save_status": status,
    }


def outbox_recipient_banner_html():
    action = (request.args.get("recipient_action") or "").strip().lower()
    draft_key = unquote_plus((request.args.get("draft_key") or "").strip())
    if action != "resolve_telegram" or not draft_key:
        return ""
    result = apply_telegram_recipient_resolution(draft_key)
    state = result.get("recipient_state") or "recipient_unresolved"
    label = "Recipient resolved" if state == "recipient_resolved" else "Recipient unresolved"
    note = (
        f"Telegram chat_id: {html_escape(result.get('telegram_chat_id'))}"
        if result.get("telegram_chat_id")
        else "No verified Telegram chat_id is linked to this client yet. Add and confirm a client contact mapping before real send is enabled."
    )
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>Telegram recipient resolution</div>"
        "<div class='list'>"
        f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(draft_key)}</span><span class='muted'>{note}</span></div><span class='pill'>{html_escape(result.get('save_status') or '')}</span></div>"
        "</div><div class='safe-note'>V51.2 safe mode: recipient resolution uses a verified client contact mapping and does not change review or send-prep state. No Telegram message was sent.</div></section><br>"
    )


def outbox_send_prep_banner_html():
    send_prep = (request.args.get("send_prep") or "").strip().lower()
    draft_key = unquote_plus((request.args.get("draft_key") or "").strip())
    if send_prep != "telegram" or not draft_key:
        return ""
    result = apply_telegram_send_prep(draft_key)
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>Telegram send action prepared</div>"
        "<div class='list'>"
        f"<div class='row'><div><b>Prepared, not sent</b><span class='muted'>{html_escape(draft_key)}</span></div><span class='pill'>{html_escape(result.get('save_status') or '')}</span></div>"
        "</div><div class='safe-note'>V51.2 safe mode: send preparation is stored without changing review or recipient state. No Telegram message was sent.</div></section><br>"
    )


def outbox_review_banner_html():
    decision = (request.args.get("draft_decision") or "").strip().lower()
    draft_key = unquote_plus((request.args.get("draft_key") or "").strip())
    if not decision or not draft_key:
        return ""
    result = apply_draft_review_decision(draft_key, decision)
    if not result:
        return ""
    label_map = {
        "approved_for_send": "Approved for send",
        "needs_edit": "Needs edit",
        "rejected": "Rejected",
        "draft_saved": "Draft saved",
    }
    state = result.get("review_state") or "draft_saved"
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>Draft review saved</div>"
        "<div class='list'>"
        f"<div class='row'><div><b>{html_escape(label_map.get(state, state))}</b><span class='muted'>{html_escape(draft_key)}</span></div><span class='pill'>{html_escape(result.get('save_status') or '')}</span></div>"
        "</div><div class='safe-note'>V51.2: owner review status is saved before queue counts render, so KPIs and queues stay aligned. No client message is sent yet.</div></section><br>"
    )


def reviewed_sendback_drafts(limit=500):
    """V51.2 STATE RECOVERY FIX: merge persistent state by draft_key.

    Review, send-prep and recipient resolution remain independent sources. The
    final runtime draft gets one effective state from all persisted layers.
    """
    drafts = load_persistent_sendback_drafts_from_db(None, limit=limit)
    ensure_draft_review_states_loaded()
    ensure_telegram_send_prep_states_loaded()
    ensure_telegram_recipient_states_loaded()
    review_history = load_draft_review_history_from_db(limit=max(int(limit or 500) * 4, 1500))

    for d in drafts:
        key = str(d.get("draft_key") or "")
        review_payload = DRAFT_REVIEW_STATES.get(key) or {}
        prep_payload = TELEGRAM_SEND_PREP_STATES.get(key) or {}
        recipient_payload = TELEGRAM_RECIPIENT_STATES.get(key) or {}

        latest_review_state = (
            review_payload.get("review_state")
            or review_payload.get("approval_state")
            or d.get("approval_state")
            or "draft_saved"
        )
        prep_state = prep_payload.get("send_prep_state") or prep_payload.get("status") or "not_prepared"
        recipient_state = recipient_payload.get("recipient_state") or "recipient_not_checked"

        effective_review_state, recovered, recovery_reason = _recover_effective_review_state(
            key, latest_review_state, prep_state, recipient_state, review_history
        )

        d["review_state"] = effective_review_state
        d["review_state_raw"] = latest_review_state
        d["review_state_recovered"] = bool(recovered)
        d["review_recovery_reason"] = recovery_reason
        d["review_saved_at"] = review_payload.get("updated_at") or review_payload.get("created_at") or ""
        d["telegram_send_prep_state"] = prep_state
        d["telegram_send_prep_saved_at"] = prep_payload.get("updated_at") or prep_payload.get("created_at") or ""
        d["telegram_recipient_state"] = recipient_state
        d["telegram_chat_id"] = recipient_payload.get("telegram_chat_id")
        d["telegram_recipient_saved_at"] = recipient_payload.get("updated_at") or recipient_payload.get("created_at") or ""

    return drafts



def save_sendback_draft_to_db(client_name, item, channel, draft):
    """V50.0: save draft preview to client profile memory.

    Safe scope: stores draft text only in memory_backups/source=web_sendback_draft.
    Real sending bridges come later.
    """
    database_url = _db_url()
    if not database_url:
        return False, "missing_database_url"
    draft_key = sendback_draft_key(client_name, item, channel)
    meta = (item or {}).get("metadata") if isinstance((item or {}).get("metadata"), dict) else {}
    payload = {
        "type": "sendback_draft",
        "version": "V51.2",
        "draft_key": draft_key,
        "client_name": client_name or meta.get("client_name") or "Workspace",
        "client_slug": _client_profile_slug(client_name or meta.get("client_name") or "Workspace"),
        "source_object_id": (item or {}).get("object_id") or meta.get("source_thread_id") or "",
        "source_title": (item or {}).get("title") or "Client work",
        "object_type": (item or {}).get("object_type") or "work",
        "channel": (draft or {}).get("channel") or _sendback_channel_label(channel),
        "subject": (draft or {}).get("subject") or "",
        "body": (draft or {}).get("body") or "",
        "evidence": (draft or {}).get("evidence") or "NinaOS memory",
        "approval_state": "draft_saved",
        "status": "owner_review",
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "db_write_scope": "sendback_draft_only",
    }
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO memory_backups (user_id, backup_text, source)
            VALUES (%s, %s, %s)
            """,
            ("__web__", _json_dumps_safe(payload), "web_sendback_draft"),
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "saved"
    except Exception as e:
        print("V50.0 save sendback draft error:", repr(e))
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return False, str(e)[:200]


def saved_sendback_drafts_html(client_name):
    drafts = load_persistent_sendback_drafts_from_db(client_name, limit=200)
    lang = current_language()
    if not drafts:
        rows = f"<div class='row'><div><b>{html_escape(tx('no_items', lang))}</b><span class='muted'>No saved drafts yet.</span></div><span class='pill'>idle</span></div>"
    else:
        rows = ""
        for d in drafts[:10]:
            subject = d.get("subject") or ""
            body = str(d.get("body") or "")
            body_short = body[:240] + ("…" if len(body) > 240 else "")
            detail = f"{d.get('channel','Draft')} · {d.get('object_type','work')} · saved {d.get('saved_at','')}"
            if subject:
                detail += f" · {subject}"
            rows += (
                "<div class='row'><div>"
                f"<b>{html_escape(d.get('source_title') or 'Saved draft')}</b>"
                f"<span class='muted'>{html_escape(detail)}</span>"
                f"<span class='muted'>{html_escape(body_short)}</span>"
                "</div><span class='pill'>saved draft</span></div>"
            )
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>Saved Send-back Drafts</div>"
        f"<div class='list'>{rows}</div>"
        "<div class='safe-note'>V50.0: prepared drafts are saved to this client profile for owner review. Nothing is sent yet.</div>"
        "</section><br>"
    )


def global_outbox_draft_items(limit=500):
    """V50.0: load all saved send-back drafts with owner review state."""
    return reviewed_sendback_drafts(limit=limit) or []


def global_outbox_rows(limit=20, empty_text=None):
    lang = current_language()
    drafts = global_outbox_draft_items(limit=500)
    if not drafts:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>No saved send-back drafts yet.</span></div><span class='pill'>idle</span></div>"
    rows = ""
    label_map = {
        "draft_saved": "draft saved",
        "approved_for_send": "approved for send",
        "needs_edit": "needs edit",
        "rejected": "rejected",
    }
    for d in drafts[:limit]:
        client = d.get("client_name") or "Workspace"
        channel = d.get("channel") or "Draft"
        title = d.get("source_title") or "Saved draft"
        object_type = d.get("object_type") or "work"
        state = d.get("review_state") or "draft_saved"
        body = str(d.get("body") or "")
        body_short = body[:220] + ("…" if len(body) > 220 else "")
        href = q('/clients/' + _client_profile_slug(client))
        outbox_href = q('/outbox')
        sep = '&' if '?' in outbox_href else '?'
        key = quote_plus(str(d.get("draft_key") or ""))
        actions = ""
        if state not in ["approved_for_send", "rejected"]:
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=approve&draft_key={key}'>Approve for send</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=edit&draft_key={key}'>Needs edit</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=reject&draft_key={key}'>Reject draft</a>"
        else:
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=reset&draft_key={key}'>Return to review</a>"
        if state == "approved_for_send" and "Telegram" in str(channel):
            actions += f"<a class='pill' href='{outbox_href}{sep}send_prep=telegram&draft_key={key}'>Prepare Telegram Send</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}recipient_action=resolve_telegram&draft_key={key}'>Resolve Telegram Recipient</a>"
        actions += f"<a class='pill' href='{href}'>Open client</a>"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(title)}</b>"
            f"<span class='muted'>{html_escape(client)} · {html_escape(channel)} · {html_escape(object_type)} · {html_escape(label_map.get(state, state))} · {html_escape(d.get('telegram_send_prep_state') or 'not_prepared')} · {html_escape(d.get('telegram_recipient_state') or 'recipient_not_checked')}{' · state_recovered' if d.get('review_state_recovered') else ''}</span>"
            f"<span class='muted'>{html_escape(body_short)}</span>"
            f"</div>{actions}</div>"
        )
    return rows


def outbox_channel_kpis():
    drafts = global_outbox_draft_items(limit=500)
    counts = {"WhatsApp": 0, "Telegram": 0, "Email": 0, "Other": 0}
    states = {"draft_saved": 0, "approved_for_send": 0, "needs_edit": 0, "rejected": 0}
    clients = set()
    for d in drafts:
        clients.add(d.get("client_name") or "Workspace")
        ch = str(d.get("channel") or "Other")
        if "WhatsApp" in ch:
            counts["WhatsApp"] += 1
        elif "Telegram" in ch:
            counts["Telegram"] += 1
        elif "Email" in ch:
            counts["Email"] += 1
        else:
            counts["Other"] += 1
        st = d.get("review_state") or "draft_saved"
        states[st] = states.get(st, 0) + 1
    return (
        "<div class='kpis'>"
        f"<div class='kpi'><b>{len(drafts)}</b><span>Saved drafts</span></div>"
        f"<div class='kpi'><b>{len(clients)}</b><span>Clients</span></div>"
        f"<div class='kpi'><b>{counts['Telegram']}</b><span>Telegram</span></div>"
        f"<div class='kpi'><b>{states.get('approved_for_send',0)}</b><span>Approved to send</span></div>"
        f"<div class='kpi'><b>{states.get('needs_edit',0)}</b><span>Needs edit</span></div>"
        "</div>"
    )


def global_outbox_rows_for_items(items):
    """Render a supplied subset of draft payloads with the V50.0 review actions."""
    if not items:
        return ""
    rows = ""
    label_map = {
        "draft_saved": "draft saved",
        "approved_for_send": "approved for send",
        "needs_edit": "needs edit",
        "rejected": "rejected",
    }
    for d in items:
        client = d.get("client_name") or "Workspace"
        channel = d.get("channel") or "Draft"
        title = d.get("source_title") or "Saved draft"
        object_type = d.get("object_type") or "work"
        state = d.get("review_state") or "draft_saved"
        body = str(d.get("body") or "")
        body_short = body[:220] + ("…" if len(body) > 220 else "")
        href = q('/clients/' + _client_profile_slug(client))
        outbox_href = q('/outbox')
        sep = '&' if '?' in outbox_href else '?'
        key = quote_plus(str(d.get("draft_key") or ""))
        actions = ""
        if state not in ["approved_for_send", "rejected"]:
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=approve&draft_key={key}'>Approve for send</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=edit&draft_key={key}'>Needs edit</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=reject&draft_key={key}'>Reject draft</a>"
        else:
            actions += f"<a class='pill' href='{outbox_href}{sep}draft_decision=reset&draft_key={key}'>Return to review</a>"
        if state == "approved_for_send" and "Telegram" in str(channel):
            actions += f"<a class='pill' href='{outbox_href}{sep}send_prep=telegram&draft_key={key}'>Prepare Telegram Send</a>"
            actions += f"<a class='pill' href='{outbox_href}{sep}recipient_action=resolve_telegram&draft_key={key}'>Resolve Telegram Recipient</a>"
        actions += f"<a class='pill' href='{href}'>Open client</a>"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(title)}</b>"
            f"<span class='muted'>{html_escape(client)} · {html_escape(channel)} · {html_escape(object_type)} · {html_escape(label_map.get(state, state))} · {html_escape(d.get('telegram_send_prep_state') or 'not_prepared')} · {html_escape(d.get('telegram_recipient_state') or 'recipient_not_checked')}{' · state_recovered' if d.get('review_state_recovered') else ''}</span>"
            f"<span class='muted'>{html_escape(body_short)}</span>"
            f"</div>{actions}</div>"
        )
    return rows


def outbox_body(data=None):
    lang = current_language()
    # V51.0 FIX: apply the requested decision before computing drafts, KPIs and queues.
    # In V50.0 the banner saved the decision after the `approved` subset was already built,
    # so the KPI could say 2 approved while the Approved To Send Queue showed 1.
    review_banner = outbox_review_banner_html()
    send_prep_banner = outbox_send_prep_banner_html()
    recipient_banner = outbox_recipient_banner_html()
    contact_mapping_banner = outbox_contact_mapping_banner_html()
    contact_mapping_surface = telegram_contact_mapping_form_html()
    drafts = global_outbox_draft_items(limit=500)
    approved = [d for d in drafts if (d.get("review_state") or "") == "approved_for_send"]
    needs_edit = [d for d in drafts if (d.get("review_state") or "") == "needs_edit"]
    rejected = [d for d in drafts if (d.get("review_state") or "") == "rejected"]
    telegram_prepared = [d for d in drafts if (d.get("telegram_send_prep_state") or "") == "telegram_send_prepared"]
    recipient_resolved = [d for d in drafts if (d.get("telegram_recipient_state") or "") == "recipient_resolved"]
    recipient_unresolved = [d for d in drafts if "Telegram" in str(d.get("channel") or "") and (d.get("telegram_recipient_state") or "recipient_not_checked") != "recipient_resolved"]
    draft_saved = [d for d in drafts if (d.get("review_state") or "draft_saved") == "draft_saved"]

    def rows_for(items, empty="No drafts in this queue."):
        if not items:
            return f"<div class='row'><div><b>{html_escape(empty)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
        all_drafts = drafts
        try:
            # Temporarily render a subset through the same row logic.
            return global_outbox_rows_for_items(items)
        except Exception:
            return global_outbox_rows(limit=len(items))

    return (
        work_page_header("Outbox", "V51.2 STATE RECOVERY FIX — latest persistent review, send-prep, recipient and verified mapping state merged by draft_key.")
        + review_banner
        + send_prep_banner
        + contact_mapping_banner
        + recipient_banner
        + contact_mapping_surface
        + f"<section class='card card-pad'>{outbox_channel_kpis()}<br><div class='safe-note'>V51.2 STATE RECOVERY FIX: review, send-prep, recipient and mapping state are merged independently by draft_key. Legacy accidental resets cannot erase an already prepared approved Telegram workflow. No client message is sent yet.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Saved Drafts Review Queue</div><div class='list'>{global_outbox_rows(limit=40, empty_text=tx('no_items', lang))}</div><div class='safe-note'>Use Approve for send / Needs edit / Reject draft. Approved Telegram drafts can prepare a safe send action and resolve a verified recipient.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Approved To Send Queue</div><div class='list'>{global_outbox_rows_for_items(approved) if approved else rows_for([], 'No approved drafts yet.')}</div><div class='safe-note'>V51.2 STATE RECOVERY FIX: effective approval is recovered from persistent history when a legacy reset conflicts with an already persisted Telegram send-prep stage. Ambiguous mappings remain blocked. Real sending is still disabled.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Telegram Send Prep Queue</div><div class='list'>{global_outbox_rows_for_items(telegram_prepared) if telegram_prepared else rows_for([], 'No prepared Telegram send actions yet.')}</div><div class='safe-note'>Prepared means queued for future bridge review only. Recipient resolution is separate and no Telegram API call has been made.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Telegram Recipient Resolution Queue</div><div class='list'>{global_outbox_rows_for_items(recipient_resolved) if recipient_resolved else rows_for([], 'No resolved Telegram recipients yet.')}</div><div class='safe-note'>Only drafts with a verified Telegram chat_id can move toward a future real send bridge.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Unresolved Telegram Recipients</div><div class='list'>{global_outbox_rows_for_items(recipient_unresolved) if recipient_unresolved else rows_for([], 'No unresolved Telegram recipients.')}</div><div class='safe-note'>Unresolved drafts are blocked from real sending until a client contact mapping exists.</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Needs Edit Queue</div><div class='list'>{global_outbox_rows_for_items(needs_edit) if needs_edit else rows_for([], 'No drafts needing edit.')}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Rejected Draft Log</div><div class='list'>{global_outbox_rows_for_items(rejected) if rejected else rows_for([], 'No rejected drafts.')}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>Pending Send-back Objects</div><div class='list'>{send_back_candidate_rows(limit=12, empty_text=tx('no_items', lang))}</div><div class='safe-note'>These approved workspace objects can still generate more draft previews from client profiles.</div></section>"
    )


def sendback_draft_preview_html(client_name, profile):
    prepare = (request.args.get("prepare") or "").strip().lower()
    object_key = (request.args.get("object") or "").strip()
    if prepare not in ["whatsapp", "telegram", "email"]:
        return ""
    item = find_sendback_item_for_client(profile, object_key)
    if not item:
        return ""
    draft = build_sendback_draft_preview(client_name, item, prepare)
    saved_ok, saved_status = save_sendback_draft_to_db(client_name, item, prepare, draft)
    subject_html = ""
    if draft.get("subject"):
        subject_html = f"<div class='row'><div><b>Subject</b><span class='muted'>{html_escape(draft.get('subject'))}</span></div><span class='pill'>email</span></div>"
    body = html_escape(draft.get("body", "")).replace("\n", "<br>")
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>Saved Drafts Inbox / Global Outbox</div>"
        "<div class='list'>"
        f"<div class='row'><div><b>{html_escape(draft.get('title'))}</b><span class='muted'>{html_escape(draft.get('channel'))} draft · evidence: {html_escape(draft.get('evidence'))}</span></div><span class='pill'>draft preview</span></div>"
        f"{subject_html}"
        f"<div class='row'><div><b>Draft message</b><span class='muted'>{body}</span></div><span class='pill'>owner review</span></div>"
        f"<div class='row'><div><b>Save status</b><span class='muted'>{html_escape(saved_status)}</span></div><span class='pill'>{'saved' if saved_ok else 'not saved'}</span></div>"
        "<div class='row'><div><b>Next step</b><span class='muted'>Owner reviews this saved draft. Real WhatsApp / Telegram / email send bridge comes later.</span></div><span class='pill'>safe mode</span></div>"
        "</div><div class='safe-note'>V51.2: Nina prepares draft previews and saves them to the client profile. Nothing is sent to the client yet; the draft is saved to this client profile.</div></section><br>"
    )


def client_profile_detail_body(client_name):
    client_name = one_nina_normalize_client_name(client_name) or "Workspace"
    profile = one_nina_find_client_profile(client_name)

    if profile:
        client_name = profile["name"]

    header = work_page_header(
        client_name,
        "V51.6 ONE NINA Client Profile — canonical business details from the same persistent Work Objects.",
    )

    if not profile:
        return (
            header
            + "<section class='card card-pad'>"
              "<div class='section-title'>ONE NINA Canonical Client Work</div>"
              "<div class='list'>"
              "<div class='row'><div><b>No canonical client work yet.</b>"
              "<span class='muted'>This profile will populate when Nina links a canonical Work Object to this client_id.</span>"
              "</div><span class='pill'>idle</span></div>"
              "</div>"
              "<div class='safe-note'>"
              "Legacy client memory is preserved, but V51.5 does not render it as a second active client-work truth."
              "</div>"
              "</section>"
        )

    object_rows = one_nina_client_object_rows(profile)
    business_detail_cards = one_nina_client_business_detail_cards(profile)
    channels = " + ".join(sorted(profile["channels"])) or "NinaOS"
    type_summary = " · ".join(
        f"{object_type}: {count}"
        for object_type, count in sorted(profile["types"].items())
    ) or "work"

    return (
        header
        + "<section class='card card-pad'>"
          f"{one_nina_client_kpis_html(profile)}"
          "<br><div class='safe-note'>"
          f"V51.6: {html_escape(client_name)} is linked directly by client_id to canonical nina_work_objects. "
          f"Types: {html_escape(type_summary)} · channels: {html_escape(channels)}."
          "</div>"
          "</section><br>"
        + business_detail_cards
        + "<section class='card card-pad'>"
          "<div class='section-title'>ONE NINA Canonical Client Work</div>"
          f"<div class='list'>{object_rows}</div>"
          "<div class='safe-note'>"
          "These are the same persistent objects shown in Tasks. "
          "The client profile does not create copies or reinterpret Telegram text."
          "</div>"
          "</section><br>"
        + "<section class='card card-pad'>"
          "<div class='section-title'>Client Context Rule</div>"
          "<div class='list'>"
          "<div class='row'><div><b>One Nina</b>"
          "<span class='muted'>Telegram, Web and future channels use the same client-linked work truth.</span>"
          "</div><span class='pill'>ONE NINA</span></div>"
          "<div class='row'><div><b>Persistent client work</b>"
          "<span class='muted'>Code can be upgraded while canonical client work remains in PostgreSQL.</span>"
          "</div><span class='pill'>persistent</span></div>"
          "</div>"
          "</section>"
    )

def client_thread_rows(items, empty_text=None, limit=None, show_controls=True, show_state=True):
    lang = current_language()
    if limit:
        items = items[:limit]
    if not items:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for obj in items:
        obj = _with_thread_state(obj)
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("thread_client") or obj.get("client_id") or "Workspace"
        family = meta.get("thread_family") or obj.get("object_type") or "work"
        count = int(meta.get("thread_items_count") or 1)
        badges = meta.get("source_badges") or []
        if isinstance(badges, str):
            badges = [badges]
        badge_text = " + ".join(str(b) for b in badges[:5] if b) or object_source_label(obj, lang)
        evidence = meta.get("thread_evidence_titles") or []
        evidence_text = " | ".join(str(x) for x in evidence[:3] if x)
        if len(evidence) > 3:
            evidence_text += f" | +{len(evidence)-3} more"
        state = thread_workflow_state(obj)
        state_text = approval_label_from_state(state, lang)
        muted = f"{client} · {family} · {count} linked item{'s' if count != 1 else ''} · {badge_text}"
        state_suffix = f" · {state_text}" if show_state else ""
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(obj.get('title'))}</b>"
            f"<span class='muted'>{html_escape(muted)}</span>"
            + (f"<span class='muted'>{html_escape(evidence_text)}</span>" if evidence_text else "")
            + (thread_approval_controls(obj) if show_controls else "")
            + "</div>"
            f"<span class='pill'>{html_escape(obj.get('status'))} · {html_escape(obj.get('priority', 'normal'))} · thread{html_escape(state_suffix)}</span></div>"
        )
    return rows

def load_existing_telegram_intake_sync():
    """V45.2: bridge Web Inbox to the Telegram memory that already exists in app.py.

    Correct priority now:
    1) existing task_engine memory_backups (real Telegram work objects);
    2) existing conversation_state voice/photo records;
    3) future intake_events table if someone adds it later;
    4) safe demo fallback.
    """
    task_memory = load_existing_task_engine_memory_from_db()
    voice_photo_memory = load_existing_voice_photo_state_from_db()
    recent_conversation = load_recent_conversation_state_from_db()
    tasks_table = load_existing_tasks_table_from_db()
    real_intake = load_real_intake_events_from_db()

    merged = []
    seen = set()
    for source_list in [task_memory, tasks_table, voice_photo_memory, recent_conversation, real_intake]:
        for obj in source_list or []:
            key = str(obj.get("object_id") or obj.get("title") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(obj)

    if merged:
        return dedupe_and_unify_intake_items(merged, limit=30)

    # Older app.py/web bridge fallback: tasks table if present.
    live = load_live_objects_from_app_db()
    synced = []
    for obj in live:
        meta = dict(obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {})
        raw_title = obj.get("title") or meta.get("raw_text") or "Telegram intake work"
        obj_type = obj.get("object_type") or infer_work_type_from_text(raw_title)
        if obj_type == "task":
            obj_type = infer_work_type_from_text(raw_title, "task")
        meta.update({
            "source": "telegram_intake_sync",
            "source_channel": meta.get("source_channel") or "Telegram",
            "intake_kind": meta.get("intake_kind") or ("followup_capture" if obj_type == "followup_task" else "telegram_work_intake"),
            "storage_target": "NinaOS client workspace",
            "approval_state": meta.get("approval_state") or "synced_from_telegram",
            "db_write": False,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        })
        synced.append({
            "object_id": str(obj.get("object_id") or "telegram_sync_item"),
            "object_type": obj_type,
            "title": raw_title,
            "status": obj.get("status") or "synced",
            "priority": obj.get("priority") or "normal",
            "client_id": obj.get("client_id") or meta.get("client_name") or "",
            "project_id": obj.get("project_id") or "",
            "due_date": obj.get("due_date") or "",
            "metadata": meta,
        })
    if synced:
        return dedupe_and_unify_intake_items(synced, limit=12)
    return telegram_intake_demo_items()


def normalize_action_to_work_object(action):
    form_type = (action.get("form_type") or "new_task").strip()
    title = (action.get("task_title") or "").strip()
    client_name = (action.get("client_name") or "").strip()
    project_name = (action.get("project_name") or "").strip()
    amount = (action.get("amount") or "").strip()
    due_date = (action.get("due_date") or "").strip()
    priority = (action.get("priority") or "normal").strip() or "normal"
    notes = (action.get("notes") or "").strip()

    type_map = {
        "new_task": "task",
        "followup": "followup_task",
        "estimate": "estimate",
        "invoice": "invoice",
    }
    status_map = {
        "new_task": "open",
        "followup": "scheduled",
        "estimate": "draft",
        "invoice": "admin_preview",
    }
    fallback_title = {
        "new_task": "New workspace task",
        "followup": "Follow up with client",
        "estimate": "Create estimate draft",
        "invoice": "Create invoice admin record",
    }

    object_type = type_map.get(form_type, "task")
    status = status_map.get(form_type, "open")
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_title = title or fallback_title.get(form_type, "Workspace action")

    metadata = {
        "client_name": client_name,
        "project_name": project_name,
        "amount": amount,
        "notes": notes,
        "owner": "Nina Office Manager",
        "source": "web_action_preview",
        "safe_mode": True,
        "db_write": False,
        "approval_state": "pending_approval",
        "approval_updated_at": "",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "object_id": f"web_preview_{form_type}_{now}_{len(WORKSPACE_ACTION_PREVIEWS) + 1}",
        "object_type": object_type,
        "title": safe_title,
        "status": status,
        "priority": priority,
        "client_id": client_name,
        "project_id": project_name,
        "due_date": due_date,
        "metadata": metadata,
    }


def create_workspace_action_preview(action):
    obj = normalize_action_to_work_object(action)
    WORKSPACE_ACTION_PREVIEWS.insert(0, obj)
    del WORKSPACE_ACTION_PREVIEWS[25:]
    return obj


def is_preview_object(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return meta.get("source") in ["web_action_preview", "web_preview", "web_voice_intake_preview", "telegram_intake_sync", "real_intake_store", "existing_task_memory", "existing_conversation_state"]


def preview_approval_state(obj):
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    return meta.get("approval_state") or "pending_approval"


def approved_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) == "approved"]


def pending_or_held_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) in ["pending_approval", "hold"]]


def rejected_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) == "rejected"]


def active_preview_items():
    return [o for o in WORKSPACE_ACTION_PREVIEWS if preview_approval_state(o) != "rejected"]


def approval_label_from_state(state, lang=None):
    state = state or "pending_approval"
    key_map = {
        "pending_approval": "pending_approval",
        "approved": "approved_preview",
        "hold": "held_preview",
        "rejected": "rejected_preview",
    }
    return tx(key_map.get(state, "pending_approval"), lang or current_language())


def apply_preview_approval(object_id, decision):
    decision = (decision or "").strip().lower()
    if decision not in ["approve", "hold", "reject"]:
        return None
    state_map = {"approve": "approved", "hold": "hold", "reject": "rejected"}
    for obj in WORKSPACE_ACTION_PREVIEWS:
        if obj.get("object_id") == object_id:
            meta = obj.setdefault("metadata", {})
            new_state = state_map[decision]
            meta["approval_state"] = new_state
            meta["approval_updated_at"] = datetime.utcnow().isoformat() + "Z"
            meta["db_write"] = False
            meta["workspace_queue_state"] = "active_approved" if new_state == "approved" else new_state
            if new_state == "approved":
                # Keep the business status stable, but mark routing clearly in metadata.
                obj["status"] = obj.get("status") or "open"
                meta["approved_queue_visible"] = True
            elif new_state == "rejected":
                meta["approved_queue_visible"] = False
            return obj
    return None


@app.before_request
def handle_preview_approval_query():
    object_id = request.args.get("preview_object_id") or ""
    decision = request.args.get("preview_decision") or ""
    if object_id and decision:
        apply_preview_approval(object_id, decision)

    thread_id = request.args.get("thread_object_id") or ""
    thread_decision = request.args.get("thread_decision") or ""
    if thread_id and thread_decision:
        try:
            from urllib.parse import unquote_plus
            thread_id = unquote_plus(thread_id)
        except Exception:
            pass
        apply_thread_approval(thread_id, thread_decision)


def preview_approval_controls(obj):
    # V43.3 FIX: show decision buttons only for preview objects that are still actionable.
    # Approved work must move to the approved workspace queue without action buttons.
    # Rejected work must stay in the rejected log without action buttons.
    if not is_preview_object(obj):
        return ""
    state = preview_approval_state(obj)
    if state not in ["pending_approval", "hold"]:
        return ""
    lang = current_language()
    object_id = html_escape(obj.get("object_id"))
    path = request.path or "/tasks"
    base = f"{path}?lang={lang}&preview_object_id={object_id}"
    return (
        "<div class='btns' style='justify-content:flex-start;margin-top:10px'>"
        f"<a class='btn primary' href='{base}&preview_decision=approve'>{tx('approve', lang)}</a>"
        f"<a class='btn' href='{base}&preview_decision=hold'>{tx('hold', lang)}</a>"
        f"<a class='btn' href='{base}&preview_decision=reject'>{tx('reject', lang)}</a>"
        "</div>"
    )


def load_workspace_data():
    workers = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "status": "ACTIVE", "detail": "1 follow-up to handle", "tone": "purple", "price": "€99/month", "category": "Sales & Growth"},
        {"name": "Nina Estimator", "role": "AI Estimator", "status": "ACTIVE", "detail": "1 estimate in progress", "tone": "blue", "price": "€119/month", "category": "Construction"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "status": "ACTIVE", "detail": "1 task · 1 active project", "tone": "green", "price": "€89/month", "category": "Operations", "route": "/workers/office-manager"},
        {"name": "Nina Support", "role": "AI Support Specialist", "status": "IDLE", "detail": "No support queue yet", "tone": "orange", "price": "€79/month", "category": "Support"},
    ]
    objects = []
    try:
        from work_objects import list_work_objects, seed_demo_work_objects
        try:
            seed_demo_work_objects()
        except Exception:
            pass
        try:
            objects = list_work_objects(workspace_id="demo_small_business") or []
        except TypeError:
            objects = list_work_objects() or []
    except Exception:
        objects = []

    normalized = [object_to_dict(o) for o in objects]
    live_objects = load_live_objects_from_app_db()
    if live_objects:
        normalized = live_objects

    approved_previews = approved_preview_items()
    if approved_previews:
        normalized = list(approved_previews) + normalized

    if not normalized:
        normalized = [
            {"object_id": "task_1", "object_type": "task", "title": "Prepare today workspace priorities", "status": "open", "priority": "high", "client_id": "", "project_id": "", "due_date": "today", "metadata": {"client_name": "", "owner": "Nina Office Manager"}},
            {"object_id": "followup_1", "object_type": "followup_task", "title": "Follow up with Demo Client about offer", "status": "scheduled", "priority": "normal", "client_id": "demo_client", "project_id": "", "due_date": "friday", "metadata": {"client_name": "Demo Client", "owner": "Nina Sales"}},
            {"object_id": "estimate_1", "object_type": "estimate", "title": "Demo estimate draft", "status": "draft", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Estimator"}},
            {"object_id": "invoice_1", "object_type": "invoice", "title": "Demo invoice follow-up", "status": "sent", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "today", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
            {"object_id": "project_1", "object_type": "project", "title": "Demo active project", "status": "active", "priority": "normal", "client_id": "demo_client", "project_id": "project_1", "due_date": "", "metadata": {"client_name": "Demo Client", "owner": "Nina Office Manager"}},
        ]

    activity = [
        {"title": "V47.1 workspace object surface polish", "body": "Inbox now groups real app.py memory into client work threads with follow-up merge.", "kind": "sync"},
        {"title": "V43.4 preview to real task surface", "body": "Approved preview objects now appear across Dashboard, Tasks and Office Manager surfaces in safe mode.", "kind": "work"},
        {"title": "Web service online", "body": "NinaOS web runtime is separated from Telegram runtime.", "kind": "info"},
        {"title": "Workspace loaded", "body": "V36 clean workspace data layer is active.", "kind": "info"},
        {"title": "Client follow-up scheduled", "body": "Ask Andris about reply.", "kind": "work"},
        {"title": "Exchange preview visible", "body": "AI worker catalog is available inside the web product.", "kind": "api"},
    ]

    active_statuses = ["open", "scheduled", "draft", "sent", "active", "in_progress"]
    tasks = [o for o in normalized if o.get("object_type") in ["task", "followup_task", "estimate", "invoice"]]
    clients = build_clients_from_objects(normalized)
    projects = [o for o in normalized if o.get("object_type") == "project"]
    counts = {
        "tasks_today": len([o for o in normalized if o.get("object_type") == "task" and o.get("status") in active_statuses]),
        "followups": len([o for o in normalized if o.get("object_type") == "followup_task" and o.get("status") in active_statuses]),
        "invoices": len([o for o in normalized if o.get("object_type") == "invoice" and o.get("status") in active_statuses]),
        "estimates": len([o for o in normalized if o.get("object_type") in ["estimate", "offer"] and o.get("status") in active_statuses]),
        "projects": len([o for o in normalized if o.get("object_type") == "project" and o.get("status") in active_statuses]),
        "clients": len(clients),
        "workers": len(workers),
    }
    return {"owner": "Katrin", "workers": workers, "objects": normalized, "tasks": tasks, "clients": clients, "projects": projects, "activity": activity, "counts": counts}


def nina_logo_html(size="small"):
    return "<div class='nina-logo " + size + "'><div class='dot-grid'></div><div class='orbit orbit-a'></div><div class='orbit orbit-b'></div></div>"


def css():
    return """
.chat-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:18px}.chat-shell{height:calc(100vh - 130px);min-height:520px;max-height:820px;display:flex;flex-direction:column;overflow:hidden}.chat-head{display:flex;align-items:center;gap:14px;padding-bottom:18px;border-bottom:1px solid var(--line2);flex:0 0 auto}.chat-stream{display:flex;flex:1 1 auto;flex-direction:column;gap:14px;min-height:0;overflow-y:auto;padding:22px 4px}.chat-message{max-width:78%;padding:14px 17px;border-radius:18px;line-height:1.55;white-space:pre-wrap}.chat-message.user{align-self:flex-end;background:linear-gradient(135deg,#187fff,#6544ff)}.chat-message.nina{align-self:flex-start;background:rgba(255,255,255,.07);border:1px solid var(--line)}.chat-message small{display:block;margin-top:7px;color:#bfd0ef}.chat-compose{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:end;gap:12px;flex:0 0 auto;margin-top:0;padding-top:16px;border-top:1px solid var(--line2);background:rgba(9,12,24,.96)}.chat-input{min-width:0}.chat-compose textarea{width:100%;min-width:0;min-height:72px;max-height:160px;resize:vertical;border:1px solid var(--line);border-radius:16px;background:rgba(5,9,20,.62);color:var(--text);padding:15px;font:inherit}.chat-compose .form-actions{margin:0;flex-wrap:nowrap}.chat-compose .btn{min-width:96px;min-height:48px}.voice-btn{min-width:52px!important;font-size:20px;cursor:pointer}.voice-btn[hidden]{display:none!important}.voice-btn.recording{background:#d83b58;border-color:#ff7890}.voice-status{min-height:18px;margin-top:6px;color:var(--muted);font-size:12px;font-weight:800}.voice-status[data-state=recording]{color:#ff9aad}.voice-status[data-state=processing]{color:#8fe7ff}.voice-status[data-state=error]{color:#ffb08f}.channel-card{display:flex;justify-content:space-between;gap:10px;padding:14px 0;border-bottom:1px solid var(--line2)}.channel-card:last-child{border-bottom:0}.channel-state{font-size:12px;font-weight:950;color:var(--green)}.channel-state.next{color:#ffd057}@media(max-width:1100px){.chat-layout{grid-template-columns:1fr}.chat-shell{height:min(720px,calc(100vh - 40px));min-height:500px}}@media(max-width:640px){.chat-message{max-width:92%}.chat-shell{height:auto;min-height:520px;max-height:none}.chat-stream{min-height:260px;max-height:48vh}.chat-compose{grid-template-columns:1fr}.chat-compose .form-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));flex-wrap:wrap}.chat-compose .btn{width:100%;min-width:0}}
:root{--line:rgba(120,153,255,.26);--line2:rgba(255,255,255,.08);--text:#f8fbff;--muted:#a8b7d4;--green:#34e6a4;--shadow:0 30px 100px rgba(0,0,0,.36)}*{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 13% 14%,rgba(30,105,255,.20),transparent 25%),radial-gradient(circle at 80% 12%,rgba(80,70,255,.20),transparent 28%),linear-gradient(135deg,#080910 0%,#0a0d19 48%,#05060b 100%)}body:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.026) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.021) 1px,transparent 1px);background-size:44px 44px;mask-image:linear-gradient(to bottom,rgba(0,0,0,.5),transparent 70%)}a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:210px 1fr;min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:22px 14px;background:radial-gradient(circle at 28px 28px,rgba(44,142,255,.24),transparent 75px),linear-gradient(180deg,rgba(18,22,37,.86),rgba(8,9,15,.83));border-right:1px solid var(--line2);backdrop-filter:blur(16px)}.brand{display:flex;align-items:center;gap:10px;margin:0 6px 28px;font-weight:950}.brand-word span:last-child{color:#2a91ff}
.nina-logo{position:relative;border-radius:50%;overflow:hidden;background:radial-gradient(circle at 30% 30%,rgba(255,255,255,.9),transparent 5%),radial-gradient(circle at 65% 25%,rgba(84,232,255,.9),transparent 10%),radial-gradient(circle at 50% 50%,#1de0ff 0%,#2358ff 38%,#7f45ff 72%,#11152a 100%);box-shadow:0 0 24px rgba(49,140,255,.52),inset 0 0 30px rgba(255,255,255,.12)}.nina-logo.small{width:34px;height:34px}.nina-logo.hero{width:156px;height:156px;flex:0 0 156px}.dot-grid{position:absolute;inset:0;background:radial-gradient(circle,rgba(255,255,255,.86) 0 2px,transparent 2.8px);background-size:16px 16px;transform:rotate(-18deg) scale(1.1);opacity:.58;mask-image:radial-gradient(circle,#000 62%,transparent 70%)}.orbit{position:absolute;left:-22%;right:-22%;top:44%;height:2px;background:rgba(255,255,255,.45);border-radius:999px;transform:rotate(-16deg);box-shadow:0 0 14px rgba(90,190,255,.8)}.orbit-b{transform:rotate(28deg);opacity:.28;top:54%}.nav{display:flex;flex-direction:column;gap:7px}.nav-item{display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:13px;color:#dce7ff;font-size:14px;border:1px solid transparent}.nav-item:hover{background:rgba(255,255,255,.06)}.nav-item.active{background:linear-gradient(90deg,rgba(28,128,255,.95),rgba(90,63,255,.86));color:#fff;box-shadow:0 14px 32px rgba(23,109,255,.23)}.new{margin-left:auto;font-size:10px;padding:2px 7px;border-radius:999px;background:#5638ff}.user{position:absolute;bottom:18px;left:14px;right:14px;border:1px solid var(--line);background:rgba(255,255,255,.045);border-radius:16px;padding:12px;color:var(--muted);font-size:13px}.user b{color:#fff}
 .main{padding:22px 26px 40px;max-width:1460px;width:100%;margin:0 auto}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.search{width:min(520px,55vw);border:1px solid var(--line);border-radius:18px;padding:14px 18px;color:var(--muted);background:rgba(16,24,45,.72);box-shadow:inset 0 0 0 1px rgba(255,255,255,.03),0 12px 34px rgba(0,0,0,.18)}.icons{display:flex;gap:10px;align-items:center}.icon{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10)}.avatar{background:linear-gradient(135deg,#7c43ff,#dc42ff);font-weight:950}.lang-switch{display:flex;gap:6px}.lang-switch a{font-size:12px;font-weight:950;padding:8px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.06);color:#dbe8ff}.lang-switch a.active{background:linear-gradient(90deg,#168dff,#6443ff);color:#fff}.grid{display:grid;gap:18px}.hero-grid{display:grid;grid-template-columns:1.02fr .98fr;gap:18px}.card{background:linear-gradient(180deg,rgba(26,36,68,.72),rgba(9,12,24,.70)),radial-gradient(circle at 25% 15%,rgba(40,140,255,.12),transparent 38%);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);backdrop-filter:blur(18px)}.card-pad{padding:24px}.hero-card{min-height:390px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}.hero-lockup{display:flex;align-items:center;justify-content:center;gap:26px}.hero-title{font-size:78px;line-height:.9;font-weight:1000;letter-spacing:-5px;text-shadow:0 10px 40px rgba(0,0,0,.5)}.hero-title span{color:#2493ff}.subtitle{color:#dbe8ff;font-weight:900;letter-spacing:2px;font-size:13px;margin-top:10px}.bigline{margin-top:34px;font-size:25px;line-height:1.35;font-weight:950}.trust{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:24px}.trust span{font-size:12px;font-weight:900;padding:7px 12px;border:1px solid var(--line);background:rgba(255,255,255,.04);border-radius:999px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi{display:block;padding:18px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.025));border-radius:18px;min-height:118px}.kpi small{color:#dbe7ff;font-weight:900}.kpi strong{display:block;font-size:38px;margin:9px 0 2px}.kpi em{color:#71e9ff;font-style:normal;font-size:13px;font-weight:900}.page-title h1{margin:0;font-size:42px;letter-spacing:-1.8px;line-height:1}.page-title p{margin:8px 0 0;color:#c3d4f5;font-weight:800}.section-title{font-size:21px;font-weight:1000;margin:6px 0 13px}.worker-grid{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:16px}.worker-card{overflow:hidden;border-radius:20px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(28,35,60,.78),rgba(9,12,24,.78));min-height:248px;box-shadow:0 20px 55px rgba(0,0,0,.22)}.worker-top{height:112px;display:grid;place-items:center;position:relative;overflow:hidden}.worker-top:before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(110deg,rgba(255,255,255,.10) 0 2px,transparent 2px 10px);opacity:.35}.tone-purple{background:linear-gradient(135deg,#4830d8,#6322b7)}.tone-blue{background:linear-gradient(135deg,#058aff,#053c8c)}.tone-green{background:linear-gradient(135deg,#02b973,#095a3b)}.tone-orange{background:linear-gradient(135deg,#d47418,#56321c)}.worker-avatar{position:relative;z-index:1;width:82px;height:82px;border-radius:50%;background:radial-gradient(circle at 36% 30%,#ffe8c8 0 16%,transparent 17%),radial-gradient(circle at 53% 65%,#ffdba8 0 23%,transparent 24%),radial-gradient(circle at 46% 45%,#ef973a 0 45%,#5d3928 46% 62%,#f6c58b 63% 100%);box-shadow:0 16px 34px rgba(0,0,0,.32)}.worker-body{padding:16px}.worker-body h3{margin:0 0 4px;font-size:20px;line-height:1.02}.muted{color:var(--muted)}.status{font-weight:950;font-size:12px;margin:10px 0}.active-dot{color:var(--green)}.idle-dot{color:#ffd057}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}.list{display:flex;flex-direction:column;gap:10px}.row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 15px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(90deg,rgba(28,111,255,.12),rgba(255,255,255,.035))}.row b{display:block;margin-bottom:4px}.pill{display:inline-flex;align-items:center;padding:7px 11px;border-radius:999px;background:rgba(31,124,255,.16);border:1px solid rgba(76,147,255,.32);color:#d7e8ff;font-size:12px;font-weight:950;white-space:nowrap}.btns{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}.btn{display:inline-flex;align-items:center;justify-content:center;padding:13px 18px;border-radius:14px;border:1px solid var(--line);font-weight:950;background:rgba(255,255,255,.055);box-shadow:0 12px 26px rgba(0,0,0,.18)}.btn.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.footer-note{margin-top:22px;color:var(--muted);font-size:13px;text-align:center;font-weight:700}.console-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.console-nav a{padding:10px 13px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.055);font-weight:950}.console-nav a.primary{background:linear-gradient(90deg,#168dff,#6443ff);border-color:transparent}.metric-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}.metric-mini{padding:13px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.045)}.metric-mini small{color:var(--muted);font-weight:900}.metric-mini b{display:block;font-size:24px;margin-top:4px}.panel-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}.stack-grid{display:grid;gap:12px}.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field label{font-size:12px;font-weight:950;color:#dbe7ff}.field input,.field select,.field textarea{width:100%;border:1px solid var(--line);border-radius:14px;background:rgba(5,9,20,.58);color:var(--text);padding:12px 13px;font:inherit;outline:none}.field textarea{min-height:92px;resize:vertical}.form-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.preview-box{border:1px solid var(--line);border-radius:18px;background:rgba(31,124,255,.10);padding:16px;margin-bottom:16px}.preview-box b{display:block;margin-bottom:6px}.safe-note{color:#8fe7ff;font-weight:800;font-size:13px;margin-top:10px}@media(max-width:1100px){.layout{grid-template-columns:1fr}.sidebar,.main{min-width:0}.sidebar{position:relative;height:auto}.user{position:static;margin-top:18px}.hero-grid,.two-col{grid-template-columns:1fr}.worker-grid{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}}@media(max-width:640px){.main{padding:16px}.topbar{gap:12px;flex-wrap:wrap}.search{order:2;width:100%}.icons{max-width:100%;flex-wrap:wrap}.worker-grid,.kpis{grid-template-columns:1fr}.hero-lockup{flex-direction:column}.hero-title{font-size:56px;letter-spacing:-3px}.nina-logo.hero{width:128px;height:128px;flex-basis:128px}}

.channels-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.connection-card{display:flex;flex-direction:column;gap:14px;min-height:260px}.connection-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.connection-head h2{margin:0}.connection-status{padding:7px 11px;border-radius:999px;font-size:12px;font-weight:950;background:rgba(255,255,255,.07);border:1px solid var(--line)}.connection-status.connected,.connection-status.active{color:var(--green)}.connection-status.pending{color:#ffd057}.connection-status.error{color:#ff9aad}.connection-actions{margin-top:auto}.connection-actions form{display:inline-block;margin:0 8px 8px 0}.connection-actions button{cursor:pointer;color:var(--text)}.channel-form{display:grid;gap:12px}.channel-form input{width:100%;border:1px solid var(--line);border-radius:14px;background:rgba(5,9,20,.58);color:var(--text);padding:12px 13px;font:inherit}.channel-message{padding:12px 14px;border-radius:14px;background:rgba(31,124,255,.12);color:#d9eaff;font-weight:800}@media(max-width:640px){.channels-grid{grid-template-columns:1fr}.connection-card{min-height:0}body.channels .sidebar{padding-bottom:14px}body.channels .brand{margin-bottom:14px}body.channels .nav{flex-direction:row;overflow-x:auto;padding-bottom:6px}body.channels .nav-item{flex:0 0 auto}body.channels .user{display:none}}
"""


def page(title, body, active="dashboard"):
    lang = current_language()
    channels_label = {"en": "Channels", "lv": "Kanāli", "ru": "Каналы"}[lang]
    nav = [
        ("nina", tx("talk_to_nina", lang), "/nina", "N"),
        ("channels", channels_label, "/channels", "◉"),
        ("dashboard", tx("dashboard", lang), "/dashboard", "⌂"),
        ("inbox", tx("inbox", lang), "/inbox", "✦"),
        ("workers", tx("workers", lang), "/workers", "♙"),
        ("tasks", tx("tasks", lang), "/tasks", "☑"),
        ("clients", tx("clients", lang), "/clients", "●"),
        ("projects", tx("projects", lang), "/projects", "▣"),
        ("calendar", tx("calendar", lang), "/calendar", "◫"),
        ("files", tx("files", lang), "/files", "▤"),
        ("analytics", tx("analytics", lang), "/analytics", "⌁"),
        ("exchange", tx("exchange", lang), "/exchange", "◎"),
    ]
    nav_html = ""
    for key, label, href, icon in nav:
        cls = "nav-item active" if key == active else "nav-item"
        badge = "<span class='new'>NEW</span>" if key == "exchange" else ""
        nav_html += f"<a class='{cls}' href='{href}?lang={lang}'><span>{icon}</span><b>{label}</b>{badge}</a>"
    def lang_link(l):
        cls = "active" if lang == l else ""
        return f'<a class="{cls}" href="?lang={l}">{l.upper()}</a>'
    customer_page = active in {"nina", "channels"}
    user_status = "<span class='pill'>Web active</span>" if customer_page else "<span class='pill'>Runtime: web_app.py</span>"
    footer = "NinaOS" if customer_page else f"{WEB_APP_VERSION} · Web service separate from Telegram app.py"
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)} · NinaOS</title><style>{css()}</style></head><body><div class="layout"><aside class="sidebar"><a href="/dashboard?lang={lang}" class="brand">{nina_logo_html("small")}<div class="brand-word"><span>Nina</span><span>OS</span></div></a><nav class="nav">{nav_html}</nav><div class="user"><b>Katrin</b><br>Owner<br><br>{user_status}</div></aside><main class="main"><div class="topbar"><div class="search">{tx("search", lang)}</div><div class="icons"><div class="icon">🔔</div><div class="icon">🌐</div><div class="lang-switch">{lang_link("en")}{lang_link("lv")}{lang_link("ru")}</div><div class="icon">☼</div><div class="icon avatar">K</div></div></div>{body}<div class="footer-note">{footer}</div></main></div></body></html>"""


def kpi_card(label, value, hint):
    return f"<a class='kpi' href='{hint.get('href', '#')}?lang={current_language()}'><small>{label}</small><strong>{value}</strong><em>{hint.get('text','Live data')}</em></a>"


def worker_card(w, marketplace=False):
    if marketplace:
        extra = f"<div class='status'>★ 4.8 · {html_escape(w.get('category',''))}</div><b>{html_escape(w.get('price',''))}</b><br><br><span class='btn'>{tx('view_details')}</span>"
    else:
        dot = "active-dot" if w["status"] == "ACTIVE" else "idle-dot"
        extra = f"<div class='status'><span class='{dot}'>●</span> {html_escape(w['status'])}</div><b>{html_escape(w['detail'])}</b>"
    return f"<a class='worker-card' href='{w.get('route','/workers')}?lang={current_language()}'><div class='worker-top tone-{w.get('tone','blue')}'><div class='worker-avatar'></div></div><div class='worker-body'><h3>{html_escape(w['name'])}</h3><div class='muted'>{html_escape(w['role'])}</div>{extra}</div></a>"


def activity_row(a):
    return f"<div class='row'><div><b>{html_escape(a.get('title'))}</b><span class='muted'>{html_escape(a.get('body'))}</span></div><span class='pill'>{html_escape(a.get('kind','info'))}</span></div>"


def nina_chat_body(messages):
    lang = current_language()
    copy = {
        "en": {"title": "Talk to Nina", "sub": "Ask a question, plan work, or tell Nina what needs attention.", "empty": "Start a conversation with Nina.", "placeholder": "Write a message...", "send": "Send", "channels": "Channels", "active": "Active", "connected": "Connected", "connect": "Connect", "next": "Coming next", "ready": "Ready", "recording": "Recording", "processing": "Processing", "error": "Voice input could not be processed.", "denied": "Microphone permission was denied.", "unsupported": "Voice recording is not supported in this browser.", "stop": "Stop", "cancel": "Cancel", "mic": "Start voice input"},
        "lv": {"title": "Runā ar Ninu", "sub": "Uzdod jautājumu, plāno darbu vai pasaki, kam jāpievērš uzmanība.", "empty": "Sāc sarunu ar Ninu.", "placeholder": "Raksti ziņu...", "send": "Sūtīt", "channels": "Kanāli", "active": "Aktīvs", "connected": "Savienots", "connect": "Savienot", "next": "Drīzumā", "ready": "Gatavs", "recording": "Ieraksta", "processing": "Apstrādā", "error": "Balss ziņu neizdevās apstrādāt.", "denied": "Mikrofona atļauja tika liegta.", "unsupported": "Šī pārlūkprogramma neatbalsta balss ierakstu.", "stop": "Apturēt", "cancel": "Atcelt", "mic": "Sākt balss ievadi"},
        "ru": {"title": "Поговорить с Ниной", "sub": "Задайте вопрос, спланируйте работу или расскажите, что требует внимания.", "empty": "Начните разговор с Ниной.", "placeholder": "Напишите сообщение...", "send": "Отправить", "channels": "Каналы", "active": "Активен", "connected": "Подключён", "connect": "Подключить", "next": "Скоро", "ready": "Готово", "recording": "Запись", "processing": "Обработка", "error": "Не удалось обработать голосовое сообщение.", "denied": "Доступ к микрофону запрещён.", "unsupported": "Этот браузер не поддерживает запись голоса.", "stop": "Стоп", "cancel": "Отмена", "mic": "Начать голосовой ввод"},
    }[lang]
    bubbles = ""
    for message in messages:
        role = "user" if message.get("role") == "user" else "nina"
        label = "You" if role == "user" and lang == "en" else ("Tu" if role == "user" else "Nina")
        bubbles += f"<div class='chat-message {role}'>{html_escape(message.get('text'))}<small>{label}</small></div>"
    if not bubbles:
        bubbles = f"<div class='chat-message nina'>{html_escape(copy['empty'])}<small>Nina</small></div>"

    telegram_connection = get_connection(NINA_WEB_WORKSPACE_ID, "telegram")
    telegram_state = copy["connected"] if telegram_connection["status"] == "connected" else copy["connect"]
    channels = (
        f"<div class='channel-card'><div><b>Web</b></div><span class='channel-state'>{copy['active']}</span></div>"
        f"<div class='channel-card'><div><b>Telegram</b></div><span class='channel-state'>{telegram_state}</span></div>"
        f"<div class='channel-card'><div><b>WhatsApp</b><span class='muted'>{copy['next']}</span></div><span class='channel-state next'>{copy['connect']}</span></div>"
        f"<div class='channel-card'><div><b>Email</b><span class='muted'>{copy['next']}</span></div><span class='channel-state next'>{copy['connect']}</span></div>"
    )
    return (
        "<div class='chat-layout'>"
        "<section class='card card-pad chat-shell'>"
        f"<div class='chat-head'>{nina_logo_html('small')}<div><div class='section-title' style='margin:0'>{copy['title']}</div><span class='muted'>{copy['sub']}</span></div></div>"
        f"<div class='chat-stream'>{bubbles}</div>"
        f"<form class='chat-compose' method='post' action='/nina?lang={lang}'>"
        f"<div class='chat-input'><textarea name='message' maxlength='4000' required placeholder='{copy['placeholder']}'></textarea>"
        f"<div id='voice-status' class='voice-status' data-state='ready' role='status' aria-live='polite'>{copy['ready']}</div></div>"
        f"<div class='form-actions'><button id='voice-start' class='btn voice-btn' type='button' aria-label='{copy['mic']}' title='{copy['mic']}'>🎤</button>"
        f"<button id='voice-stop' class='btn voice-btn recording' type='button' hidden>{copy['stop']}</button>"
        f"<button id='voice-cancel' class='btn voice-btn' type='button' hidden>{copy['cancel']}</button>"
        f"<button id='chat-send' class='btn primary' type='submit'>{copy['send']}</button></div></form>"
        "</section>"
        f"<aside class='card card-pad'><div class='section-title'>{copy['channels']}</div>{channels}<div class='form-actions'><a class='btn' href='/channels?lang={lang}'>{copy['channels']}</a></div></aside>"
        "</div>"
        f"<script>window.NinaVoiceConfig={json.dumps({'lang': lang, 'ready': copy['ready'], 'recording': copy['recording'], 'processing': copy['processing'], 'error': copy['error'], 'denied': copy['denied'], 'unsupported': copy['unsupported']}, ensure_ascii=False)};</script>"
        "<script>(function(){const c=window.NinaVoiceConfig,s=document.getElementById('voice-status'),start=document.getElementById('voice-start'),stop=document.getElementById('voice-stop'),cancel=document.getElementById('voice-cancel'),send=document.getElementById('chat-send');let recorder=null,stream=null,chunks=[],cancelled=false;function state(name,text){s.dataset.state=name;s.textContent=text;}function tracksOff(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}}function controls(active){start.hidden=active;stop.hidden=!active;cancel.hidden=!active;send.disabled=active;}function reset(){tracksOff();controls(false);recorder=null;chunks=[];cancelled=false;state('ready',c.ready);}async function upload(blob){state('processing',c.processing);controls(false);start.disabled=true;send.disabled=true;const data=new FormData();const ext=blob.type.includes('mp4')?'m4a':blob.type.includes('ogg')?'ogg':blob.type.includes('mpeg')?'mp3':'webm';data.append('audio',blob,'voice.'+ext);data.append('lang',c.lang);try{const response=await fetch('/nina/voice?lang='+encodeURIComponent(c.lang),{method:'POST',body:data,credentials:'same-origin'});if(!response.ok)throw new Error('upload');window.location.href='/nina?lang='+encodeURIComponent(c.lang);}catch(e){state('error',c.error);start.disabled=false;send.disabled=false;}}start.addEventListener('click',async function(){if(!navigator.mediaDevices||!window.MediaRecorder){state('error',c.unsupported);return;}try{stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});chunks=[];cancelled=false;const preferred=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4','audio/webm','audio/ogg'].find(t=>MediaRecorder.isTypeSupported(t));const options={audioBitsPerSecond:128000};if(preferred)options.mimeType=preferred;recorder=new MediaRecorder(stream,options);recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data);};recorder.onerror=()=>{tracksOff();controls(false);state('error',c.error);};recorder.onstop=()=>{tracksOff();controls(false);if(cancelled){reset();return;}const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});if(!blob.size){state('error',c.error);return;}upload(blob);};recorder.start();controls(true);state('recording',c.recording);}catch(e){tracksOff();controls(false);state('error',e&&e.name==='NotAllowedError'?c.denied:c.error);}});stop.addEventListener('click',()=>{if(recorder&&recorder.state!=='inactive')recorder.stop();});cancel.addEventListener('click',()=>{cancelled=true;if(recorder&&recorder.state!=='inactive')recorder.stop();else reset();});})();</script>"
    )


def dashboard_body(data):
    lang = current_language()
    c = data["counts"]
    one_nina_surface = one_nina_work_surface_html(limit=6)
    kpis = (
        "<div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), c["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), c["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), c["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div>"
    )
    workers = "".join(worker_card(w) for w in data["workers"])
    activity = "".join(activity_row(a) for a in data["activity"][:6])
    snapshot_kpis = (
        kpi_card(tx("clients", lang), c["clients"], {"text": tx("crm", lang), "href": "/clients"})
        + kpi_card(tx("workers", lang), c["workers"], {"text": tx("ai_workforce", lang), "href": "/workers"})
        + kpi_card(tx("estimates", lang), c["estimates"], {"text": tx("in_progress", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), c["invoices"], {"text": tx("due_sent", lang), "href": "/clients"})
    )
    return one_nina_surface + f"<div class='grid'><div class='hero-grid'><section class='card card-pad hero-card'><div class='hero-lockup'>{nina_logo_html('hero')}<div><div class='hero-title'>Nina<span>OS</span></div><div class='subtitle'>AI WORKFORCE OPERATING SYSTEM</div></div></div><div class='bigline'>{tx('hero_line', lang)}</div><br><div class='btns'><a class='btn primary' href='{q('/inbox')}'>{tx('channel_hub', lang)}</a><a class='btn' href='{q('/tasks')}'>{tx('open_work', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div><div class='trust'><span>GLOBAL</span><span>WORKFORCE</span><span>SECURE</span><span>SCALE</span></div></section><section class='card card-pad'><div class='page-title'><h1>{tx('good_morning', lang)}</h1><p>{tx('workspace_today', lang)}</p></div><br>{kpis}<br><div class='card card-pad' style='background:rgba(27,84,255,.16)'><div class='section-title'>{tx('global', lang)}</div><p class='muted'>{tx('connected', lang)}</p><a class='btn' href='{q('/exchange')}'>{tx('view_global', lang)}</a></div></section></div><section><div class='section-title'>{tx('your_workers', lang)}</div><div class='worker-grid'>{workers}</div></section><div class='two-col'><section class='card card-pad'><div class='section-title'>{tx('recent', lang)}</div><div class='list'>{activity}</div></section><section class='card card-pad'><div class='section-title'>{tx('snapshot', lang)}</div><div class='kpis'>{snapshot_kpis}</div><br><div class='btns'><a class='btn primary' href='{q('/tasks')}'>{tx('tasks', lang)}</a><a class='btn' href='{q('/clients')}'>{tx('clients', lang)}</a><a class='btn' href='{q('/projects')}'>{tx('projects', lang)}</a><a class='btn' href='{q('/workers')}'>{tx('workers', lang)}</a></div></section></div></div>"


def work_page_header(title, subtitle):
    return f"<div class='grid'><section class='card card-pad'><div class='page-title'><h1>{html_escape(title)}</h1><p>{html_escape(subtitle)}</p></div><br><div class='btns'><a class='btn primary' href='{q('/dashboard')}'>{tx('dashboard')}</a><a class='btn' href='{q('/tasks')}'>{tx('tasks')}</a><a class='btn' href='{q('/clients')}'>{tx('clients')}</a><a class='btn' href='{q('/outbox')}'>Outbox</a><a class='btn' href='{q('/workers')}'>{tx('workers')}</a><a class='btn' href='{q('/exchange')}'>{tx('exchange')}</a></div></section></div><br>"

def object_source_label(obj, lang=None):
    lang = lang or current_language()
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    source = meta.get("source") or "workspace"
    if source in ["web_action_preview", "web_preview", "web_voice_intake_preview"]:
        return tx("source_preview", lang)
    if source == "telegram_intake_sync":
        return "Telegram sync"
    if source == "existing_task_memory":
        return "Existing task memory" if lang == "en" else ("Esošā task atmiņa" if lang == "lv" else "Память задач")
    if source == "existing_conversation_state":
        return "Existing voice/photo memory" if lang == "en" else ("Esošā balss/foto atmiņa" if lang == "lv" else "Память голоса/фото")
    if source == "real_intake_store":
        return "Real intake store" if lang == "en" else ("Intake store" if lang == "lv" else "Intake store")
    if source == "approved_thread_workspace_object":
        return "Workspace object" if lang == "en" else ("Darba objekts" if lang == "lv" else "Рабочий объект")
    if source == "database":
        return tx("source_database", lang)
    if source == "demo":
        return tx("source_demo", lang)
    return tx("source_workspace", lang)


def work_object_rows(items, empty_text=None, limit=None, show_source=True, show_approval=True):
    lang = current_language()
    if limit:
        items = items[:limit]
    if not items:
        label = empty_text or tx("no_items", lang)
        return f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>—</span></div><span class='pill'>idle</span></div>"
    rows = ""
    for obj in items:
        meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
        client = meta.get("client_name") or obj.get("client_id") or "Workspace"
        source = object_source_label(obj, lang)
        badges = meta.get("source_badges") or []
        if isinstance(badges, str):
            badges = [badges]
        badge_suffix = ""
        if badges:
            badge_suffix = " · " + html_escape(" + ".join(str(b) for b in badges[:4] if b))
        source_part = f" · {html_escape(source)}{badge_suffix}" if show_source else ""
        approval_state = meta.get("approval_state") or ("pending_approval" if is_preview_object(obj) else "")
        approval_part = f" · {html_escape(approval_label_from_state(approval_state, lang))}" if show_approval and is_preview_object(obj) else ""
        badge = f"{html_escape(obj.get('status'))} · {html_escape(obj.get('priority', 'normal'))}{approval_part}"
        rows += (
            "<div class='row'><div>"
            f"<b>{html_escape(obj.get('title'))}</b>"
            f"<span class='muted'>{html_escape(client)} · {html_escape(obj.get('object_type'))}{source_part}</span>"
            f"{preview_approval_controls(obj)}"
            "</div>"
            f"<span class='pill'>{badge}</span></div>"
        )
    return rows


def tasks_body(data):
    lang = current_language()
    return (
        work_page_header(
            tx("tasks"),
            "V51.4 PRODUCTION CLEANUP — one canonical persistent work truth; demo seed objects hidden from active product work.",
        )
        + one_nina_work_surface_html(limit=100)
        + "<section class='card card-pad'>"
          "<div class='section-title'>ONE NINA Work Rule</div>"
          "<div class='list'>"
          "<div class='row'><div><b>One work object</b>"
          "<span class='muted'>Telegram, Web and future channels read the same nina_work_objects record.</span>"
          "</div><span class='pill'>active</span></div>"
          "<div class='row'><div><b>Legacy data preserved</b>"
          "<span class='muted'>memory_backups and conversation_state remain available for migration and history; they are not deleted.</span>"
          "</div><span class='pill'>safe</span></div>"
          "<div class='row'><div><b>No second work brain in Web</b>"
          "<span class='muted'>Tasks no longer renders legacy thread inference, preview queues or workspace snapshots as parallel work truth.</span>"
          "</div><span class='pill'>ONE NINA</span></div>"
          "<div class='row'><div><b>Production work only</b>"
          "<span class='muted'>Demo seed objects stay preserved in persistence but are hidden from active Dashboard and Tasks work surfaces.</span>"
          "</div><span class='pill'>clean</span></div>"
          "</div>"
          "</section>"
    )

def clients_body(data):
    lang = current_language()
    canonical_rows = one_nina_client_rows(
        empty_text=tx("no_items", lang)
    )
    profiles = one_nina_client_work_map()
    total_objects = sum(len(profile["objects"]) for profile in profiles.values())
    telegram_clients = sum(
        1 for profile in profiles.values()
        if "telegram" in {str(ch).lower() for ch in profile["channels"]}
    )

    kpis = (
        "<div class='kpis'>"
        + kpi_card("Canonical clients", len(profiles), {"text": "ONE NINA", "href": "/clients"})
        + kpi_card("Linked work", total_objects, {"text": "same work objects", "href": "/tasks"})
        + kpi_card("Telegram-linked", telegram_clients, {"text": "shared context", "href": "/clients"})
        + kpi_card("Work truth", "1", {"text": "nina_work_objects", "href": "/tasks"})
        + "</div>"
    )

    return (
        work_page_header(
            tx("clients"),
            "V51.6 ONE NINA — clients render canonical business details from the same persistent Work Objects.",
        )
        + "<section class='card card-pad'>"
          "<div class='section-title'>ONE NINA Canonical Clients</div>"
          f"{kpis}<br>"
          f"<div class='list'>{canonical_rows}</div>"
          "<div class='safe-note'>"
          "V51.6: client profiles are grouped directly from client_id on nina_work_objects and render shared metadata.business_details. "
          "No web client-work copy, preview object or second work truth is created. "
          "Legacy memory remains preserved for migration/history."
          "</div>"
          "</section><br>"
        + "<section class='card card-pad'>"
          "<div class='section-title'>ONE NINA Client Rule</div>"
          "<div class='list'>"
          "<div class='row'><div><b>One client context</b>"
          "<span class='muted'>The same canonical work object appears in Tasks and in the linked client profile.</span>"
          "</div><span class='pill'>active</span></div>"
          "<div class='row'><div><b>No duplicated client work</b>"
          "<span class='muted'>Clients does not rebuild Telegram memory into a second workspace object.</span>"
          "</div><span class='pill'>ONE NINA</span></div>"
          "</div>"
          "</section>"
    )

def projects_body(data):
    items = data["projects"] or [{"title":"Demo active project", "status":"active", "priority":"normal", "metadata":{"client_name":"Demo Client"}}]
    rows = ""
    for p in items:
        meta = p.get("metadata", {}) if isinstance(p.get("metadata"), dict) else {}
        rows += f"<div class='row'><div><b>{html_escape(p.get('title'))}</b><span class='muted'>{html_escape(meta.get('client_name','Workspace'))}</span></div><span class='pill'>{html_escape(p.get('status'))} · {html_escape(p.get('priority','normal'))}</span></div>"
    return work_page_header(tx("projects"), tx("projects_sub")) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"


def workers_body(data):
    lang = current_language()
    cards = ''.join(worker_card(w) for w in data['workers'])
    top = work_page_header(tx("workers"), tx("workers_sub"))
    top += f"<section class='card card-pad'><div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'><a class='btn primary' href='{q('/workers/office-manager')}'>{tx('open_office_manager', lang)}</a><a class='btn' href='{q('/exchange')}'>{tx('explore', lang)}</a></div></section><br>"
    return top + f"<div class='worker-grid'>{cards}</div>"


def exchange_body(data):
    catalog = [
        {"name": "Nina Sales", "role": "AI Sales Executive", "price": "€99/month", "category": "Sales & Growth", "tone": "purple"},
        {"name": "Nina Estimator", "role": "AI Estimator", "price": "€119/month", "category": "Construction", "tone": "blue"},
        {"name": "Nina Office Manager", "role": "AI Office Manager", "price": "€89/month", "category": "Operations", "tone": "green"},
        {"name": "Nina Support", "role": "AI Support Specialist", "price": "€79/month", "category": "Support", "tone": "orange"},
        {"name": "Nina Marketing", "role": "AI Marketing Specialist", "price": "€99/month", "category": "Marketing", "tone": "purple"},
        {"name": "Nina HR", "role": "AI HR Assistant", "price": "€89/month", "category": "HR", "tone": "orange"},
    ]
    return work_page_header(tx("exchange"), tx("exchange_sub")) + f"<div class='worker-grid'>{''.join(worker_card(w, marketplace=True) for w in catalog)}</div>"



def channel_card(title, body, status, icon="●"):
    return (
        "<div class='card card-pad'>"
        f"<div class='section-title'>{icon} {html_escape(title)}</div>"
        f"<p class='muted'>{html_escape(body)}</p>"
        f"<span class='pill'>{html_escape(status)}</span>"
        "</div>"
    )



def detect_voice_intake_action(voice_text, source_channel="voice", priority="normal"):
    text = (voice_text or "").strip()
    low = text.lower()

    if any(w in low for w in ["tāme", "tame", "tami", "estimate", "quote", "offer", "piedāvāj", "piedavaj"]):
        form_type = "estimate"
    elif any(w in low for w in ["rēķin", "rekin", "rekins", "invoice", "bill"]):
        form_type = "invoice"
    elif any(w in low for w in ["piezvan", "atgādin", "atgadin", "follow", "sazin", "pajaut", "uzrakst", "atsūti", "atsuti"]):
        form_type = "followup"
    else:
        form_type = "new_task"

    client_name = ""
    # Simple V44.1 FIX extraction: enough for safe preview; real CRM extraction comes later.
    for name in ["andris", "jānis", "janis", "marija", "katrin", "klients", "client"]:
        if name in low:
            client_name = "Klients" if name in ["klients", "client"] else name[:1].upper() + name[1:]
            break

    title = text[:140] if text else "Inbox intake work"
    if form_type == "estimate" and "tāme" not in low and "estimate" not in low:
        title = "Prepare estimate from inbox intake"
    elif form_type == "invoice":
        title = "Prepare invoice/admin record from inbox intake"
    elif form_type == "followup":
        title = "Follow up from inbox intake"

    return {
        "form_type": form_type,
        "task_title": title,
        "client_name": client_name,
        "project_name": "",
        "amount": "",
        "due_date": "",
        "priority": priority or "normal",
        "notes": f"Omnichannel intake from {source_channel}: {text}",
    }

def get_voice_intake_preview():
    global LAST_VOICE_INTAKE_PREVIEW
    if request.method != "POST":
        return None
    voice_text = (request.form.get("voice_text", "") or "").strip()
    source_channel = request.form.get("source_channel", "voice")
    priority = request.form.get("priority", "normal")
    # V44.1 POST FIX: browsers show placeholder text but do not submit it.
    # For the current safe preview sprint, an empty submit creates a demo intake preview
    # instead of silently returning to "No items yet".
    if not voice_text:
        voice_text = (request.form.get("fallback_voice_text", "") or "").strip()
    if not voice_text:
        voice_text = "Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp"

    action = detect_voice_intake_action(voice_text, source_channel, priority)
    obj = normalize_action_to_work_object(action)
    meta = obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {}
    meta["source"] = "web_voice_intake_preview"
    meta["source_channel"] = source_channel
    meta["voice_text"] = voice_text.strip()
    meta["intake_kind"] = "omnichannel_voice_text"
    meta["document_intake"] = True
    meta["storage_target"] = "NinaOS client workspace"
    meta["send_back_channels"] = "WhatsApp / Telegram / Email"
    meta["approval_state"] = "pending_approval"
    obj["metadata"] = meta
    obj["object_id"] = obj.get("object_id", "web_preview_voice") .replace("web_preview_", "web_voice_preview_", 1)

    WORKSPACE_ACTION_PREVIEWS.insert(0, obj)
    del WORKSPACE_ACTION_PREVIEWS[25:]
    LAST_VOICE_INTAKE_PREVIEW = obj
    return obj

def voice_intake_form_html(created_obj=None):
    lang = current_language()
    source_options = ["voice", "WhatsApp", "Telegram", "Email", "Files", "Web"]
    options = "".join(f"<option value='{html_escape(x)}'>{html_escape(x)}</option>" for x in source_options)
    created = ""
    if created_obj:
        meta = created_obj.get("metadata", {}) if isinstance(created_obj.get("metadata"), dict) else {}
        created = (
            "<div class='preview-box'>"
            f"<b>{tx('voice_preview_created', lang)}</b>"
            "<div class='list'>"
            f"<div class='row'><div><b>{html_escape(created_obj.get('title'))}</b><span class='muted'>{html_escape(created_obj.get('object_type'))} · {html_escape(meta.get('source_channel','voice'))}</span></div><span class='pill'>{tx('pending_preview', lang)}</span></div>"
            f"<div class='row'><div><b>{tx('detected_intent', lang)}</b><span class='muted'>{html_escape(created_obj.get('object_type'))}</span></div><span class='pill'>V44.1</span></div>"
            "</div>"
            f"<div class='safe-note'>{tx('voice_safe_note', lang)}</div>"
            "</div>"
        )
    return f"""
    <section class='card card-pad'>
      <div class='section-title'>🎙 {tx('voice_intake_form', lang)}</div>
      <p class='muted'>{tx('voice_intake_hint', lang)}</p>
      {created}
      <form method='post' action='/inbox?lang={lang}'>
        <div class='form-grid'>
          <div class='field'>
            <label>{tx('source_channel', lang)}</label>
            <select name='source_channel'>{options}</select>
          </div>
          <div class='field'>
            <label>{tx('priority', lang)}</label>
            <select name='priority'><option value='normal'>{tx('normal', lang)}</option><option value='high'>{tx('high', lang)}</option></select>
          </div>
        </div>
        <br>
        <div class='field'>
          <label>{tx('voice_text', lang)}</label>
          <textarea name='voice_text' placeholder='Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp...'></textarea><input type='hidden' name='fallback_voice_text' value='Nina, man vajag sagatavot tāmi klientam par vannas istabas remontu un atsūtīt WhatsApp'>
        </div>
        <div class='form-actions'>
          <button class='btn primary' type='submit'>{tx('nina_prepare', lang)}</button>
          <a class='btn' href='{q('/office-manager/actions')}'>{tx('approval_required', lang)}</a>
        </div>
        <div class='safe-note'>{tx('voice_safe_note', lang)}</div>
      </form>
    </section>
    """



# =========================
# V45.3
# =========================

def mask_db_url(url):
    """Show only safe DB connection signal, never expose credentials."""
    url = str(url or "")
    if not url:
        return "missing"
    try:
        if "@" in url:
            prefix, rest = url.split("@", 1)
            scheme = prefix.split(":", 1)[0] if ":" in prefix else "db"
            host = rest.split("/", 1)[0]
            return f"{scheme}://***@{host}/***"
        return url[:18] + "..." if len(url) > 18 else "configured"
    except Exception:
        return "configured"


def _diag_table_exists(cur, table_name):
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table_name,))
        row = cur.fetchone()
        return bool(row[0]) if row else False
    except Exception:
        return False


def _diag_count(cur, sql, params=()):
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception as e:
        return f"error: {str(e)[:160]}"


def _diag_latest_rows(cur, sql, params=(), limit=5):
    try:
        cur.execute(sql, params)
        rows = cur.fetchall() or []
        names = [d[0] for d in cur.description]
        out = []
        for r in rows[:limit]:
            item = {}
            for name, value in zip(names, r):
                text = str(value or "")
                if len(text) > 220:
                    text = text[:220] + "…"
                item[name] = text
            out.append(item)
        return out
    except Exception as e:
        return [{"error": str(e)[:220]}]


def telegram_bridge_db_diagnostics():
    """Visible read-only diagnostics for the Telegram → Web sync bridge."""
    info = db_url_info()
    database_url = info.get("url") or ""
    diag = {
        "version": WEB_APP_VERSION,
        "database_url_present": bool(database_url),
        "database_url_source": info.get("source") or "",
        "database_url_safe": info.get("safe") or "missing",
        "database_url_candidates_found": info.get("found") or [],
        "relevant_env_keys": info.get("relevant_env_keys") or [],
        "postgres_driver": "unknown",
        "db_connect_ok": False,
        "db_error": "",
        "tables": {},
        "counts": {},
        "latest": {},
        "web_reader_counts": {},
        "note": "V47.1 diagnostic. Web reads Telegram memory and writes safe workspace-object snapshots to memory_backups.",
    }

    try:
        import psycopg2
        diag["postgres_driver"] = "psycopg2 available"
    except Exception as e:
        diag["postgres_driver"] = "psycopg2 missing"
        diag["db_error"] = str(e)[:220]
        return diag

    if not database_url:
        diag["db_error"] = "No usable Postgres URL found in Web service env. Checked DATABASE_URL, POSTGRES_URL and Railway/Postgres variants."
        return diag

    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        diag["db_connect_ok"] = True

        for table in ["conversation_state", "memory_backups", "tasks", "intake_events"]:
            diag["tables"][table] = _diag_table_exists(cur, table)

        if diag["tables"].get("conversation_state"):
            diag["counts"]["conversation_state_total"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state")
            diag["counts"]["conversation_state_voice"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE user_text LIKE %s OR intent = %s OR topic = %s", ("[VOICE]%", "voice_transcript", "voice"))
            diag["counts"]["conversation_state_photo"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE user_text LIKE %s OR intent = %s OR topic = %s", ("[PHOTO]%", "photo", "vision"))
            diag["counts"]["conversation_state_recent_text"] = _diag_count(cur, "SELECT COUNT(*) FROM conversation_state WHERE COALESCE(user_text,'') <> ''")
            diag["latest"]["conversation_state"] = _diag_latest_rows(cur, """
                SELECT id, user_id, user_text, intent, topic, created_at
                FROM conversation_state
                ORDER BY id DESC
                LIMIT 5
            """)
        else:
            diag["counts"]["conversation_state_total"] = "table missing"

        if diag["tables"].get("memory_backups"):
            diag["counts"]["memory_backups_total"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups")
            diag["counts"]["memory_backups_task_engine"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("task_engine",))
            diag["counts"]["memory_backups_thread_approval_state"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("web_thread_approval_state",))
            diag["counts"]["memory_backups_workspace_object"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("web_workspace_object",))
            diag["counts"]["memory_backups_sendback_draft"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("web_sendback_draft",))
            diag["counts"]["memory_backups_sendback_review_state"] = _diag_count(cur, "SELECT COUNT(*) FROM memory_backups WHERE source = %s", ("web_sendback_review_state",))
            diag["latest"]["memory_backups_task_engine"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("task_engine",))
            diag["latest"]["memory_backups_any"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                ORDER BY id DESC
                LIMIT 5
            """)
            diag["latest"]["memory_backups_thread_approval_state"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("web_thread_approval_state",))
            diag["latest"]["memory_backups_workspace_object"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("web_workspace_object",))
            diag["latest"]["memory_backups_sendback_draft"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("web_sendback_draft",))
            diag["latest"]["memory_backups_sendback_review_state"] = _diag_latest_rows(cur, """
                SELECT id, user_id, source, backup_text, created_at
                FROM memory_backups
                WHERE source = %s
                ORDER BY id DESC
                LIMIT 5
            """, ("web_sendback_review_state",))
        else:
            diag["counts"]["memory_backups_total"] = "table missing"

        if diag["tables"].get("tasks"):
            diag["counts"]["tasks_total"] = _diag_count(cur, "SELECT COUNT(*) FROM tasks")
            diag["latest"]["tasks"] = _diag_latest_rows(cur, "SELECT * FROM tasks ORDER BY id DESC LIMIT 5")
        else:
            diag["counts"]["tasks_total"] = "table missing"

        if diag["tables"].get("intake_events"):
            diag["counts"]["intake_events_total"] = _diag_count(cur, "SELECT COUNT(*) FROM intake_events")
            diag["latest"]["intake_events"] = _diag_latest_rows(cur, "SELECT * FROM intake_events ORDER BY id DESC LIMIT 5")
        else:
            diag["counts"]["intake_events_total"] = "table missing"

        cur.close()
        conn.close()
    except Exception as e:
        diag["db_error"] = str(e)[:500]
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    # These are the actual web reader outputs, so we can compare DB truth vs UI reader.
    try:
        diag["web_reader_counts"]["task_engine_memory_reader"] = len(load_existing_task_engine_memory_from_db())
    except Exception as e:
        diag["web_reader_counts"]["task_engine_memory_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["voice_photo_reader"] = len(load_existing_voice_photo_state_from_db())
    except Exception as e:
        diag["web_reader_counts"]["voice_photo_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["recent_conversation_reader"] = len(load_recent_conversation_state_from_db())
    except Exception as e:
        diag["web_reader_counts"]["recent_conversation_reader"] = "error: " + str(e)[:160]
    try:
        diag["web_reader_counts"]["tasks_table_reader"] = len(load_existing_tasks_table_from_db())
    except Exception as e:
        diag["web_reader_counts"]["tasks_table_reader"] = "error: " + str(e)[:160]
    try:
        unified_items = load_existing_telegram_intake_sync()
        diag["web_reader_counts"]["merged_telegram_intake_sync"] = len(unified_items)
        diag["web_reader_counts"]["unified_dedup_cards"] = len(unified_items)
        diag["web_reader_counts"]["client_work_threads"] = len(build_client_work_threads(unified_items, limit=50))
        ensure_thread_workflow_states_loaded()
        diag["web_reader_counts"]["persistent_thread_states_loaded"] = len(THREAD_WORKFLOW_STATES)
        ensure_workspace_object_cache_loaded()
        diag["web_reader_counts"]["workspace_objects_loaded"] = len(WORKSPACE_OBJECT_CACHE)
        diag["web_reader_counts"]["approved_workspace_objects"] = approved_workspace_object_count()
        diag["web_reader_counts"]["saved_sendback_drafts"] = len(load_persistent_sendback_drafts_from_db(limit=200))
        ensure_draft_review_states_loaded()
        diag["web_reader_counts"]["draft_review_states_loaded"] = len(DRAFT_REVIEW_STATES)
    except Exception as e:
        diag["web_reader_counts"]["merged_telegram_intake_sync"] = "error: " + str(e)[:160]

    return diag


def diagnostic_rows_html(diag):
    rows = []
    def add(label, value, pill="diag"):
        rows.append(f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(value)}</span></div><span class='pill'>{html_escape(pill)}</span></div>")

    add("DB URL source", diag.get("database_url_source") or "missing", "env")
    add("DB URL safe", diag.get("database_url_safe", "missing"), "env")
    candidates = diag.get("database_url_candidates_found") or []
    if candidates:
        add("DB env candidates", ", ".join([str(x.get("key")) for x in candidates]), "env")
    else:
        add("DB env candidates", "none", "env")
    env_keys = diag.get("relevant_env_keys") or []
    add("Relevant env key names", ", ".join(env_keys[:30]) if env_keys else "none visible", "env")
    add("DB connect", "OK" if diag.get("db_connect_ok") else (diag.get("db_error") or "not connected"), "OK" if diag.get("db_connect_ok") else "check")
    for table, exists in (diag.get("tables") or {}).items():
        add(f"table: {table}", "exists" if exists else "missing", "table")
    for key, value in (diag.get("counts") or {}).items():
        add(key, value, "count")
    for key, value in (diag.get("web_reader_counts") or {}).items():
        add(key, value, "reader")
    if diag.get("db_error"):
        add("DB error", diag.get("db_error"), "error")
    return "".join(rows)


def latest_debug_rows_html(diag):
    blocks = []
    latest = diag.get("latest") or {}
    for group, rows in latest.items():
        inner = ""
        for item in rows[:5]:
            title = str(item.get("user_text") or item.get("backup_text") or item.get("title") or item.get("raw_text") or item.get("id") or "row")
            meta = " · ".join([f"{k}: {v}" for k, v in item.items() if k not in ["user_text", "backup_text", "title", "raw_text"]])
            inner += f"<div class='row'><div><b>{html_escape(title)}</b><span class='muted'>{html_escape(meta)}</span></div><span class='pill'>{html_escape(group)}</span></div>"
        if not inner:
            inner = "<div class='row'><div><b>No rows</b><span class='muted'>—</span></div><span class='pill'>empty</span></div>"
        blocks.append(f"<section class='card card-pad'><div class='section-title'>Latest: {html_escape(group)}</div><div class='list'>{inner}</div></section>")
    return "<div class='stack-grid'>" + "".join(blocks) + "</div>" if blocks else ""


def telegram_db_diagnostic_block_html():
    diag = telegram_bridge_db_diagnostics()
    return (
        "<section class='card card-pad'>"
        "<div class='section-title'>🧪 V51.0 DB Diagnostic</div>"
        "<p class='muted'>Read-only check: does Web service see the same Postgres memory that Telegram app.py writes?</p>"
        "<div class='list'>" + diagnostic_rows_html(diag) + "</div>"
        "<div class='safe-note'>Open JSON: <a href='/diagnostics/telegram-sync'>/diagnostics/telegram-sync</a>. If counts are zero here but Telegram works, Railway services may not share the same DATABASE_URL or app.py writes to a different table/source.</div>"
        "</section><br>"
        + latest_debug_rows_html(diag)
        + "<br>"
    )

def channel_hub_body(data):
    """V51.6.1: Inbox reads the same canonical ONE NINA work truth."""
    lang = current_language()
    objects = one_nina_canonical_work_objects(limit=500)
    telegram_objects = [
        obj for obj in objects
        if str(getattr(obj, "origin_channel", "") or "").strip().lower() == "telegram"
    ]

    if telegram_objects:
        rows = ""
        for obj in telegram_objects[:50]:
            details = one_nina_business_details(obj)
            metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
            subject = str(details.get("subject") or "").strip()
            raw_text = str(metadata.get("raw_text") or "").strip()
            amount = one_nina_business_amount_label(details)
            client_name = str(getattr(obj, "client_id", "") or details.get("client_name") or "").strip()
            due_context = str(details.get("due_context") or getattr(obj, "due_date", "") or "").strip()
            info = [str(getattr(obj, "object_type", "") or "work"), str(getattr(obj, "status", "") or "open")]
            if client_name: info.append(client_name)
            if amount: info.append(amount)
            if due_context: info.append(due_context)
            evidence = subject or raw_text or str(getattr(obj, "source_key", "") or "")
            if len(evidence) > 320: evidence = evidence[:317] + "..."
            rows += ("<div class='row'><div>" f"<b>{html_escape(getattr(obj, 'title', '') or 'Telegram intake')}</b>" f"<span class='muted'>{html_escape(' · '.join(info))}</span>" f"<span class='muted'> · {html_escape(evidence)}</span>" "</div><span class='pill'>ONE NINA</span></div>")
    else:
        rows = "<div class='row'><div><b>No canonical Telegram intake yet.</b><span class='muted'>New Telegram work appears after Nina saves it to nina_work_objects.</span></div><span class='pill'>idle</span></div>"

    channel_counts = {}
    for obj in objects:
        channel = str(getattr(obj, "origin_channel", "") or "").strip().lower() or "ninaos"
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
    channel_rows = "".join("<div class='row'><div>" f"<b>{html_escape(channel.title())}</b>" "<span class='muted'>Canonical channel-linked Work Objects</span></div>" f"<span class='pill'>{count}</span></div>" for channel, count in sorted(channel_counts.items()))
    if not channel_rows:
        channel_rows = "<div class='row'><div><b>No active channel work yet.</b><span class='muted'>nina_work_objects</span></div><span class='pill'>idle</span></div>"

    return (
        work_page_header(tx("channel_hub", lang), "V51.6.2 ONE NINA UI SPACING FIX — canonical Inbox detail rows render with a visible separator.")
        + "<section class='card card-pad'><div class='section-title'>ONE NINA Inbox</div>"
        + one_nina_work_kpis_html() + "<br><div class='list'>" + rows + "</div>"
        + "<div class='safe-note'>V51.6.2: Inbox reads the same nina_work_objects used by Tasks and Clients. Legacy Telegram thread-preview inference is not executed as a parallel Inbox work system.</div></section><br>"
        + "<section class='card card-pad'><div class='section-title'>Canonical Channel Intake</div><div class='list'>" + channel_rows + "</div>"
        + "<div class='safe-note'>One Nina, one persistent work truth. Channels are intake and delivery surfaces, not separate brains.</div></section>"
    )

def simple_module_body(title, subtitle, blocks):
    rows = "".join(f"<div class='row'><div><b>{html_escape(b[0])}</b><span class='muted'>{html_escape(b[1])}</span></div><span class='pill'>{html_escape(b[2])}</span></div>" for b in blocks)
    return work_page_header(title, subtitle) + f"<section class='card card-pad'><div class='list'>{rows}</div></section>"




def action_panel_card(title, hint, count, href, tone="normal"):
    return (
        "<div class='card card-pad'>"
        f"<div class='section-title'>{html_escape(title)}</div>"
        f"<p class='muted'>{html_escape(hint)}</p>"
        f"<div class='kpi'><small>{tx('active')}</small><strong>{count}</strong><em>{tx('open_work_label')}</em></div>"
        "<br>"
        f"<a class='btn primary' href='{href}'>{tx('open_panel')}</a>"
        "</div>"
    )


def office_manager_action_panels(data):
    lang = current_language()
    tasks = len([o for o in data["tasks"] if o.get("object_type") == "task"])
    followups = len([o for o in data["tasks"] if o.get("object_type") == "followup_task"])
    estimates = len([o for o in data["tasks"] if o.get("object_type") == "estimate"])
    invoices = len([o for o in data["tasks"] if o.get("object_type") == "invoice"])
    documents = 3
    approvals = 0

    return (
        f"<section class='card card-pad'><div class='section-title'>{tx('action_panels', lang)}</div>"
        "<div class='worker-grid'>"
        + action_panel_card(tx("task_panel", lang), tx("create_task_hint", lang), tasks, q("/tasks"))
        + action_panel_card(tx("followup_panel", lang), tx("followup_hint", lang), followups, q("/tasks"))
        + action_panel_card(tx("estimate_panel", lang), tx("estimate_hint", lang), estimates, q("/tasks"))
        + action_panel_card(tx("invoice_panel", lang), tx("invoice_hint", lang), invoices, q("/clients"))
        + action_panel_card(tx("document_panel", lang), tx("document_hint", lang), documents, q("/files"))
        + action_panel_card(tx("approval_queue", lang), tx("approval_hint", lang), approvals, q("/workers/office-manager"))
        + "</div></section>"
    )




def get_action_preview():
    if request.method != "POST":
        return None
    form = request.form
    action = {
        "form_type": form.get("form_type", ""),
        "task_title": form.get("task_title", ""),
        "client_name": form.get("client_name", ""),
        "project_name": form.get("project_name", ""),
        "amount": form.get("amount", ""),
        "due_date": form.get("due_date", ""),
        "priority": form.get("priority", "normal"),
        "notes": form.get("notes", ""),
    }
    obj = create_workspace_action_preview(action)
    action["workspace_object"] = obj
    return action


def action_preview_html(preview):
    if not preview:
        return ""
    lang = current_language()
    labels = [
        ("form_type", tx("form_type", lang)),
        ("task_title", tx("task_title", lang)),
        ("client_name", tx("client_name", lang)),
        ("project_name", tx("project_name", lang)),
        ("amount", tx("amount", lang)),
        ("due_date", tx("due_date", lang)),
        ("priority", tx("priority", lang)),
        ("notes", tx("notes", lang)),
    ]
    rows = ""
    for key, label in labels:
        value = preview.get(key) or "—"
        rows += f"<div class='row'><div><b>{html_escape(label)}</b><span class='muted'>{html_escape(value)}</span></div><span class='pill'>preview</span></div>"
    obj = preview.get("workspace_object") or {}
    if obj:
        rows += f"<div class='row'><div><b>{tx('object_id', lang)}</b><span class='muted'>{html_escape(obj.get('object_id'))}</span></div><span class='pill'>V43.3</span></div>"
        rows += f"<div class='row'><div><b>{tx('object_type', lang)}</b><span class='muted'>{html_escape(obj.get('object_type'))}</span></div><span class='pill'>{html_escape(obj.get('status'))}</span></div>"
        meta = obj.get('metadata', {}) if isinstance(obj.get('metadata'), dict) else {}
        rows += f"<div class='row'><div><b>{tx('approval_state', lang)}</b><span class='muted'>{html_escape(approval_label_from_state(meta.get('approval_state'), lang))}</span></div><span class='pill'>safe</span></div>"
    return f"<div class='preview-box'><b>{tx('saved_to_workspace', lang)}</b><div class='list'>{rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></div>"


def action_form_card(form_type, title, hint, defaults=None):
    lang = current_language()
    defaults = defaults or {}
    action = q("/office-manager/actions")
    return f"""
    <section class='card card-pad'>
      <div class='section-title'>{html_escape(title)}</div>
      <p class='muted'>{html_escape(hint)}</p>
      <form method='post' action='{action}'>
        <input type='hidden' name='form_type' value='{html_escape(form_type)}'>
        <div class='form-grid'>
          <div class='field'>
            <label>{tx('task_title', lang)}</label>
            <input name='task_title' placeholder='{tx('task_title', lang)}' value='{html_escape(defaults.get('task_title',''))}'>
          </div>
          <div class='field'>
            <label>{tx('client_name', lang)}</label>
            <input name='client_name' placeholder='{tx('client_name', lang)}' value='{html_escape(defaults.get('client_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('project_name', lang)}</label>
            <input name='project_name' placeholder='{tx('project_name', lang)}' value='{html_escape(defaults.get('project_name',''))}'>
          </div>
          <div class='field'>
            <label>{tx('due_date', lang)}</label>
            <input name='due_date' placeholder='today / friday / 2026-07-10' value='{html_escape(defaults.get('due_date',''))}'>
          </div>
          <div class='field'>
            <label>{tx('amount', lang)}</label>
            <input name='amount' placeholder='€0.00' value='{html_escape(defaults.get('amount',''))}'>
          </div>
          <div class='field'>
            <label>{tx('priority', lang)}</label>
            <select name='priority'>
              <option value='normal'>{tx('normal', lang)}</option>
              <option value='high'>{tx('high', lang)}</option>
            </select>
          </div>
        </div>
        <br>
        <div class='field'>
          <label>{tx('notes', lang)}</label>
          <textarea name='notes' placeholder='{tx('notes', lang)}'>{html_escape(defaults.get('notes',''))}</textarea>
        </div>
        <div class='form-actions'>
          <button class='btn primary' type='submit'>{tx('submit_preview', lang)}</button>
          <a class='btn' href='{q('/office-manager')}'>{tx('work_console', lang)}</a>
        </div>
        <div class='safe-note'>{tx('safe_note', lang)}</div>
      </form>
    </section>
    """


def action_center_body(data):
    lang = current_language()
    preview = get_action_preview()
    if preview and preview.get("workspace_object"):
        obj = preview["workspace_object"]
        data["objects"].insert(0, obj)
        if obj.get("object_type") in ["task", "followup_task", "estimate", "invoice"]:
            data["tasks"].insert(0, obj)
    preview_rows = work_object_rows(pending_or_held_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
    approved_rows = work_object_rows(approved_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
    rejected_rows = work_object_rows(rejected_preview_items(), empty_text=tx("no_items", lang), limit=5, show_source=True, show_approval=True)
    forms = (
        "<div class='stack-grid'>"
        + action_form_card("new_task", tx("new_task_form", lang), tx("create_task_hint", lang))
        + action_form_card("followup", tx("followup_form", lang), tx("followup_hint", lang), {"task_title": "Follow up with client"})
        + action_form_card("estimate", tx("estimate_form", lang), tx("estimate_hint", lang), {"task_title": "Create estimate draft"})
        + action_form_card("invoice", tx("invoice_form", lang), tx("invoice_hint", lang), {"task_title": "Create invoice admin record"})
        + "</div>"
    )
    return (
        work_page_header(tx("action_center", lang), tx("action_center_sub", lang))
        + action_preview_html(preview)
        + "<div class='console-nav'>"
        + f"<a class='primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>"
        + f"<a href='{q('/office-manager')}'>{tx('work_console', lang)}</a>"
        + f"<a href='{q('/office-manager/panels')}'>{tx('action_panels', lang)}</a>"
        + f"<a href='{q('/tasks')}'>{tx('tasks', lang)}</a>"
        + f"<a href='{q('/clients')}'>{tx('clients', lang)}</a>"
        + "</div>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approval_workspace_bridge', lang)}</div><div class='list'>{preview_rows}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approved_workspace_queue', lang)}</div><div class='list'>{approved_rows}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section><br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('rejected_preview_log', lang)}</div><div class='list'>{rejected_rows}</div></section><br>"
        + forms
    )



def office_manager_body(data):
    lang = current_language()
    tasks = [o for o in data["tasks"] if o.get("object_type") in ["task", "followup_task"]]
    invoices = [o for o in data["tasks"] if o.get("object_type") == "invoice"]
    estimates = [o for o in data["tasks"] if o.get("object_type") == "estimate"]

    def mini_list(items, empty_text):
        return work_object_rows(items, empty_text=empty_text, limit=5, show_source=True)

    role_rows = [
        ("Office Manager", "Coordinates daily workspace operations", "active"),
        ("Task Router", "Organizes tasks, follow-ups and due work", "active"),
        ("Client Admin", "Keeps client work visible in one place", "active"),
        ("Finance Admin", "Tracks invoice and estimate admin records", "preview"),
    ]
    role_html = "".join(f"<div class='row'><div><b>{html_escape(a)}</b><span class='muted'>{html_escape(b)}</span></div><span class='pill'>{html_escape(c)}</span></div>" for a,b,c in role_rows)

    right_blocks = "".join([
        f"<div class='row'><div><b>{tx('approval_required', lang)}</b><span class='muted'>No approval queue yet</span></div><span class='pill'>0</span></div>",
        f"<div class='row'><div><b>{tx('allowed_tools', lang)}</b><span class='muted'>tasks · clients · files · estimates · invoices</span></div><span class='pill'>safe</span></div>",
        f"<div class='row'><div><b>{tx('memory_scopes', lang)}</b><span class='muted'>workspace · client · project</span></div><span class='pill'>read</span></div>",
        f"<div class='row'><div><b>{tx('permissions', lang)}</b><span class='muted'>write_task · write_client · write_document</span></div><span class='pill'>limited</span></div>",
    ])

    quick = "".join([
        f"<a class='btn primary' href='{q('/office-manager/actions')}'>{tx('action_center', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('new_task', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('followup_client', lang)}</a>",
        f"<a class='btn' href='{q('/tasks')}'>{tx('create_estimate', lang)}</a>",
        f"<a class='btn' href='{q('/clients')}'>{tx('create_invoice', lang)}</a>",
        f"<a class='btn' href='{q('/files')}'>{tx('upload_document', lang)}</a>",
    ])

    return (
        work_page_header(tx("office_manager", lang), tx("worker_detail_sub", lang))
        + "<div class='hero-grid'>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('worker_summary', lang)}</div>"
        + "<div class='row'><div><b>Nina Office Manager SMB</b><span class='muted'>AI Office Manager · ACTIVE · Operations</span></div><span class='pill'>ready</span></div>"
        + "<br><div class='kpis'>"
        + kpi_card(tx("tasks_today", lang), data["counts"]["tasks_today"], {"text": tx("open_work_label", lang), "href": "/tasks"})
        + kpi_card(tx("followups", lang), data["counts"]["followups"], {"text": tx("need_attention", lang), "href": "/tasks"})
        + kpi_card(tx("invoices", lang), data["counts"]["invoices"], {"text": tx("finance", lang), "href": "/clients"})
        + kpi_card(tx("projects_kpi", lang), data["counts"]["projects"], {"text": tx("active", lang), "href": "/projects"})
        + "</div><br>"
        + f"<div class='section-title'>{tx('role_stack', lang)}</div><div class='list'>{role_html}</div>"
        + "</section>"
        + "<section class='card card-pad'>"
        + f"<div class='section-title'>{tx('quick_actions', lang)}</div><div class='btns'>{quick}</div><br>"
        + f"<div class='section-title'>{tx('approval_required', lang)}</div><div class='list'>{right_blocks}</div>"
        + "</section>"
        + "</div><br>"
        + office_manager_action_panels(data)
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>Office Manager Active Workspace Objects</div><div class='list'>{workspace_object_surface_rows(limit=6, empty_text=tx('no_items', lang))}</div><div class='safe-note'>V47.1: Office Manager works from approved workspace objects, not raw Telegram thread previews.</div></section>"
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approval_workspace_bridge', lang)}</div><div class='list'>{work_object_rows(pending_or_held_preview_items(), empty_text=tx('no_items', lang), limit=5, show_source=True)}</div><div class='safe-note'>{tx('safe_note', lang)}</div></section>"
        + "<br>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('approved_workspace_queue', lang)}</div><div class='list'>{active_workspace_work_rows(limit=6, empty_text=tx('no_items', lang))}</div><div class='safe-note'>{tx('approved_work_note', lang)}</div></section>"
        + "<br><div class='two-col'>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('linked_work', lang)}</div><div class='list'>{mini_list(tasks, 'No task queue yet')}</div></section>"
        + f"<section class='card card-pad'><div class='section-title'>{tx('estimates', lang)} / {tx('invoices', lang)}</div><div class='list'>{mini_list(estimates + invoices, 'No finance admin queue yet')}</div></section>"
        + "</div>"
    )


def _channel_csrf(action):
    message = f"{NINA_WEB_WORKSPACE_ID}:{action}".encode()
    return hmac.new(_CHANNEL_CSRF_SECRET, message, hashlib.sha256).hexdigest()


def _valid_channel_csrf(action):
    supplied = (request.form.get("csrf_token") or "").strip()
    return bool(supplied) and hmac.compare_digest(supplied, _channel_csrf(action))


def _telegram_bot_username():
    candidate = (os.environ.get("TELEGRAM_BOT_USERNAME") or "Nina7727_bot").strip().lstrip("@")
    return candidate if re.fullmatch(r"[A-Za-z0-9_]{5,64}", candidate) else "Nina7727_bot"


def _channels_copy(lang):
    return {
        "en": {"title": "Channels", "sub": "Choose where you want to talk with Nina.", "active": "Active", "connected": "Connected", "disconnected": "Not connected", "pending": "Connecting", "error": "Connection needs attention", "web_text": "Your Web workspace is ready.", "telegram_text": "Connect your Telegram account to this workspace.", "connect_telegram": "Connect Telegram", "open_telegram": "Open Telegram", "disconnect": "Disconnect", "pending_text": "Open the bot and press Start. Confirmation will appear here when linking is enabled in Telegram.", "whatsapp_text": "Connect your WhatsApp and talk to Nina from the app you already use.", "connect_whatsapp": "Connect WhatsApp", "whatsapp_failed": "This number could not be connected. Your existing WhatsApp account was not changed.", "prepare": "Your current number can be kept. To connect Nina, this number first needs to use WhatsApp Business App.", "backup": "Back up your chats in WhatsApp first, then switch the same number to WhatsApp Business App using WhatsApp's supported process.", "already_business": "I already use WhatsApp Business", "switch_safely": "How to switch safely", "cancel": "Cancel", "retry": "Retry", "email_text": "Email connection is coming soon.", "coming": "Coming soon"},
        "lv": {"title": "Kanāli", "sub": "Izvēlies, kur vēlies sarunāties ar Ninu.", "active": "Aktīvs", "connected": "Savienots", "disconnected": "Nav savienots", "pending": "Savieno", "error": "Savienojumam jāpievērš uzmanība", "web_text": "Tava tīmekļa darba vide ir gatava.", "telegram_text": "Savieno savu Telegram kontu ar šo darba vidi.", "connect_telegram": "Savienot Telegram", "open_telegram": "Atvērt Telegram", "disconnect": "Atvienot", "pending_text": "Atver botu un nospied Start. Apstiprinājums šeit parādīsies, kad Telegram savienošana būs iespējota.", "whatsapp_text": "Savieno savu WhatsApp un runā ar Ninu lietotnē, ko jau izmanto.", "connect_whatsapp": "Savienot WhatsApp", "whatsapp_failed": "Šo numuru neizdevās savienot. Tavs esošais WhatsApp konts netika mainīts.", "prepare": "Vari paturēt savu pašreizējo numuru. Lai savienotu Ninu, šim numuram vispirms jāizmanto WhatsApp Business lietotne.", "backup": "Vispirms izveido sarunu rezerves kopiju WhatsApp, pēc tam pārej ar to pašu numuru uz WhatsApp Business lietotni, izmantojot WhatsApp drošo pāreju.", "already_business": "Es jau izmantoju WhatsApp Business", "switch_safely": "Kā droši pāriet", "cancel": "Atcelt", "retry": "Mēģināt vēlreiz", "email_text": "E-pasta savienojums būs drīzumā.", "coming": "Drīzumā"},
        "ru": {"title": "Каналы", "sub": "Выберите, где вы хотите общаться с Ниной.", "active": "Активен", "connected": "Подключён", "disconnected": "Не подключён", "pending": "Подключение", "error": "Подключение требует внимания", "web_text": "Ваше веб-пространство готово.", "telegram_text": "Подключите Telegram к этому рабочему пространству.", "connect_telegram": "Подключить Telegram", "open_telegram": "Открыть Telegram", "disconnect": "Отключить", "pending_text": "Откройте бота и нажмите Start. Подтверждение появится здесь, когда подключение в Telegram будет включено.", "whatsapp_text": "Подключите WhatsApp и общайтесь с Ниной в привычном приложении.", "connect_whatsapp": "Подключить WhatsApp", "whatsapp_failed": "Не удалось подключить этот номер. Существующий аккаунт WhatsApp не был изменён.", "prepare": "Текущий номер можно сохранить. Чтобы подключить Нину, сначала используйте этот номер в приложении WhatsApp Business.", "backup": "Сначала создайте резервную копию чатов в WhatsApp, затем перейдите с тем же номером в WhatsApp Business официальным способом.", "already_business": "Я уже использую WhatsApp Business", "switch_safely": "Как перейти безопасно", "cancel": "Отмена", "retry": "Повторить", "email_text": "Подключение электронной почты появится позже.", "coming": "Скоро"},
    }[lang]


def _whatsapp_connect_script():
    return r"""
(() => {
  const button = document.getElementById('whatsapp-business-connect');
  if (!button) return;
  let setup = null, signup = null, code = '';
  const fail = async () => {
    button.disabled = false;
    if (setup && setup.state) {
      try { await fetch('/channels/whatsapp/attention', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({csrf_token:window.NinaWhatsApp.callbackCsrf,state:setup.state})}); } catch (_) {}
    }
    window.location.href = '/channels?lang=' + encodeURIComponent(window.NinaWhatsApp.lang) + '&notice=whatsapp_failed';
  };
  const finish = async () => {
    if (!setup || !signup || !code) return;
    try {
      const response = await fetch('/channels/whatsapp/callback', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({csrf_token: window.NinaWhatsApp.callbackCsrf, state: setup.state, code,
          phone_number_id: signup.phone_number_id, business_account_id: signup.waba_id,
          business_portfolio_id: signup.business_id || ''})
      });
      if (!response.ok) return fail();
      window.location.href = '/channels?lang=' + encodeURIComponent(window.NinaWhatsApp.lang);
    } catch (_) { fail(); }
  };
  window.addEventListener('message', (event) => {
    if (!(event.origin === 'https://www.facebook.com' || event.origin.endsWith('.facebook.com'))) return;
    try {
      const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      if (data && data.type === 'WA_EMBEDDED_SIGNUP' && data.event === 'FINISH') { signup = data.data || {}; finish(); }
    } catch (_) {}
  });
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const response = await fetch('/channels/whatsapp/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({csrf_token:window.NinaWhatsApp.startCsrf})});
      if (!response.ok) return fail();
      setup = await response.json();
      if (!window.FB) return fail();
      const init = {appId: setup.app_id, cookie:true, xfbml:false}; init['ver'+'sion'] = setup.gv; FB.init(init);
      const extras = {setup:{}, featureType:'whatsapp_business_app_onboarding'}; extras['sessionInfo'+'Ver'+'sion'] = '3';
      FB.login((result) => {
        code = result && result.authResponse ? (result.authResponse.code || '') : '';
        if (!code) return fail();
        finish();
      }, {config_id:setup.config_id, response_type:'code', override_default_response_type:true, extras});
    } catch (_) { fail(); }
  });
})();
"""


def channels_body(telegram_setup=None, notice="", whatsapp_view=""):
    lang = current_language()
    c = _channels_copy(lang)
    telegram = get_connection(NINA_WEB_WORKSPACE_ID, "telegram")
    whatsapp = get_connection(NINA_WEB_WORKSPACE_ID, "whatsapp")
    tmeta, wmeta = telegram["metadata"], whatsapp["metadata"]
    refresh_label = {"en": "Refresh status", "lv": "Atjaunot statusu", "ru": "Обновить статус"}[lang]
    status_label = {"connected": c["connected"], "pending": c["pending"], "error": c["error"], "disconnected": c["disconnected"]}
    saved_username = str(tmeta.get("bot_username") or "").strip().lstrip("@")
    bot_username = saved_username if re.fullmatch(r"[A-Za-z0-9_]{5,64}", saved_username) else _telegram_bot_username()
    telegram_action = ""
    if telegram_setup and telegram_setup.get("deep_link"):
        telegram_action = f"<a class='btn primary' href='{html_escape(telegram_setup['deep_link'])}' rel='noopener noreferrer'>{c['open_telegram']}</a><div class='safe-note'>{c['pending_text']}</div>"
    elif telegram["status"] != "connected":
        telegram_action = f"<form method='post' action='/channels/telegram/connect?lang={lang}'><input type='hidden' name='csrf_token' value='{_channel_csrf('telegram_connect')}'><button class='btn primary' type='submit'>{c['connect_telegram']}</button></form>"
    if telegram["status"] in {"connected", "pending", "error"}:
        telegram_action += f"<form method='post' action='/channels/telegram/disconnect?lang={lang}'><input type='hidden' name='csrf_token' value='{_channel_csrf('telegram_disconnect')}'><button class='btn' type='submit'>{c['disconnect']}</button></form>"
    telegram_action += f"<a class='btn' href='/channels?lang={lang}'>{refresh_label}</a>"
    linked_account = ""
    if telegram["status"] == "connected":
        account_name = str(tmeta.get("telegram_display_name") or tmeta.get("telegram_username") or "").strip()
        username = str(tmeta.get("telegram_username") or "").strip().lstrip("@")
        account_label = account_name + (f" · @{username}" if username and username.lower() not in account_name.lower() else "")
        linked_account = f"<div class='safe-note'>{html_escape(account_label)}</div>" if account_label else ""
    whatsapp_action = ""
    whatsapp_help = ""
    if whatsapp["status"] == "disconnected" and whatsapp_view == "prepare":
        whatsapp_help = f"<div class='channel-message'>{html_escape(c['prepare'])}</div>"
        whatsapp_action = f"<button class='btn primary' id='whatsapp-business-connect' type='button'>{c['already_business']}</button><a class='btn' href='/channels?lang={lang}&whatsapp=switch'>{c['switch_safely']}</a><a class='btn' href='/channels?lang={lang}'>{c['cancel']}</a>"
    elif whatsapp["status"] == "disconnected" and whatsapp_view == "switch":
        whatsapp_help = f"<div class='channel-message'>{html_escape(c['backup'])}</div>"
        whatsapp_action = f"<button class='btn primary' id='whatsapp-business-connect' type='button'>{c['already_business']}</button><a class='btn' href='https://business.whatsapp.com/products/business-app' rel='noopener noreferrer' target='_blank'>{c['switch_safely']}</a><a class='btn' href='/channels?lang={lang}'>{c['cancel']}</a>"
    elif whatsapp["status"] == "disconnected":
        whatsapp_action = f"<a class='btn primary' href='/channels?lang={lang}&whatsapp=prepare'>{c['connect_whatsapp']}</a>"
    elif whatsapp["status"] == "error":
        whatsapp_action = f"<a class='btn primary' href='/channels?lang={lang}&whatsapp=prepare'>{c['retry']}</a>"
    if whatsapp["status"] in {"connected", "pending", "error"}:
        whatsapp_action += f"<form method='post' action='/channels/whatsapp/disconnect?lang={lang}'><input type='hidden' name='csrf_token' value='{_channel_csrf('whatsapp_disconnect')}'><button class='btn' type='submit'>{c['disconnect']}</button></form>"
    whatsapp_identity = " · ".join(filter(None, [str(wmeta.get("business_display_name") or ""), str(wmeta.get("display_phone_number") or "")]))
    whatsapp_identity_html = f"<div class='safe-note'>{html_escape(whatsapp_identity)}</div>" if whatsapp_identity else ""
    whatsapp_error_html = f"<div class='channel-message'>{html_escape(c['whatsapp_failed'])}</div>" if whatsapp["status"] == "error" else ""
    notice_text = c.get(notice, notice)
    notice_html = f"<div class='channel-message'>{html_escape(notice_text)}</div>" if notice else ""
    return (
        "<style>@media(max-width:640px){.sidebar{padding-bottom:14px}.brand{margin-bottom:14px}.nav{flex-direction:row;overflow-x:auto;padding-bottom:6px}.nav-item{flex:0 0 auto}.user{display:none}}</style>"
        f"<div class='page-title'><h1>{c['title']}</h1><p>{c['sub']}</p></div><br>{notice_html}"
        "<div class='channels-grid'>"
        f"<section class='card card-pad connection-card'><div class='connection-head'><h2>Web</h2><span class='connection-status active'>{c['active']}</span></div><p class='muted'>{c['web_text']}</p></section>"
        f"<section class='card card-pad connection-card'><div class='connection-head'><h2>Telegram</h2><span class='connection-status {telegram['status']}'>{status_label[telegram['status']]}</span></div><p class='muted'>{c['telegram_text']}</p><div><b>@{html_escape(bot_username)}</b></div>{linked_account}<div class='connection-actions'>{telegram_action}</div></section>"
        f"<section class='card card-pad connection-card'><div class='connection-head'><h2>WhatsApp</h2><span class='connection-status {whatsapp['status']}'>{html_escape({'en':'Preparation needed','lv':'Nepieciešama sagatavošana','ru':'Требуется подготовка'}[lang] if whatsapp['status'] == 'disconnected' and whatsapp_view in {'prepare','switch'} else status_label[whatsapp['status']])}</span></div><p class='muted'>{c['whatsapp_text']}</p>{whatsapp_help}{whatsapp_error_html}{whatsapp_identity_html}<div class='connection-actions'>{whatsapp_action}</div></section>"
        f"<section class='card card-pad connection-card'><div class='connection-head'><h2>Email</h2><span class='connection-status'>{c['coming']}</span></div><p class='muted'>{c['email_text']}</p></section>"
        "</div>"
        "<script async defer crossorigin='anonymous' src='https://connect.facebook.net/en_US/sdk.js'></script>"
        f"<script>window.NinaWhatsApp={{startCsrf:{json.dumps(_channel_csrf('whatsapp_start'))},callbackCsrf:{json.dumps(_channel_csrf('whatsapp_callback'))},lang:{json.dumps(lang)}}};</script>"
        "<script>" + _whatsapp_connect_script() + "</script>"
    )



def _transcribe_web_voice(audio_bytes, filename, mime_type, language_hint):
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return ""
    from openai import OpenAI
    return transcribe_audio_with_openai(
        OpenAI(api_key=api_key),
        audio_bytes,
        filename=filename,
        language_hint=language_hint,
        force_language=False,
        model=WEB_VOICE_TRANSCRIPTION_MODEL,
        mime_type=mime_type,
    )


@app.post("/nina/voice")
def nina_voice():
    if request.content_length and request.content_length > WEB_VOICE_MAX_BYTES + (1024 * 1024):
        return jsonify({"ok": False, "error": "audio_too_large"}), 413

    upload = request.files.get("audio")
    if upload is None:
        return jsonify({"ok": False, "error": "audio_required"}), 400

    content_type = (upload.content_type or upload.mimetype or "").lower().strip()
    mime_type = content_type.split(";", 1)[0].strip()
    if mime_type not in WEB_VOICE_MIME_TYPES:
        return jsonify({"ok": False, "error": "unsupported_audio"}), 415

    audio_bytes = upload.stream.read(WEB_VOICE_MAX_BYTES + 1)
    if not audio_bytes:
        return jsonify({"ok": False, "error": "audio_required"}), 400
    if len(audio_bytes) > WEB_VOICE_MAX_BYTES:
        return jsonify({"ok": False, "error": "audio_too_large"}), 413

    lang = (request.form.get("lang") or current_language()).strip().lower()
    lang = lang if lang in {"lv", "en", "ru"} else "en"
    logger.info(
        "Web voice transcription started mime=%s bytes=%d model=%s language_hint=%s",
        content_type,
        len(audio_bytes),
        WEB_VOICE_TRANSCRIPTION_MODEL,
        lang,
    )
    try:
        transcript = _transcribe_web_voice(
            audio_bytes,
            upload.filename or "voice.webm",
            content_type,
            lang,
        ).strip()
    except Exception:
        logger.warning(
            "Web voice transcription completed success=False chars=0 model=%s language_hint=%s",
            WEB_VOICE_TRANSCRIPTION_MODEL,
            lang,
        )
        return jsonify({"ok": False, "error": "transcription_unavailable"}), 502
    logger.info(
        "Web voice transcription completed success=%s chars=%d model=%s language_hint=%s",
        bool(transcript),
        len(transcript),
        WEB_VOICE_TRANSCRIPTION_MODEL,
        lang,
    )
    if not transcript:
        return jsonify({"ok": False, "error": "transcription_unavailable"}), 502

    send_message_to_nina(transcript, workspace_id=NINA_WEB_WORKSPACE_ID, channel="web")
    return jsonify({"ok": True})


@app.get("/channels")
def channels():
    notice = (request.args.get("notice") or "").strip()
    notice = notice if notice in {"whatsapp_failed"} else ""
    whatsapp_view = (request.args.get("whatsapp") or "").strip()
    whatsapp_view = whatsapp_view if whatsapp_view in {"prepare", "switch"} else ""
    return Response(page(_channels_copy(current_language())["title"], channels_body(notice=notice, whatsapp_view=whatsapp_view), active="channels"), mimetype="text/html")


@app.post("/channels/telegram/connect")
def channels_telegram_connect():
    if not _valid_channel_csrf("telegram_connect"):
        return Response("Invalid request", status=400)
    bot_username = _telegram_bot_username()
    try:
        setup = create_telegram_token(NINA_WEB_WORKSPACE_ID, bot_username=bot_username)
    except ValueError as exc:
        if str(exc) == "telegram_already_connected":
            return redirect(q("/channels"))
        raise
    return Response(page(_channels_copy(current_language())["title"], channels_body(telegram_setup=setup), active="channels"), mimetype="text/html")


@app.post("/channels/telegram/disconnect")
def channels_telegram_disconnect():
    if not _valid_channel_csrf("telegram_disconnect"):
        return Response("Invalid request", status=400)
    disconnect_channel(NINA_WEB_WORKSPACE_ID, "telegram")
    return redirect(q("/channels"))


@app.post("/channels/whatsapp/start")
def channels_whatsapp_start():
    payload = request.get_json(silent=True) or {}
    if not hmac.compare_digest(str(payload.get("csrf_token") or ""), _channel_csrf("whatsapp_start")):
        return jsonify({"ok": False}), 400
    try:
        provider = embedded_signup_public_config()
        state = create_whatsapp_onboarding_state(NINA_WEB_WORKSPACE_ID)
    except (ValueError, WhatsAppProviderError):
        return jsonify({"ok": False}), 503
    return jsonify({"ok": True, "state": state["state"], "expires_at": state["expires_at"], "app_id": provider["app_id"], "config_id": provider["config_id"], "gv": os.environ.get("WHATSAPP_GRAPH_API_VERSION", "v25.0")})


@app.post("/channels/whatsapp/callback")
def channels_whatsapp_callback():
    payload = request.get_json(silent=True) or {}
    if not hmac.compare_digest(str(payload.get("csrf_token") or ""), _channel_csrf("whatsapp_callback")):
        return jsonify({"ok": False}), 400
    workspace_id = consume_whatsapp_onboarding_state(payload.get("state"), expected_workspace_id=NINA_WEB_WORKSPACE_ID)
    if not workspace_id:
        return jsonify({"ok": False}), 400
    try:
        complete_embedded_signup(
            workspace_id,
            payload.get("code"),
            payload.get("phone_number_id"),
            payload.get("business_account_id"),
            payload.get("business_portfolio_id"),
        )
    except WhatsAppProviderError:
        update_whatsapp_verification(workspace_id, False, error_code="onboarding_failed")
        return jsonify({"ok": False}), 400
    return jsonify({"ok": True})


@app.post("/channels/whatsapp/attention")
def channels_whatsapp_attention():
    payload = request.get_json(silent=True) or {}
    if not hmac.compare_digest(str(payload.get("csrf_token") or ""), _channel_csrf("whatsapp_callback")):
        return jsonify({"ok": False}), 400
    workspace_id = consume_whatsapp_onboarding_state(payload.get("state"), expected_workspace_id=NINA_WEB_WORKSPACE_ID)
    if not workspace_id:
        return jsonify({"ok": False}), 400
    update_whatsapp_verification(workspace_id, False, error_code="coexistence_not_completed")
    return jsonify({"ok": True})


@app.post("/channels/whatsapp/disconnect")
def channels_whatsapp_disconnect():
    if not _valid_channel_csrf("whatsapp_disconnect"):
        return Response("Invalid request", status=400)
    disconnect_channel(NINA_WEB_WORKSPACE_ID, "whatsapp")
    return redirect(q("/channels"))


@app.get("/webhooks/whatsapp")
def whatsapp_webhook_verify():
    mode = (request.args.get("hub.mode") or "").strip()
    token = request.args.get("hub.verify_token") or ""
    challenge = request.args.get("hub.challenge") or ""
    if not challenge or len(challenge) > 256 or not resolve_webhook_verification(mode, token):
        return Response("Verification rejected", status=403)
    return Response(challenge, status=200, mimetype="text/plain")


@app.post("/webhooks/whatsapp")
def whatsapp_webhook_receive():
    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"ok": False, "error": "payload_too_large"}), 413
    raw_body = request.get_data(cache=True)
    try:
        payload = request.get_json(force=False, silent=False)
        messages = parse_inbound_text(payload)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_payload"}), 400
    workspaces = {resolve_workspace_for_phone_number(item["phone_number_id"]) for item in messages}
    if None in workspaces or len(workspaces) != 1:
        return jsonify({"ok": False, "error": "connection_not_resolved"}), 403
    workspace_id = next(iter(workspaces))
    try:
        signature_ok = verify_webhook_signature(workspace_id, raw_body, request.headers.get("X-Hub-Signature-256"))
    except WhatsAppProviderError:
        return jsonify({"ok": False, "error": "signature_not_configured"}), 503
    if not signature_ok:
        return jsonify({"ok": False, "error": "invalid_signature"}), 403
    sent = 0
    processed = 0
    for item in messages:
        if not claim_channel_message(workspace_id, "whatsapp", item["message_id"]):
            continue
        processed += 1
        nina_result = send_message_to_nina(item["text"], workspace_id=workspace_id, channel="whatsapp")
        reply_text = str(nina_result.get("text") or "").strip()
        if reply_text:
            try:
                send_whatsapp_message(workspace_id, item["sender"], reply_text)
                sent += 1
            except WhatsAppProviderError:
                pass
    return jsonify({"ok": True, "processed": processed, "replies_sent": sent})


@app.route("/nina", methods=["GET", "POST"])
@app.route("/chat", methods=["GET", "POST"])
def nina_chat():
    if request.method == "POST":
        user_text = (request.form.get("message") or "").strip()
        if user_text:
            send_message_to_nina(user_text, workspace_id=NINA_WEB_WORKSPACE_ID, channel="web")
        return redirect(q("/nina"))
    messages = load_web_conversation(workspace_id=NINA_WEB_WORKSPACE_ID, limit=30)
    return Response(page(tx("talk_to_nina"), nina_chat_body(messages), active="nina"), mimetype="text/html")


@app.route("/")
def home():
    return redirect(q("/dashboard"))


@app.route("/dashboard")
def dashboard():
    data = load_workspace_data()
    return Response(page(tx("dashboard"), dashboard_body(data), active="dashboard"), mimetype="text/html")


@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    return Response(page(tx("channel_hub"), channel_hub_body(load_workspace_data()), "inbox"), mimetype="text/html")


@app.route("/channel-hub")
def channel_hub():
    return redirect(q("/inbox"))


@app.route("/workers")
def workers():
    data = load_workspace_data()
    return Response(page(tx("workers"), workers_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager")
def office_manager_short():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/console")
def office_manager_console():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/office-manager/panels")
def office_manager_panels():
    data = load_workspace_data()
    body = work_page_header(tx("action_panels"), tx("worker_detail_sub")) + office_manager_action_panels(data)
    return Response(page(tx("action_panels"), body, active="workers"), mimetype="text/html")


@app.route("/office-manager/actions", methods=["GET", "POST"])
def office_manager_actions():
    data = load_workspace_data()
    return Response(page(tx("action_center"), action_center_body(data), active="workers"), mimetype="text/html")


@app.route("/workers/office-manager")
def office_manager():
    data = load_workspace_data()
    return Response(page(tx("office_manager"), office_manager_body(data), active="workers"), mimetype="text/html")


@app.route("/work-objects/<object_id>/estimate-draft", methods=["POST"])
def prepare_estimate_draft(object_id):
    result = one_nina_prepare_estimate_draft(unquote_plus(object_id))
    return_to = (request.args.get("return_to") or request.referrer or q("/tasks")).strip()
    if not result.get("ok"):
        print("V51.8.1 estimate action error:", result)
    return redirect(return_to)


@app.route("/work-objects/<object_id>/estimate-approval/<decision>", methods=["POST"])
def decide_estimate_draft(object_id, decision):
    result = one_nina_decide_estimate_draft(unquote_plus(object_id), decision)
    return_to = (request.args.get("return_to") or request.referrer or q("/tasks")).strip()
    if not result.get("ok"):
        print("V51.8.1 estimate approval error:", result)
    return redirect(return_to)


@app.route("/tasks")
def tasks():
    data = load_workspace_data()
    return Response(page(tx("tasks"), tasks_body(data), active="tasks"), mimetype="text/html")


@app.route("/clients")
def clients():
    data = load_workspace_data()
    return Response(page(tx("clients"), clients_body(data), active="clients"), mimetype="text/html")


@app.route("/clients/<client_key>")
def client_profile(client_key):
    name = _client_from_slug(client_key)
    return Response(page(name, client_profile_detail_body(name), active="clients"), mimetype="text/html")


@app.route("/outbox")
def outbox():
    """V51.2: process one state-changing action, then redirect to a clean URL.

    This prevents stale query parameters (especially draft_decision=reset) from being
    re-applied on refresh/redeploy and preserves review, send-prep and recipient states
    as three independent persistent layers.
    """
    draft_key = unquote_plus((request.args.get("draft_key") or "").strip())
    decision = (request.args.get("draft_decision") or "").strip().lower()
    send_prep = (request.args.get("send_prep") or "").strip().lower()
    recipient_action = (request.args.get("recipient_action") or "").strip().lower()
    contact_action = (request.args.get("contact_action") or "").strip().lower()

    if contact_action == "save_mapping":
        client_name = (request.args.get("client_name") or "").strip()
        telegram_chat_id = (request.args.get("telegram_chat_id") or "").strip()
        mapping_note = (request.args.get("mapping_note") or "").strip()
        verified = (request.args.get("verified") or "").strip().lower() in ("yes", "true", "1", "on")
        ok, status, payload = save_telegram_client_contact_mapping_to_db(client_name, telegram_chat_id, verified=verified, note=mapping_note)
        target = q("/outbox")
        sep = "&" if "?" in target else "?"
        conflict_owner = ", ".join(payload.get("conflicting_clients") or []) if isinstance(payload, dict) else ""
        return redirect(
            f"{target}{sep}mapping_status={quote_plus(status)}"
            f"&mapping_client={quote_plus(client_name)}"
            f"&mapping_conflict_owner={quote_plus(conflict_owner)}"
        )

    if contact_action == "deactivate_mapping":
        client_name = (request.args.get("client_name") or "").strip()
        ok, status, payload = deactivate_telegram_client_contact_mapping_to_db(client_name)
        target = q("/outbox")
        sep = "&" if "?" in target else "?"
        return redirect(f"{target}{sep}mapping_status={quote_plus(status)}&mapping_client={quote_plus(client_name)}")

    acted = False
    if draft_key and decision:
        apply_draft_review_decision(draft_key, decision)
        acted = True
    elif draft_key and send_prep == "telegram":
        apply_telegram_send_prep(draft_key)
        acted = True
    elif draft_key and recipient_action == "resolve_telegram":
        apply_telegram_recipient_resolution(draft_key)
        acted = True

    if acted:
        # PRG pattern: remove the state-changing query so browser refresh cannot replay it.
        return redirect(q("/outbox"))

    data = load_workspace_data()
    return Response(page("Outbox", outbox_body(data), active="tasks"), mimetype="text/html")


@app.route("/projects")
def projects():
    data = load_workspace_data()
    return Response(page(tx("projects"), projects_body(data), active="projects"), mimetype="text/html")


@app.route("/calendar")
def calendar():
    body = simple_module_body(tx("calendar"), tx("calendar_sub"), [("Today", "Workspace priorities and follow-ups", "live"), ("Follow-up Friday", "Ask Andris about reply", "scheduled"), ("Upcoming", "Calendar integration placeholder", "next")])
    return Response(page(tx("calendar"), body, active="calendar"), mimetype="text/html")


@app.route("/files")
def files():
    body = simple_module_body(tx("files"), tx("files_sub"), [("Demo client package", "Ready for organization", "document"), ("Invoice admin record", "Linked to workspace", "finance"), ("Estimate draft", "Linked to Demo Client", "estimate")])
    return Response(page(tx("files"), body, active="files"), mimetype="text/html")


@app.route("/analytics")
def analytics():
    data = load_workspace_data()
    c = data["counts"]
    body = work_page_header(tx("analytics"), tx("analytics_sub"))
    body += (
        "<section class='card card-pad'><div class='kpis'>"
        + kpi_card(tx("tasks"), c["tasks_today"], {"text": tx("today"), "href": "/tasks"})
        + kpi_card(tx("followups"), c["followups"], {"text": tx("attention"), "href": "/tasks"})
        + kpi_card(tx("clients"), c["clients"], {"text": tx("crm"), "href": "/clients"})
        + kpi_card(tx("workers"), c["workers"], {"text": tx("active"), "href": "/workers"})
        + "</div></section>"
    )
    return Response(page(tx("analytics"), body, active="analytics"), mimetype="text/html")


@app.route("/exchange")
def exchange():
    data = load_workspace_data()
    return Response(page(tx("exchange"), exchange_body(data), active="exchange"), mimetype="text/html")


@app.route("/diagnostics/telegram-sync")
def diagnostics_telegram_sync():
    return telegram_bridge_db_diagnostics()

@app.route("/health")
def health():
    
    diag = telegram_bridge_db_diagnostics()
    return {
        "ok": True,
        "runtime": "web_app.py",
        "version": WEB_APP_VERSION,
        "language": current_language(),
        "preview_objects": len(WORKSPACE_ACTION_PREVIEWS),
        "approved_preview_objects": len(approved_preview_items()),
        "approved_client_threads": len(approved_client_thread_items()),
        "active_workspace_work_count": approved_workspace_object_count(),
        "pending_or_held_preview_objects": len(pending_or_held_preview_items()),
        "rejected_preview_objects": len(rejected_preview_items()),
        "telegram_intake_sync_items": len(load_existing_telegram_intake_sync()),
        "real_intake_store_items": len(load_real_intake_events_from_db()),
        "existing_task_memory_items": len(load_existing_task_engine_memory_from_db()),
        "existing_voice_photo_items": len(load_existing_voice_photo_state_from_db()),
        "existing_recent_conversation_items": len(load_recent_conversation_state_from_db()),
        "existing_tasks_table_items": len(load_existing_tasks_table_from_db()),
        "db_diagnostic": {
            "database_url_present": diag.get("database_url_present"),
            "db_connect_ok": diag.get("db_connect_ok"),
            "tables": diag.get("tables"),
            "counts": diag.get("counts"),
            "web_reader_counts": diag.get("web_reader_counts"),
            "db_error": diag.get("db_error"),
        },
        "time": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    port = safe_int(os.environ.get("PORT"), 8080)
    app.run(host="0.0.0.0", port=port)
