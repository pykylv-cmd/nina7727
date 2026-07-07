"""
followup_engine.py
NinaOS Follow-up Engine — V1.3 Work Object Bridge

V1.3:
- keeps V1.2 detection logic;
- adds NinaOS-compatible followup_task payload builder;
- can create a WorkObject through assistant_work_bridge.py if available.
"""

FOLLOWUP_ENGINE_VERSION = "Follow-up Engine V1.3 — Work Object Bridge"

try:
    from assistant_work_bridge import (
        build_followup_work_object_payload,
        create_followup_work_object,
        ASSISTANT_WORK_BRIDGE_VERSION,
    )
except Exception:
    ASSISTANT_WORK_BRIDGE_VERSION = "Assistant Work Bridge not connected"

    def build_followup_work_object_payload(**kwargs):
        return {
            "object_type": "followup_task",
            "title": kwargs.get("title", ""),
            "workspace_id": kwargs.get("workspace_id", "demo_small_business"),
            "priority": kwargs.get("priority", "normal"),
            "due_date": kwargs.get("due_code", ""),
            "status": "scheduled" if kwargs.get("due_code") else "open",
            "metadata": kwargs,
            "stored": False,
        }

    def create_followup_work_object(**kwargs):
        data = build_followup_work_object_payload(**kwargs)
        data["stored"] = False
        return data


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def is_followup_text(text):
    lower = _lower(text)
    if not lower:
        return False
    if lower in ["follow-up", "followup", "follow up", "follow-up engine", "followup engine", "follow up engine"]:
        return False
    markers = [
        "jāpajautā", "japajauta", "pajautā", "pajauta", "pārjautā", "parjauta",
        "jāatgādina", "jaatgadina", "atgādināt", "atgadinat", "jāsazvana",
        "jasazvana", "sazvanīt", "sazvanit", "vēlreiz", "velreiz", "par atbildi",
        "par piedāvājumu", "par piedavajumu", "par rēķinu", "par rekinu",
        "follow-up", "follow up", "followup",
    ]
    return any(m in lower for m in markers)


def detect_deadline(text):
    lower = _lower(text)
    if "šodien" in lower or "sodien" in lower:
        return "today"
    if "rīt" in lower or "rit" in lower:
        return "tomorrow"
    if "parīt" in lower or "parit" in lower:
        return "day_after_tomorrow"
    weekdays = {
        "pirmdien": "monday", "otrdien": "tuesday", "trešdien": "wednesday",
        "tresdien": "wednesday", "ceturtdien": "thursday", "piektdien": "friday",
        "sestdien": "saturday", "svētdien": "sunday", "svetdien": "sunday",
    }
    for lv, code in weekdays.items():
        if lv in lower:
            return code
    return ""


def deadline_label(code):
    labels = {
        "today": "šodien", "tomorrow": "rīt", "day_after_tomorrow": "parīt",
        "monday": "pirmdien", "tuesday": "otrdien", "wednesday": "trešdien",
        "thursday": "ceturtdien", "friday": "piektdien", "saturday": "sestdien",
        "sunday": "svētdien",
    }
    return labels.get(code or "", "")


def normalize_person_name(name):
    raw = _clean(name).strip(" .,!?:;")
    if not raw:
        return ""
    known = {
        "andrim": "Andris", "andri": "Andris", "andris": "Andris",
        "annai": "Anna", "anna": "Anna",
        "jānim": "Jānis", "janim": "Jānis", "jānis": "Jānis", "janis": "Jānis",
    }
    lower = raw.lower()
    if lower in known:
        return known[lower]
    if lower.endswith("im") and len(raw) > 4:
        return raw[:-2].capitalize() + "is"
    if lower.endswith("am") and len(raw) > 4:
        return raw[:-2].capitalize() + "s"
    if lower.endswith("ai") and len(raw) > 4:
        return raw[:-2].capitalize() + "a"
    return raw[:1].upper() + raw[1:]


def detect_client(text):
    raw = _clean(text)
    lower = raw.lower()
    words = raw.split()
    for word in words:
        w = word.strip(" .,!?:;")
        lw = w.lower()
        if lw in ["andrim", "andris", "andri", "annai", "anna", "jānim", "janim", "janis", "jānis"]:
            return normalize_person_name(w)
    for marker in ["klientam ", "klientei ", "klientu ", "klients "]:
        if marker in lower:
            idx = lower.find(marker) + len(marker)
            tail = raw[idx:].strip(" .,!?:;")
            if tail:
                return normalize_person_name(tail.split()[0])
    return ""


