# permission_engine.py
# NinaOS Permission Engine V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Central permission logic for NinaOS Platform Core
# - Define action permissions by role
# - Define approval-gated actions
# - Validate whether agent/role/workspace can perform action
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    from role_registry import (
        get_role_pack,
        get_worker_role_stack,
        get_worker_approval_rules,
        ROLE_REGISTRY_VERSION,
    )
except Exception:
    ROLE_REGISTRY_VERSION = "Role Registry nav pieejams"

    def get_role_pack(role_id):
        return None

    def get_worker_role_stack(worker_id):
        return []

    def get_worker_approval_rules(worker_id):
        return []

try:
    from agent_registry import (
        get_agent,
        get_agent_role_stack,
        AGENT_REGISTRY_VERSION,
    )
except Exception:
    AGENT_REGISTRY_VERSION = "Agent Registry nav pieejams"

    def get_agent(agent_id):
        return None

    def get_agent_role_stack(agent_id):
        return []

try:
    from workspace_engine import (
        get_workspace_state,
        get_workspace_agents,
        WORKSPACE_ENGINE_VERSION,
    )
except Exception:
    WORKSPACE_ENGINE_VERSION = "Workspace Engine nav pieejams"

    def get_workspace_state(workspace_id):
        return None

    def get_workspace_agents(workspace_id):
        return []


PERMISSION_ENGINE_VERSION = "Permission Engine V1.0"


@dataclass(frozen=True)
class PermissionRule:
    permission_id: str
    label: str
    description: str
    category: str
    approval_required: bool = False
    risk_level: str = "low"
    status: str = "active"


# =========================================================
# Global NinaOS permissions catalog
# =========================================================

