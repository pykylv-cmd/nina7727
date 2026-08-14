"""
voice_engine.py
NinaOS Voice Intake V1.8.2 — Call Phrase Normalization

Mērķis:
- saglabāt termiņu follow-up balss komandās;
- pārvērst "rīt jāpiezvana Andrim" par īstu Task Engine komandu;
- atstāt pilnu transkripcijas funkciju, lai app.py imports nekristu;
- pirms nodošanas reply routerim pārrakstīt šķību balss tekstu uz stabilu NinaOS komandu.
"""

import os
import re
import tempfile

VOICE_ENGINE_VERSION = "Voice Intake V1.8.2 — Call Phrase Normalization"

LAST_VOICE_DEBUG = {
    "raw": "",
    "cleaned": "",
    "route": "",
    "error": "",
}


WEEKDAY_ALIASES = {
    "šodien": "šodien",
    "sodien": "šodien",
    "rīt": "rīt",
    "rit": "rīt",
    "parīt": "parīt",
    "parit": "parīt",
    "pirmdien": "pirmdien",
    "otrdien": "otrdien",
    "trešdien": "trešdien",
    "tresdien": "trešdien",
    "ceturtdien": "ceturtdien",
    "piektdien": "piektdien",
    "piekdien": "piektdien",
    "piktdien": "piektdien",
    "sestdien": "sestdien",
    "svētdien": "svētdien",
    "svetdien": "svētdien",
}


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.8.2 — Call Phrase Normalization ir aktīvs. ✅\n\n"
        "Ko tas labo:\n"
        "• follow-up balss komandās saglabā termiņu;\n"
        "• 'piektdien jāpajautā Andrim par atbildi' paliek ar piektdien;\n"
        "• agresīvāk labo šķībus zvana transkriptus, piemēram: pas van andriu → rīt jāzvana Andrim;\n"
        "• Initiative balss komandas paliek Initiative ceļā.\n\n"
        "Testi:\n"
        "• piektdien jāpajautā Andrim par atbildi\n"
        "• rīt jāpiezvana Andrim\n"
        "• ko man tagad darīt\n\n"
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


def audio_suffix_for_mime(mime_type="", filename="voice.ogg"):
    mime = str(mime_type or "").lower().split(";", 1)[0].strip()
    mime_suffixes = {
        "audio/aac": ".aac",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/x-m4a": ".m4a",
        "audio/x-wav": ".wav",
        "video/webm": ".webm",
    }
    if mime in mime_suffixes:
        return mime_suffixes[mime]
    name = (filename or "voice.ogg").lower().strip()
    for suffix in [".ogg", ".oga", ".opus", ".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga", ".aac"]:
        if name.endswith(suffix):
            return suffix
    return ".ogg"


def _safe_suffix(filename):
    return audio_suffix_for_mime(filename=filename)


def transcription_context_prompt(language_hint=""):
    language_names = {"lv": "Latvian", "en": "English", "ru": "Russian"}
    hint_name = language_names.get(str(language_hint or "").lower(), "")
    language_note = f"Speech may primarily be in {hint_name}. " if hint_name else ""
    return (
        language_note
        + "Transcribe exactly in the language or languages spoken; do not translate. "
        + "Helpful business vocabulary: uzdevums, izveido uzdevumu, atgādini, piezvanīt, "
        + "klients, piedāvājums, projekts, rīt, šodien; task, create task, remind me, call, "
        + "client, offer, project, tomorrow, today; задача, создай задачу, напомни, позвонить, "
        + "клиент, предложение, проект, завтра, сегодня."
    )


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


