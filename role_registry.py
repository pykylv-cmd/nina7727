# role_registry.py
# NinaOS Role Registry V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Central registry for NinaOS RolePacks
# - Supports composite workers
# - First strategic worker: Nina Office Manager SMB
#
# This file is intentionally standalone and safe to import.
# It does not require database access.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


ROLE_REGISTRY_VERSION = "Role Registry V1.0"


@dataclass(frozen=True)
class RolePackDefinition:
    role_id: str
    name: str
    category: str
    description: str
    allowed_work_objects: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    memory_scopes: List[str] = field(default_factory=list)
    approval_required_for: List[str] = field(default_factory=list)
    risk_level: str = "low"
    exchange_allowed: bool = False
    status: str = "active"


@dataclass(frozen=True)
class CompositeWorkerDefinition:
    worker_id: str
    name: str
    description: str
    role_ids: List[str]
    target_customer: str
    primary_channel: str = "workspace"
    status: str = "active"


# =========================
# Core RolePacks
# =========================

ROLE_PACKS: Dict[str, RolePackDefinition] = {
    "office_manager_core": RolePackDefinition(
        role_id="office_manager_core",
        name="Office Manager Core",
        category="operations",
        description=(
            "Pamata biroja vadības slānis: taski, termiņi, dienas plāns, "
            "darba prioritātes un koordinācija."
        ),
        allowed_work_objects=[
            "task",
            "reminder",
            "project",
            "daily_plan",
            "meeting_note",
        ],
        allowed_tools=[
            "task_tools",
            "daily_planner",
            "reminder_tools",
            "project_tools",
            "workspace_summary",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Agent Memory",
            "Role Memory",
            "Project Memory",
        ],
        approval_required_for=[
            "delete_project",
            "export_workspace_tasks",
        ],
        risk_level="low",
        exchange_allowed=True,
    ),

    "finance_admin_assistant": RolePackDefinition(
        role_id="finance_admin_assistant",
        name="Finance Admin Assistant",
        category="finance",
        description=(
            "Administratīvs finanšu palīgs mazam uzņēmumam: invoice admin, "
            "maksājumu termiņi, dokumentu sagatavošana grāmatvedim."
        ),
        allowed_work_objects=[
            "invoice",
            "payment_request",
            "expense_record",
            "accounting_document_case",
            "document_case",
            "client",
        ],
        allowed_tools=[
            "invoice_admin_tools",
            "payment_reminder_tools",
            "document_tools",
            "client_tools",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Company Memory",
            "Client Memory",
            "Document Memory",
            "Role Memory",
        ],
        approval_required_for=[
            "approve_payment",
            "send_invoice",
            "export_financial_data",
            "delete_invoice",
        ],
        risk_level="medium",
        exchange_allowed=True,
    ),

    "estimating_assistant_basic": RolePackDefinition(
        role_id="estimating_assistant_basic",
        name="Estimating Assistant Basic",
        category="estimating",
        description=(
            "Sākotnējās tāmes un piedāvājuma sagatavošanas palīgs: klienta "
            "pieprasījuma strukturēšana, estimate/offer drafti, follow-up."
        ),
        allowed_work_objects=[
            "estimate",
            "offer",
            "project_scope",
            "material_list",
            "client_request",
            "project",
            "client",
            "document_case",
        ],
        allowed_tools=[
            "estimate_draft_tools",
            "offer_tools",
            "client_tools",
            "document_tools",
            "followup_tools",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Client Memory",
            "Project Memory",
            "Document Memory",
            "Role Memory",
        ],
        approval_required_for=[
            "send_final_estimate",
            "approve_price",
            "send_binding_offer",
            "delete_estimate",
        ],
        risk_level="medium",
        exchange_allowed=True,
    ),

    "client_followup_manager": RolePackDefinition(
        role_id="client_followup_manager",
        name="Client Follow-up Manager",
        category="sales_operations",
        description=(
            "Klientu follow-up slānis: piedāvājumi, tikšanās, rēķini, "
            "neatbildēti klienti un termiņi."
        ),
        allowed_work_objects=[
            "client",
            "followup_task",
            "deal",
            "invoice",
            "estimate",
            "offer",
            "meeting_note",
            "reminder",
        ],
        allowed_tools=[
            "followup_tools",
            "client_tools",
            "task_tools",
            "reminder_tools",
            "message_draft_tools",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Client Memory",
            "Project Memory",
            "Agent Memory",
            "Role Memory",
        ],
        approval_required_for=[
            "send_client_message",
            "export_client_data",
            "delete_client",
        ],
        risk_level="medium",
        exchange_allowed=True,
    ),

    "document_admin": RolePackDefinition(
        role_id="document_admin",
        name="Document Admin",
        category="documents",
        description=(
            "Dokumentu kārtības slānis: failu piesaiste klientiem, projektiem, "
            "rēķiniem, tāmēm un dokumentu lietām."
        ),
        allowed_work_objects=[
            "document_case",
            "contract",
            "invoice",
            "estimate",
            "client_file_bundle",
            "project",
            "client",
        ],
        allowed_tools=[
            "document_tools",
            "file_upload_tools",
            "file_linking_tools",
            "knowledge_vault_tools",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Document Memory",
            "Client Memory",
            "Project Memory",
            "Role Memory",
        ],
        approval_required_for=[
            "delete_file",
            "export_sensitive_file",
            "share_document_external",
        ],
        risk_level="medium",
        exchange_allowed=True,
    ),
}


