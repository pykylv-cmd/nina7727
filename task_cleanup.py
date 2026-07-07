"""
task_cleanup.py
NinaOS Task Cleanup — V1.2 Work Object Filter

V1.2:
- keeps legacy task cleanup;
- adds NinaOS Work Object filtering;
- supports object_type/status/source metadata.
"""

TASK_CLEANUP_VERSION = "Task Cleanup V1.2 — Work Object Filter"

def _clean(text):
    return (text or "").strip()

def _lower(text):
    return _clean(text).lower()

JUNK_TITLES = {
    "follow-up", "follow up", "followup",
    "client context", "client context status",
    "memory router", "memory router status",
    "persistence health", "db health", "database health",
    "[deleted task cleanup]",
}

HIDDEN_STATUSES = {"completed", "done", "deleted", "archived", "cancelled", "canceled"}

def _get(obj, key, default=""):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _metadata(obj):
    data = _get(obj, "metadata", {})
    return data if isinstance(data, dict) else {}

def is_junk_task_title(title):
    lower = _lower(title)
    if not lower:
        return False
    return lower in JUNK_TITLES

def is_active_real_task(task):
    task = task or {}
    status = _lower(_get(task, "status", "open"))
    title = _clean(_get(task, "title", ""))

    if status in HIDDEN_STATUSES:
        return False
    if is_junk_task_title(title):
        return False
    return True

def is_active_real_work_object(obj):
    obj = obj or {}
    status = _lower(_get(obj, "status", "open"))
    title = _clean(_get(obj, "title", ""))
    object_type = _lower(_get(obj, "object_type", _get(obj, "type", "")))
    metadata = _metadata(obj)
    source = _lower(metadata.get("source", ""))

    if status in HIDDEN_STATUSES:
        return False
    if is_junk_task_title(title):
        return False
    if object_type in ["debug", "health_check", "test_object"]:
        return False
    if source in ["debug", "health_check"] and is_junk_task_title(title):
        return False
    return True

def filter_active_work_objects(objects):
    return [obj for obj in (objects or []) if is_active_real_work_object(obj)]

def find_cleanup_candidates(tasks):
    result = []
    for task in tasks or []:
        title = _clean(_get(task, "title", ""))
        status = _lower(_get(task, "status", "open"))
        if is_junk_task_title(title) and status not in ["deleted", "archived"]:
            result.append(task)
    return result

def find_cleanup_candidates_for_work_objects(objects):
    result = []
    for obj in objects or []:
        title = _clean(_get(obj, "title", ""))
        status = _lower(_get(obj, "status", "open"))
        object_type = _lower(_get(obj, "object_type", _get(obj, "type", "")))
        if status in ["deleted", "archived"]:
            continue
        if is_junk_task_title(title) or object_type in ["debug", "health_check", "test_object"]:
            result.append(obj)
    return result

def build_cleanup_preview(tasks):
    junk = find_cleanup_candidates(tasks)
    if not junk:
        return (
            "🧹 Task Cleanup neko lieku neatrada.\n\n"
            "Darba galds izskatās tīrs.\n\n"
            f"Versija: {TASK_CLEANUP_VERSION}"
        )
    lines = ["🧹 Atradu uzdevumus, kurus vajag paslēpt no darba galda:", ""]
    for i, task in enumerate(junk, 1):
        title = _clean(_get(task, "title", ""))
        lines.append(f"{i}. {title}")
    lines.append("")
    lines.append("Raksti: task cleanup confirm")
    lines.append("")
    lines.append(f"Versija: {TASK_CLEANUP_VERSION}")
    return "\n".join(lines)

def build_work_object_cleanup_preview(objects):
    junk = find_cleanup_candidates_for_work_objects(objects)
    if not junk:
        return (
            "🧹 Work Object Cleanup neko lieku neatrada.\n\n"
            "NinaOS darba objekti izskatās tīri.\n\n"
            f"Versija: {TASK_CLEANUP_VERSION}"
        )
    lines = ["🧹 Atradu NinaOS work objects, kurus vajag paslēpt / arhivēt:", ""]
    for i, obj in enumerate(junk, 1):
        title = _clean(_get(obj, "title", ""))
        object_type = _clean(_get(obj, "object_type", _get(obj, "type", "")))
        lines.append(f"{i}. {title} ({object_type})")
    lines.append("")
    lines.append("Raksti: work object cleanup confirm")
    lines.append("")
    lines.append(f"Versija: {TASK_CLEANUP_VERSION}")
    return "\n".join(lines)

def build_cleanup_done_answer(deleted_count):
    return (
        "🧹 Darba galds iztīrīts. ✅\n\n"
        f"Paslēpti tehniskie/testa uzdevumi: {int(deleted_count or 0)}\n\n"
        f"Versija: {TASK_CLEANUP_VERSION}"
    )