PERMISSION_RULES: Dict[str, PermissionRule] = {
    # Task / workspace actions
    "read_task": PermissionRule(
        permission_id="read_task",
        label="Read Task",
        description="Drīkst skatīt task objektu.",
        category="task",
    ),
    "write_task": PermissionRule(
        permission_id="write_task",
        label="Write Task",
        description="Drīkst izveidot vai atjaunot task objektu.",
        category="task",
    ),
    "delete_task": PermissionRule(
        permission_id="delete_task",
        label="Delete Task",
        description="Drīkst dzēst task objektu.",
        category="task",
        approval_required=True,
        risk_level="medium",
    ),
    "read_project": PermissionRule(
        permission_id="read_project",
        label="Read Project",
        description="Drīkst skatīt project objektu.",
        category="project",
    ),
    "write_project": PermissionRule(
        permission_id="write_project",
        label="Write Project",
        description="Drīkst izveidot vai atjaunot project objektu.",
        category="project",
    ),
    "delete_project": PermissionRule(
        permission_id="delete_project",
        label="Delete Project",
        description="Drīkst dzēst project objektu.",
        category="project",
        approval_required=True,
        risk_level="medium",
    ),

    # Client / follow-up
    "read_client": PermissionRule(
        permission_id="read_client",
        label="Read Client",
        description="Drīkst skatīt klienta objektu.",
        category="client",
    ),
    "write_client": PermissionRule(
        permission_id="write_client",
        label="Write Client",
        description="Drīkst izveidot vai atjaunot klienta objektu.",
        category="client",
    ),
    "delete_client": PermissionRule(
        permission_id="delete_client",
        label="Delete Client",
        description="Drīkst dzēst klienta objektu.",
        category="client",
        approval_required=True,
        risk_level="medium",
    ),
    "send_client_message": PermissionRule(
        permission_id="send_client_message",
        label="Send Client Message",
        description="Drīkst nosūtīt klientam ziņu vai follow-up.",
        category="client_communication",
        approval_required=True,
        risk_level="medium",
    ),
    "export_client_data": PermissionRule(
        permission_id="export_client_data",
        label="Export Client Data",
        description="Drīkst eksportēt klienta datus ārpus NinaOS.",
        category="client_data",
        approval_required=True,
        risk_level="high",
    ),

    # Estimates / offers
    "read_estimate": PermissionRule(
        permission_id="read_estimate",
        label="Read Estimate",
        description="Drīkst skatīt estimate objektu.",
        category="estimate",
    ),
    "write_estimate": PermissionRule(
        permission_id="write_estimate",
        label="Write Estimate",
        description="Drīkst veidot vai rediģēt estimate objektu.",
        category="estimate",
    ),
    "delete_estimate": PermissionRule(
        permission_id="delete_estimate",
        label="Delete Estimate",
        description="Drīkst dzēst estimate objektu.",
        category="estimate",
        approval_required=True,
        risk_level="medium",
    ),
    "send_final_estimate": PermissionRule(
        permission_id="send_final_estimate",
        label="Send Final Estimate",
        description="Drīkst nosūtīt galīgo tāmi klientam.",
        category="estimate",
        approval_required=True,
        risk_level="high",
    ),
    "approve_price": PermissionRule(
        permission_id="approve_price",
        label="Approve Price",
        description="Drīkst apstiprināt cenu vai gala summu.",
        category="estimate",
        approval_required=True,
        risk_level="high",
    ),
    "send_binding_offer": PermissionRule(
        permission_id="send_binding_offer",
        label="Send Binding Offer",
        description="Drīkst nosūtīt saistošu piedāvājumu.",
        category="offer",
        approval_required=True,
        risk_level="high",
    ),

    # Invoice / finance admin
    "read_invoice": PermissionRule(
        permission_id="read_invoice",
        label="Read Invoice",
        description="Drīkst skatīt invoice objektu.",
        category="invoice",
    ),
    "write_invoice": PermissionRule(
        permission_id="write_invoice",
        label="Write Invoice",
        description="Drīkst veidot vai rediģēt invoice objektu.",
        category="invoice",
    ),
    "delete_invoice": PermissionRule(
        permission_id="delete_invoice",
        label="Delete Invoice",
        description="Drīkst dzēst invoice objektu.",
        category="invoice",
        approval_required=True,
        risk_level="high",
    ),
    "send_invoice": PermissionRule(
        permission_id="send_invoice",
        label="Send Invoice",
        description="Drīkst nosūtīt invoice klientam.",
        category="invoice",
        approval_required=True,
        risk_level="high",
    ),
    "approve_payment": PermissionRule(
        permission_id="approve_payment",
        label="Approve Payment",
        description="Drīkst apstiprināt maksājumu.",
        category="payment",
        approval_required=True,
        risk_level="high",
    ),
    "export_financial_data": PermissionRule(
        permission_id="export_financial_data",
        label="Export Financial Data",
        description="Drīkst eksportēt finanšu datus.",
        category="finance",
        approval_required=True,
        risk_level="high",
    ),

    # Files / documents
    "read_document": PermissionRule(
        permission_id="read_document",
        label="Read Document",
        description="Drīkst skatīt dokumentus un failus.",
        category="document",
    ),
    "write_document": PermissionRule(
        permission_id="write_document",
        label="Write Document",
        description="Drīkst veidot vai atjaunot dokumentu objektus.",
        category="document",
    ),
    "delete_file": PermissionRule(
        permission_id="delete_file",
        label="Delete File",
        description="Drīkst dzēst failus no Knowledge Vault / dokumentu slāņa.",
        category="document",
        approval_required=True,
        risk_level="high",
    ),
    "export_sensitive_file": PermissionRule(
        permission_id="export_sensitive_file",
        label="Export Sensitive File",
        description="Drīkst eksportēt sensitīvu dokumentu.",
        category="document",
        approval_required=True,
        risk_level="high",
    ),
    "share_document_external": PermissionRule(
        permission_id="share_document_external",
        label="Share Document External",
        description="Drīkst nosūtīt dokumentu ārpus NinaOS.",
        category="document",
        approval_required=True,
        risk_level="high",
    ),

    # Workspace / admin / data
    "export_workspace_tasks": PermissionRule(
        permission_id="export_workspace_tasks",
        label="Export Workspace Tasks",
        description="Drīkst eksportēt workspace task datus.",
        category="workspace",
        approval_required=True,
        risk_level="medium",
    ),
    "submit_tax_document": PermissionRule(
        permission_id="submit_tax_document",
        label="Submit Tax Document",
        description="Drīkst iesniegt nodokļu dokumentu.",
        category="finance",
        approval_required=True,
        risk_level="high",
    ),
    "approve_accounting_report": PermissionRule(
        permission_id="approve_accounting_report",
        label="Approve Accounting Report",
        description="Drīkst apstiprināt grāmatvedības atskaiti.",
        category="finance",
        approval_required=True,
        risk_level="high",
    ),
}


