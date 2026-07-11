"""
reply_builder.py
NinaOS Core 2.5.2 — Reply Builder Polish V1.1

Mērķis:
- centrāli sakārtot gala atbildi pirms sūtīšanas lietotājam;
- noņemt visas vecās moduļu/APP versiju rindas;
- atstāt tikai vienu gala versijas rindu;
- uzturēt vienotu NinaOS publisko toni Telegram kanālā.
"""
"""
reply_builder.py
NinaOS Reply Builder V1.1 — ONE NINA Canonical Estimate Draft

Central communication layer for NinaOS.
Business actions pass structured canonical context into this module.
The Reply Builder does not extract Telegram/Web text and does not persist work truth.
"""

from __future__ import annotations

import re
from typing import Any, Dict

REPLY_BUILDER_VERSION = "Reply Builder V1.1 — ONE NINA Canonical Estimate Draft"
APP_VERSION = "V116.5 + ONE NINA Canonical Estimate Action V1"

_VERSION_PATTERNS = [
    r"\n{0,2}Versija:\s*V[0-9.]+\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*Core\s*2\.5\.1\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*.*$",
]


def rb_clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern in _VERSION_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def rb_detect_intent(text: str) -> str:
    lower = (text or "").strip().lower()
    if not lower:
        return "empty"
    if any(x in lower for x in ["premium", "abonements", "pirkt", "cena", "tarifs"]):
        return "business"
    if any(x in lower for x in [
        "klienti", "andri", "andris", "piedāvājums", "piedavajums",
        "follow-up", "followup", "jāpajautā", "japajauta"
    ]):
        return "client_work"
    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "daily_brief"
    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "ko iesaki"]):
        return "initiative"
    if any(x in lower for x in ["core", "ninaos", "initiative", "think engine", "learning", "quality", "reply builder"]):
        return "ninaos_core"
    if any(x in lower for x in ["čau", "cau", "sveika", "sveiks", "hello", "hi", "kā tev iet", "ka tev iet"]):
        return "conversation"
    return "general"


def rb_detect_tone(text: str) -> str:
    lower = (text or "").strip().lower()
    if any(x in lower for x in ["smagi", "grūti", "gruti", "slikti", "noguris", "nogurusi", "bēdīgi", "bedigi"]):
        return "supportive"
    if any(x in lower for x in ["premium", "cena", "tarifs", "pirkt", "abonements"]):
        return "commercial_warm"
    if any(x in lower for x in ["core", "ninaos", "architecture", "arhitekt", "engine"]):
        return "architectural"
    return "warm"


def build_reply_object(main_message="", user_text="", source="legacy_router", intent="", tone="", channel="telegram", metadata=None):
    return {
        "intent": intent or rb_detect_intent(user_text or main_message),
        "tone": tone or rb_detect_tone(user_text or main_message),
        "priority": "normal",
        "identity": "Nina — AI darbiniece NinaOS platformā",
        "main_message": main_message or "",
        "channel": channel or "telegram",
        "metadata": metadata or {"source": source},
    }


def reply_builder_build(reply_object):
    if isinstance(reply_object, str):
        reply_object = build_reply_object(main_message=reply_object)
    if not isinstance(reply_object, dict):
        reply_object = build_reply_object(main_message=str(reply_object or ""))

    text = rb_clean_text(reply_object.get("main_message", ""))
    if not text:
        text = "Esmu te. 😊\n\nPasaki, ko vajag sakārtot, un es palīdzēšu soli pa solim."

    channel = (reply_object.get("channel") or "telegram").lower()
    if channel == "telegram" and len(text) > 3800:
        text = text[:3700].rstrip() + "\n\n…"

    if not reply_object.get("client_deliverable"):
        text = rb_clean_text(text).rstrip() + f"\n\nVersija: {APP_VERSION}"

    return {
        "text": text,
        "buttons": [],
        "attachments": [],
        "actions": [],
        "metadata": {
            "builder": REPLY_BUILDER_VERSION,
            "intent": reply_object.get("intent", ""),
            "tone": reply_object.get("tone", ""),
            **(reply_object.get("metadata") or {}),
        },
    }


def reply_builder_text(text, user_text="", source="legacy_router", channel="telegram"):
    obj = build_reply_object(
        main_message=text,
        user_text=user_text,
        source=source,
        channel=channel,
    )
    return reply_builder_build(obj).get("text", "")


def _display_amount(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        number = float(value)
        if number.is_integer():
            return f"{int(number):,}".replace(",", " ")
        return f"{number:,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value).strip()


def build_client_estimate_draft(business_details: Dict[str, Any]) -> Dict[str, Any]:
    """Build a client-ready estimate draft from canonical structured fields only."""
    details = dict(business_details or {})
    client_name = str(details.get("client_name") or "").strip()
    subject = str(details.get("subject") or "").strip()
    currency = str(details.get("currency") or "EUR").strip().upper()
    start_context = str(details.get("start_context") or "").strip()
    amount = _display_amount(details.get("amount"))

    missing = []
    if not client_name:
        missing.append("client_name")
    if not subject:
        missing.append("subject")
    if not amount:
        missing.append("amount")

    if missing:
        return {
            "ok": False,
            "error": "missing_canonical_business_details",
            "missing": missing,
            "text": "",
            "builder": REPLY_BUILDER_VERSION,
        }

    lines = [
        f"Labdien, {client_name}!",
        "",
        f"Sagatavojām piedāvājumu par {subject}.",
        f"Kopējā piedāvājuma summa ir {amount} {currency}.",
    ]
    if start_context:
        lines.extend(["", f"Darbus varam uzsākt {start_context}."])
    lines.extend([
        "",
        "Ja piedāvājums Jums ir pieņemams, dodiet ziņu, un vienosimies par nākamajiem soļiem.",
        "",
        "Ar cieņu",
    ])

    reply_object = build_reply_object(
        main_message="\n".join(lines),
        source="canonical_estimate_action_v1",
        intent="client_estimate_draft",
        tone="professional_warm",
        channel="client_deliverable",
        metadata={"source": "canonical_estimate_action_v1"},
    )
    reply_object["client_deliverable"] = True
    built = reply_builder_build(reply_object)
    return {
        "ok": True,
        "text": built["text"],
        "builder": REPLY_BUILDER_VERSION,
        "missing": [],
    }


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Reply Builder ir aktīvs kā ONE NINA centrālais komunikācijas slānis. ✅\n\n"
        "Canonical estimate actions var nodot strukturētus business_details un saņemt klientam gatavu draftu.",
        source="reply_builder_status",
    )

import re

REPLY_BUILDER_VERSION = "Reply Builder Polish V1.1"
APP_VERSION = "V115.4 + Core 2.5.2"


def rb_remove_version_lines(text):
    """Noņem jebkuru rindu, kas sākas ar 'Versija:'."""
    lines = str(text or "").splitlines()
    cleaned = []
    for line in lines:
        if re.match(r"^\s*Versija\s*:", line or "", flags=re.IGNORECASE):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def rb_clean_text(value):
    """Notīra liekas versiju rindas, tukšumus un tehnisko troksni."""
    text = str(value or "").strip()
    if not text:
        return ""

    text = rb_remove_version_lines(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def rb_detect_intent(text):
    lower = (text or "").strip().lower()
    if not lower:
        return "empty"

    if any(x in lower for x in ["premium", "abonements", "pirkt", "cena", "tarifs"]):
        return "business"

    if any(x in lower for x in [
        "klienti", "andri", "andris", "piedāvājums", "piedavajums",
        "follow-up", "followup", "jāpajautā", "japajauta"
    ]):
        return "client_work"

    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "daily_brief"

    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "ko iesaki"]):
        return "initiative"

    if any(x in lower for x in ["core", "ninaos", "initiative", "think engine", "learning", "quality", "reply builder"]):
        return "ninaos_core"

    if any(x in lower for x in ["čau", "cau", "sveika", "sveiks", "hello", "hi", "kā tev iet", "ka tev iet"]):
        return "conversation"

    return "general"


def rb_detect_tone(text):
    lower = (text or "").strip().lower()

    if any(x in lower for x in ["smagi", "grūti", "gruti", "slikti", "noguris", "nogurusi", "bēdīgi", "bedigi"]):
        return "supportive"

    if any(x in lower for x in ["premium", "cena", "tarifs", "pirkt", "abonements"]):
        return "commercial_warm"

    if any(x in lower for x in ["core", "ninaos", "architecture", "arhitekt", "engine"]):
        return "architectural"

    return "warm"


def build_reply_object(main_message="", user_text="", source="legacy_router", intent="", tone="", channel="telegram", metadata=None):
    return {
        "intent": intent or rb_detect_intent(user_text or main_message),
        "tone": tone or rb_detect_tone(user_text or main_message),
        "priority": "normal",
        "identity": "Nina — AI darbiniece NinaOS platformā",
        "main_message": main_message or "",
        "channel": channel or "telegram",
        "metadata": metadata or {"source": source},
    }


def reply_builder_build(reply_object):
    if isinstance(reply_object, str):
        reply_object = build_reply_object(main_message=reply_object)

    if not isinstance(reply_object, dict):
        reply_object = build_reply_object(main_message=str(reply_object or ""))

    text = rb_clean_text(reply_object.get("main_message", ""))

    if not text:
        text = "Esmu te. 😊\n\nPasaki, ko vajag sakārtot, un es palīdzēšu soli pa solim."

    channel = (reply_object.get("channel") or "telegram").lower()

    if channel == "telegram" and len(text) > 3800:
        text = text[:3700].rstrip() + "\n\n…"

    # Core 2.5.2: vienmēr tikai viena gala versijas rinda.
    text = rb_remove_version_lines(text).rstrip()
    text = text + f"\n\nVersija: {APP_VERSION}"

    return {
        "text": text,
        "buttons": [],
        "attachments": [],
        "actions": [],
        "metadata": {
            "builder": REPLY_BUILDER_VERSION,
            "intent": reply_object.get("intent", ""),
            "tone": reply_object.get("tone", ""),
            **(reply_object.get("metadata") or {}),
        },
    }


def reply_builder_text(text, user_text="", source="legacy_router", channel="telegram"):
    obj = build_reply_object(
        main_message=text,
        user_text=user_text,
        source=source,
        channel=channel,
    )
    return reply_builder_build(obj).get("text", "")


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Core 2.5.2 — Reply Builder Polish V1.1 ir aktīvs. ✅\n\n"
        "Gala atbildes pirms sūtīšanas iet caur vienu centrālo komunikācijas slāni.\n\n"
        "Ko šis polish labo:\n"
        "• noņem dubultās Versija rindas;\n"
        "• saglabā moduļa saturu;\n"
        "• pieliek tikai vienu gala versiju;\n"
        "• laba moduļa atbilde netiek pārrakstīta ar fallback.\n\n"
        "Tests:\n"
        "• klienti\n"
        "• kas notiek ar Andri\n"
        "• ko man tagad darīt\n"
        "• mana diena",
        source="reply_builder_status",
    )