# =========================
# Future / catalog roles
# =========================

FUTURE_ROLE_PACKS: Dict[str, RolePackDefinition] = {
    "sales_assistant": RolePackDefinition(
        role_id="sales_assistant",
        name="Sales Assistant",
        category="sales",
        description="Pārdošanas palīgs: lead, deal, offer, CRM un follow-up.",
        allowed_work_objects=["lead", "deal", "offer", "client", "followup_task"],
        allowed_tools=["sales_tools", "client_tools", "followup_tools"],
        memory_scopes=["Workspace Memory", "Client Memory", "Role Memory"],
        approval_required_for=["send_offer", "export_client_data"],
        risk_level="medium",
        exchange_allowed=True,
        status="planned",
    ),

    "support_assistant": RolePackDefinition(
        role_id="support_assistant",
        name="Client Support Assistant",
        category="customer_service",
        description="Klientu servisa palīgs: FAQ, tickets, sūdzības un eskalācijas.",
        allowed_work_objects=["case", "client", "report", "followup_task"],
        allowed_tools=["support_tools", "client_tools", "escalation_tools"],
        memory_scopes=["Workspace Memory", "Client Memory", "Role Memory"],
        approval_required_for=["close_sensitive_case"],
        risk_level="medium",
        exchange_allowed=True,
        status="planned",
    ),

    "finance_accountant_basic": RolePackDefinition(
        role_id="finance_accountant_basic",
        name="Accountant Assistant Basic",
        category="finance",
        description="Grāmatvedības asistents: invoice, reports, documents, accounting period.",
        allowed_work_objects=["invoice", "report", "accounting_document_case", "expense_record"],
        allowed_tools=["accounting_tools", "document_tools"],
        memory_scopes=["Workspace Memory", "Company Memory", "Document Memory", "Role Memory"],
        approval_required_for=["submit_tax_document", "approve_accounting_report"],
        risk_level="high",
        exchange_allowed=True,
        status="planned",
    ),

    "estimator_professional": RolePackDefinition(
        role_id="estimator_professional",
        name="Estimator Professional",
        category="construction",
        description="Pilns tāmētāja role pack būvniecības un servisa uzņēmumiem.",
        allowed_work_objects=["estimate", "project", "material_list", "offer", "document_case"],
        allowed_tools=["estimate_tools", "document_tools", "project_tools"],
        memory_scopes=["Workspace Memory", "Project Memory", "Document Memory", "Role Memory"],
        approval_required_for=["send_final_estimate", "approve_project_budget"],
        risk_level="high",
        exchange_allowed=True,
        status="planned",
    ),
}


