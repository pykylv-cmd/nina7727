"""
memory_service.py — V20.1

Nina AI Platform Memory Service.
Atmiņu, mērķu un īstermiņa konteksta palīgfunkcijas ārpus app.py.
"""


def clean_memory_text(text: str) -> str:
    text = (text or "").strip()
    lower = text.lower()

    prefixes = [
        "atceries, ka ",
        "atceries ka ",
        "nina, atceries, ka ",
        "nina atceries, ka ",
        "neaizmirst ",
    ]

    for prefix in prefixes:
        if lower.startswith(prefix):
            return text[len(prefix):].strip()

    return text


def clean_goal_text(text: str) -> str:
    text = (text or "").strip()
    lower = text.lower()

    prefixes = ["mērķis:", "merkis:", "mērķis", "merkis"]

    for prefix in prefixes:
        if lower.startswith(prefix):
            return text[len(prefix):].strip(" :")

    return text


def build_memory_saved_text(memory_text: str, version="V20.1") -> str:
    memory_text = clean_memory_text(memory_text)

    return (
        "🧠 Paturēšu prātā. ✅\n\n"
        f"Atcerēšos: {memory_text}\n\n"
        "Tagad šī lieta nav tikai tavā galvā. 😉\n\n"
        f"Versija: {version}"
    )


def build_goal_saved_text(goal_text: str, version="V20.1") -> str:
    goal_text = clean_goal_text(goal_text)

    return (
        "🎯 Noķēru mērķi. ✅\n\n"
        f"Šodienas virziens: {goal_text}\n\n"
        "Tagad nevajag darīt visu uzreiz. Sākam ar vienu mazu soli.\n\n"
        f"Versija: {version}"
    )


def build_contextual_memory_hint(last_topic: str = "") -> str:
    topic = (last_topic or "").strip().lower()

    if topic in ["darbs", "klients", "klienti"]:
        return (
            "Izskatās, ka te ir darba vai klientu tēma. "
            "Ja gribi, varam šo pārvērst par konkrētu atgādinājumu vai dienas mērķi."
        )

    if topic in ["finanses", "nauda"]:
        return (
            "Te izklausās pēc naudas vai maksājumu tēmas. "
            "Tādas lietas labāk neatstāt tikai galvā."
        )

    if topic in ["ģimene", "gimene"]:
        return (
            "Šī izklausās pēc personīgas lietas. "
            "Varu palīdzēt to paturēt prātā mierīgi un bez haosa."
        )

    return "Ja šī lieta ir svarīga, varu to paturēt prātā vai pārvērst par atgādinājumu."


def summarize_recent_context(rows):
    if not rows:
        return ""

    last = rows[0]
    user_text = (last[0] or "").strip() if len(last) > 0 else ""
    emotion = (last[3] or "").strip() if len(last) > 3 else ""
    topic = (last[4] or "").strip() if len(last) > 4 else ""

    parts = []

    if user_text:
        parts.append(f"iepriekš cilvēks rakstīja: {user_text}")

    if emotion:
        parts.append(f"noskaņojums: {emotion}")

    if topic:
        parts.append(f"tēma: {topic}")

    return "; ".join(parts)


def should_save_as_memory(text: str) -> bool:
    lower = (text or "").strip().lower()

    if not lower:
        return False

    if "?" in lower:
        return False

    markers = [
        "rīt", "rit", "pirmdien", "otrdien", "trešdien", "tresdien",
        "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien",
        "neaizmirst", "jāzvana", "jazvana", "jānopērk", "janoperk",
        "klientam", "atceries"
    ]

    return any(m in lower for m in markers)


def should_save_as_goal(text: str) -> bool:
    lower = (text or "").strip().lower()

    if not lower:
        return False

    if lower.startswith("mērķis") or lower.startswith("merkis"):
        return True

    if ("šodien" in lower or "sodien" in lower) and any(
        word in lower for word in [
            "jāizdara", "jaizdara", "jāpabeidz",
            "japabeidz", "jāuztaisa", "jauztaisa"
        ]
    ):
        return True

    return False
