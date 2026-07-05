# work_objects.py
# NinaOS Work Objects V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Universal Work Object layer for NinaOS
# - First object model for Nina Office Manager SMB dashboard
# - Supports tasks, clients, projects, estimates, invoices, follow-ups, documents
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


WORK_OBJECTS_VERSION = "Work Objects V1.0"


@dataclass(frozen=True)
class WorkObjectType:
    type_id: str
    name: str
    category: str
    description: str
    default_statuses: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    risk_level: str = "low"
    status: str = "active"


@dataclass
class WorkObject:
    object_id: str
    object_type: str
    title: str
    status: str = "open"
    workspace_id: str = "demo_small_business"
    assigned_agent_id: str = "nina_office_manager_smb"
    client_id: str = ""
    project_id: str = ""
    priority: str = "normal"
    due_date: str = ""
    linked_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# =========================================================
# Work Object Type Registry
# =========================================================

WORK_OBJECT_TYPES: Dict[str, WorkObjectType] = {
    "task": WorkObjectType(
        type_id="task",
        name="Task",
        category="operations",
        description="A work task with owner, status, priority and due date.",
        default_statuses=["open", "in_progress", "done", "cancelled"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "client": WorkObjectType(
        type_id="client",
        name="Client",
        category="crm",
        description="A client or customer record inside a workspace.",
        default_statuses=["active", "lead", "inactive", "archived"],
        allowed_roles=["client_followup_manager", "finance_admin_assistant", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "project": WorkObjectType(
        type_id="project",
        name="Project",
        category="operations",
        description="A client or internal project with tasks, estimates, files and invoices.",
        default_statuses=["open", "active", "on_hold", "completed", "cancelled"],
        allowed_roles=["office_manager_core", "estimating_assistant_basic", "document_admin"],
        risk_level="medium",
    ),

    "estimate": WorkObjectType(
        type_id="estimate",
        name="Estimate",
        category="estimating",
        description="An estimate or pricing draft for client work.",
        default_statuses=["draft", "in_progress", "sent", "approved", "rejected", "cancelled"],
        allowed_roles=["estimating_assistant_basic", "client_followup_manager", "document_admin"],
        risk_level="medium",
    ),

    "offer": WorkObjectType(
        type_id="offer",
        name="Offer",
        category="sales",
        description="A client offer or proposal draft.",
        default_statuses=["draft", "sent", "accepted", "rejected", "expired"],
        allowed_roles=["estimating_assistant_basic", "client_followup_manager"],
        risk_level="medium",
    ),

    "invoice": WorkObjectType(
        type_id="invoice",
        name="Invoice",
        category="finance",
        description="Invoice administration object for payment tracking.",
        default_statuses=["draft", "sent", "paid", "overdue", "cancelled"],
        allowed_roles=["finance_admin_assistant", "client_followup_manager", "document_admin"],
        risk_level="high",
    ),

    "payment_request": WorkObjectType(
        type_id="payment_request",
        name="Payment Request",
        category="finance",
        description="Payment request or payment follow-up object.",
        default_statuses=["open", "sent", "paid", "overdue", "cancelled"],
        allowed_roles=["finance_admin_assistant"],
        risk_level="high",
    ),

    "followup_task": WorkObjectType(
        type_id="followup_task",
        name="Follow-up Task",
        category="crm",
        description="Follow-up item connected to client, invoice, estimate, meeting or offer.",
        default_statuses=["open", "scheduled", "done", "cancelled"],
        allowed_roles=["client_followup_manager", "office_manager_core"],
        risk_level="medium",
    ),

    "reminder": WorkObjectType(
        type_id="reminder",
        name="Reminder",
        category="operations",
        description="Reminder object for user, workspace, client or project.",
        default_statuses=["active", "sent", "cancelled"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "document_case": WorkObjectType(
        type_id="document_case",
        name="Document Case",
        category="documents",
        description="Document bundle connected to client, project, estimate, invoice or contract.",
        default_statuses=["open", "processing", "ready", "archived"],
        allowed_roles=["document_admin", "finance_admin_assistant", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "contract": WorkObjectType(
        type_id="contract",
        name="Contract",
        category="legal_documents",
        description="Contract document object requiring careful approval before sending.",
        default_statuses=["draft", "review", "approved", "sent", "signed", "archived"],
        allowed_roles=["document_admin"],
        risk_level="high",
    ),

    "daily_plan": WorkObjectType(
        type_id="daily_plan",
        name="Daily Plan",
        category="operations",
        description="Daily work plan for a workspace or user.",
        default_statuses=["draft", "active", "completed"],
        allowed_roles=["office_manager_core"],
        risk_level="low",
    ),

    "expense_record": WorkObjectType(
        type_id="expense_record",
        name="Expense Record",
        category="finance",
        description="Basic expense administration record.",
        default_statuses=["draft", "categorized", "sent_to_accountant", "archived"],
        allowed_roles=["finance_admin_assistant"],
        risk_level="medium",
    ),

    "meeting_note": WorkObjectType(
        type_id="meeting_note",
        name="Meeting Note",
        category="operations",
        description="Meeting notes connected to client, project or follow-up.",
        default_statuses=["draft", "saved", "linked"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "client_request": WorkObjectType(
        type_id="client_request",
        name="Client Request",
        category="crm",
        description="Incoming client request that may become task, project, estimate or offer.",
        default_statuses=["new", "reviewed", "converted", "closed"],
        allowed_roles=["client_followup_manager", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "project_scope": WorkObjectType(
        type_id="project_scope",
        name="Project Scope",
        category="estimating",
        description="Structured scope of work for project or estimate.",
        default_statuses=["draft", "review", "approved"],
        allowed_roles=["estimating_assistant_basic"],
        risk_level="medium",
    ),

    "client_file_bundle": WorkObjectType(
        type_id="client_file_bundle",
        name="Client File Bundle",
        category="documents",
        description="File bundle connected to one client.",
        default_statuses=["open", "organized", "archived"],
        allowed_roles=["document_admin"],
        risk_level="medium",
    ),

    "accounting_document_case": WorkObjectType(
        type_id="accounting_document_case",
        name="Accounting Document Case",
        category="finance_documents",
        description="Document package prepared for accountant or finance review.",
        default_statuses=["open", "prepared", "sent_to_accountant", "archived"],
        allowed_roles=["finance_admin_assistant", "document_admin"],
        risk_level="high",
    ),
}


# =========================================================
# Demo object store
# =========================================================

WORK_OBJECT_STORE: Dict[str, WorkObject] = {}


# =========================================================
# Core helpers
# =========================================================

def work_objects_status() -> str:
    return (
        "🧱 NinaOS Work Objects\n\n"
        f"Version: {WORK_OBJECTS_VERSION}\n"
        f"Registered object types: {len(WORK_OBJECT_TYPES)}\n"
        f"Stored demo objects: {len(WORK_OBJECT_STORE)}\n\n"
        "Core objects:\n"
        "• task\n"
        "• client\n"
        "• project\n"
        "• estimate\n"
        "• invoice\n"
        "• followup_task\n"
        "• document_case\n\n"
        "Status: active ✅"
    )


def get_work_object_type(type_id: str) -> Optional[WorkObjectType]:
    return WORK_OBJECT_TYPES.get(type_id)


def list_work_object_types() -> List[WorkObjectType]:
    return list(WORK_OBJECT_TYPES.values())


def list_work_object_type_ids() -> List[str]:
    return sorted(WORK_OBJECT_TYPES.keys())


def create_work_object(
    object_type: str,
    title: str,
    workspace_id: str = "demo_small_business",
    assigned_agent_id: str = "nina_office_manager_smb",
    client_id: str = "",
    project_id: str = "",
    priority: str = "normal",
    due_date: str = "",
    status: Optional[str] = None,
    linked_files: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkObject:
    object_type_def = get_work_object_type(object_type)
    if not object_type_def:
        raise ValueError(f"Unknown work object type: {object_type}")

    if status is None:
        status = object_type_def.default_statuses[0] if object_type_def.default_statuses else "open"

    object_id = f"{object_type}_{len(WORK_OBJECT_STORE) + 1}"

    obj = WorkObject(
        object_id=object_id,
        object_type=object_type,
        title=title.strip(),
        status=status,
        workspace_id=workspace_id,
        assigned_agent_id=assigned_agent_id,
        client_id=client_id,
        project_id=project_id,
        priority=priority,
        due_date=due_date,
        linked_files=linked_files or [],
        metadata=metadata or {},
    )

    WORK_OBJECT_STORE[object_id] = obj
    return obj


def get_work_object(object_id: str) -> Optional[WorkObject]:
    return WORK_OBJECT_STORE.get(object_id)


def list_work_objects(
    workspace_id: Optional[str] = None,
    object_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[WorkObject]:
    objects = list(WORK_OBJECT_STORE.values())

    if workspace_id:
        objects = [o for o in objects if o.workspace_id == workspace_id]

    if object_type:
        objects = [o for o in objects if o.object_type == object_type]

    if status:
        objects = [o for o in objects if o.status == status]

    return objects


def update_work_object_status(object_id: str, status: str) -> Optional[WorkObject]:
    obj = get_work_object(object_id)
    if not obj:
        return None

    obj.status = status
    obj.updated_at = datetime.utcnow().isoformat()
    return obj


def count_work_objects(
    workspace_id: str = "demo_small_business",
    object_type: Optional[str] = None,
    statuses: Optional[List[str]] = None,
) -> int:
    objects = list_work_objects(workspace_id=workspace_id, object_type=object_type)

    if statuses:
        objects = [o for o in objects if o.status in statuses]

    return len(objects)


def dashboard_counts(workspace_id: str = "demo_small_business") -> Dict[str, int]:
    return {
        "tasks_today": count_work_objects(
            workspace_id=workspace_id,
            object_type="task",
            statuses=["open", "in_progress"],
        ),
        "followups": count_work_objects(
            workspace_id=workspace_id,
            object_type="followup_task",
            statuses=["open", "scheduled"],
        ),
        "invoices_due": count_work_objects(
            workspace_id=workspace_id,
            object_type="invoice",
            statuses=["sent", "overdue"],
        ),
        "estimates_in_progress": count_work_objects(
            workspace_id=workspace_id,
            object_type="estimate",
            statuses=["draft", "in_progress"],
        ),
        "projects_active": count_work_objects(
            workspace_id=workspace_id,
            object_type="project",
            statuses=["open", "active"],
        ),
    }


# =========================================================
# Demo seed
# =========================================================

def seed_demo_work_objects() -> Dict[str, Any]:
    if WORK_OBJECT_STORE:
        return {
            "ok": True,
            "message": "Demo work objects already exist.",
            "count": len(WORK_OBJECT_STORE),
        }

    create_work_object(
        object_type="client",
        title="Demo Client",
        status="active",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="task",
        title="Prepare today workspace priorities",
        priority="high",
        status="open",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="followup_task",
        title="Follow up with Demo Client about offer",
        priority="normal",
        status="scheduled",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="estimate",
        title="Demo estimate draft",
        status="draft",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="invoice",
        title="Demo invoice follow-up",
        status="sent",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="project",
        title="Demo active project",
        status="active",
        metadata={"source": "demo_seed"},
    )

    create_work_object(
        object_type="document_case",
        title="Demo client document package",
        status="open",
        metadata={"source": "demo_seed"},
    )

    return {
        "ok": True,
        "message": "Demo work objects created.",
        "count": len(WORK_OBJECT_STORE),
    }


def clear_demo_work_objects() -> Dict[str, Any]:
    WORK_OBJECT_STORE.clear()
    return {
        "ok": True,
        "message": "Demo work objects cleared.",
        "count": 0,
    }


# =========================================================
# Human-readable answers
# =========================================================

def build_work_object_types_answer() -> str:
    lines = [
        "🧱 NinaOS Work Object Types",
        "",
        f"Version: {WORK_OBJECTS_VERSION}",
        "",
    ]

    for obj_type in list_work_object_types():
        lines.append(f"• {obj_type.type_id}")
        lines.append(f"  Name: {obj_type.name}")
        lines.append(f"  Category: {obj_type.category}")
        lines.append(f"  Risk: {obj_type.risk_level}")
        lines.append("")

    return "\n".join(lines).strip()


def build_work_objects_answer(workspace_id: str = "demo_small_business") -> str:
    objects = list_work_objects(workspace_id=workspace_id)

    lines = [
        "🧱 NinaOS Work Objects",
        "",
        f"Workspace: {workspace_id}",
        f"Objects: {len(objects)}",
        "",
    ]

    if not objects:
        lines.append("No work objects yet.")
    else:
        for obj in objects:
            lines.append(f"• {obj.object_id}")
            lines.append(f"  Type: {obj.object_type}")
            lines.append(f"  Title: {obj.title}")
            lines.append(f"  Status: {obj.status}")
            lines.append(f"  Priority: {obj.priority}")
            lines.append("")

    lines.append(f"Version: {WORK_OBJECTS_VERSION}")
    return "\n".join(lines).strip()


def build_work_object_counts_answer(workspace_id: str = "demo_small_business") -> str:
    counts = dashboard_counts(workspace_id)

    return (
        "📊 NinaOS Work Object Counts\n\n"
        f"Workspace: {workspace_id}\n\n"
        f"Tasks Today: {counts['tasks_today']}\n"
        f"Follow-ups: {counts['followups']}\n"
        f"Invoices Due: {counts['invoices_due']}\n"
        f"Estimates in Progress: {counts['estimates_in_progress']}\n"
        f"Active Projects: {counts['projects_active']}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def build_demo_seed_answer() -> str:
    result = seed_demo_work_objects()

    return (
        "🧪 NinaOS Demo Work Objects\n\n"
        f"{result.get('message')}\n"
        f"Objects: {result.get('count')}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def build_demo_clear_answer() -> str:
    result = clear_demo_work_objects()

    return (
        "🧹 NinaOS Demo Work Objects\n\n"
        f"{result.get('message')}\n"
        f"Objects: {result.get('count')}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def route_work_objects_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["work objects", "objects", "object types"]:
        return build_work_object_types_answer()

    if lower in ["work object list", "objects list", "my objects"]:
        return build_work_objects_answer()

    if lower in ["object counts", "work object counts", "dashboard counts"]:
        return build_work_object_counts_answer()

    if lower in ["seed demo objects", "demo objects", "create demo objects"]:
        return build_demo_seed_answer()

    if lower in ["clear demo objects", "delete demo objects"]:
        return build_demo_clear_answer()

    if lower in ["work objects status", "objects status"]:
        return work_objects_status()

    return None


def work_objects_schema() -> Dict[str, Any]:
    return {
        "version": WORK_OBJECTS_VERSION,
        "object_types": {
            type_id: obj_type.__dict__
            for type_id, obj_type in WORK_OBJECT_TYPES.items()
        },
        "stored_objects": {
            object_id: obj.__dict__
            for object_id, obj in WORK_OBJECT_STORE.items()
        },
    }


if __name__ == "__main__":
    print(work_objects_status())
    print()
    print(build_work_object_types_answer())
    print()
    print(build_demo_seed_answer())
    print()
    print(build_work_object_counts_answer())