# =========================================================
# Role → permission mapping
# =========================================================

ROLE_PERMISSION_MAP: Dict[str, List[str]] = {
    "office_manager_core": [
        "read_task",
        "write_task",
        "delete_task",
        "read_project",
        "write_project",
        "delete_project",
        "export_workspace_tasks",
    ],

    "finance_admin_assistant": [
        "read_invoice",
        "write_invoice",
        "delete_invoice",
        "send_invoice",
        "approve_payment",
        "export_financial_data",
        "read_client",
        "read_document",
        "write_document",
    ],

    "estimating_assistant_basic": [
        "read_estimate",
        "write_estimate",
        "delete_estimate",
        "send_final_estimate",
        "approve_price",
        "send_binding_offer",
        "read_client",
        "read_document",
    ],

    "client_followup_manager": [
        "read_client",
        "write_client",
        "delete_client",
        "send_client_message",
        "export_client_data",
        "read_estimate",
        "read_invoice",
        "write_task",
    ],

    "document_admin": [
        "read_document",
        "write_document",
        "delete_file",
        "export_sensitive_file",
        "share_document_external",
        "read_client",
        "read_invoice",
        "read_estimate",
    ],

    # planned roles
    "sales_assistant": [
        "read_client",
        "write_client",
        "send_client_message",
        "read_estimate",
    ],
    "support_assistant": [
        "read_client",
        "write_client",
        "read_document",
    ],
    "finance_accountant_basic": [
        "read_invoice",
        "write_invoice",
        "approve_payment",
        "submit_tax_document",
        "approve_accounting_report",
        "export_financial_data",
    ],
    "estimator_professional": [
        "read_estimate",
        "write_estimate",
        "send_final_estimate",
        "approve_price",
        "send_binding_offer",
    ],
}


# =========================================================
# Engine helpers
# =========================================================

def permission_engine_status() -> str:
    active_rules = len(PERMISSION_RULES)
    mapped_roles = len(ROLE_PERMISSION_MAP)

    return (
        "🔐 NinaOS Permission Engine\n\n"
        f"Versija: {PERMISSION_ENGINE_VERSION}\n"
        f"Role Registry: {ROLE_REGISTRY_VERSION}\n"
        f"Agent Registry: {AGENT_REGISTRY_VERSION}\n"
        f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
        f"Permission rules: {active_rules}\n"
        f"Role mappings: {mapped_roles}\n\n"
        "Prioritārais worker:\n"
        "• Nina Office Manager SMB\n\n"
        "Statuss: aktīvs ✅"
    )


def get_permission_rule(permission_id: str) -> Optional[PermissionRule]:
    return PERMISSION_RULES.get(permission_id)


def list_permission_rules() -> List[PermissionRule]:
    return list(PERMISSION_RULES.values())


def get_role_permissions(role_id: str) -> List[str]:
    return list(ROLE_PERMISSION_MAP.get(role_id, []))


def get_role_permission_rules(role_id: str) -> List[PermissionRule]:
    rules = []
    for permission_id in get_role_permissions(role_id):
        rule = get_permission_rule(permission_id)
        if rule:
            rules.append(rule)
    return rules


def get_agent_permissions(agent_id: str) -> List[str]:
    role_stack = get_agent_role_stack(agent_id)
    permissions = set()

    for role in role_stack:
        permissions.update(get_role_permissions(role.role_id))

    return sorted(permissions)


def get_agent_permission_rules(agent_id: str) -> List[PermissionRule]:
    rules = []
    seen = set()

    for permission_id in get_agent_permissions(agent_id):
        rule = get_permission_rule(permission_id)
        if rule and permission_id not in seen:
            rules.append(rule)
            seen.add(permission_id)

    return rules


