"""
conversation.py — V14.4

Ninas dabiskās sarunas klasifikācija.
Šeit nav Stripe, Premium, webhook vai datubāzes koda.
Šis modulis tikai pasaka, ko lietotājs, visticamāk, grib:
- memory
- goal
- none
"""


def classify_natural_message(text):
    lower = (text or "").strip().lower()
    if not lower:
        return "none"

    blocked_starts = [
        "/start", "premium", "pirkt", "mana diena", "labrīt", "labrit",
        "vakars", "mērķis:", "merkis:", "atceries", "invite", "referral",
        "stripe", "mans plāns", "abonements"
    ]
    if any(lower.startswith(x) for x in blocked_starts):
        return "none"

    today_words = ["šodien", "sodien"]
    goal_words = ["jāizdara", "jaizdara", "jāpabeidz", "japabeidz", "jāuztaisa", "jauztaisa", "vajag pabeigt"]

    if any(w in lower for w in today_words) and any(w in lower for w in goal_words):
        return "goal"

    memory_keywords = [
        "rīt", "rit", "pirmdien", "otrdien", "trešdien", "tresdien",
        "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien",
        "jāzvana", "jazvana", "neaizmirst", "atgādini", "atgadini",
        "jānopērk", "janoperk", "jāsatiek", "jasatiek", "tikšanās",
        "tiksanas", "klientam", "ārsts", "arsts", "zobārsts", "zobarsts",
        "vajag nopirkt", "vajag atcerēties", "vajag atcereties"
    ]

    if any(k in lower for k in memory_keywords):
        return "memory"

    return "none"


def build_auto_memory_answer(memory_text, version="V14.4"):
    return (
        "🧠 Saglabāju. ✅\n\n"
        f"Atcerēšos: {memory_text}\n\n"
        "Ja vajadzēs, vēlāk varēsim no tā izveidot arī atgādinājumu.\n\n"
        f"Versija: {version}"
    )


def build_auto_goal_answer(goal_text, version="V14.4"):
    return (
        "🎯 Labi, šo iestatīju kā tavas dienas galveno mērķi. ✅\n\n"
        f"Mērķis: {goal_text}\n\n"
        "Ja gribi, vari uzrakstīt pirmo mazo soli, un es palīdzēšu sakārtot plānu.\n\n"
        f"Versija: {version}"
    )
