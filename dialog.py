"""
dialog.py — V15.9

Dialoga modulis.
Jautājumi nav atmiņas. Nina atbild dzīvāk, izmantojot charm.py.
"""

try:
    from charm import charm_capabilities_answer, charm_smalltalk_answer, charm_rough_answer
except Exception:
    def charm_capabilities_answer(version="V15.9"):
        return "Es varu palīdzēt atcerēties, plānot un sakārtot dienu. 😉\n\nVersija: " + version
    def charm_smalltalk_answer(user_text="", version="V15.9"):
        return "Čau. 😊 Esmu te. Ko šodien sakārtojam?\n\nVersija: " + version
    def charm_rough_answer(version="V15.9"):
        return "😄 Es vēl mācos nebūt robots. Dod man uzdevumu, un pierādīšu sevi.\n\nVersija: " + version


QUESTION_PATTERNS = [
    "ko vari", "ko tu vari", "ko māki", "ko maki", "ko dari",
    "kas tu esi", "kā tu vari", "ka tu vari", "ko vari darīt",
    "ko vari darit", "ko vari darīt manā labā", "ko vari darit mana laba",
]

ROUGH_PLAYFUL_PATTERNS = [
    "visi mājās", "visi majas", "tev visi", "dumja", "robots", "romots",
    "stulba", "tu neko nesaproti", "garlaicīga", "garlaiciga"
]

SMALLTALK_PATTERNS = ["čau", "cau", "sveika", "sveiks", "hello", "hi", "hei"]


def classify_dialog_message(text):
    lower = (text or "").strip().lower()
    if not lower:
        return "smalltalk"
    if any(p in lower for p in QUESTION_PATTERNS):
        return "capabilities"
    if any(p in lower for p in ROUGH_PLAYFUL_PATTERNS):
        return "rough_playful"
    if any(lower == p for p in SMALLTALK_PATTERNS):
        return "smalltalk"
    if "?" in lower and len(lower) < 120:
        return "question"
    return "none"


def build_capabilities_answer(version="V15.9"):
    return charm_capabilities_answer(version=version)


def build_playful_rough_answer(version="V15.9"):
    return charm_rough_answer(version=version)


def build_smalltalk_answer(user_text="", version="V15.9"):
    return charm_smalltalk_answer(user_text=user_text, version=version)
