"""
task_engine.py
NinaOS Task Engine — V1.2

Pārvērš sarunu par darāmiem darbiem.
V1.2:
- normalizē vārdus: Andrim -> Andris, Annai -> Anna, Jānim -> Jānis
- uzdevumu sarakstā nerāda pabeigtos darbus
- saglabā statusus: open / completed
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TASK_ENGINE_VERSION = "Task Engine V1.2"


def create_canonical_task(tenant_id, title, **values):
    """Task Engine adapter: persist only in Universal Work Objects."""
    from universal_work_objects import create_work_object
    return create_work_object(
        tenant_id,
        object_type="task",
        title=title,
        source_type=values.pop("source_type", "nina"),
        **values,
    )


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


def detect_task(text, reminder_requested=False):
    raw = _clean(text)
    lower = raw.lower()

    if not raw:
        return None

    if "?" in lower and not lower.startswith(("vai vari", "vari", "palīdzi", "palidzi")):
        return None

    explicit_task = _explicit_task_command(raw)
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

    natural_reminder = detect_reminder_schedule(
        raw, reminder_requested=reminder_requested,
    )
    if not explicit_task and not _contains_any(lower, task_markers) and not natural_reminder:
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
        "reminder_at": natural_reminder.get("reminder_at", "") if natural_reminder else "",
        "priority": priority,
        "priority_label": priority_label(priority),
        "status": "open",
        "status_label": "atvērts",
        "source": "telegram",
        "version": TASK_ENGINE_VERSION,
    }


def _detect_single_reminder_schedule(
    text, now=None, timezone_name="Europe/Riga", reminder_requested=False,
):
    """Interpret reminder timing for the existing Work Object contract."""
    raw = _clean(text)
    lower = raw.casefold()
    if not raw:
        return {}
    actions = (
        "atgādini", "atgadini", "atsūti atgādinājumu", "atsuti atgadinajumu",
        "piezvanīt", "piezvanit", "jāzvana", "jazvana",
    )
    temporal = (
        "šodien", "sodien", "rīt", "rit", "pēc ", "pec ", "pirmdien",
        "otrdien", "trešdien", "tresdien", "ceturtdien", "piektdien",
        "sestdien", "svētdien", "svetdien",
    )
    has_action = any(value in lower for value in actions)
    has_temporal = (
        any(value in lower for value in temporal)
        or bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", lower))
        or bool(re.search(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", lower))
        or "katru dienu" in lower or "ik dienu" in lower
        or "parīt" in lower or "parit" in lower
    )
    if not (has_action or reminder_requested) or not has_temporal:
        return {}

    tz = ZoneInfo(timezone_name)
    current = now or datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    relative = re.search(
        r"\bp(?:ē|e)c\s+(?:(?:(\d+)|vienas?|div(?:ā|a)m?|tr(?:ī|i)m?)\s+)?"
        r"(stund(?:as?|u|ām?)|minūt(?:es?|ēm?)|minut(?:es?|em?)|min)\b",
        lower,
    )
    if relative:
        word = relative.group(1) or relative.group(0)
        amount = int(relative.group(1)) if relative.group(1) else (
            2 if "div" in word else 3 if "tr" in word else 1
        )
        target = current + (
            timedelta(hours=amount) if "stund" in relative.group(2)
            else timedelta(minutes=amount)
        )
    else:
        absolute = re.search(
            r"\b(\d{4})-(\d{2})-(\d{2})(?:[ t]([01]?\d|2[0-3])[:.]([0-5]\d))?\b",
            lower,
        )
        day = current.date()
        target_weekday = None
        explicit_next_week = "nākam" in lower or "nakam" in lower
        if absolute:
            day = datetime(
                int(absolute.group(1)), int(absolute.group(2)),
                int(absolute.group(3)), tzinfo=tz,
            ).date()
        elif "rīt" in lower or re.search(r"\brit\b", lower):
            day += timedelta(days=1)
        elif "parīt" in lower or "parit" in lower:
            day += timedelta(days=2)
        elif not ("šodien" in lower or "sodien" in lower):
            weekdays = {
                "pirmdien": 0, "otrdien": 1, "trešdien": 2, "tresdien": 2,
                "ceturtdien": 3, "piektdien": 4, "sestdien": 5,
                "svētdien": 6, "svetdien": 6,
            }
            for marker, weekday in weekdays.items():
                if marker in lower:
                    days = (weekday - current.weekday()) % 7
                    if explicit_next_week:
                        days = 7
                    day += timedelta(days=days)
                    target_weekday = weekday
                    break
        time_match = re.search(r"\b(?:pulksten\s*)?([01]?\d|2[0-3])[:.]([0-5]\d)\b", lower)
        hour = int(time_match.group(1)) if time_match else 9
        minute = int(time_match.group(2)) if time_match else 0
        target = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
        if target_weekday is not None and not explicit_next_week and target <= current:
            target += timedelta(days=7)
    return {"reminder_at": target.isoformat(timespec="minutes"), "timezone": timezone_name}


def detect_reminder_schedules(
    text, now=None, timezone_name="Europe/Riga", reminder_requested=False,
):
    """Return every explicit reminder time without inventing additional times."""
    raw = _clean(text)
    clocks = list(re.finditer(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", raw))
    recurrence = "daily" if re.search(
        r"\b(?:katru\s+dienu|ik\s+dienu|every\s+day|daily)\b",
        raw, re.IGNORECASE,
    ) else ""
    if len(clocks) <= 1:
        parsed = _detect_single_reminder_schedule(
            raw, now=now, timezone_name=timezone_name,
            reminder_requested=reminder_requested,
        )
        if parsed and recurrence:
            parsed["recurrence"] = recurrence
        return [parsed] if parsed else []

    results = []
    seen = set()
    for selected in clocks:
        pieces = []
        cursor = 0
        for clock in clocks:
            pieces.append(raw[cursor:clock.start()])
            if clock.start() == selected.start():
                pieces.append(clock.group(0))
            cursor = clock.end()
        pieces.append(raw[cursor:])
        candidate = re.sub(r"\s+", " ", "".join(pieces)).strip(" ,")
        parsed = _detect_single_reminder_schedule(
            candidate, now=now, timezone_name=timezone_name,
            reminder_requested=reminder_requested,
        )
        reminder_at = str(parsed.get("reminder_at") or "") if parsed else ""
        if not reminder_at or reminder_at in seen:
            continue
        seen.add(reminder_at)
        if recurrence:
            parsed["recurrence"] = recurrence
        results.append(parsed)
    return results


def detect_reminder_schedule(
    text, now=None, timezone_name="Europe/Riga", reminder_requested=False,
):
    schedules = detect_reminder_schedules(
        text, now=now, timezone_name=timezone_name,
        reminder_requested=reminder_requested,
    )
    return schedules[0] if schedules else {}


def build_task_title(text):
    raw = _clean(text)
    lower = raw.lower()

    reminder_title = _reminder_task_title(raw)
    if reminder_title:
        return reminder_title[:120]

    explicit = _explicit_task_command(raw)
    if explicit:
        title = raw[explicit.end():].strip(" :.,!")
        title = re.sub(
            r"^(?:rīt|rit|tomorrow|завтра)\b\s*[:,\-]?\s*",
            "",
            title,
            flags=re.IGNORECASE,
        )
        return title.strip(" :.,!")[:120] or raw[:120]

    prefixes = ["uzdevums:", "mērķis:", "merkis:", "atgādini", "atgadini", "vajag"]

    for prefix in prefixes:
        if lower.startswith(prefix):
            return raw[len(prefix):].strip(" :.,!")[:120] or raw[:120]

    return raw[:120]


def _reminder_task_title(text):
    """Extract only the user action; delivery date/time never becomes the title."""
    raw = _clean(text)
    lower = raw.casefold()
    if "atgādini" not in lower and "atgadini" not in lower:
        return ""
    value = re.sub(r"^.*?\batg[āa]dini(?:\s+man)?(?:\s+ka)?\s*", "", raw, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:šodien|sodien|rīt|rit|parīt|parit|pirmdien|otrdien|trešdien|tresdien|"
        r"ceturtdien|piektdien|sestdien|svētdien|svetdien)\b", "", value, flags=re.IGNORECASE,
    )
    value = re.sub(r"\b(?:pulksten\s*)?\d{1,2}[:.]\d{2}\b", "", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:katru\s+dienu|ik\s+dienu|every\s+day|daily)\b",
        "", value, flags=re.IGNORECASE,
    )
    value = re.sub(r"\bno\s+rīta\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\s*ka\s+", "", value, flags=re.IGNORECASE)
    value = " ".join(value.strip(" :,.!?- ").split())
    value = re.sub(r"^jāsarēķina\b", "Sarēķināt", value, flags=re.IGNORECASE)
    value = re.sub(r"\balga\b", "algu", value, flags=re.IGNORECASE)
    value = re.sub(r"\bpa\s+jumtu\b", "par jumtu", value, flags=re.IGNORECASE)
    return value


def _explicit_task_command(text):
    raw = _clean(text)
    if not raw:
        return None
    patterns = (
        r"^(?:lūdzu\s+)?izveido\s+uzdevumu\b\s*:?\s*",
        r"^atgādini(?:\s+man)?\b\s*:?\s*",
        r"^atgadini(?:\s+man)?\b\s*:?\s*",
        r"^(?:please\s+)?(?:create|add|make)\s+(?:a\s+)?task\b\s*:?\s*",
        r"^remind\s+me(?:\s+to)?\b\s*:?\s*",
        r"^(?:пожалуйста[,.]?\s+)?(?:создай|создать|добавь)\s+задачу\b\s*:?\s*",
        r"^напомни(?:\s+мне)?\b\s*:?\s*",
    )
    for pattern in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            return match
    return None


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
    if any(x in lower for x in ["rīt", "rit", "tomorrow", "завтра"]):
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
