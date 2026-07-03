"""
client_work_view.py
NinaOS Client Work View — V1.0
"""

CLIENT_WORK_VIEW_VERSION = "Client Work View V1.0"


def _clean(text):
    return (text or "").strip()


def normalize_client_name_v1(name):
    raw = _clean(name)
    if not raw:
        return ""

    mapping = {
        "andrim": "Andris",
        "andri": "Andris",
        "andris": "Andris",
        "annai": "Anna",
        "anna": "Anna",
        "jānim": "Jānis",
        "janim": "Jānis",
        "janis": "Jānis",
        "jānis": "Jānis",
    }
    lower = raw.lower().strip(" .,!?:;")
    if lower in mapping:
        return mapping[lower]
    return raw[:1].upper() + raw[1:]


def extract_client_from_query(text):
    raw = _clean(text)
    lower = raw.lower()

    prefixes = ["kas notiek ar ", "kas ar ", "client work "]
    for prefix in prefixes:
        if lower.startswith(prefix):
            tail = raw[len(prefix):].strip(" .,!?:;")
            return normalize_client_name_v1(tail)

    return ""


def task_matches_client(task, client_name):
    client_name = _clean(client_name)
    if not client_name:
        return False

    task = task or {}
    task_client = _clean(task.get("client", ""))
    title = _clean(task.get("title", ""))
    raw_text = _clean(task.get("raw_text", ""))

    if task_client.lower() == client_name.lower():
        return True

    blob = f"{title} {raw_text}".lower()
    return client_name.lower() in blob


def build_client_work_view(client_name, tasks):
    client_name = _clean(client_name)

    if not client_name:
        return (
            "👥 Client Work View\n\n"
            "Pasaki klienta vārdu, piemēram:\n"
            "kas notiek ar Andri\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )

    matched = [task for task in (tasks or []) if task_matches_client(task, client_name)]

    if not matched:
        return (
            f"👥 Klientam {client_name} šobrīd neredzu aktīvus darbus.\n\n"
            "Ja vajag, vispirms iedod uzdevumu.\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )

    lines = [
        f"👥 Kas notiek ar {client_name}",
        "",
        f"Aktīvie darbi: {len(matched)}",
        ""
    ]

    for i, task in enumerate(matched, 1):
        title = _clean(task.get("title", ""))
        deadline = _clean(task.get("deadline_label", "")) or _clean(task.get("deadline", ""))
        followup = bool(task.get("followup"))
        suffix = []
        if deadline:
            suffix.append(deadline)
        if followup:
            suffix.append("follow-up")
        suffix_text = f" ({', '.join(suffix)})" if suffix else ""
        lines.append(f"{i}. {title}{suffix_text}")

    lines.append("")
    lines.append("Šis ir klienta skats — visi darbi vienā vietā.")
    lines.append("")
    lines.append(f"Versija: {CLIENT_WORK_VIEW_VERSION}")
    return "\n".join(lines)


def client_work_status():
    return (
        "👥 Client Work View V1.0 ir aktīvs. ✅\n\n"
        "Tests:\n"
        "kas notiek ar Andri\n\n"
        "Sagaidāmais rezultāts: Nina parāda visus Andra aktīvos darbus vienā skatā.\n\n"
        f"Versija: {CLIENT_WORK_VIEW_VERSION}"
    )
