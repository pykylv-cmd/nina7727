# agent_registry.py
# NinaOS Agent Registry V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Central registry for ready AI workers
# - First strategic worker: Nina Office Manager SMB
# - Connects workers to Role Registry definitions
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    from role_registry import (
        get_composite_worker,
        get_worker_role_stack,
        get_worker_allowed_work_objects,
        get_worker_allowed_tools,
        get_worker_memory_scopes,
        get_worker_approval_rules,
        ROLE_REGISTRY_VERSION,
    )
except Exception:
    ROLE_REGISTRY_VERSION = "Role Registry nav pieejams"

    def get_composite_worker(worker_id):
        return None

    def get_worker_role_stack(worker_id):
        return []

    def get_worker_allowed_work_objects(worker_id):
        return []

    def get_worker_allowed_tools(worker_id):
        return []

    def get_worker_memory_scopes(worker_id):
        return []

    def get_worker_approval_rules(worker_id):
        return []


AGENT_REGISTRY_VERSION = "Agent Registry V1.0"


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    name: str
    worker_type: str
    description: str
    composite_worker_id: str
    default_workspace_type: str
    target_customer: str
    channels: List[str] = field(default_factory=list)
    status: str = "active"
    priority: str = "normal"
    exchange_listed: bool = False
    tags: List[str] = field(default_factory=list)


AGENTS: Dict[str, AgentDefinition] = {
    "nina_office_manager_smb": AgentDefinition(
        agent_id="nina_office_manager_smb",
        name="Nina Office Manager SMB",
        worker_type="composite_worker",
        description=(
            "AI biroja vadītāja mazajiem uzņēmumiem. Apvieno office management, "
            "finance admin, estimating support, client follow-up un document admin."
        ),
        composite_worker_id="nina_office_manager_smb",
        default_workspace_type="small_business",
        target_customer="Small businesses, 1–20 people",
        channels=[
            "web_workspace",
            "telegram",
            "mobile_later",
            "email_later",
            "whatsapp_later",
        ],
        status="active",
        priority="strategic_wedge",
        exchange_listed=True,
        tags=[
            "office_manager",
            "small_business",
            "finance_admin",
            "estimating",
            "followup",
            "documents",
        ],
    ),
}


PLANNED_AGENTS: Dict[str, AgentDefinition] = {
    "nina_sales": AgentDefinition(
        agent_id="nina_sales",
        name="Nina Sales",
        worker_type="single_or_composite_worker",
        description="Pārdošanas un follow-up AI darbinieks.",
        composite_worker_id="planned_sales_worker",
        default_workspace_type="sales_workspace",
        target_customer="SMB and sales teams",
        channels=["web_workspace", "telegram", "email_later"],
        status="planned",
        priority="future",
        exchange_listed=True,
        tags=["sales", "crm", "followup", "offers"],
    ),

    "nina_estimator": AgentDefinition(
        agent_id="nina_estimator",
        name="Nina Estimator",
        worker_type="single_or_composite_worker",
        description="Tāmēšanas, piedāvājumu un projektu sagatavošanas AI darbinieks.",
        composite_worker_id="planned_estimator_worker",
        default_workspace_type="construction_workspace",
        target_customer="Construction and service companies",
        channels=["web_workspace", "telegram", "mobile_later"],
        status="planned",
        priority="future",
        exchange_listed=True,
        tags=["estimating", "construction", "offers", "projects"],
    ),

    "nina_support": AgentDefinition(
        agent_id="nina_support",
        name="Nina Support",
        worker_type="single_or_composite_worker",
        description="Klientu servisa un ticket palīdzības AI darbinieks.",
        composite_worker_id="planned_support_worker",
        default_workspace_type="support_workspace",
        target_customer="SMB support teams",
        channels=["web_workspace", "email_later", "whatsapp_later"],
        status="planned",
        priority="future",
        exchange_listed=True,
        tags=["support", "tickets", "faq", "customers"],
    ),
}


def agent_registry_status() -> str:
    active_agents = len([a for a in AGENTS.values() if a.status == "active"])
    planned_agents = len(PLANNED_AGENTS)

    return (
        "🤖 NinaOS Agent Registry\n\n"
        f"Versija: {AGENT_REGISTRY_VERSION}\n"
        f"Role Registry: {ROLE_REGISTRY_VERSION}\n"
        f"Aktīvie agenti: {active_agents}\n"
        f"Plānotie agenti: {planned_agents}\n\n"
        "Prioritārais gatavais darbinieks:\n"
        "• Nina Office Manager SMB\n\n"
        "Statuss: aktīvs ✅"
    )


def get_agent(agent_id: str) -> Optional[AgentDefinition]:
    if agent_id in AGENTS:
        return AGENTS[agent_id]
    if agent_id in PLANNED_AGENTS:
        return PLANNED_AGENTS[agent_id]
    return None


def list_agents(include_planned: bool = False) -> List[AgentDefinition]:
    agents = list(AGENTS.values())
    if include_planned:
        agents.extend(PLANNED_AGENTS.values())
    return agents


def list_agent_ids(include_planned: bool = False) -> List[str]:
    return [agent.agent_id for agent in list_agents(include_planned=include_planned)]