# =========================
# Composite Workers
# =========================

COMPOSITE_WORKERS: Dict[str, CompositeWorkerDefinition] = {
    "nina_office_manager_smb": CompositeWorkerDefinition(
        worker_id="nina_office_manager_smb",
        name="Nina Office Manager SMB",
        description=(
            "Pirmais stratēģiskais NinaOS gatavais darbinieks: AI biroja vadītāja "
            "mazajiem uzņēmumiem ar office, finance admin, estimating, follow-up "
            "un document admin slāņiem."
        ),
        role_ids=[
            "office_manager_core",
            "finance_admin_assistant",
            "estimating_assistant_basic",
            "client_followup_manager",
            "document_admin",
        ],
        target_customer="Small businesses, 1–20 people",
        primary_channel="Web Workspace + Telegram + Mobile later",
        status="priority",
    ),
}


# =========================
# Public API
# =========================

def role_registry_status() -> str:
    active_roles = len([r for r in ROLE_PACKS.values() if r.status == "active"])
    planned_roles = len(FUTURE_ROLE_PACKS)
    composite_workers = len(COMPOSITE_WORKERS)

    return (
        "🧩 NinaOS Role Registry\n\n"
        f"Versija: {ROLE_REGISTRY_VERSION}\n"
        f"Aktīvie RolePacks: {active_roles}\n"
        f"Plānotie RolePacks: {planned_roles}\n"
        f"Composite Workers: {composite_workers}\n\n"
        "Prioritārais worker:\n"
        "• Nina Office Manager SMB\n\n"
        "Statuss: aktīvs ✅"
    )


def get_role_pack(role_id: str) -> Optional[RolePackDefinition]:
    if role_id in ROLE_PACKS:
        return ROLE_PACKS[role_id]
    if role_id in FUTURE_ROLE_PACKS:
        return FUTURE_ROLE_PACKS[role_id]
    return None


def list_role_packs(include_planned: bool = False) -> List[RolePackDefinition]:
    roles = list(ROLE_PACKS.values())
    if include_planned:
        roles.extend(FUTURE_ROLE_PACKS.values())
    return roles


def list_role_ids(include_planned: bool = False) -> List[str]:
    return [role.role_id for role in list_role_packs(include_planned=include_planned)]


def get_composite_worker(worker_id: str) -> Optional[CompositeWorkerDefinition]:
    return COMPOSITE_WORKERS.get(worker_id)


def list_composite_workers() -> List[CompositeWorkerDefinition]:
    return list(COMPOSITE_WORKERS.values())


def get_worker_role_stack(worker_id: str) -> List[RolePackDefinition]:
    worker = get_composite_worker(worker_id)
    if not worker:
        return []

    stack = []
    for role_id in worker.role_ids:
        role = get_role_pack(role_id)
        if role:
            stack.append(role)
    return stack


def get_worker_allowed_work_objects(worker_id: str) -> List[str]:
    objects = set()
    for role in get_worker_role_stack(worker_id):
        objects.update(role.allowed_work_objects)
    return sorted(objects)


def get_worker_allowed_tools(worker_id: str) -> List[str]:
    tools = set()
    for role in get_worker_role_stack(worker_id):
        tools.update(role.allowed_tools)
    return sorted(tools)


def get_worker_memory_scopes(worker_id: str) -> List[str]:
    scopes = set()
    for role in get_worker_role_stack(worker_id):
        scopes.update(role.memory_scopes)
    return sorted(scopes)


def get_worker_approval_rules(worker_id: str) -> List[str]:
    rules = set()
    for role in get_worker_role_stack(worker_id):
        rules.update(role.approval_required_for)
    return sorted(rules)


