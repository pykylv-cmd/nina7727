"""
task_engine.py
NinaOS Task Engine — V1.2

Pārvērš sarunu par darāmiem darbiem.
V1.2:
- normalizē vārdus: Andrim -> Andris, Annai -> Anna, Jānim -> Jānis
- uzdevumu sarakstā nerāda pabeigtos darbus
- saglabā statusus: open / completed
"""

TASK_ENGINE_VERSION = "Task Engine V1.2"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(lower, words):
    return any(w in lower for w in words)


def normalize_person_name(name):
    raw = _clean(name)
    if not raw:
        return ""

    lower = raw.lower().strip(" .,!?:;")

    known = {
        "andrim": "Andris",
        "andri": "Andris",
        "andris": "Andris",
        "annai": "Anna",
        "annu": "Anna",
        "anna": "Anna",
        "jānim": "Jānis",
        "janim": "Jānis",
        "jāni": "Jānis",
        "jani": "Jānis",
        "jānis": "Jānis",
        "janis": "Jānis",
    }

    if lower in known:
        return known[lower]

    # Vienkāršs latviešu datīva heuristisks labojums vīriešu vārdiem.
    if lower.endswith("im") and len(raw) > 4:
        base = raw[:-2]
        return base[:1].upper() + base[1:] + "is"

    if lower.endswith("am") and len(raw) > 4:
        base = raw[:-2]
        return base[:1].upper() + base[1:] + "s"

    if lower.endswith("ai") and len(raw) > 4:
        base = raw[:-2]
        return base[:1].upper() + base[1:] + "a"

    return raw[:1].upper() + raw[1:]


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

    deadline = detect_deadline(raw)
    priority = detect_priority(raw)

    return {
        "type": "task",
        "title": build_task_title(raw),
        "raw_text": raw,
        "client": detect_client(raw),
        "deadline": deadline,
        "deadline_label": deadline_label(deadline),
        "priority": priority,
        "priority_label": priority_label(priority),
        "status": "open",
        "status_label": "atvērts",
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

    for marker in ["klientam ", "klientei ", "klientu ", "klients "]:
        if marker in lower:
            idx = lower.find(marker) + len(marker)
            tail = raw[idx:].strip(" .,!?:;")
            if tail:
                parts = tail.split()
                candidate = parts[0].strip(" .,!?:;")
                if candidate.lower() not in ["", "rīt", "rit", "šodien", "sodien"]:
                    return normalize_person_name(candidate)

    for candidate in ["andrim", "andris", "annai", "anna", "jānim", "janim", "jānis", "janis"]:
        if candidate in lower:
            return normalize_person_name(candidate)

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


def deadline_label(code):
    labels = {
        "today": "šodien",
        "tomorrow": "rīt",
        "day_after_tomorrow": "parīt",
        "monday": "pirmdien",
        "tuesday": "otrdien",
        "wednesday": "trešdien",
        "thursday": "ceturtdien",
        "friday": "piektdien",
        "saturday": "sestdien",
        "sunday": "svētdien",
    }
    return labels.get(code or "", "")


def detect_priority(text):
    lower = _lower(text)

    if any(x in lower for x in ["steidzami", "ātri", "atri", "šodien", "sodien", "obligāti", "obligati"]):
        return "high"

    if any(x in lower for x in ["kaut kad", "vēlāk", "velak", "nav steidzami"]):
        return "low"

    return "normal"


def priority_label(code):
    labels = {
        "high": "augsta",
        "normal": "normāla",
        "low": "zema",
    }
    return labels.get(code or "", "normāla")


def task_key(task):
    return _lower((task or {}).get("title") or (task or {}).get("raw_text") or "")


def active_tasks(tasks):
    """
    Ņem task ierakstus jaunākie -> vecākie.
    Ja jaunākais statuss šim title ir completed, veco open vairs nerāda.
    """
    result = []
    seen = set()

    for task in tasks or []:
        key = task_key(task)
        if not key or key in seen:
            continue
        seen.add(key)
        if (task or {}).get("status", "open") != "completed":
            result.append(task)

    return result


def build_task_saved_answer(task, user_name=""):
    if not task:
        return ""

    prefix = f"{user_name}, " if user_name else ""

    lines = [
        f"🧩 {prefix}pārvērtu šo par uzdevumu. ✅",
        "",
        f"Uzdevums: {task.get('title')}",
    ]

    if task.get("deadline_label"):
        lines.append(f"Termiņš: {task.get('deadline_label')}")

    if task.get("client"):
        lines.append(f"Klients/tēma: {task.get('client')}")

    lines.append(f"Prioritāte: {task.get('priority_label', 'normāla')}")
    lines.append("Statuss: atvērts")
    lines.append("")
    lines.append("Nākamais solis: kad uzrakstīsi `sakārto manu dienu`, es pateikšu, ar ko sākt.")
    lines.append("")
    lines.append(f"Versija: {TASK_ENGINE_VERSION}")

    return "\n".join(lines)


def task_summary(tasks):
    tasks = active_tasks(tasks or [])

    if not tasks:
        return (
            "📋 Šobrīd neredzu aktīvus uzdevumus.\n\n"
            "Uzraksti, piemēram: šodien steidzami jāzvana klientam Andrim.\n\n"
            f"Versija: {TASK_ENGINE_VERSION}"
        )

    lines = ["📋 Aktīvie uzdevumi"]
    for i, task in enumerate(tasks[:10], 1):
        title = task.get("title", "Bez nosaukuma")
        deadline = task.get("deadline_label") or deadline_label(task.get("deadline", ""))
        priority = task.get("priority_label") or priority_label(task.get("priority", "normal"))
        client = task.get("client", "")

        extra = []
        if deadline:
            extra.append(deadline)
        if priority:
            extra.append(priority)
        if client:
            extra.append(client)

        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"{i}. {title}{suffix}")

    lines.append("")
    lines.append("Šis ir Ninas darba galds — nevis tikai sarunu vēsture.")
    lines.append("")
    lines.append(f"Versija: {TASK_ENGINE_VERSION}")
    return "\n".join(lines)


def task_engine_status():
    return (
        "🧩 Task Engine V1.2 ir aktīvs. ✅\n\n"
        "Jaunums: vārdu normalizācija un pabeigto uzdevumu filtrēšana.\n\n"
        "Tests:\n"
        "šodien steidzami jāzvana klientam Andrim\n\n"
        "Sagaidāmais: klients = Andris, nevis Andrim.\n\n"
        f"Versija: {TASK_ENGINE_VERSION}"
    )