def transcribe_audio_with_openai(
    openai_client,
    audio_bytes,
    filename="voice.ogg",
    language_hint="lv",
    force_language=True,
    model="whisper-1",
    mime_type="",
    context_prompt="",
):
    """Telegram audio bytes -> teksts. Pilnā funkcija, lai app.py imports nekristu."""
    if not openai_client:
        LAST_VOICE_DEBUG["error"] = "OpenAI client nav pieejams"
        return ""

    audio_bytes = audio_bytes or b""
    if not audio_bytes:
        LAST_VOICE_DEBUG["error"] = "audio bytes ir tukšs"
        return ""

    suffix = audio_suffix_for_mime(mime_type=mime_type, filename=filename)
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        with open(temp_path, "rb") as audio_file:
            transcription_args = {
                "model": model,
                "file": audio_file,
                "response_format": "text",
            }
            if language_hint and force_language:
                transcription_args["language"] = language_hint
            prompt = str(context_prompt or "").strip()
            if prompt:
                transcription_args["prompt"] = prompt
            elif language_hint and not force_language:
                transcription_args["prompt"] = transcription_context_prompt(language_hint)
            try:
                result = openai_client.audio.transcriptions.create(**transcription_args)
            except TypeError:
                audio_file.seek(0)
                result = openai_client.audio.transcriptions.create(
                    model=model,
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


def _normalize_deadline(lower):
    for bad, good in WEEKDAY_ALIASES.items():
        lower = lower.replace(bad, good)
    return lower


def _detect_deadline(lower):
    lower = _normalize_deadline(lower)
    for canonical in ["šodien", "rīt", "parīt", "pirmdien", "otrdien", "trešdien", "ceturtdien", "piektdien", "sestdien", "svētdien"]:
        if canonical in lower:
            return canonical
    return ""


def _cleanup_noise(text):
    text = str(text or "").strip()
    if not text:
        return ""

    lower = text.lower()
    lower = _normalize_deadline(lower)

    replacements = {
        # call / phone noisy Latvian transcription variants
        "pas van": "jāzvana",
        "pasvan": "jāzvana",
        "paz van": "jāzvana",
        "pazvan": "jāzvana",
        "pa zvan": "jāzvana",
        "paz vana": "jāzvana",
        "pas vana": "jāzvana",
        "pēs van": "jāzvana",
        "pies van": "jāzvana",
        "piez van": "jāzvana",
        "zvan andriu": "jāzvana andrim",
        "jāzvan andriu": "jāzvana andrim",
        "jāzvana andriu": "jāzvana andrim",
        "pazūnīt": "piezvanīt",
        "pazunīt": "piezvanīt",
        "pazudīt": "piezvanīt",
        "pazūdīt": "piezvanīt",
        "pazvanīt": "piezvanīt",
        "jābiedz vana": "jāpiezvana",
        "jābeidz vana": "jāpiezvana",
        "jābied zvan": "jāpiezvana",
        "jābiezvana": "jāpiezvana",
        "jābeidz zvan": "jāpiezvana",
        "beidz vana": "piezvana",
        "biedz vana": "piezvana",
        "jā zvan": "jāzvana",
        "jazvana": "jāzvana",
        "japiezvana": "jāpiezvana",
        "jāpiezvana": "jāpiezvana",
        "piezvani": "jāpiezvana",
        "piezvanit": "piezvanīt",
        "piezvanīt": "jāpiezvana",
        # follow-up / question variants
        "japajauta": "jāpajautā",
        "jā pajautā": "jāpajautā",
        "pajautāt": "jāpajautā",
        "pajautā": "jāpajautā",
        "jautāt": "jāpajautā",
        "jauta": "jāpajautā",
        # offer variants
        "janosuta": "jānosūta",
        "jā nosūta": "jānosūta",
        "nosūtīt": "jānosūta",
        "nosutit": "jānosūta",
        "piedavajumu": "piedāvājumu",
        "piedavajums": "piedāvājums",
        "piedavaj": "piedāvāj",
        # names
        "antrim": "andrim",
        "andriem": "andrim",
        "uandrim": "andrim",
        "andram": "andrim",
        "andriu": "andrim",
        "andriu.": "andrim",
        "andru": "andrim",
        "andriju": "andrim",
    }

    for bad, good in replacements.items():
        lower = lower.replace(bad, good)

    lower = re.sub(r"\b(ā|nu|emm|mm|eee|eu|nu jā|vienkārši|lūdzu|ludzu)\b", " ", lower)
    lower = _normalize_spaces(lower)

    lower = re.sub(r"\bandris\b", "Andris", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandrim\b", "Andrim", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bandri\b", "Andri", lower, flags=re.IGNORECASE)

    return lower.strip()


def _has_andris(lower):
    return "andr" in lower


def _route_command(text):
    lower = (text or "").lower().strip()
    deadline = _detect_deadline(lower)

    # Strict command routing first
    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "kas svarigakais", "ar ko sākt", "ar ko sakt", "ko iesaki"]):
        return "ko man tagad darīt", "initiative"
    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "mana diena", "daily_brief"
    if lower in ["klienti", "mani klienti", "klientu pārskats", "klientu parskats"]:
        return "klienti", "clients"

    # Follow-up: always preserve deadline when it exists
    if _has_andris(lower) and ("jāpajaut" in lower or "pajaut" in lower or "jaut" in lower or "atbild" in lower or "follow" in lower):
        prefix = (deadline + " ") if deadline else ""
        return f"{prefix}jāpajautā Andrim par atbildi".strip(), "followup"

    # Offer task
    if _has_andris(lower) and ("piedāvāj" in lower or "piedavaj" in lower or "tāme" in lower or "tame" in lower):
        prefix = (deadline + " ") if deadline else ""
        return f"{prefix}jānosūta piedāvājums Andrim".strip(), "task"

    # Call task: catch all zvan/piezvan/pas-van variants, preserve deadline
    call_markers = ["piezvan", "jāzvan", "jazvan", "zvan", "vana", "pas van", "pasvan", "paz van", "pazvan"]
    if _has_andris(lower) and any(marker in lower for marker in call_markers):
        prefix = (deadline + " ") if deadline else ""
        return f"{prefix}jāzvana Andrim".strip(), "task"

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
