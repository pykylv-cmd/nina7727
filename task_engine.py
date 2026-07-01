"""
task_engine.py
NinaOS Task Engine — V1.0

Pārvērš sarunu par darāmiem darbiem.
Šis modulis pats nesūta Telegram ziņas.
"""

TASK_ENGINE_VERSION = "Task Engine V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(lower, words):
    return any(w in lower for w in words)


def detect_task(text):
    raw = _clean(text)
    lower = raw.lower()

    if not raw:
        return None

    if "?" in lower and not lower.startswith(("vai vari", "vari", "palīdzi", "palidzi")):
        return None

    task_markers = [
        "jāizdara", "jaizdara",
        "jāpabeidz", "japabeidz",
        "jānosūta", "janosuta",
        "jāzvana", "jazvana",
        "jāsagatavo", "jasagatavo",
        "jāuztaisa", "jauztaisa",
        "vajag izdarīt", "vajag izdarit",
        "vajag pabeigt",
        "vajag nosūtīt", "vajag nosutit",
        "vajag sagatavot",
        "atgādini", "atgadini",
        "mērķis:", "merkis:",
        "uzdevums:",
    ]

    if not _contains_any(lower, task_markers):
        return None

    return {
        "type": "task",
        "title": build_task_title(raw),
        "raw_text": raw,
        "client": detect_client(raw),
        "deadline": detect_deadline(raw),
        "priority": detect_priority(raw),
        "status": "open",
        "source": "telegram",
        "version": TASK_ENGINE_VERSION,
    }


def build_task_title(text):
    raw = _clean(text)
    lower = raw.lower()

    prefixes = ["uzdevums:", "mērķis:", "merkis:", "atgādini", "atgadini", "vajag"]

    for prefix in prefixes:
        if lower.startswith(prefix):
            return raw[len(prefix):].strip(" :.,!")[:120] or raw[:120]

    return raw[:120]


def detect_client(text):
    raw = _clean(text)
    lower = raw.lower()

    markers = ["klientam ", "klientu ", "klients ", "priekš ", "prieks "]
    for marker in markers:
        if marker in lower:
            idx = lower.find(marker) + len(marker)
            tail = raw[idx:].strip(" .,!?:;")
            if tail:
                parts = tail.split()
                return " ".join(parts[:3]).strip(" .,!?:;")

    return ""


def detect_deadline(text):
    lower = _lower(text)

    if any(x in lower for x in ["šodien", "sodien"]):
        return "today"
    if any(x in lower for x in ["rīt", "rit"]):
        return "tomorrow"
    if any(x in lower for x in ["parīt", "parit"]):
        return "day_after_tomorrow"

    weekdays = {
        "pirmdien": "monday",
        "otrdien": "tuesday",
        "trešdien": "wednesday",
        "tresdien": "wednesday",
        "ceturtdien": "thursday",
        "piektdien": "friday",
        "sestdien": "saturday",
        "svētdien": "sunday",
        "svetdien": "sunday",
    }

    for lv, code in weekdays.items():
        if lv in lower:
            return code

    return ""


def detect_priority(text):
    lower = _lower(text)

    if any(x in lower for x in ["steidzami", "ātri", "atri", "šodien", "sodien", "obligāti", "obligati"]):
        return "high"

    if any(x in lower for x in ["kaut kad", "vēlāk", "velak", "nav steidzami"]):
        return "low"

    return "normal"


def build_task_saved_answer(task, user_name=""):
    if not task:
        return ""

    prefix = f"{user_name}, " if user_name else ""

    lines = [
        f"🧩 {prefix}pārvērtu šo par uzdevumu. ✅",
        "",
        f"Uzdevums: {task.get('title')}",
    ]

    if task.get("deadline"):
        lines.append(f"Termiņš: {task.get('deadline')}")

    if task.get("client"):
        lines.append(f"Klients/tēma: {task.get('client')}")

    lines.append(f"Prioritāte: {task.get('priority', 'normal')}")
    lines.append("")
    lines.append("Nākamais solis: es šo turu darba sarakstā, nevis tikai kā parastu sarunu.")
    lines.append("")
    lines.append(f"Versija: {TASK_ENGINE_VERSION}")

    return "\n".join(lines)


def task_summary(tasks):
    tasks = tasks or []
    if not tasks:
        return (
            "📋 Šobrīd neredzu aktīvus uzdevumus.\n\n"
            "Uzraksti, piemēram: rīt jānosūta piedāvājums klientam.\n\n"
            f"Versija: {TASK_ENGINE_VERSION}"
        )

    lines = ["📋 Aktīvie uzdevumi"]
    for i, task in enumerate(tasks[:10], 1):
        title = task.get("title", "Bez nosaukuma")
        deadline = task.get("deadline", "")
        priority = task.get("priority", "normal")
        extra = []
        if deadline:
            extra.append(deadline)
        if priority:
            extra.append(priority)
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"{i}. {title}{suffix}")

    lines.append("")
    lines.append(f"Versija: {TASK_ENGINE_VERSION}")
    return "\n".join(lines)


def task_engine_status():
    return (
        "🧩 Task Engine V1.0 ir gatavs pieslēgšanai. ✅\n\n"
        "Mērķis: pārvērst sarunu par darāmiem darbiem.\n\n"
        "Pirmais tests:\n"
        "rīt jānosūta piedāvājums klientam\n\n"
        "Sagaidāmais rezultāts: Nina izveido uzdevumu, nevis tikai atbild kā čatbots.\n\n"
        f"Versija: {TASK_ENGINE_VERSION}"
    )
