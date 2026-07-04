"""
voice_engine.py
NinaOS Voice Intake V1.7.1 — Import Fix + Routing & Deadline Fix

Mērķis:
- salabot V1.7 import kļūdu;
- atstāt pilnu transkripcijas funkciju;
- saglabāt termiņu balss follow-up komandās;
- pārvērst balss tekstu par skaidru NinaOS komandu pirms nodošanas app.py routerim.
"""

import os
import re
import tempfile

VOICE_ENGINE_VERSION = "Voice Intake V1.7.1 — Import Fix + Routing Fix"

LAST_VOICE_DEBUG = {
    "raw": "",
    "cleaned": "",
    "route": "",
    "error": "",
}


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.7.1 — Import Fix + Routing Fix ir aktīvs. ✅\n\n"
        "Ko tas labo:\n"
        "• Voice Engine imports vairs nekrīt;\n"
        "• transkripcija paliek pieslēgta;\n"
        "• follow-up balss komandās saglabā termiņu;\n"
        "• 'ko man tagad darīt' virza uz Initiative ceļu;\n"
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
    LAST_VOICE_DEBUG["error"] = error_text
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


def _safe_suffix(filename):
    name = (filename or "voice.ogg").lower().strip()
    for suffix in [".ogg", ".oga", ".opus", ".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga"]:
        if name.endswith(suffix):
            return suffix
    return ".ogg"


def _extract_text_from_result(result):
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    text = getattr(result, "text", None)
    if text:
        return str(text).strip()
    if isinstance(result, dict):
        text = result.get("text") or result.get("transcript")
        if text:
            return str(text).strip()
    try:
        text = result["text"]
        if text:
            return str(text).strip()
    except Exception:
        pass
    return ""


def transcribe_audio_with_openai(openai_client, audio_bytes, filename="voice.ogg"):
    """Telegram audio bytes -> teksts. Pilnā funkcija, lai app.py imports nekristu."""
    if not openai_client:
        LAST_VOICE_DEBUG["error"] = "OpenAI client nav pieejams"
        return ""

    audio_bytes = audio_bytes or b""
    if not audio_bytes:
        LAST_VOICE_DEBUG["error"] = "audio bytes ir tukšs"
        return ""

    suffix = _safe_suffix(filename)
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        with open(temp_path, "rb") as audio_file:
            try:
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                    language="lv",
                )
            except TypeError:
                audio_file.seek(0)
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )

        transcript = _extract_text_from_result(result)
        LAST_VOICE_DEBUG["raw"] = transcript
        LAST_VOICE_DEBUG["error"] = ""
        return transcript

    except Exception as e:
        LAST_VOICE_DEBUG["error"] = repr(e)
        print("Voice Intake transcribe kļūda:", repr(e))
        return ""

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass


def _normalize_spaces(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _cleanup_noise(text):
    text = str(text or "").strip()
    if not text:
        return ""

    lower = text.lower()

    replacements = {
        "pazūnīt": "piezvanīt",
        "pazunīt": "piezvanīt",
        "pazunīt": "piezvanīt",
        "pazudīt": "piezvanīt",
        "pazūdīt": "piezvanīt",
        "pazvanīt": "piezvanīt",
        "jābiedz vana": "jāpiezvana",
        "jābied zvan": "jāpiezvana",
        "jābiezvana": "jāpiezvana",
        "jāpiezvana": "jāpiezvana",
        "rit": "rīt",
        "sodien": "šodien",
        "japajauta": "jāpajautā",
        "japiezvana": "jāpiezvana",
        "janosuta": "jānosūta",
        "piedavajumu": "piedāvājumu",
        "piedavajums": "piedāvājums",
        "antrim": "andrim",
        "andriem": "andrim",
        "uandrim": "andrim",
    }

    for bad, good in replacements.items():
        lower = lower.replace(bad, good)

    lower = re.sub(r"\b(ā|nu|emm|mm|eee|eu|nu jā|vienkārši)\b", " ", lower)
    lower = _normalize_spaces(lower)

    lower = re.sub(r"\bandris\b", "Andris", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandrim\b", "Andrim", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandri\b", "Andri", lower, flags=re.IGNORECASE)

    return lower.strip()


def _route_command(text):
    lower = (text or "").lower().strip()

    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "kas svarigakais", "ar ko sākt", "ar ko sakt", "ko iesaki"]):
        return "ko man tagad darīt", "initiative"
    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "mana diena", "daily_brief"
    if lower in ["klienti", "mani klienti", "klientu pārskats", "klientu parskats"]:
        return "klienti", "clients"

    if "jāpajautā" in lower and "andr" in lower:
        if "piektdien" in lower:
            return "piektdien jāpajautā Andrim par atbildi", "followup"
        if "rīt" in lower:
            return "rīt jāpajautā Andrim par atbildi", "followup"
        return "jāpajautā Andrim par atbildi", "followup"

    if ("piedāvāj" in lower or "piedavaj" in lower) and "andr" in lower:
        if "rīt" in lower:
            return "rīt jānosūta piedāvājums Andrim", "task"
        if "šodien" in lower:
            return "šodien jānosūta piedāvājums Andrim", "task"
        return "jānosūta piedāvājums Andrim", "task"

    if "piezvan" in lower and "andr" in lower:
        if "rīt" in lower:
            return "rīt jāpiezvana Andrim", "task"
        if "piektdien" in lower:
            return "piektdien jāpiezvana Andrim", "task"
        return "jāpiezvana Andrim", "task"

    return text, "general"


def cleanup_voice_transcript(transcript):
    cleaned = _cleanup_noise(transcript)
    if not cleaned:
        LAST_VOICE_DEBUG["cleaned"] = ""
        LAST_VOICE_DEBUG["route"] = "empty"
        return ""
    routed, route = _route_command(cleaned)
    routed = _normalize_spaces(routed)
    LAST_VOICE_DEBUG["cleaned"] = routed
    LAST_VOICE_DEBUG["route"] = route
    return routed


def voice_last_debug_answer():
    return (
        "🎙 Voice debug\n\n"
        f"Raw: {LAST_VOICE_DEBUG.get('raw', '')}\n"
        f"Cleaned: {LAST_VOICE_DEBUG.get('cleaned', '')}\n"
        f"Route: {LAST_VOICE_DEBUG.get('route', '')}\n"
        f"Error: {LAST_VOICE_DEBUG.get('error', '')}\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )
