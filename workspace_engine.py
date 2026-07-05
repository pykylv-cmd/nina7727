# workspace_engine.py
# NinaOS Workspace Engine V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Define NinaOS workspace model
# - Attach ready workers (agents) to workspace
# - Expose workspace summary / status / allowed objects
# - First default workspace: small business workspace with Nina Office Manager SMB
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    from agent_registry import (
        get_agent,
        list_agents,
        get_agent_allowed_work_objects,
        get_agent_allowed_tools,
        get_agent_memory_scopes,
        AGENT_REGISTRY_VERSION,
    )
except Exception:
    AGENT_REGISTRY_VERSION = "Agent Registry nav pieejams"

    def get_agent(agent_id):
        return None

    def list_agents(include_planned=False):
        return []

    def get_agent_allowed_work_objects(agent_id):
        return []

    def get_agent_allowed_tools(agent_id):
        return []

    def get_agent_memory_scopes(agent_id):
        return []


WORKSPACE_ENGINE_VERSION = "Workspace Engine V1.0"


@dataclass(frozen=True)
class WorkspaceTemplate:
    workspace_type: str
    name: str
    description: str
    default_agents: List[str] = field(default_factory=list)
    allowed_work_objects: List[str] = field(default_factory=list)
    allowed_channels: List[str] = field(default_factory=list)
    memory_scopes: List[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class WorkspaceState:
    workspace_id: str
    workspace_type: str
    name: str
    company_name: str = ""
    owner_name: str = ""
    assigned_agents: List[str] = field(default_factory=list)
    status: str = "active"


# =========================================
# Workspace templates
# =========================================

WORKSPACE_TEMPLATES: Dict[str, WorkspaceTemplate] = {
    "small_business": WorkspaceTemplate(
        workspace_type="small_business",
        name="Small Business Workspace",
        description=(
            "NinaOS darba vide mazam uzņēmumam ar klientiem, taskiem, projektiem, "
            "rēķiniem, estimate/offer darbu un dokumentu administrēšanu."
        ),
        default_agents=[
            "nina_office_manager_smb",
        ],
        allowed_work_objects=[
            "task",
            "client",
            "project",
            "estimate",
            "offer",
            "invoice",
            "payment_request",
            "reminder",
            "followup_task",
            "document_case",
            "contract",
            "expense_record",
            "daily_plan",
            "project_scope",
            "client_request",
            "meeting_note",
            "accounting_document_case",
            "client_file_bundle",
        ],
        allowed_channels=[
            "web_workspace",
            "telegram",
            "mobile_later",
            "email_later",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Client Memory",
            "Project Memory",
            "Document Memory",
            "Role Memory",
            "Agent Memory",
            "Company Memory",
        ],
        status="active",
    ),

    "sales_workspace": WorkspaceTemplate(
        workspace_type="sales_workspace",
        name="Sales Workspace",
        description="NinaOS darba vide pārdošanas komandām un lead/deal pārvaldībai.",
        default_agents=[],
        allowed_work_objects=[
            "lead",
            "deal",
            "offer",
            "client",
            "followup_task",
            "meeting_note",
            "task",
        ],
        allowed_channels=[
            "web_workspace",
            "telegram",
            "email_later",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Client Memory",
            "Role Memory",
            "Agent Memory",
        ],
        status="planned",
    ),

    "construction_workspace": WorkspaceTemplate(
        workspace_type="construction_workspace",
        name="Construction Workspace",
        description="NinaOS darba vide tāmēšanai, projektiem un būvniecības dokumentiem.",
        default_agents=[],
        allowed_work_objects=[
            "estimate",
            "offer",
            "project",
            "project_scope",
            "document_case",
            "invoice",
            "task",
            "client",
        ],
        allowed_channels=[
            "web_workspace",
            "telegram",
            "mobile_later",
        ],
        memory_scopes=[
            "Workspace Memory",
            "Project Memory",
            "Document Memory",
            "Client Memory",
            "Role Memory",
        ],
        status="planned",
    ),
}


# =========================================
# Demo / registry workspace states
# =========================================

WORKSPACE_STATES: Dict[str, WorkspaceState] = {
    "demo_small_business": WorkspaceState(
        workspace_id="demo_small_business",
        workspace_type="small_business",
        name="Demo Small Business Workspace",
        company_name="Demo Company",
        owner_name="Demo Owner",
        assigned_agents=["nina_office_manager_smb"],
        status="active",
    )
}


# =========================================
# Core helpers
# =========================================

def workspace_engine_status() -> str:
    active_templates = len([w for w in WORKSPACE_TEMPLATES.values() if w.status == "active"])
    planned_templates = len([w for w in WORKSPACE_TEMPLATES.values() if w.status != "active"])
    workspace_count = len(WORKSPACE_STATES)

    return (
        "🏢 NinaOS Workspace Engine\n\n"
        f"Versija: {WORKSPACE_ENGINE_VERSION}\n"
        f"Agent Registry: {AGENT_REGISTRY_VERSION}\n"
        f"Aktīvie workspace templates: {active_templates}\n"
        f"Plānotie workspace templates: {planned_templates}\n"
        f"Reģistrētie workspace: {workspace_count}\n\n"
        "Prioritārais templates:\n"
        "• Small Business Workspace + Nina Office Manager SMB\n\n"
        "Statuss: aktīvs ✅"
    )


def get_workspace_template(workspace_type: str) -> Optional[WorkspaceTemplate]:
    return WORKSPACE_TEMPLATES.get(workspace_type)


def list_workspace_templates() -> List[WorkspaceTemplate]:
    return list(WORKSPACE_TEMPLATES.values())


def list_workspace_template_ids() -> List[str]:
    return list(WORKSPACE_TEMPLATES.keys())


def get_workspace_state(workspace_id: str) -> Optional[WorkspaceState]:
    return WORKSPACE_STATES.get(workspace_id)


def list_workspace_states() -> List[WorkspaceState]:
    return list(WORKSPACE_STATES.values())


def create_workspace_state(
    workspace_id: str,
    workspace_type: str,
    name: str,
    company_name: str = "",
    owner_name: str = "",
    assigned_agents: Optional[List[str]] = None,
) -> WorkspaceState:
    template = get_workspace_template(workspace_type)
    if not template:
        raise ValueError(f"Unknown workspace_type: {workspace_type}")

    if assigned_agents is None:
        assigned_agents = list(template.default_agents)

    state = WorkspaceState(
        workspace_id=workspace_id,
        workspace_type=workspace_type,
        name=name,
        company_name=company_name,
        owner_name=owner_name,
        assigned_agents=assigned_agents,
        status="active",
    )
    WORKSPACE_STATES[workspace_id] = state
    return state


# =========================================
# Workspace → Agent mapping
# =========================================

def get_workspace_agents(workspace_id: str) -> List[str]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return []
    return list(workspace.assigned_agents)


def get_workspace_agent_objects(workspace_id: str) -> Dict[str, Dict[str, List[str]]]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return {}

    result: Dict[str, Dict[str, List[str]]] = {}

    for agent_id in workspace.assigned_agents:
        result[agent_id] = {
            "work_objects": get_agent_allowed_work_objects(agent_id),
            "tools": get_agent_allowed_tools(agent_id),
            "memory_scopes": get_agent_memory_scopes(agent_id),
        }

    return result


def get_workspace_allowed_work_objects(workspace_id: str) -> List[str]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return []

    template = get_workspace_template(workspace.workspace_type)
    if not template:
        return []

    objects = set(template.allowed_work_objects)

    for agent_id in workspace.assigned_agents:
        objects.update(get_agent_allowed_work_objects(agent_id))

    return sorted(objects)


def get_workspace_allowed_tools(workspace_id: str) -> List[str]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return []

    tools = set()
    for agent_id in workspace.assigned_agents:
        tools.update(get_agent_allowed_tools(agent_id))

    return sorted(tools)


def get_workspace_memory_scopes(workspace_id: str) -> List[str]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return []

    template = get_workspace_template(workspace.workspace_type)
    scopes = set(template.memory_scopes if template else [])

    for agent_id in workspace.assigned_agents:
        scopes.update(get_agent_memory_scopes(agent_id))

    return sorted(scopes)


def attach_agent_to_workspace(workspace_id: str, agent_id: str) -> Dict[str, Any]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return {
            "ok": False,
            "error": "workspace_not_found",
            "workspace_id": workspace_id,
        }

    agent = get_agent(agent_id)
    if not agent:
        return {
            "ok": False,
            "error": "agent_not_found",
            "agent_id": agent_id,
        }

    if agent_id not in workspace.assigned_agents:
        workspace.assigned_agents.append(agent_id)

    return {
        "ok": True,
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "assigned_agents": list(workspace.assigned_agents),
    }


# =========================================
# Workspace answers
# =========================================

def build_workspaces_answer() -> str:
    lines = [
        "🏢 NinaOS Workspaces",
        "",
        f"Versija: {WORKSPACE_ENGINE_VERSION}",
        "",
    ]

    for template in list_workspace_templates():
        mark = "✅" if template.status == "active" else "🕓"
        lines.append(f"{mark} {template.workspace_type}")
        lines.append(f"   Nosaukums: {template.name}")
        lines.append(f"   Default agents: {', '.join(template.default_agents) if template.default_agents else 'nav'}")
        lines.append(f"   Statuss: {template.status}")
        lines.append("")

    return "\n".join(lines).strip()


def build_workspace_detail_answer(workspace_id: str) -> str:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return f"Workspace nav atrasts: {workspace_id}"

    template = get_workspace_template(workspace.workspace_type)

    lines = [
        f"🏢 {workspace.name}",
        "",
        f"Workspace ID: {workspace.workspace_id}",
        f"Workspace tips: {workspace.workspace_type}",
        f"Uzņēmums: {workspace.company_name or '—'}",
        f"Īpašnieks: {workspace.owner_name or '—'}",
        f"Statuss: {workspace.status}",
        "",
    ]

    if template:
        lines.append("Template:")
        lines.append(f"• {template.name}")
        lines.append(f"• {template.description}")
        lines.append("")

    lines.append("Piesaistītie agenti:")
    if workspace.assigned_agents:
        for agent_id in workspace.assigned_agents:
            agent = get_agent(agent_id)
            if agent:
                lines.append(f"• {agent.name} ({agent.agent_id})")
            else:
                lines.append(f"• {agent_id}")
    else:
        lines.append("• nav")

    lines.append("")
    lines.append("Atļautie Work Objects:")
    for obj in get_workspace_allowed_work_objects(workspace_id):
        lines.append(f"• {obj}")

    lines.append("")
    lines.append("Atļautie Tools:")
    for tool in get_workspace_allowed_tools(workspace_id):
        lines.append(f"• {tool}")

    lines.append("")
    lines.append("Memory Scopes:")
    for scope in get_workspace_memory_scopes(workspace_id):
        lines.append(f"• {scope}")

    lines.extend([
        "",
        f"Versija: {WORKSPACE_ENGINE_VERSION}",
    ])

    return "\n".join(lines)


def build_small_business_workspace_answer() -> str:
    return build_workspace_detail_answer("demo_small_business")


# =========================================
# Validation / schema
# =========================================

def validate_workspace(workspace_id: str) -> Dict[str, Any]:
    workspace = get_workspace_state(workspace_id)
    if not workspace:
        return {
            "ok": False,
            "workspace_id": workspace_id,
            "error": "workspace_not_found",
        }

    template = get_workspace_template(workspace.workspace_type)
    if not template:
        return {
            "ok": False,
            "workspace_id": workspace_id,
            "error": "workspace_template_not_found",
            "workspace_type": workspace.workspace_type,
        }

    missing_agents = []
    for agent_id in workspace.assigned_agents:
        if not get_agent(agent_id):
            missing_agents.append(agent_id)

    return {
        "ok": len(missing_agents) == 0,
        "workspace_id": workspace_id,
        "workspace_type": workspace.workspace_type,
        "assigned_agents": list(workspace.assigned_agents),
        "missing_agents": missing_agents,
    }


def workspace_engine_schema() -> Dict[str, Any]:
    return {
        "version": WORKSPACE_ENGINE_VERSION,
        "agent_registry_version": AGENT_REGISTRY_VERSION,
        "workspace_templates": {
            workspace_type: template.__dict__
            for workspace_type, template in WORKSPACE_TEMPLATES.items()
        },
        "workspace_states": {
            workspace_id: state.__dict__
            for workspace_id, state in WORKSPACE_STATES.items()
        },
    }


# =========================================
# Manual test
# =========================================

if __name__ == "__main__":
    print(workspace_engine_status())
    print()
    print(build_small_business_workspace_answer())
