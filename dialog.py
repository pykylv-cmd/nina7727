"""
dialog.py — V15.8.3

Nina AI Platform dialoga modulis.
Šeit nav Telegram, Stripe, DB vai webhook koda.

Uzdevums:
- nepārprast jautājumus kā atmiņas;
- atbildēt dzīvāk;
- rupjus/joku tekstus apstrādāt cilvēcīgi;
- pārdot Ninas vērtību normālā veidā.
"""


QUESTION_PATTERNS = [
    "ko vari",
    "ko tu vari",
    "ko māki",
    "ko maki",
    "ko dari",
    "kas tu esi",
    "kā tu vari",
    "ka tu vari",
    "ko vari darīt",
    "ko vari darit",
    "ko vari darīt manā labā",
    "ko vari darit mana laba",
]


ROUGH_PLAYFUL_PATTERNS = [
    "visi mājās",
    "visi majas",
    "tev visi",
    "dumja",
    "robots",
    "romots",
    "stulba",
    "tu neko nesaproti",
]


SMALLTALK_PATTERNS = [
    "čau",
    "cau",
    "sveika",
    "sveiks",
    "hello",
    "hi",
    "hei",
]


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

    # Jebkurš īss jautājums lai iet dialogā, nevis atmiņā.
    if "?" in lower and len(lower) < 120:
        return "question"

    return "none"


def build_capabilities_answer(version="V15.8.3"):
    return (
        "Es varu tev palīdzēt nevis tikai čatot, bet reāli sakārtot ikdienu. 😉\n\n"
        "Ko es varu darīt tavā labā:\n"
        "🧠 atcerēties svarīgas lietas;\n"
        "🎯 palīdzēt izvēlēties šodienas galveno mērķi;\n"
        "⏰ izveidot atgādinājumus;\n"
        "📊 parādīt progresu;\n"
        "💬 palīdzēt sakārtot domas, kad galvā ir haoss.\n\n"
        "Tu vari rakstīt dabiski, piemēram:\n"
        "• rīt jāzvana klientam\n"
        "• šodien jāpabeidz projekts\n"
        "• atgādini rīt 10:00 piezvanīt klientam\n\n"
        "Un jā — es vēl mācos būt dzīvāka, nevis kā robots. 😄\n\n"
        f"Versija: {version}"
    )


def build_playful_rough_answer(version="V15.8.3"):
    return (
        "Hei, hei 😄 Es vēl mācos, bet mājās man viss ir.\n\n"
        "Ja atbildu pārāk taisni vai robotiski, saki. Mans darbs ir kļūt par normālu palīgu, nevis sausu automātu.\n\n"
        "Pajautā man, piemēram:\n"
        "ko tu vari darīt manā labā?\n\n"
        f"Versija: {version}"
    )


def build_smalltalk_answer(user_text="", version="V15.8.3"):
    return (
        "Esmu te. 😊\n\n"
        "Vari man vienkārši pastāstīt, kas jāizdara, ko nedrīkst aizmirst, vai pajautāt, ko es māku.\n\n"
        "Piemēram:\n"
        "rīt jāzvana klientam\n"
        "vai:\n"
        "atgādini rīt 10:00 piezvanīt klientam\n\n"
        f"Versija: {version}"
    )
