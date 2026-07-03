"""
voice_engine.py
NinaOS Voice Intake V1.2 — Telegram OGG/OPUS Fix

Mērķis:
- Telegram voice ziņas (.ogg/.oga OPUS) pirms OpenAI transkripcijas pārkonvertēt uz WAV;
- izmantot imageio-ffmpeg, lai Render vidē nav jāpaļaujas uz sistēmas ffmpeg;
- saglabāt V1.1 tempfile drošību un skaidrus servera logus.
"""

import os
import shutil
import subprocess
import tempfile

VOICE_ENGINE_VERSION = "Voice Intake V1.2 — Telegram OGG/OPUS Fix"


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.2 — Telegram OGG/OPUS Fix ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• pieņem Telegram balss/audio ziņu;\n"
        "• Telegram .ogg/.opus audio pārtaisa uz WAV;\n"
        "• pārvērš audio tekstā ar OpenAI transkripciju;\n"
        "• nodod tekstu Ninai tā, it kā tu būtu to uzrakstījis.\n\n"
        "Tests:\n"
        "• ierunā Telegram voice ziņu: rīt jānosūta piedāvājums Andrim\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    return (
        "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
        "Visticamāk audio konvertācija vai transkripcija vēl neizgāja serverī. "
        "Pamēģini vēlreiz pēc redeploy. Ja nesanāk, atsūti Render logu rindu ar `Voice Intake`.\n\n"
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


def _ffmpeg_exe():
    """Atrod ffmpeg. Vispirms sistēmas ffmpeg, tad imageio-ffmpeg pip binary."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        print("Voice Intake V1.2: ffmpeg nav pieejams:", repr(e))
        return ""


def _convert_to_wav_if_needed(input_path, suffix):
    """Telegram voice parasti ir .ogg OPUS. OpenAI transkripcijai drošāk dodam WAV."""
    if suffix in [".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm"]:
        return input_path

    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return input_path

    output_path = input_path + ".wav"
    cmd = [
        ffmpeg,
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]
    print("Voice Intake V1.2: ffmpeg convert start", cmd)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    if proc.returncode != 0:
        print("Voice Intake V1.2: ffmpeg convert failed:", proc.stderr[-1000:])
        return input_path

    print("Voice Intake V1.2: ffmpeg convert OK", output_path)
    return output_path


def transcribe_audio_with_openai(openai_client, audio_bytes, filename="voice.ogg"):
    if not openai_client:
        print("Voice Intake V1.2: OpenAI client nav pieejams.")
        return ""

    audio_bytes = audio_bytes or b""
    if not audio_bytes:
        print("Voice Intake V1.2: audio_bytes ir tukšs.")
        return ""

    suffix = _safe_suffix(filename)
    temp_path = ""
    transcribe_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        transcribe_path = _convert_to_wav_if_needed(temp_path, suffix)
        print(
            f"Voice Intake V1.2: transcribe start file={filename} "
            f"suffix={suffix} bytes={len(audio_bytes)} send={transcribe_path}"
        )

        with open(transcribe_path, "rb") as audio_file:
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
        print(f"Voice Intake V1.2: transcript length={len(transcript)} text={transcript[:120]!r}")
        return transcript

    except Exception as e:
        print("Voice Intake V1.2 transcribe kļūda:", repr(e))
        return ""

    finally:
        for path in [transcribe_path, temp_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