def detect_followup_task(text):
    raw = _clean(text)
    if not is_followup_text(raw):
        return None
    deadline = detect_deadline(raw)
    client = detect_client(raw)
    return {
        "type": "task",
        "object_type": "followup_task",
        "title": raw[:120],
        "raw_text": raw,
        "client": client,
        "client_name": client,
        "deadline": deadline,
        "deadline_label": deadline_label(deadline),
        "due_code": deadline,
        "due_label": deadline_label(deadline),
        "priority": "normal",
        "priority_label": "normāla",
        "status": "open",
        "status_label": "atvērts",
        "followup": True,
        "work_type": "followup",
        "source": "telegram",
        "source_module": "followup_engine",
        "origin": "assistant",
        "version": FOLLOWUP_ENGINE_VERSION,
    }


def build_followup_work_object(task_or_text, workspace_id="demo_small_business", store=False):
    if isinstance(task_or_text, dict):
        task = dict(task_or_text)
    else:
        task = detect_followup_task(str(task_or_text or "")) or {}
    if not task:
        return {}
    kwargs = {
        "title": task.get("title", task.get("raw_text", "")),
        "client_name": task.get("client_name") or task.get("client", ""),
        "due_code": task.get("due_code") or task.get("deadline", ""),
        "due_label": task.get("due_label") or task.get("deadline_label", ""),
        "workspace_id": workspace_id,
        "priority": task.get("priority", "normal"),
        "source": task.get("source", "telegram"),
        "raw_text": task.get("raw_text", task.get("title", "")),
    }
    if store:
        return create_followup_work_object(**kwargs)
    return build_followup_work_object_payload(**kwargs)


def is_followup_task(task):
    if (task or {}).get("followup") is True:
        return True
    title = _lower((task or {}).get("title", ""))
    raw_text = _lower((task or {}).get("raw_text", ""))
    return is_followup_text(f"{title} {raw_text}")


def enrich_task_with_followup(task):
    task = dict(task or {})
    if is_followup_task(task):
        task["followup"] = True
        task["work_type"] = "followup"
        task["object_type"] = "followup_task"
    else:
        task["followup"] = False
        task["work_type"] = task.get("work_type") or "general"
        task["object_type"] = task.get("object_type") or "task"
    task["version_followup"] = FOLLOWUP_ENGINE_VERSION
    return task


def build_followup_saved_answer(task):
    if not task:
        return ""
    lines = [
        "🔁 Piefiksēju follow-up darbu. ✅",
        "",
        f"Uzdevums: {task.get('title', '')}",
    ]
    if task.get("client") or task.get("client_name"):
        lines.append(f"Klients: {task.get('client') or task.get('client_name')}")
    if task.get("deadline_label") or task.get("due_label"):
        lines.append(f"Termiņš: {task.get('deadline_label') or task.get('due_label')}")
    lines.append("Tips: follow-up / atkārtots kontakts")
    lines.append("")
    lines.append("Nina šo uztvers kā klienta sekošanas darbu un var pārvērst par NinaOS Work Object.")
    lines.append("")
    lines.append(f"Versija: {FOLLOWUP_ENGINE_VERSION}")
    return "\n".join(lines)


def build_followup_status_answer():
    return (
        "🔁 Follow-up Engine V1.3 ir aktīvs. ✅\n\n"
        "Mērķis: follow-up tekstu pārvērst par NinaOS followup_task objektu.\n\n"
        "Tests:\n"
        "piektdien jāpajautā Andrim par atbildi\n\n"
        f"Bridge: {ASSISTANT_WORK_BRIDGE_VERSION}\n"
        f"Versija: {FOLLOWUP_ENGINE_VERSION}"
    )


def build_followup_context_answer(task):
    enriched = enrich_task_with_followup(task)
    title = _clean(enriched.get("title", ""))
    client = _clean(enriched.get("client", "")) or _clean(enriched.get("client_name", ""))
    if not enriched.get("followup"):
        return (
            "🔁 Šis uzdevums šobrīd neizskatās pēc follow-up darba.\n\n"
            f"Uzdevums: {title or '—'}\n"
            f"Klients: {client or '—'}\n\n"
            f"Versija: {FOLLOWUP_ENGINE_VERSION}"
        )
    payload = build_followup_work_object(enriched, store=False)
    return (
        "🔁 Nina atrada follow-up darbu. ✅\n\n"
        f"Uzdevums: {title or '—'}\n"
        f"Klients: {client or '—'}\n"
        "Tips: follow-up / atkārtots kontakts\n"
        f"Work Object Type: {payload.get('object_type', 'followup_task')}\n\n"
        f"Versija: {FOLLOWUP_ENGINE_VERSION}"
    )