def build_roles_answer(include_planned: bool = False) -> str:
    roles = list_role_packs(include_planned=include_planned)

    lines = [
        "🧩 NinaOS RolePacks",
        "",
        f"Versija: {ROLE_REGISTRY_VERSION}",
        "",
    ]

    for role in roles:
        status_mark = "✅" if role.status == "active" else "🕓"
        lines.append(f"{status_mark} {role.role_id}")
        lines.append(f"   Nosaukums: {role.name}")
        lines.append(f"   Kategorija: {role.category}")
        lines.append(f"   Risks: {role.risk_level}")
        lines.append("")

    return "\n".join(lines).strip()


def build_composite_workers_answer() -> str:
    lines = [
        "👥 NinaOS Composite Workers",
        "",
        f"Versija: {ROLE_REGISTRY_VERSION}",
        "",
    ]

    for worker in list_composite_workers():
        lines.append(f"✅ {worker.worker_id}")
        lines.append(f"   Nosaukums: {worker.name}")
        lines.append(f"   Klients: {worker.target_customer}")
        lines.append(f"   Statuss: {worker.status}")
        lines.append("   Role stack:")
        for role_id in worker.role_ids:
            lines.append(f"   • {role_id}")
        lines.append("")

    return "\n".join(lines).strip()


def build_office_manager_smb_answer() -> str:
    worker_id = "nina_office_manager_smb"
    worker = get_composite_worker(worker_id)

    if not worker:
        return "Nina Office Manager SMB nav atrasta role registry."

    lines = [
        "🏢 Nina Office Manager SMB",
        "",
        worker.description,
        "",
        "Role stack:",
    ]

    for role in get_worker_role_stack(worker_id):
        lines.append(f"• {role.name} ({role.role_id})")

    lines.extend([
        "",
        "Atļautie Work Objects:",
    ])

    for obj in get_worker_allowed_work_objects(worker_id):
        lines.append(f"• {obj}")

    lines.extend([
        "",
        "Atļautie Tools:",
    ])

    for tool in get_worker_allowed_tools(worker_id):
        lines.append(f"• {tool}")

    lines.extend([
        "",
        "Memory Scopes:",
    ])

    for scope in get_worker_memory_scopes(worker_id):
        lines.append(f"• {scope}")

    lines.extend([
        "",
        "Approval vajadzīgs:",
    ])

    for rule in get_worker_approval_rules(worker_id):
        lines.append(f"• {rule}")

    lines.extend([
        "",
        f"Versija: {ROLE_REGISTRY_VERSION}",
    ])

    return "\n".join(lines)


def role_registry_schema() -> Dict[str, Any]:
    return {
        "version": ROLE_REGISTRY_VERSION,
        "active_roles": {
            role_id: role.__dict__ for role_id, role in ROLE_PACKS.items()
        },
        "planned_roles": {
            role_id: role.__dict__ for role_id, role in FUTURE_ROLE_PACKS.items()
        },
        "composite_workers": {
            worker_id: worker.__dict__ for worker_id, worker in COMPOSITE_WORKERS.items()
        },
    }


def validate_worker_role_stack(worker_id: str) -> Dict[str, Any]:
    worker = get_composite_worker(worker_id)

    if not worker:
        return {
            "ok": False,
            "worker_id": worker_id,
            "error": "worker_not_found",
            "missing_roles": [],
        }

    missing = []
    for role_id in worker.role_ids:
        if not get_role_pack(role_id):
            missing.append(role_id)

    return {
        "ok": len(missing) == 0,
        "worker_id": worker_id,
        "missing_roles": missing,
        "role_count": len(worker.role_ids),
    }


# =========================
# Quick manual test
# =========================

if __name__ == "__main__":
    print(role_registry_status())
    print()
    print(build_office_manager_smb_answer())
