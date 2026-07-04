"""
context_engine.py
NinaOS Core 2.7 — Context V1

Mērķis:
- uzturēt aktīvo darba kontekstu vienas runtime sesijas laikā;
- atcerēties pēdējo klientu / darba objektu;
- pārrakstīt nepilnas komandas pilnā NinaOS komandā pirms routeriem.

Piemēri:
- "piezvani viņam rīt" -> "rīt jāzvana Andrim"
- "pajautā piektdien" -> "piektdien jāpajautā Andrim par atbildi"
- "kas ar viņu" -> "kas notiek ar Andri"
- "ok, un pēc tam?" -> "ko man tagad darīt"
"""

import re
from datetime import datetime, timezone

CONTEXT_ENGINE_VERSION = "Core 2.7.1 — Context Dedup Fix"
_ACTIVE_CONTEXT = {}


def _clean(text):
    return str(text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _normalize_client(name):
    raw = _clean(name).strip(" .,!?:;\"'")
    if not raw:
        return ""
    known = {
        "andris": "Andris",
        "andri": "Andris",
        "andrim": "Andris",
        "andriu": "Andris",
        "andriem": "Andris",
    }
    return known.get(raw.lower(), raw[:1].upper() + raw[1:])


def extract_client_name(text):
    raw = _clean(text)
    lower = raw.lower()

    for token in ["andrim", "andri", "andris", "andriu", "andriem"]:
        if re.search(rf"\b{token}\b", lower):
            return "Andris"

    patterns = [
        r"kas\s+(?:notiek\s+)?ar\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)",
        r"(?:klients|klientam|piedāvājums|piedavajums|jāzvana|jazvana|jāpiezvana|japiezvana|jāpajautā|japajauta).*?\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b",
        r"\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw)
        if m:
            name = _normalize_client(m.group(1))
            if name.lower() not in {"nina", "telegram", "core", "voice", "context"}:
                return name
    return ""



def client_accusative(name):
    n = _normalize_client(name)
    if n == "Andris":
        return "Andri"
    if n.endswith("s"):
        return n[:-1] + "u"
    return n


def client_dative(name):
    n = _normalize_client(name)
    if n == "Andris":
        return "Andrim"
    if n.endswith("s"):
        return n[:-1] + "am"
    return n


def detect_deadline_word(text):
    lower = _lower(text)
    words = [
        "šodien", "sodien", "rīt", "rit", "parīt", "parit",
        "pirmdien", "otrdien", "trešdien", "tresdien", "ceturtdien",
        "piektdien", "sestdien", "svētdien", "svetdien",
    ]
    for word in words:
        if re.search(rf"\b{word}\b", lower):
            return {"rit": "rīt", "sodien": "šodien", "parit": "parīt", "tresdien": "trešdien", "svetdien": "svētdien"}.get(word, word)
    return ""


def get_active_context(user_id):
    return dict(_ACTIVE_CONTEXT.get(str(user_id), {}))


def clear_context(user_id):
    _ACTIVE_CONTEXT.pop(str(user_id), None)


def update_context_from_text(user_id, text, source="incoming"):
    user_id = str(user_id)
    text = _clean(text)
    if not text:
        return get_active_context(user_id)

    ctx = _ACTIVE_CONTEXT.get(user_id, {})
    client = extract_client_name(text)
    if client:
        ctx["client"] = client
        ctx["last_client"] = client

    lower = text.lower()
    if "piedāvāj" in lower or "piedavaj" in lower:
        ctx["topic"] = "piedāvājums"
    if "jāpajautā" in lower or "japajauta" in lower or "par atbildi" in lower or "follow" in lower:
        ctx["topic"] = "follow-up"
    if "jāzvana" in lower or "jazvana" in lower or "jāpiezvana" in lower or "japiezvana" in lower:
        ctx["topic"] = "zvans"
    if any(x in lower for x in ["ko man tagad darīt", "kas svarīgākais", "kas svarigakais", "ar ko sākt", "ar ko sakt"]):
        ctx["topic"] = "initiative"

    deadline = detect_deadline_word(text)
    if deadline:
        ctx["last_deadline"] = deadline

    ctx["last_text"] = text
    ctx["source"] = source
    ctx["updated_at"] = _now()
    _ACTIVE_CONTEXT[user_id] = ctx
    return dict(ctx)


def _has_pronoun(text):
    lower = _lower(text)
    return any(re.search(rf"\b{p}\b", lower) for p in ["viņam", "vinam", "viņu", "vinu", "viņš", "vins", "tas", "to", "tur"])


def resolve_context_command(text, context):
    raw = _clean(text)
    if not raw:
        return raw

    lower = raw.lower().strip(" .!?;")
    ctx = context or {}
    client = ctx.get("client") or ctx.get("last_client") or ""
    deadline = detect_deadline_word(raw) or ctx.get("last_deadline") or ""

    # Explicit commands stay unchanged.
    if extract_client_name(raw) and not _has_pronoun(raw):
        return raw

    if lower in ["context", "context status", "konteksts", "konteksta statuss"]:
        return raw

    # Initiative continuation.
    if lower in ["pēc tam", "pec tam", "un pēc tam", "un pec tam", "ok un pēc tam", "ok un pec tam", "tālāk", "talak"]:
        return "ko man tagad darīt"

    # Client view pronouns.
    if client and (lower.startswith("kas ar viņ") or lower.startswith("kas ar vin") or lower in ["kas ar viņu", "kas ar vinu", "ko ar viņu", "ko ar vinu"]):
        return f"kas notiek ar {client_accusative(client)}"

    # Call commands with pronouns.
    if client and any(x in lower for x in ["piezvani", "jāpiezvana", "japiezvana", "jāzvana", "jazvana", "zvani", "zvanīt", "zvanit"]):
        when = deadline or ""
        if when:
            return f"{when} jāzvana {client_dative(client)}"
        return f"jāzvana {client_dative(client)}"

    # Follow-up commands with missing client.
    if client and any(x in lower for x in ["pajautā", "pajauta", "jāpajautā", "japajauta", "par atbildi", "atbildi"]):
        when = deadline or ""
        if when:
            return f"{when} jāpajautā {client_dative(client)} par atbildi"
        return f"jāpajautā {client_dative(client)} par atbildi"

    # Offer command missing client.
    if client and any(x in lower for x in ["piedāvājumu", "piedavajumu", "piedāvājums", "piedavajums", "nosūti", "nosuti", "jānosūta", "janosuta"]):
        if any(x in lower for x in ["piedāv", "piedav", "nosū", "nosu"]):
            when = deadline or ""
            if when:
                return f"{when} jānosūta piedāvājums {client_dative(client)}"
            return f"jānosūta piedāvājums {client_dative(client)}"

    return raw


def context_status_answer(user_id=None):
    ctx = get_active_context(user_id or "default") if user_id is not None else {}
    lines = [
        "🧠 Core 2.7.1 — Context Dedup Fix ir aktīvs. ✅",
        "",
        "Ko tas dara:",
        "• atceras pēdējo darba klientu;",
        "• saprot īsās komandas ar 'viņam/viņu/to/tur';",
        "• pārraksta nepilnu komandu pilnā NinaOS darba komandā.",
        "",
        "Testi:",
        "• kas notiek ar Andri",
        "• piezvani viņam rīt",
        "• pajautā piektdien",
        "• ko ar viņu darām",
        "",
        f"Versija: {CONTEXT_ENGINE_VERSION}",
    ]
    if ctx:
        lines.extend([
            "",
            "Aktīvais konteksts:",
            f"• klients: {ctx.get('client') or ctx.get('last_client') or '-'}",
            f"• tēma: {ctx.get('topic') or '-'}",
            f"• termiņš: {ctx.get('last_deadline') or '-'}",
        ])
    return "\n".join(lines)


def context_debug_answer(user_id):
    ctx = get_active_context(user_id)
    if not ctx:
        return f"🧠 Context debug\n\nNav aktīva konteksta.\n\nVersija: {CONTEXT_ENGINE_VERSION}"
    lines = ["🧠 Context debug", ""]
    for key in sorted(ctx.keys()):
        lines.append(f"{key}: {ctx.get(key)}")
    lines.append("")
    lines.append(f"Versija: {CONTEXT_ENGINE_VERSION}")
    return "\n".join(lines)
