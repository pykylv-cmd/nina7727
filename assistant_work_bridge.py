"""
assistant_work_bridge.py
NinaOS Assistant Work Bridge — V1.0

Purpose:
- Connect assistant/core task flow to NinaOS Work Objects.
- Keep app.py thinner.
- Let follow-up, client work view, cleanup and future assistant actions speak the same object language as web_app.py.

Safe standalone import:
- If work_objects.py is missing, returns safe dict payloads and does not crash.
"""

from typing import Any, Dict, List, Optional

ASSISTANT_WORK_BRIDGE_VERSION = "Assistant Work Bridge V1.0"
DEFAULT_WORKSPACE_ID = "demo_small_business"
DEFAULT_AGENT_ID = "nina_office_manager_smb"

try:
    from work_objects import create_work_object, list_work_objects, WORK_OBJECTS_VERSION
except Exception:
    WORK_OBJECTS_VERSION = "Work Objects not connected"

    def create_work_object(*args, **kwargs):
        return None

    def list_work_objects(*args, **kwargs):
        return []


def _clean(text: Any) -> str:
    return str(text or "").strip()


def _lower(text: Any) -> str:
    return _clean(text).lower()


def object_to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}

    if isinstance(obj, dict):
        data = dict(obj)
    else:
        data = {
            "object_id": getattr(obj, "object_id", ""),
            "object_type": getattr(obj, "object_type", ""),
            "title": getattr(obj, "title", ""),
            "status": getattr(obj, "status", ""),
            "workspace_id": getattr(obj, "workspace_id", DEFAULT_WORKSPACE_ID),
            "assigned_agent_id": getattr(obj, "assigned_agent_id", DEFAULT_AGENT_ID),
            "client_id": getattr(obj, "client_id", ""),
            "project_id": getattr(obj, "project_id", ""),
            "priority": getattr(obj, "priority", "normal"),
            "due_date": getattr(obj, "due_date", ""),
            "linked_files": getattr(obj, "linked_files", []),
            "metadata": getattr(obj, "metadata", {}),
            "created_at": getattr(obj, "created_at", ""),
            "updated_at": getattr(obj, "updated_at", ""),
        }

    data.setdefault("metadata", {})
    if data.get("client") and not data.get("client_name"):
        data["client_name"] = data.get("client")
    if isinstance(data.get("metadata"), dict) and not data.get("client_name"):
        data["client_name"] = data["metadata"].get("client_name", "")
    return data