def get_workspace_permissions(workspace_id: str) -> List[str]:
    permissions = set()
    for agent_id in get_workspace_agents(workspace_id):
        permissions.update(get_agent_permissions(agent_id))
    return sorted(permissions)


def get_workspace_permission_rules(workspace_id: str) -> List[PermissionRule]:
    rules = []
    seen = set()

    for permission_id in get_workspace_permissions(workspace_id):
        rule = get_permission_rule(permission_id)
        if rule and permission_id not in seen:
            rules.append(rule)
            seen.add(permission_id)

    return rules


# =========================================================
# Approval / permission checks
# =========================================================

def permission_requires_approval(permission_id: str) -> bool:
    rule = get_permission_rule(permission_id)
    if not rule:
        return False
    return rule.approval_required


def role_has_permission(role_id: str, permission_id: str) -> bool:
    return permission_id in ROLE_PERMISSION_MAP.get(role_id, [])


def agent_has_permission(agent_id: str, permission_id: str) -> bool:
    return permission_id in get_agent_permissions(agent_id)


def workspace_has_permission(workspace_id: str, permission_id: str) -> bool:
    return permission_id in get_workspace_permissions(workspace_id)


def check_agent_permission(agent_id: str, permission_id: str) -> Dict[str, Any]:
    agent = get_agent(agent_id)
    rule = get_permission_rule(permission_id)

    if not agent:
        return {
            "ok": False,
            "error": "agent_not_found",
            "agent_id": agent_id,
            "permission_id": permission_id,
        }

    if not rule:
        return {
            "ok": False,
            "error": "permission_not_found",
            "agent_id": agent_id,
            "permission_id": permission_id,
        }

    allowed = agent_has_permission(agent_id, permission_id)

    return {
        "ok": allowed,
        "agent_id": agent_id,
        "agent_name": agent.name,
        "permission_id": permission_id,
        "permission_label": rule.label,
        "approval_required": rule.approval_required if allowed else False,
        "risk_level": rule.risk_level,
    }


def check_workspace_permission(workspace_id: str, permission_id: str) -> Dict[str, Any]:
    workspace = get_workspace_state(workspace_id)
    rule = get_permission_rule(permission_id)

    if not workspace:
        return {
            "ok": False,
            "error": "workspace_not_found",
            "workspace_id": workspace_id,
            "permission_id": permission_id,
        }

    if not rule:
        return {
            "ok": False,
            "error": "permission_not_found",
            "workspace_id": workspace_id,
            "permission_id": permission_id,
        }

    allowed = workspace_has_permission(workspace_id, permission_id)

    return {
        "ok": allowed,
        "workspace_id": workspace_id,
        "workspace_name": workspace.name,
        "permission_id": permission_id,
        "permission_label": rule.label,
        "approval_required": rule.approval_required if allowed else False,
        "risk_level": rule.risk_level,
    }


def can_agent_execute_action(
    agent_id: str,
    permission_id: str,
    approved: bool = False,
) -> Dict[str, Any]:
    check = check_agent_permission(agent_id, permission_id)

    if not check.get("ok"):
        return {
            **check,
            "can_execute": False,
            "reason": "permission_denied",
        }

    if check.get("approval_required") and not approved:
        return {
            **check,
            "can_execute": False,
            "reason": "approval_required",
        }

    return {
        **check,
        "can_execute": True,
        "reason": "allowed",
    }


def can_workspace_execute_action(
    workspace_id: str,
    permission_id: str,
    approved: bool = False,
) -> Dict[str, Any]:
    check = check_workspace_permission(workspace_id, permission_id)

    if not check.get("ok"):
        return {
            **check,
            "can_execute": False,
            "reason": "permission_denied",
        }

    if check.get("approval_required") and not approved:
        return {
            **check,
            "can_execute": False,
            "reason": "approval_required",
        }

    return {
        **check,
        "can_execute": True,
        "reason": "allowed",
    }


# =========================================================
# Human-readable answers
# =========================================================

