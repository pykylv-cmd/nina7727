"""
task_cleanup.py
NinaOS Task Cleanup — V1.1

Mērķis:
iztīrīt tehniskos/testa uzdevumus no darba galda.

V1.1:
- junk uzdevumus marķē kā status='deleted'
- Task List Filter Fix filtrē ārā deleted/archived un tehniskos title
"""

TASK_CLEANUP_VERSION = "Task Cleanup V1.1"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


JUNK_TITLES = {
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
    "[deleted task cleanup]",
}


def is_junk_task_title(title):
    lower = _lower(title)
    if not lower:
        return False
    return lower in JUNK_TITLES


def is_active_real_task(task):
    task = task or {}
    status = _lower(task.get("status", "open"))
    title = _clean(task.get("title", ""))

    if status in ["completed", "deleted", "archived", "cancelled", "canceled"]:
        return False

    if is_junk_task_title(title):
        return False

    return True


def find_cleanup_candidates(tasks):
    result = []

    for task in tasks or []:
        title = _clean((task or {}).get("title", ""))
        status = _lower((task or {}).get("status", "open"))

        if is_junk_task_title(title) and status not in ["deleted", "archived"]:
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
        "🧹 Atradu uzdevumus, kurus vajag paslēpt no darba galda:",
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
        f"Paslēpti tehniskie/testa uzdevumi: {int(deleted_count or 0)}\n\n"
        f"Versija: {TASK_CLEANUP_VERSION}"
    )
