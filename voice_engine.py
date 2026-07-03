"""
voice_engine.py
NinaOS Voice Intake V1.0

Mērķis:
- Telegram balss/audio ziņu pārvērst tekstā;
- nodot pārrakstīto tekstu esošajai NinaOS teksta loģikai;
- neatvērt jaunu sarunas ceļu un nelauzt task/CRM/Initiative maršrutus.
"""

VOICE_ENGINE_VERSION = "Voice Intake V1.0"


def voice_status_answer():
    return (
        "🎙 Voice Intake V1.0 ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• pieņem Telegram balss/audio ziņu;\n"
        "• pārvērš audio tekstā;\n"
        "• nodod tekstu Ninai tā, it kā tu būtu to uzrakstījis.\n\n"
        "Tests:\n"
        "• ierunā Telegram voice ziņu: rīt jānosūta piedāvājums Andrim\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_transcribed_answer(transcript):
    transcript = (transcript or "").strip()
    if not transcript:
        return (
            "🎙 Es saņēmu balss ziņu, bet tekstu šoreiz nevarēju skaidri nolasīt.\n\n"
            "Pamēģini ierunāt vēlreiz mazliet skaidrāk vai uzraksti tekstā.\n\n"
            f"Versija: {VOICE_ENGINE_VERSION}"
        )

    return (
        "🎙 Balss ziņu pārvērtu tekstā. ✅\n\n"
        f"Teksts: {transcript}\n\n"
        "Tagad apstrādāju to kā parastu ziņu.\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def build_voice_error_answer(error_text=""):
    return (
        "🎙 Balss ziņu saņēmu, bet šoreiz neizdevās to pārvērst tekstā.\n\n"
        "Vari pamēģināt vēlreiz vai uzrakstīt tekstā.\n\n"
        f"Versija: {VOICE_ENGINE_VERSION}"
    )


def transcribe_audio_with_openai(openai_client, audio_bytes, filename="voice.ogg"):
    """
    Atgriež tekstu no audio bytes.
    Izmanto OpenAI audio transcriptions API ar whisper-1.
    """
    if not openai_client:
        return ""

    import io

    audio_file = io.BytesIO(audio_bytes or b"")
    audio_file.name = filename

    result = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )

    text = getattr(result, "text", "") or ""
    return text.strip()
