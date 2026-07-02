"""
daily_planner.py
NinaOS Daily Planner — V1.0

Mērķis:
Pārvērst aktīvos darbus par vienkāršu dienas plānu.

Task Engine = uztver darbus.
Work Engine = izvēlas prioritātes.
Daily Planner = saliek darbus saprotamā dienas secībā.
"""

DAILY_PLANNER_VERSION = "Daily Planner V1.0"


def _clean(text):
    return (text or "").strip()


def task_key(task):
    return ((task or {}).get("title") or (task or {}).get("raw_text") or "").strip().lower()


def active_tasks(tasks):
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


def priority_score(task):
    priority = (task or {}).get("priority", "normal")
    deadline = (task or {}).get("deadline", "")

    score = 0

    if priority == "high":
        score += 100
    elif priority == "normal":
        score += 50
    elif priority == "low":
        score += 10

    if deadline == "today":
        score += 80
    elif deadline == "tomorrow":
        score += 40
    elif deadline:
        score += 20

    return score


def sort_tasks(tasks):
    return sorted(active_tasks(tasks or []), key=priority_score, reverse=True)


def task_type(task):
    text = ((task or {}).get("title") or (task or {}).get("raw_text") or "").lower()

    if any(x in text for x in ["zvan", "jāzvana", "jazvana"]):
        return "📞 Zvans"
    if any(x in text for x in ["e-past", "epast", "email", "atbildēt", "atbildet"]):
        return "✉️ E-pasts"
    if any(x in text for x in ["piedāvāj", "piedavaj"]):
        return "📄 Piedāvājums"
    if any(x in text for x in ["tāme", "tame", "tāmi", "tami"]):
        return "📑 Tāme"
    if any(x in text for x in ["rēķin", "rekin"]):
        return "💰 Rēķins"
    if any(x in text for x in ["dokuments", "līgums", "ligums"]):
        return "📝 Dokuments"
    if any(x in text for x in ["tikšanās", "tiksanas", "sapulce"]):
        return "📅 Tikšanās"

    return "✔️ Darbs"


def estimate_minutes(task):
    text = ((task or {}).get("title") or "").lower()

    if any(x in text for x in ["zvan", "jāzvana", "jazvana"]):
        return 20
    if any(x in text for x in ["piedāvāj", "piedavaj", "tāme", "tame", "dokuments"]):
        return 45
    if any(x in text for x in ["e-past", "epast", "email", "atbildēt", "atbildet"]):
        return 25
    if any(x in text for x in ["rēķin", "rekin"]):
        return 30

    return 30


def minutes_to_time(start_hour, start_minute, offset):
    total = start_hour * 60 + start_minute + offset
    hour = total // 60
    minute = total % 60
    return f"{hour:02d}:{minute:02d}"


def build_daily_plan(tasks, user_name="", start_hour=9, start_minute=0):
    tasks = sort_tasks(tasks)

    if not tasks:
        return (
            "🌅 Dienas plāns\n\n"
            "Šobrīd neredzu aktīvus darbus, ko salikt plānā.\n\n"
            "Uzraksti vienu darbu, piemēram:\n"
            "šodien steidzami jāzvana klientam Andrim\n\n"
            f"Versija: {DAILY_PLANNER_VERSION}"
        )

    name = f"{user_name}, " if user_name else ""

    lines = [
        f"🌅 {name}saliku tev vienkāršu dienas plānu.",
        "",
        "Mērķis: noņemt haosu no galvas un sākt ar svarīgāko.",
        "",
    ]

    current_offset = 0

    for i, task in enumerate(tasks[:6], 1):
        duration = estimate_minutes(task)
        start = minutes_to_time(start_hour, start_minute, current_offset)
        end = minutes_to_time(start_hour, start_minute, current_offset + duration)

        title = task.get("title", "Bez nosaukuma")
        client = task.get("client", "")
        deadline = task.get("deadline_label") or task.get("deadline", "")
        priority = task.get("priority_label") or task.get("priority", "normal")

        meta = []
        if client:
            meta.append(client)
        if deadline:
            meta.append(deadline)
        if priority:
            meta.append(priority)

        suffix = f" — {', '.join(meta)}" if meta else ""

        lines.append(f"{i}. {start}–{end} {task_type(task)} {title}{suffix}")

        current_offset += duration + 10

    first = tasks[0]
    lines.append("")
    lines.append("Ar ko sākt:")
    lines.append(f"{task_type(first)} {first.get('title', 'Bez nosaukuma')}")
    lines.append("")
    lines.append("Kad pabeigts, uzraksti: izdarīts.")
    lines.append("Es pēc tam pārkārtošu nākamo soli.")
    lines.append("")
    lines.append(f"Versija: {DAILY_PLANNER_VERSION}")

    return "\n".join(lines)


def daily_planner_status():
    return (
        "🌅 Daily Planner V1.0 ir aktīvs. ✅\n\n"
        "Mērķis: pārvērst aktīvos uzdevumus dienas plānā.\n\n"
        "Tests:\n"
        "saplāno manu dienu\n"
        "ko man darīt šodien\n"
        "ar ko sākt\n\n"
        f"Versija: {DAILY_PLANNER_VERSION}"
    )
