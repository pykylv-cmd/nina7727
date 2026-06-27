
"""
emotion.py — V16.2

Nina AI Platform
Emotion Engine

Nosaka cilvēka aptuveno noskaņojumu pēc teksta.
Šeit nav Telegram, DB, Stripe vai webhook koda.
"""


EMOTION_KEYWORDS = {
    "angry": [
        "besī", "besi", "dusmas", "dusmīgs", "dusmiga", "stulba",
        "dumja", "nekas nestrādā", "nestrada", "sūds", "suds"
    ],
    "tired": [
        "noguris", "nogurusi", "nav spēka", "nav speka", "pārguris",
        "parguris", "miegs", "apnicis"
    ],
    "sad": [
        "skumji", "slikti", "slikta diena", "bēdīgi", "bedigi",
        "negribu", "viss slikti"
    ],
    "curious": [
        "ko vari", "ko māki", "ko maki", "kā", "ka", "kāpēc", "kapec",
        "vai tu", "kas tu"
    ],
    "playful": [
        "haha", "hehe", "lol", "tev visi mājās", "tev visi majas",
        "testēju", "testeju", "pārbaudu", "parbaudu", "😉", "😄", "😂"
    ],
    "motivated": [
        "aiziet", "sākam", "sakam", "darām", "daram", "uz priekšu",
        "uzpriekšu", "vajag izdarīt", "gribu"
    ],
}


def detect_emotion(text: str) -> str:
    lower = (text or "").strip().lower()

    if not lower:
        return "neutral"

    for emotion, words in EMOTION_KEYWORDS.items():
        if any(word in lower for word in words):
            return emotion

    if "?" in lower:
        return "curious"

    return "neutral"


def emotion_prefix(emotion: str) -> str:
    emotion = (emotion or "neutral").lower()

    prefixes = {
        "angry": "Es jūtu, ka tur ir mazliet dusmas. Tas ir ok.",
        "tired": "Izklausās, ka esi noguris. Tad ejam mierīgi.",
        "sad": "Tas neizklausās viegli. Es nesteigšos ar gudriem padomiem.",
        "curious": "Labs jautājums.",
        "playful": "😄 Labi, spēlējam.",
        "motivated": "Patīk šī enerģija. Aiziet.",
        "neutral": "",
    }

    return prefixes.get(emotion, "")


def choose_tone(emotion: str) -> str:
    emotion = (emotion or "neutral").lower()

    tones = {
        "angry": "calm",
        "tired": "soft",
        "sad": "supportive",
        "curious": "curious",
        "playful": "playful",
        "motivated": "energetic",
        "neutral": "warm",
    }

    return tones.get(emotion, "warm")


def build_emotion_debug(text: str, version="V16.2") -> str:
    emotion = detect_emotion(text)
    tone = choose_tone(emotion)
    prefix = emotion_prefix(emotion)

    return (
        "🧭 Emotion Engine\\n\\n"
        f"Emocija: {emotion}\\n"
        f"Tonis: {tone}\\n"
        f"Reakcija: {prefix or 'silta/neitrāla'}\\n\\n"
        f"Versija: {version}"
    )
