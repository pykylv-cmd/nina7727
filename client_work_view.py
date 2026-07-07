"""
client_work_view.py
NinaOS Client Work View — V1.2 Work Object Bridge + Sales Pipeline

V1.2:
- keeps old command behavior;
- supports old task dict lists;
- adds NinaOS Work Object snapshot via assistant_work_bridge.py;
- still uses sales_pipeline.py for CRM/Pipeline view when available.
"""

CLIENT_WORK_VIEW_VERSION = "Client Work View V1.2 — Work Object Bridge + Sales Pipeline"

try:
    from sales_pipeline import format_client_crm_view, analyze_client_tasks, SALES_PIPELINE_VERSION
except Exception as e:
    print("sales_pipeline.py imports nav pieejams client_work_view.py:", e)
    SALES_PIPELINE_VERSION = "Sales Pipeline nav pieslēgts"

    def format_client_crm_view(client_name, tasks):
        return ""

    def analyze_client_tasks(client_name, tasks):
        return {}

try:
    from assistant_work_bridge import build_client_workspace_snapshot, object_to_dict, ASSISTANT_WORK_BRIDGE_VERSION
except Exception as e:
    ASSISTANT_WORK_BRIDGE_VERSION = "Assistant Work Bridge not connected"

    def object_to_dict(obj):
        return dict(obj or {}) if isinstance(obj, dict) else {}

    def build_client_workspace_snapshot(client_name, workspace_id="demo_small_business"):
        return {"client_name": client_name, "workspace_id": workspace_id, "objects": [], "grouped": {}, "counts": {}, "total": 0}

def _clean(text):
    return (text or "").strip()

def normalize_client_name_v1(name):
    raw = _clean(name)
    if not raw:
        return ""
    mapping = {
        "andrim": "Andris", "andri": "Andris", "andris": "Andris",
        "annai": "Anna", "anna": "Anna",
        "jānim": "Jānis", "janim": "Jānis", "janis": "Jānis", "jānis": "Jānis",
    }
    lower = raw.lower().strip(" .,!?:;")
    if lower in mapping:
        return mapping[lower]
    return raw[:1].upper() + raw[1:]

def client_name_dative_v1(client_name):
    name = normalize_client_name_v1(client_name)
    mapping = {"Andris": "Andri", "Jānis": "Jāni", "Janis": "Jāni", "Anna": "Annu"}
    return mapping.get(name, name)

def extract_client_from_query(text):
    raw = _clean(text)
    lower = raw.lower()
    prefixes = [
        "kas notiek ar ", "kas ar ", "client work ",
        "andra pipeline", "andra statuss", "andris pipeline", "andris statuss",
    ]
    if lower in ["andra pipeline", "andra statuss", "andris pipeline", "andris statuss", "kas ar andri tālāk", "kas ar andri talak"]:
        return "Andris"
    for prefix in prefixes:
        if lower.startswith(prefix):
            tail = raw[len(prefix):].strip(" .,!?:;")
            return normalize_client_name_v1(tail)
    return ""

def task_matches_client(task, client_name):
    client_name = normalize_client_name_v1(client_name)
    if not client_name:
        return False
    task = object_to_dict(task)
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    task_client = normalize_client_name_v1(task.get("client", "") or task.get("client_name", "") or metadata.get("client_name", ""))
    title = _clean(task.get("title", ""))
    raw_text = _clean(task.get("raw_text", "")) or _clean(metadata.get("raw_text", ""))
    if task_client and task_client.lower() == client_name.lower():
        return True
    blob = f"{title} {raw_text}".lower()
    variants = {
        "Andris": ["andris", "andri", "andrim"],
        "Jānis": ["jānis", "janis", "jāni", "jani", "jānim", "janim"],
        "Anna": ["anna", "annu", "annai"],
    }.get(client_name, [client_name.lower()])
    return any(v in blob for v in variants)

def _object_text_for_crm(obj):
    data = object_to_dict(obj)
    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    return _clean(metadata.get("raw_text", "")) or _clean(data.get("title", ""))