def build_permissions_answer() -> str:
    lines = [
        "🔐 NinaOS Permission Rules",
        "",
        f"Versija: {PERMISSION_ENGINE_VERSION}",
        "",
    ]

    for rule in list_permission_rules():
        approval = "jā" if rule.approval_required else "nē"
        lines.append(f"• {rule.permission_id}")
        lines.append(f"  Nosaukums: {rule.label}")
        lines.append(f"  Kategorija: {rule.category}")
        lines.append(f"  Approval: {approval}")
        lines.append(f"  Risks: {rule.risk_level}")
        lines.append("")

    return "\n".join(lines).strip()


def build_role_permissions_answer(role_id: str) -> str:
    role = get_role_pack(role_id)
    permissions = get_role_permission_rules(role_id)

    if not role:
        return f"Role nav atrasta: {role_id}"

    lines = [
        f"🔐 Role permissions — {role.name}",
        "",
        f"Role ID: {role.role_id}",
        f"Kategorija: {role.category}",
        "",
        "Permissions:",
    ]

    if permissions:
        for rule in permissions:
            approval = " (approval)" if rule.approval_required else ""
            lines.append(f"• {rule.permission_id}{approval}")
    else:
        lines.append("• nav")

    return "\n".join(lines)


def build_agent_permissions_answer(agent_id: str) -> str:
    agent = get_agent(agent_id)
    permissions = get_agent_permission_rules(agent_id)

    if not agent:
        return f"Agents nav atrasts: {agent_id}"

    lines = [
        f"🔐 Agent permissions — {agent.name}",
        "",
        f"Agent ID: {agent.agent_id}",
        "",
        "Permissions:",
    ]

    if permissions:
        for rule in permissions:
            approval = " (approval)" if rule.approval_required else ""
            lines.append(f"• {rule.permission_id}{approval}")
    else:
        lines.append("• nav")

    return "\n".join(lines)


def build_workspace_permissions_answer(workspace_id: str) -> str:
    workspace = get_workspace_state(workspace_id)
    permissions = get_workspace_permission_rules(workspace_id)

    if not workspace:
        return f"Workspace nav atrasts: {workspace_id}"

    lines = [
        f"🔐 Workspace permissions — {workspace.name}",
        "",
        f"Workspace ID: {workspace.workspace_id}",
        f"Workspace tips: {workspace.workspace_type}",
        "",
        "Permissions:",
    ]

    if permissions:
        for rule in permissions:
            approval = " (approval)" if rule.approval_required else ""
            lines.append(f"• {rule.permission_id}{approval}")
    else:
        lines.append("• nav")

    return "\n".join(lines)


def build_office_manager_permissions_answer() -> str:
    return build_agent_permissions_answer("nina_office_manager_smb")


# =========================================================
# Schema / validation
# =========================================================

def permission_engine_schema() -> Dict[str, Any]:
    return {
        "version": PERMISSION_ENGINE_VERSION,
        "role_registry_version": ROLE_REGISTRY_VERSION,
        "agent_registry_version": AGENT_REGISTRY_VERSION,
        "workspace_engine_version": WORKSPACE_ENGINE_VERSION,
        "permission_rules": {
            permission_id: rule.__dict__
            for permission_id, rule in PERMISSION_RULES.items()
        },
        "role_permission_map": ROLE_PERMISSION_MAP,
    }


def validate_permission_engine() -> Dict[str, Any]:
    missing_roles = []
    for role_id in ROLE_PERMISSION_MAP.keys():
        if not get_role_pack(role_id):
            missing_roles.append(role_id)

    missing_permissions = []
    for role_id, permission_ids in ROLE_PERMISSION_MAP.items():
        for permission_id in permission_ids:
            if permission_id not in PERMISSION_RULES:
                missing_permissions.append({
                    "role_id": role_id,
                    "permission_id": permission_id,
                })

    return {
        "ok": len(missing_roles) == 0 and len(missing_permissions) == 0,
        "missing_roles": missing_roles,
        "missing_permissions": missing_permissions,
    }


# =========================================================
# Manual test
# =========================================================

if __name__ == "__main__":
    print(permission_engine_status())
    print()
    print(build_office_manager_permissions_answer())
