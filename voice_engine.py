"""
voice_engine.py
NinaOS Voice Intake V1.7 — Routing & Deadline Fix

Mērķis:
- saglabāt termiņu balss follow-up komandās;
- piespiest balss prioritātes komandas iet uz Initiative/Daily/Client ceļu;
- pārvērst 'piezvanīt Andrim' un līdzīgus šķībus transkriptus par īstiem taskiem.
"""

import re

VOICE_ENGINE_VERSION = "Voice Intake V1.7 — Routing & Deadline Fix"


LAST_VOICE_DEBUG = {
    "raw": "",
    "cleaned": "",
    "route": "",
}


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.7 — Routing & Deadline Fix ir aktīvs. ✅\n\n"
        "Ko tas labo:\n"
        "• follow-up balss komandās saglabā termiņu;\n"
        "• 'ko man tagad darīt' virza uz Initiative ceļu;\n"
        "• 'mana diena' virza uz Daily Brief ceļu;\n"
        "• 'klienti' virza uz klientu pārskatu;\n"
        "• 'rīt jāpiezvana Andrim' pārvērš par īstu uzdevumu.\n\n"
        "Testi:\n"
        "• rīt jānosūta piedāvājums Andrim\n"
        "• piektdien jāpajautā Andrim par atbildi\n"
        "• ko man tagad darīt\n"
        "• rīt jāpiezvana Andrim\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    error_text = (error_text or "").strip()
    if error_text:
        return (
            "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
            "Debug:\n"
            f"{error_text}\n\n"
            f"Versija: {VOICE_ENGINE_VERSION}"
        )
    return (
        "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
        "Pamēģini vēlreiz mazliet skaidrāk.\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def _normalize_spaces(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _lv_lower(text):
    return str(text or "").strip().lower()


def _has_any(text, words):
    lower = _lv_lower(text)
    return any(w in lower for w in words)


def _detect_deadline(text):
    lower = _lv_lower(text)
    if _has_any(lower, ["šodien", "sodien", "šodienas"]):
        return "šodien"
    if _has_any(lower, ["rīt", "rit", "riit", "rītdien", "ritdien"]):
        return "rīt"
    if _has_any(lower, ["parīt", "parit"]):
        return "parīt"
    weekdays = [
        ("pirmdien", ["pirmdien"]),
        ("otrdien", ["otrdien"]),
        ("trešdien", ["trešdien", "tresdien"]),
        ("ceturtdien", ["ceturtdien"]),
        ("piektdien", ["piektdien", "piekdien", "piktien", "piekdienā", "piektdienā"]),
        ("sestdien", ["sestdien"]),
        ("svētdien", ["svētdien", "svetdien"]),
    ]
    for canonical, variants in weekdays:
        if any(v in lower for v in variants):
            return canonical
    return ""


def _has_andris(text):
    return _has_any(text, ["andri", "andrim", "andris", "antri", "antrim", "andriem", "andriu", "andri"])


def _cleanup_noise(text):
    text = str(text or "").strip()
    if not text:
        return ""

    lower = text.lower()

    replacements = {
        "pazūnīt": "piezvanīt",
        "pazunīt": "piezvanīt",
        "pazvanīt": "piezvanīt",
        "pazudīt": "piezvanīt",
        "zvanīt": "piezvanīt",
        "piedzvanīt": "piezvanīt",
        "piez vana": "piezvana",
        "biedz vana": "piezvana",
        "biedzvana": "piezvana",
        "biedzu vana": "piezvana",
        "jābiedz vana": "jāpiezvana",
        "jā biezvana": "jāpiezvana",
        "jā piez vana": "jāpiezvana",
        "japiezvana": "jāpiezvana",
        "jāpie zvana": "jāpiezvana",
        "piedavajumu": "piedāvājumu",
        "piedavajums": "piedāvājums",
        "piedāvājums andrim": "piedāvājums Andrim",
        "japajauta": "jāpajautā",
        "jā pajautā": "jāpajautā",
        "janosuta": "jānosūta",
        "jā nosūta": "jānosūta",
        "jaanosuuta": "jānosūta",
        "rit": "rīt",
        "riit": "rīt",
        "sodien": "šodien",
        "piekdien": "piektdien",
        "piktien": "piektdien",
        "antrim": "Andrim",
        "andriem": "Andrim",
        "andrim": "Andrim",
        "andris": "Andris",
        "andri": "Andri",
    }

    for bad, good in replacements.items():
        lower = lower.replace(bad, good.lower())

    # noņem runas parazītvārdus, bet nepieskaras jēgai
    lower = re.sub(r"\b(ā|nu|emm|mm|eee|ēē|eu|nu jā|vienkārši|lūdzu)\b", " ", lower, flags=re.IGNORECASE)
    lower = _normalize_spaces(lower)

    # normalizē Andra formas pēc tīrīšanas
    lower = re.sub(r"\bandrim\b", "Andrim", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandris\b", "Andris", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandri\b", "Andri", lower, flags=re.IGNORECASE)

    return lower.strip()


def _rewrite_system_command(text):
    lower = _lv_lower(text)

    # Initiative komandas — agresīvi virzām uz pārbaudīto tekstu
    if (
        "ko man" in lower and ("tagad" in lower or "darīt" in lower or "darit" in lower)
    ) or _has_any(lower, ["kas svarīgākais", "kas svarigakais", "ko iesaki", "ar ko sākt", "ar ko sakt"]):
        return "ko man tagad darīt", "initiative"

    if _has_any(lower, ["mana diena", "darba inbox", "ko man šodien", "ko man sodien", "šodienas plāns", "sodienas plans"]):
        return "mana diena", "daily_brief"

    if lower.strip() in {"klienti", "mani klienti", "klientu pārskats", "klientu parskats"} or _has_any(lower, ["parādi klientus", "paradi klientus"]):
        return "klienti", "clients"

    return "", ""


def _rewrite_task_command(text):
    t = _normalize_spaces(text)
    lower = _lv_lower(t)
    deadline = _detect_deadline(t)
    deadline_prefix = (deadline + " ") if deadline else ""

    system_cmd, route = _rewrite_system_command(t)
    if system_cmd:
        return system_cmd, route

    # Piedāvājums Andrim
    if _has_andris(lower) and _has_any(lower, ["piedāvāj", "piedavaj", "offer", "tāme", "tame"]):
        return f"{deadline_prefix}jānosūta piedāvājums Andrim".strip(), "task"

    # Follow-up / pajautāt par atbildi Andrim — termiņu saglabājam obligāti
    if _has_andris(lower) and (_has_any(lower, ["jāpajautā", "pajaut", "atbild", "follow"])):
        return f"{deadline_prefix}jāpajautā Andrim par atbildi".strip(), "followup"

    # Piezvanīt Andrim — kā īsts task
    if _has_andris(lower) and _has_any(lower, ["piezvan", "zvan", "jāpiezvana", "japiezvana", "vana"]):
        return f"{deadline_prefix}jāpiezvana Andrim".strip(), "task"

    # Vispārīgs Andris + termiņš + neskaidra darbība: labāk izveidot follow-up, nevis pļāpāt
    if _has_andris(lower) and deadline and _has_any(lower, ["atbild", "jaut", "pajaut", "sazin", "klient"]):
        return f"{deadline_prefix}jāpajautā Andrim par atbildi".strip(), "followup"

    return t, "general"


def cleanup_voice_transcript(transcript):
    raw = str(transcript or "").strip()
    cleaned = _cleanup_noise(raw)
    if not cleaned:
        LAST_VOICE_DEBUG.update({"raw": raw, "cleaned": "", "route": "empty"})
        return ""

    rewritten, route = _rewrite_task_command(cleaned)
    rewritten = _normalize_spaces(rewritten)

    LAST_VOICE_DEBUG.update({"raw": raw, "cleaned": rewritten, "route": route or "general"})
    return rewritten


def voice_last_debug_answer():
    return (
        "🎙 Voice pēdējais debug\n\n"
        f"Raw: {LAST_VOICE_DEBUG.get('raw') or '—'}\n"
        f"Cleaned: {LAST_VOICE_DEBUG.get('cleaned') or '—'}\n"
        f"Route: {LAST_VOICE_DEBUG.get('route') or '—'}\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_debug_answer(original_transcript, cleaned_transcript):
    return (
        "🎙 Voice Cleanup debug\n\n"
        f"Raw: {original_transcript}\n"
        f"Cleaned: {cleaned_transcript}\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )
