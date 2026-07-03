"""
voice_engine.py
NinaOS Voice Intake V1.4 — Debug in Telegram

Mērķis:
- Telegram voice/audio failu sūtīt tieši OpenAI transkripcijai;
- ja transkripcija neizdodas, īso kļūdu parādīt pašā Telegram atbildē;
- netērēt laiku ārējo servera logu meklēšanai;
- app.py un requirements.txt šajā versijā nav jāmaina.
"""

import io
import traceback

VOICE_ENGINE_VERSION = "Voice Intake V1.4 — Debug in Telegram"
LAST_VOICE_DEBUG = ""


def _set_debug(message):
    global LAST_VOICE_DEBUG
    LAST_VOICE_DEBUG = str(message or "").strip()[:900]
    try:
        print("Voice Intake V1.4 debug:", LAST_VOICE_DEBUG)
    except Exception:
        pass


def _get_debug():
    return (LAST_VOICE_DEBUG or "").strip()


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.4 — Debug in Telegram ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• pieņem Telegram balss/audio ziņu;\n"
        "• sūta .ogg/.opus audio tieši transkripcijai;\n"
        "• ja transkripcija neizdodas, kļūdu parāda tepat Telegramā;\n"
        "• app.py un requirements.txt nav jāmaina.\n\n"
        "Tests:\n"
        "• ierunā Telegram voice ziņu: rīt jānosūta piedāvājums Andrim\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    debug = (error_text or "").strip() or _get_debug()

    base = (
        "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
        "Tagad rādu īso tehnisko kļūdu tepat, lai varam salabot bez ārējiem logiem."
    )

    if debug:
        return (
            f"{base}\n\n"
            f"Debug:\n{debug}\n\n"
            f"Versija: {VOICE_ENGINE_VERSION}"
        )

    return (
        f"{base}\n\n"
        "Debug: kļūda netika atgriezta no transkripcijas funkcijas.\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def _safe_filename(filename):
    name = (filename or "voice.ogg").strip()
    lower = name.lower()

    # Telegram voice parasti ir OGG/OPUS. OpenAI transcriptions pieņem ogg failus.
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
    """
    Atgriež tekstu no Telegram audio bytes.

    V1.4:
    - izmanto BytesIO ar drošu .name;
    - mēģina response_format='text';
    - ja kļūda, saglabā LAST_VOICE_DEBUG, ko build_voice_error_answer parāda Telegramā.
    """
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
        _set_debug(f"OpenAI transcribe error: {repr(e)}\n{short_trace}")
        return ""