def get_agent_role_stack(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        return []

    return get_worker_role_stack(agent.composite_worker_id)


def get_agent_allowed_work_objects(agent_id: str) -> List[str]:
    agent = get_agent(agent_id)
    if not agent:
        return []

    return get_worker_allowed_work_objects(agent.composite_worker_id)


def get_agent_allowed_tools(agent_id: str) -> List[str]:
    agent = get_agent(agent_id)
    if not agent:
        return []

    return get_worker_allowed_tools(agent.composite_worker_id)


def get_agent_memory_scopes(agent_id: str) -> List[str]:
    agent = get_agent(agent_id)
    if not agent:
        return []

    return get_worker_memory_scopes(agent.composite_worker_id)


def get_agent_approval_rules(agent_id: str) -> List[str]:
    agent = get_agent(agent_id)
    if not agent:
        return []

    return get_worker_approval_rules(agent.composite_worker_id)


def build_agents_answer(include_planned: bool = False) -> str:
    agents = list_agents(include_planned=include_planned)

    lines = [
        "🤖 NinaOS Agents",
        "",
        f"Versija: {AGENT_REGISTRY_VERSION}",
        "",
    ]

    for agent in agents:
        mark = "✅" if agent.status == "active" else "🕓"
        lines.append(f"{mark} {agent.agent_id}")
        lines.append(f"   Nosaukums: {agent.name}")
        lines.append(f"   Tips: {agent.worker_type}")
        lines.append(f"   Klients: {agent.target_customer}")
        lines.append(f"   Statuss: {agent.status}")
        lines.append(f"   Exchange: {'jā' if agent.exchange_listed else 'nē'}")
        lines.append("")

    return "\n".join(lines).strip()


def build_agent_detail_answer(agent_id: str) -> str:
    agent = get_agent(agent_id)

    if not agent:
        return f"Agents nav atrasts: {agent_id}"

    lines = [
        f"🤖 {agent.name}",
        "",
        agent.description,
        "",
        f"Agent ID: {agent.agent_id}",
        f"Tips: {agent.worker_type}",
        f"Composite Worker ID: {agent.composite_worker_id}",
        f"Workspace tips: {agent.default_workspace_type}",
        f"Klients: {agent.target_customer}",
        f"Statuss: {agent.status}",
        f"Prioritāte: {agent.priority}",
        f"Exchange listed: {'jā' if agent.exchange_listed else 'nē'}",
        "",
        "Kanāli:",
    ]

    for channel in agent.channels:
        lines.append(f"• {channel}")

    lines.append("")
    lines.append("Role stack:")

    role_stack = get_agent_role_stack(agent_id)
    if role_stack:
        for role in role_stack:
            lines.append(f"• {role.name} ({role.role_id})")
    else:
        lines.append("• Role stack vēl nav pieslēgts vai ir plānots.")

    lines.append("")
    lines.append("Atļautie Work Objects:")

    objects = get_agent_allowed_work_objects(agent_id)
    if objects:
        for obj in objects:
            lines.append(f"• {obj}")
    else:
        lines.append("• Nav definēts.")

    lines.append("")
    lines.append("Atļautie Tools:")

    tools = get_agent_allowed_tools(agent_id)
    if tools:
        for tool in tools:
            lines.append(f"• {tool}")
    else:
        lines.append("• Nav definēts.")

    lines.append("")
    lines.append("Memory Scopes:")

    scopes = get_agent_memory_scopes(agent_id)
    if scopes:
        for scope in scopes:
            lines.append(f"• {scope}")
    else:
        lines.append("• Nav definēts.")

    lines.append("")
    lines.append("Approval vajadzīgs:")

    rules = get_agent_approval_rules(agent_id)
    if rules:
        for rule in rules:
            lines.append(f"• {rule}")
    else:
        lines.append("• Nav definēts.")

    lines.extend([
        "",
        f"Versija: {AGENT_REGISTRY_VERSION}",
    ])

    return "\n".join(lines)


def build_office_manager_agent_answer() -> str:
    return build_agent_detail_answer("nina_office_manager_smb")


def agent_registry_schema() -> Dict[str, Any]:
    return {
        "version": AGENT_REGISTRY_VERSION,
        "role_registry_version": ROLE_REGISTRY_VERSION,
        "active_agents": {
            agent_id: agent.__dict__ for agent_id, agent in AGENTS.items()
        },
        "planned_agents": {
            agent_id: agent.__dict__ for agent_id, agent in PLANNED_AGENTS.items()
        },
    }


def validate_agent(agent_id: str) -> Dict[str, Any]:
    agent = get_agent(agent_id)

    if not agent:
        return {
            "ok": False,
            "agent_id": agent_id,
            "error": "agent_not_found",
        }

    composite_worker = get_composite_worker(agent.composite_worker_id)

    if agent.status == "planned":
        return {
            "ok": True,
            "agent_id": agent_id,
            "status": "planned",
            "message": "Plānots agents. Composite worker vēl nav obligāts.",
        }

    if not composite_worker:
        return {
            "ok": False,
            "agent_id": agent_id,
            "error": "composite_worker_not_found",
            "composite_worker_id": agent.composite_worker_id,
        }

    role_stack = get_agent_role_stack(agent_id)

    return {
        "ok": len(role_stack) > 0,
        "agent_id": agent_id,
        "composite_worker_id": agent.composite_worker_id,
        "role_count": len(role_stack),
        "status": agent.status,
    }


if __name__ == "__main__":
    print(agent_registry_status())
    print()
    print(build_office_manager_agent_answer())