def list_assistant_work_objects(workspace_id: str = DEFAULT_WORKSPACE_ID, object_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        objs = list_work_objects(workspace_id=workspace_id, object_type=object_type, status=status)
        return [object_to_dict(o) for o in objs]
    except Exception:
        return []


def build_followup_work_object_payload(title: str, client_name: str = "", due_code: str = "", due_label: str = "", workspace_id: str = DEFAULT_WORKSPACE_ID, priority: str = "normal", source: str = "telegram", raw_text: str = "") -> Dict[str, Any]:
    title = _clean(title) or _clean(raw_text)
    client_name = _clean(client_name)

    return {
        "object_type": "followup_task",
        "title": title[:160],
        "workspace_id": workspace_id or DEFAULT_WORKSPACE_ID,
        "assigned_agent_id": DEFAULT_AGENT_ID,
        "client_id": "",
        "project_id": "",
        "priority": priority or "normal",
        "due_date": due_code or "",
        "status": "scheduled" if due_code else "open",
        "linked_files": [],
        "metadata": {
            "client_name": client_name,
            "due_code": due_code or "",
            "due_label": due_label or "",
            "raw_text": raw_text or title,
            "source": source or "telegram",
            "source_module": "followup_engine",
            "origin": "assistant",
            "tags": ["followup", "client_contact"],
            "bridge_version": ASSISTANT_WORK_BRIDGE_VERSION,
        },
    }


def create_followup_work_object(title: str, client_name: str = "", due_code: str = "", due_label: str = "", workspace_id: str = DEFAULT_WORKSPACE_ID, priority: str = "normal", source: str = "telegram", raw_text: str = "") -> Dict[str, Any]:
    payload = build_followup_work_object_payload(title, client_name, due_code, due_label, workspace_id, priority, source, raw_text)

    try:
        obj = create_work_object(**payload)
        data = object_to_dict(obj)
        if data:
            data["stored"] = True
            return data
    except TypeError:
        try:
            obj = create_work_object(
                object_type=payload["object_type"],
                title=payload["title"],
                workspace_id=payload["workspace_id"],
                assigned_agent_id=payload["assigned_agent_id"],
                client_id=payload["client_id"],
                project_id=payload["project_id"],
                priority=payload["priority"],
                due_date=payload["due_date"],
                status=payload["status"],
                metadata=payload["metadata"],
            )
            data = object_to_dict(obj)
            if data:
                data["stored"] = True
                return data
        except Exception:
            pass
    except Exception:
        pass

    payload["stored"] = False
    return payload


def object_matches_client(obj: Any, client_name: str) -> bool:
    data = object_to_dict(obj)
    client_name = _clean(client_name)
    if not client_name:
        return False

    variants = {
        "Andris": ["andris", "andri", "andrim"],
        "Jānis": ["jānis", "janis", "jāni", "jani", "jānim", "janim"],
        "Anna": ["anna", "annu", "annai"],
    }.get(client_name, [client_name.lower()])

    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    blob = " ".join([
        _clean(data.get("title")),
        _clean(data.get("client_name")),
        _clean(data.get("client_id")),
        _clean(metadata.get("client_name", "")),
        _clean(metadata.get("raw_text", "")),
    ]).lower()

    return any(v.lower() in blob for v in variants)


def get_client_work_objects(client_name: str, workspace_id: str = DEFAULT_WORKSPACE_ID) -> List[Dict[str, Any]]:
    objects = list_assistant_work_objects(workspace_id=workspace_id)
    return [o for o in objects if object_matches_client(o, client_name)]


def build_client_workspace_snapshot(client_name: str, workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    objects = get_client_work_objects(client_name, workspace_id=workspace_id)

    grouped = {
        "tasks": [],
        "followups": [],
        "estimates": [],
        "invoices": [],
        "projects": [],
        "documents": [],
        "other": [],
    }

    for obj in objects:
        t = obj.get("object_type", "")
        if t == "task":
            grouped["tasks"].append(obj)
        elif t == "followup_task":
            grouped["followups"].append(obj)
        elif t in ["estimate", "offer"]:
            grouped["estimates"].append(obj)
        elif t in ["invoice", "payment_request"]:
            grouped["invoices"].append(obj)
        elif t == "project":
            grouped["projects"].append(obj)
        elif t in ["document_case", "client_file_bundle", "accounting_document_case", "contract"]:
            grouped["documents"].append(obj)
        else:
            grouped["other"].append(obj)

    return {
        "client_name": client_name,
        "workspace_id": workspace_id,
        "objects": objects,
        "grouped": grouped,
        "counts": {k: len(v) for k, v in grouped.items()},
        "total": len(objects),
        "version": ASSISTANT_WORK_BRIDGE_VERSION,
    }


def filter_assistant_visible_objects(objects: List[Any]) -> List[Dict[str, Any]]:
    hidden_statuses = {"completed", "done", "deleted", "archived", "cancelled", "canceled"}
    visible = []
    for obj in objects or []:
        data = object_to_dict(obj)
        if _lower(data.get("status")) in hidden_statuses:
            continue
        if _lower(data.get("title")) in {"follow-up", "followup", "client context", "db health"}:
            continue
        visible.append(data)
    return visible


def assistant_work_bridge_status() -> str:
    return (
        "🔗 NinaOS Assistant Work Bridge\n\n"
        f"Version: {ASSISTANT_WORK_BRIDGE_VERSION}\n"
        f"Work Objects: {WORK_OBJECTS_VERSION}\n\n"
        "Purpose: connect assistant/core flows to NinaOS Work Objects.\n\n"
        "Status: active ✅"
    )