def _legacy_client_work_view(client_name, matched):
    header_name = client_name_dative_v1(client_name)
    lines = [f"👥 Kas notiek ar {header_name}", "", f"Aktīvie darbi: {len(matched)}", ""]
    for i, task in enumerate(matched, 1):
        data = object_to_dict(task)
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
        title = _clean(data.get("title", ""))
        deadline = _clean(data.get("deadline_label", "")) or _clean(data.get("deadline", "")) or _clean(data.get("due_date", "")) or _clean(metadata.get("due_label", ""))
        followup = bool(data.get("followup")) or data.get("object_type") == "followup_task"
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

def build_client_workspace_answer(client_name, workspace_id="demo_small_business"):
    client_name = normalize_client_name_v1(client_name)
    snapshot = build_client_workspace_snapshot(client_name, workspace_id=workspace_id)
    grouped = snapshot.get("grouped", {})
    counts = snapshot.get("counts", {})
    lines = [
        f"👥 Klienta workspace: {client_name_dative_v1(client_name)}",
        "",
        f"Kopā objekti: {snapshot.get('total', 0)}",
        f"Follow-ups: {counts.get('followups', 0)}",
        f"Estimates/Offers: {counts.get('estimates', 0)}",
        f"Invoices: {counts.get('invoices', 0)}",
        f"Projects: {counts.get('projects', 0)}",
        "",
    ]
    for title, key in [("Follow-ups", "followups"), ("Tasks", "tasks"), ("Estimates / Offers", "estimates"), ("Invoices", "invoices"), ("Projects", "projects")]:
        items = grouped.get(key, [])
        if not items:
            continue
        lines.append(f"{title}:")
        for item in items[:5]:
            data = object_to_dict(item)
            lines.append(f"- {data.get('title', '')} ({data.get('status', '')})")
        lines.append("")
    if snapshot.get("total", 0) == 0:
        lines.append("Šobrīd neredzu aktīvus NinaOS work objects šim klientam.")
        lines.append("Ja vajag, vispirms iedod uzdevumu vai follow-up.")
    lines.append("")
    lines.append(f"Bridge: {ASSISTANT_WORK_BRIDGE_VERSION}")
    lines.append(f"Versija: {CLIENT_WORK_VIEW_VERSION}")
    return "\n".join(lines).strip()

def build_client_work_view(client_name, tasks=None, workspace_id="demo_small_business"):
    client_name = normalize_client_name_v1(client_name)
    if not client_name:
        return (
            "👥 Client Work View\n\n"
            "Pasaki klienta vārdu, piemēram:\n"
            "kas notiek ar Andri\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )
    matched = [task for task in (tasks or []) if task_matches_client(task, client_name)]
    if not matched:
        snapshot = build_client_workspace_snapshot(client_name, workspace_id=workspace_id)
        matched = snapshot.get("objects", [])
    if not matched:
        return (
            f"👥 Klientam {client_name_dative_v1(client_name)} šobrīd neredzu aktīvus darbus.\n\n"
            "Ja vajag, vispirms iedod uzdevumu.\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )
    try:
        crm_tasks = [_object_text_for_crm(task) for task in matched]
        crm_view = format_client_crm_view(client_name, crm_tasks)
        if crm_view:
            return crm_view + f"\n\nBridge: {ASSISTANT_WORK_BRIDGE_VERSION}"
    except Exception as e:
        print("build_client_work_view sales pipeline kļūda:", repr(e))
    return _legacy_client_work_view(client_name, matched)

def client_work_status():
    return (
        "👥 Client Work View V1.2 ir aktīvs. ✅\n\n"
        "Ja sales_pipeline.py ir pieslēgts, komanda rāda CRM/Pipeline skatu.\n"
        "Ja assistant_work_bridge.py ir pieslēgts, var lasīt NinaOS Work Objects.\n\n"
        "Tests:\n"
        "kas notiek ar Andri\n\n"
        f"Client Work versija: {CLIENT_WORK_VIEW_VERSION}\n"
        f"Sales Pipeline: {SALES_PIPELINE_VERSION}\n"
        f"Bridge: {ASSISTANT_WORK_BRIDGE_VERSION}"
    )
