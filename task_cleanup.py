"""
task_cleanup.py
NinaOS Task Cleanup — V1.0

Mērķis:
iztīrīt acīmredzami nederīgus vai tehniskus uzdevumus no task saraksta,
piemēram:
- follow-up
- client context
- memory router
- persistence health

Tas nav domāts normāliem darbiem, bet tikai testu / komandu atkritumiem.
"""

TASK_CLEANUP_VERSION = "Task Cleanup V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def is_junk_task_title(title):
    lower = _lower(title)

    if not lower:
        return False

    junk_titles = {
        "follow-up",
        "follow up",
        "followup",
        "client context",
        "client context status",
        "memory router",
        "memory router status",
        "persistence health",
        "db health",
        "database health",
    }

    return lower in junk_titles


def find_cleanup_candidates(tasks):
    result = []

    for task in tasks or []:
        title = _clean((task or {}).get("title", ""))
        if is_junk_task_title(title):
            result.append(task)

    return result


def build_cleanup_preview(tasks):
    junk = find_cleanup_candidates(tasks)

    if not junk:
        return (
            "🧹 Task Cleanup neko lieku neatrada.\n\n"
            "Darba galds izskatās tīrs.\n\n"
            f"Versija: {TASK_CLEANUP_VERSION}"
        )

    lines = [
        "🧹 Atradu uzdevumus, kurus vajag izmest no darba galda:",
        ""
    ]

    for i, task in enumerate(junk, 1):
        title = _clean(task.get("title", ""))
        lines.append(f"{i}. {title}")

    lines.append("")
    lines.append("Raksti: task cleanup confirm")
    lines.append("")
    lines.append(f"Versija: {TASK_CLEANUP_VERSION}")
    return "\n".join(lines)


def build_cleanup_done_answer(deleted_count):
    return (
        "🧹 Darba galds iztīrīts. ✅\n\n"
        f"Izdzēsti tehniskie/testa uzdevumi: {int(deleted_count or 0)}\n\n"
        f"Versija: {TASK_CLEANUP_VERSION}"
    )
