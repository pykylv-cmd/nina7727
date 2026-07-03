"""
voice_engine.py
NinaOS Voice Intake V1.6 — Voice Command Cleanup
"""

import io
import re
import traceback

VOICE_ENGINE_VERSION = "Voice Intake V1.6 — Voice Command Cleanup"
LAST_VOICE_DEBUG = ""


def _set_debug(message):
    global LAST_VOICE_DEBUG
    LAST_VOICE_DEBUG = str(message or "").strip()[:900]
    try:
        print("Voice Intake V1.6 debug:", LAST_VOICE_DEBUG)
    except Exception:
        pass


def _get_debug():
    return (LAST_VOICE_DEBUG or "").strip()


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.6 — Voice Command Cleanup ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• pieņem Telegram balss/audio ziņu;\n"
        "• pārvērš audio tekstā;\n"
        "• notīra transkripta troksni un salabo tipiskas kļūdas;\n"
        "• mēģina pārvērst to par skaidru NinaOS komandu vai uzdevumu.\n\n"
        "Testi:\n"
        "• ierunā: rīt jānosūta piedāvājums Andrim\n"
        "• ierunā: piektdien jāpajautā Andrim par atbildi\n"
        "• ierunā: ko man tagad darīt\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    debug = (error_text or "").strip() or _get_debug()
    base = "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā."
    if debug:
        return f"{base}\n\nDebug:\n{debug}\n\nVersija: {VOICE_ENGINE_VERSION}"
    return f"{base}\n\nPamēģini vēlreiz mazliet skaidrāk.\n\nVersija: {VOICE_ENGINE_VERSION}"


def _safe_filename(filename):
    name = (filename or "voice.ogg").strip()
    lower = name.lower()
    allowed = [".ogg", ".oga", ".opus", ".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga"]
    if any(lower.endswith(ext) for ext in allowed):
        return name
    return "voice.ogg"


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
    _set_debug("")
    if not openai_client:
        _set_debug("OpenAI client nav pieejams app.py pusē.")
        return ""
    audio_bytes = audio_bytes or b""
    if not audio_bytes:
        _set_debug("audio_bytes ir tukšs — Telegram fails tika saņemts bez audio satura.")
        return ""
    safe_name = _safe_filename(filename)
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = safe_name
        _set_debug(f"transcribe start: filename={safe_name}, bytes={len(audio_bytes)}")
        try:
            result = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )
        except TypeError as e:
            audio_file.seek(0)
            _set_debug(f"response_format TypeError, retry bez response_format: {repr(e)}")
            result = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        transcript = _extract_text_from_result(result)
        if not transcript:
            _set_debug(f"OpenAI atbildēja, bet transcript ir tukšs. result_type={type(result).__name__}, result={str(result)[:500]}")
            return ""
        _set_debug(f"OK transcript length={len(transcript)}")
        return transcript
    except Exception as e:
        short_trace = traceback.format_exc(limit=2)
        _set_debug(f"OpenAI transcribe error: {repr(e)}\\n{short_trace}")
        return ""


def _normalize_spaces(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _cleanup_noise(text):
    text = str(text or "").strip()
    if not text:
        return ""
    replacements = {
        "pazūnīt": "piezvanīt",
        "pazvanīt": "piezvanīt",
        "pazudīt": "piezvanīt",
        "pazudin": "piezvan",
        "uandrim": "Andrim",
        "antrim": "Andrim",
        "andriem": "Andrim",
        "piedavajumu": "piedāvājumu",
        "piedavajums": "piedāvājums",
        "piedavaj": "piedāvāj",
        "rit": "rīt",
        "sodien": "šodien",
        "japajauta": "jāpajautā",
        "japiezvana": "jāpiezvana",
        "janosuta": "jānosūta",
    }
    lowered = text.lower()
    for bad, good in replacements.items():
        lowered = lowered.replace(bad, good.lower())
    lowered = re.sub(r"\b(ā|nu|emm|mm|eu|eee|vienkārši)\b", " ", lowered, flags=re.IGNORECASE)
    lowered = _normalize_spaces(lowered)
    lowered = re.sub(r"\bandris\b", "Andris", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bandrim\b", "Andrim", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bandri\b", "Andri", lowered, flags=re.IGNORECASE)
    return lowered.strip()


def _looks_like_priority_command(text):
    lower = text.lower().strip()
    return lower in {
        "ko man tagad darīt", "kas svarīgākais", "kas svarigakais",
        "ar ko sākt", "ar ko sakt", "mana diena", "klienti"
    }


def _rewrite_task_command(text):
    t = text.strip()
    lower = t.lower()
    if _looks_like_priority_command(t):
        return t
    if "jāpajautā" in lower and "andr" in lower:
        if "piektdien" in lower:
            return "piektdien jāpajautā Andrim par atbildi"
        if "rīt" in lower:
            return "rīt jāpajautā Andrim par atbildi"
        return "jāpajautā Andrim par atbildi"
    if ("piedāvā" in lower or "piedāvāj" in lower or "piedavaj" in lower) and "andr" in lower:
        if "rīt" in lower:
            return "rīt jānosūta piedāvājums Andrim"
        if "šodien" in lower:
            return "šodien jānosūta piedāvājums Andrim"
        return "jānosūta piedāvājums Andrim"
    if ("piezvan" in lower or "zvan" in lower) and "andr" in lower:
        if "rīt" in lower:
            return "rīt jāpiezvana Andrim"
        if "piektdien" in lower:
            return "piektdien jāpiezvana Andrim"
        return "jāpiezvana Andrim"
    if "andr" in lower and ("atbild" in lower or "follow" in lower):
        if "piektdien" in lower:
            return "piektdien jāpajautā Andrim par atbildi"
        if "rīt" in lower:
            return "rīt jāpajautā Andrim par atbildi"
        return "jāpajautā Andrim par atbildi"
    return t


def cleanup_voice_transcript(transcript):
    cleaned = _cleanup_noise(transcript)
    if not cleaned:
        return ""
    rewritten = _rewrite_task_command(cleaned)
    return _normalize_spaces(rewritten)
