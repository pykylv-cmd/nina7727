"""
reply_builder.py
NinaOS Core 2.5.1 — Reply Builder V1.0
"""
reply_builder.py
NinaOS Core 2.5.1 — Reply Builder V1.0

Mērķis:
- centrāli sakārtot gala atbildi pirms sūtīšanas lietotājam;
- neļaut vecajiem routeriem pārrakstīt labu moduļa atbildi;
- uzturēt vienotu NinaOS publisko toni Telegram kanālā.
"""

import re

REPLY_BUILDER_VERSION = "Reply Builder V1.0"
APP_VERSION = "V115.3 + Core 2.5.1"


_VERSION_PATTERNS = [
    r"\n{0,2}Versija:\s*V[0-9.]+\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*Core\s*2\.5\.1\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*.*$",
]


def rb_clean_text(value):
    """Notīra liekas versiju rindas, tukšumus un tehnisko troksni."""
    text = str(value or "").strip()
    if not text:
        return ""

    for pattern in _VERSION_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

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

    # Viena versijas rinda. Ne dubultojam vecās V114/V115 rindas.
    if "Versija:" not in text:
        text = text.rstrip() + f"\n\nVersija: {APP_VERSION}"
    else:
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


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Core 2.5.1 — Reply Builder V1.0 ir aktīvs. ✅\n\n"
        "Gala atbildes pirms sūtīšanas iet caur vienu centrālo komunikācijas slāni.\n\n"
        "Ko tas dod:\n"
        "• moduļi drīkst sagatavot saturu;\n"
        "• Reply Builder sakārto gala tekstu;\n"
        "• vecās versiju rindas netiek dubultotas;\n"
        "• laba moduļa atbilde netiek pārrakstīta ar fallback.\n\n"
        "Tests:\n"
        "• klienti\n"
        "• kas notiek ar Andri\n"
        "• ko man tagad darīt\n"
        "• mana diena",
        source="reply_builder_status",
    )

Mērķis:
- centrāli sakārtot gala atbildi pirms sūtīšanas lietotājam;
- neļaut vecajiem routeriem pārrakstīt labu moduļa atbildi;
- uzturēt vienotu NinaOS publisko toni Telegram kanālā.
"""

import re

REPLY_BUILDER_VERSION = "Reply Builder V1.0"
APP_VERSION = "V115.3 + Core 2.5.1"


_VERSION_PATTERNS = [
    r"\n{0,2}Versija:\s*V[0-9.]+\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*Core\s*2\.5\.1\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*.*$",
]


def rb_clean_text(value):
    """Notīra liekas versiju rindas, tukšumus un tehnisko troksni."""
    text = str(value or "").strip()
    if not text:
        return ""

    for pattern in _VERSION_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

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

    # Viena versijas rinda. Ne dubultojam vecās V114/V115 rindas.
    if "Versija:" not in text:
        text = text.rstrip() + f"\n\nVersija: {APP_VERSION}"
    else:
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


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Core 2.5.1 — Reply Builder V1.0 ir aktīvs. ✅\n\n"
        "Gala atbildes pirms sūtīšanas iet caur vienu centrālo komunikācijas slāni.\n\n"
        "Ko tas dod:\n"
        "• moduļi drīkst sagatavot saturu;\n"
        "• Reply Builder sakārto gala tekstu;\n"
        "• vecās versiju rindas netiek dubultotas;\n"
        "• laba moduļa atbilde netiek pārrakstīta ar fallback.\n\n"
        "Tests:\n"
        "• klienti\n"
        "• kas notiek ar Andri\n"
        "• ko man tagad darīt\n"
        "• mana diena",
        source="reply_builder_status",
    )
