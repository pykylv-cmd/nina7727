"""
voice_engine.py
NinaOS Voice Intake V1.1 — Transcribe Fix

Mērķis:
- Telegram voice/audio failu droši pārvērst tekstā;
- izmantot tempfile failu, jo OpenAI audio API uzticamāk strādā ar īstu faila objektu;
- atbalstīt dažādus OpenAI response formātus;
- dot skaidru kļūdu logu, ja transkripcija neizdodas.
"""

import os
import tempfile

VOICE_ENGINE_VERSION = "Voice Intake V1.1 — Transcribe Fix"


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.1 — Transcribe Fix ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• pieņem Telegram balss/audio ziņu;\n"
        "• saglabā audio īslaicīgā failā;\n"
        "• pārvērš audio tekstā ar OpenAI transkripciju;\n"
        "• nodod tekstu Ninai tā, it kā tu būtu to uzrakstījis.\n\n"
        "Tests:\n"
        "• ierunā Telegram voice ziņu: rīt jānosūta piedāvājums Andrim\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    # Lietotājam nerādām garu tehnisku kļūdu, bet servera logā tā tiek printota app.py/voice_engine līmenī.
    return (
        "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
        "Pamēģini vēlreiz ierunāt mazliet skaidrāk. Ja nesanāk, uzraksti tekstā.\n\n"
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
    """
    Atgriež tekstu no Telegram audio bytes.

    V1.1 fix:
    - nelieto tikai BytesIO objektu;
    - ieraksta audio tempfile ar pareizu suffix;
    - atver īstu failu rb režīmā;
    - response_format='text' atgriež vienkāršu stringu, ko vieglāk droši apstrādāt.
    """
    if not openai_client:
        print("Voice Intake V1.1: OpenAI client nav pieejams.")
        return ""

    audio_bytes = audio_bytes or b""
    if not audio_bytes:
        print("Voice Intake V1.1: audio_bytes ir tukšs.")
        return ""

    suffix = _safe_suffix(filename)
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        print(f"Voice Intake V1.1: transcribe start file={filename} suffix={suffix} bytes={len(audio_bytes)}")

        with open(temp_path, "rb") as audio_file:
            try:
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )
            except TypeError:
                # Ja OpenAI bibliotēkas versija neņem response_format, mēģinām bez tā.
                audio_file.seek(0)
                result = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )

        transcript = _extract_text_from_result(result)
        print(f"Voice Intake V1.1: transcript length={len(transcript)}")
        return transcript

    except Exception as e:
        print("Voice Intake V1.1 transcribe kļūda:", repr(e))
        return ""

    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass
