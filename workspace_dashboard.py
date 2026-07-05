# workspace_dashboard.py
# NinaOS Workspace Dashboard V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - First dashboard surface layer for approved NinaOS product vision
# - Shows Small Business Workspace summary for Nina Office Manager SMB
# - Global-first UI labels through Language Engine
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


WORKSPACE_DASHBOARD_VERSION = "Workspace Dashboard V1.0"


try:
    from language_engine import (
        normalize_language,
        t,
        build_workspace_dashboard_labels,
        LANGUAGE_ENGINE_VERSION,
    )
except Exception:
    LANGUAGE_ENGINE_VERSION = "Language Engine not connected"

    def normalize_language(language=None):
        return "en"

    def t(key, language=None, fallback=None):
        return fallback if fallback is not None else key

    def build_workspace_dashboard_labels(language=None):
        return {
            "tasks_today": "Tasks Today",
            "followups": "Follow-ups",
            "invoices_due": "Invoices Due",
            "estimates_in_progress": "Estimates in Progress",
            "projects_active": "Active Projects",
            "recent_activities": "Recent Activities",
            "exchange_preview": "Exchange Preview",
        }


try:
    from workspace_engine import (
        get_workspace_state,
        get_workspace_allowed_work_objects,
        get_workspace_agents,
        WORKSPACE_ENGINE_VERSION,
    )
except Exception:
    WORKSPACE_ENGINE_VERSION = "Workspace Engine not connected"

    def get_workspace_state(workspace_id):
        return None

    def get_workspace_allowed_work_objects(workspace_id):
        return []

    def get_workspace_agents(workspace_id):
        return []


try:
    from agent_registry import (
        get_agent,
        AGENT_REGISTRY_VERSION,
    )
except Exception:
    AGENT_REGISTRY_VERSION = "Agent Registry not connected"

    def get_agent(agent_id):
        return None


@dataclass(frozen=True)
class DashboardMetric:
    metric_id: str
    label: str
    value: str
    description: str = ""
    status: str = "normal"


@dataclass(frozen=True)
class DashboardAction:
    action_id: str
    label: str
    description: str
    permission_hint: str = ""


@dataclass(frozen=True)
class DashboardActivity:
    activity_id: str
    title: str
    description: str
    object_type: str = ""
    status: str = "info"


@dataclass(frozen=True)
class WorkspaceDashboard:
    dashboard_id: str
    workspace_id: str
    title: str
    subtitle: str
    metrics: List[DashboardMetric] = field(default_factory=list)
    quick_actions: List[DashboardAction] = field(default_factory=list)
    recent_activities: List[DashboardActivity] = field(default_factory=list)
    exchange_preview: List[str] = field(default_factory=list)
    status: str = "active"


# =========================================================
# Demo dashboard state
# =========================================================

DEMO_METRICS = {
    "tasks_today": 0,
    "followups": 0,
    "invoices_due": 0,
    "estimates_in_progress": 0,
    "projects_active": 0,
}


DEMO_EXCHANGE_WORKERS = [
    "Nina Office Manager SMB — active",
    "Nina Sales — planned",
    "Nina Estimator — planned",
    "Nina Finance — planned",
    "Nina Support — planned",
]


# =========================================================
# Core dashboard builders
# =========================================================

def workspace_dashboard_status(language: Optional[str] = "en") -> str:
    lang = normalize_language(language)

    if lang == "lv":
        return (
            "📊 NinaOS Workspace Dashboard\n\n"
            f"Versija: {WORKSPACE_DASHBOARD_VERSION}\n"
            f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
            f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
            f"Agent Registry: {AGENT_REGISTRY_VERSION}\n\n"
            "Mērķis: pirmais produkta dashboard slānis Nina Office Manager SMB.\n\n"
            "Statuss: aktīvs ✅"
        )

    if lang == "ru":
        return (
            "📊 NinaOS Workspace Dashboard\n\n"
            f"Версия: {WORKSPACE_DASHBOARD_VERSION}\n"
            f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
            f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
            f"Agent Registry: {AGENT_REGISTRY_VERSION}\n\n"
            "Цель: первый слой dashboard для Nina Office Manager SMB.\n\n"
            "Статус: активно ✅"
        )

    return (
        "📊 NinaOS Workspace Dashboard\n\n"
        f"Version: {WORKSPACE_DASHBOARD_VERSION}\n"
        f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
        f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
        f"Agent Registry: {AGENT_REGISTRY_VERSION}\n\n"
        "Goal: first product dashboard surface for Nina Office Manager SMB.\n\n"
        "Status: active ✅"
    )


def build_demo_metrics(language: Optional[str] = "en") -> List[DashboardMetric]:
    lang = normalize_language(language)
    labels = build_workspace_dashboard_labels(lang)

    return [
        DashboardMetric(
            metric_id="tasks_today",
            label=labels.get("tasks_today", "Tasks Today"),
            value=str(DEMO_METRICS["tasks_today"]),
            description="Tasks scheduled or due today.",
        ),
        DashboardMetric(
            metric_id="followups",
            label=labels.get("followups", "Follow-ups"),
            value=str(DEMO_METRICS["followups"]),
            description="Client follow-ups that need attention.",
        ),
        DashboardMetric(
            metric_id="invoices_due",
            label=labels.get("invoices_due", "Invoices Due"),
            value=str(DEMO_METRICS["invoices_due"]),
            description="Invoices approaching due date or overdue.",
        ),
        DashboardMetric(
            metric_id="estimates_in_progress",
            label=labels.get("estimates_in_progress", "Estimates in Progress"),
            value=str(DEMO_METRICS["estimates_in_progress"]),
            description="Estimate or offer drafts currently in progress.",
        ),
        DashboardMetric(
            metric_id="projects_active",
            label=labels.get("projects_active", "Active Projects"),
            value=str(DEMO_METRICS["projects_active"]),
            description="Active projects in this workspace.",
        ),
    ]


def build_quick_actions(language: Optional[str] = "en") -> List[DashboardAction]:
    lang = normalize_language(language)

    if lang == "lv":
        return [
            DashboardAction("new_task", "New Task", "Izveidot jaunu tasku.", "write_task"),
            DashboardAction("new_estimate", "New Estimate", "Izveidot estimate / offer draftu.", "write_estimate"),
            DashboardAction("new_invoice", "New Invoice", "Izveidot invoice admin ierakstu.", "write_invoice"),
            DashboardAction("add_client", "Add Client", "Pievienot klientu workspace.", "write_client"),
            DashboardAction("upload_document", "Upload Document", "Pievienot dokumentu.", "write_document"),
            DashboardAction("schedule_followup", "Schedule Follow-up", "Ieplānot klienta follow-up.", "write_task"),
        ]

    if lang == "ru":
        return [
            DashboardAction("new_task", "New Task", "Создать новую задачу.", "write_task"),
            DashboardAction("new_estimate", "New Estimate", "Создать черновик сметы / предложения.", "write_estimate"),
            DashboardAction("new_invoice", "New Invoice", "Создать запись invoice admin.", "write_invoice"),
            DashboardAction("add_client", "Add Client", "Добавить клиента в workspace.", "write_client"),
            DashboardAction("upload_document", "Upload Document", "Добавить документ.", "write_document"),
            DashboardAction("schedule_followup", "Schedule Follow-up", "Запланировать follow-up клиента.", "write_task"),
        ]

    return [
        DashboardAction("new_task", "New Task", "Create a new task.", "write_task"),
        DashboardAction("new_estimate", "New Estimate", "Create an estimate or offer draft.", "write_estimate"),
        DashboardAction("new_invoice", "New Invoice", "Create an invoice admin record.", "write_invoice"),
        DashboardAction("add_client", "Add Client", "Add a client to this workspace.", "write_client"),
        DashboardAction("upload_document", "Upload Document", "Upload and link a document.", "write_document"),
        DashboardAction("schedule_followup", "Schedule Follow-up", "Schedule a client follow-up.", "write_task"),
    ]


def build_recent_activities(language: Optional[str] = "en") -> List[DashboardActivity]:
    lang = normalize_language(language)

    if lang == "lv":
        return [
            DashboardActivity(
                activity_id="dashboard_initialized",
                title="Dashboard initialized",
                description="Small Business Workspace dashboard surface ir pieslēgts.",
                object_type="system",
                status="success",
            ),
            DashboardActivity(
                activity_id="office_manager_active",
                title="Nina Office Manager SMB active",
                description="Pirmais NinaOS gatavais darbinieks ir redzams produktā.",
                object_type="agent",
                status="success",
            ),
        ]

    if lang == "ru":
        return [
            DashboardActivity(
                activity_id="dashboard_initialized",
                title="Dashboard initialized",
                description="Dashboard для Small Business Workspace подключен.",
                object_type="system",
                status="success",
            ),
            DashboardActivity(
                activity_id="office_manager_active",
                title="Nina Office Manager SMB active",
                description="Первый готовый AI-сотрудник NinaOS виден в продукте.",
                object_type="agent",
                status="success",
            ),
        ]

    return [
        DashboardActivity(
            activity_id="dashboard_initialized",
            title="Dashboard initialized",
            description="Small Business Workspace dashboard surface is connected.",
            object_type="system",
            status="success",
        ),
        DashboardActivity(
            activity_id="office_manager_active",
            title="Nina Office Manager SMB active",
            description="The first NinaOS ready worker is visible inside the product.",
            object_type="agent",
            status="success",
        ),
    ]


def build_workspace_dashboard(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> WorkspaceDashboard:
    lang = normalize_language(language)
    workspace = get_workspace_state(workspace_id)

    if workspace:
        title = "NinaOS Small Business Workspace"
        subtitle = f"{workspace.name} · {workspace.workspace_type}"
    else:
        title = "NinaOS Small Business Workspace"
        subtitle = "Demo workspace · small_business"

    return WorkspaceDashboard(
        dashboard_id="small_business_dashboard_v1",
        workspace_id=workspace_id,
        title=title,
        subtitle=subtitle,
        metrics=build_demo_metrics(lang),
        quick_actions=build_quick_actions(lang),
        recent_activities=build_recent_activities(lang),
        exchange_preview=list(DEMO_EXCHANGE_WORKERS),
        status="active",
    )


# =========================================================
# Human-readable product answers
# =========================================================

def build_workspace_dashboard_answer(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    lang = normalize_language(language)
    dashboard = build_workspace_dashboard(workspace_id, lang)

    lines = [
        "📊 NinaOS Workspace Dashboard",
        "",
        dashboard.title,
        dashboard.subtitle,
        "",
        "Dashboard metrics:",
    ]

    for metric in dashboard.metrics:
        lines.append(f"• {metric.label}: {metric.value}")
        lines.append(f"  {metric.description}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in dashboard.quick_actions:
        lines.append(f"• {action.label}")
        lines.append(f"  {action.description}")
        if action.permission_hint:
            lines.append(f"  Permission: {action.permission_hint}")

    lines.extend([
        "",
        "Recent activities:",
    ])

    for activity in dashboard.recent_activities:
        lines.append(f"• {activity.title}")
        lines.append(f"  {activity.description}")

    lines.extend([
        "",
        "Exchange preview:",
    ])

    for worker in dashboard.exchange_preview:
        lines.append(f"• {worker}")

    lines.extend([
        "",
        f"Version: {WORKSPACE_DASHBOARD_VERSION}",
    ])

    return "\n".join(lines)


def build_dashboard_schema_answer(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    dashboard = build_workspace_dashboard(workspace_id, language)

    data = {
        "dashboard_id": dashboard.dashboard_id,
        "workspace_id": dashboard.workspace_id,
        "title": dashboard.title,
        "subtitle": dashboard.subtitle,
        "metrics": [m.__dict__ for m in dashboard.metrics],
        "quick_actions": [a.__dict__ for a in dashboard.quick_actions],
        "recent_activities": [a.__dict__ for a in dashboard.recent_activities],
        "exchange_preview": dashboard.exchange_preview,
        "status": dashboard.status,
        "version": WORKSPACE_DASHBOARD_VERSION,
    }

    import json
    return json.dumps(data, ensure_ascii=False, indent=2)


def route_workspace_dashboard_command(text: str, language: Optional[str] = "en") -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in [
        "dashboard",
        "workspace dashboard",
        "ninaos dashboard",
        "office dashboard",
        "small business dashboard",
    ]:
        return build_workspace_dashboard_answer("demo_small_business", language)

    if lower in [
        "dashboard status",
        "workspace dashboard status",
        "dashboard engine",
    ]:
        return workspace_dashboard_status(language)

    if lower in [
        "dashboard schema",
        "workspace dashboard schema",
    ]:
        return build_dashboard_schema_answer("demo_small_business", language)

    return None


def workspace_dashboard_schema(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> Dict[str, Any]:
    dashboard = build_workspace_dashboard(workspace_id, language)

    return {
        "dashboard_id": dashboard.dashboard_id,
        "workspace_id": dashboard.workspace_id,
        "title": dashboard.title,
        "subtitle": dashboard.subtitle,
        "metrics": [m.__dict__ for m in dashboard.metrics],
        "quick_actions": [a.__dict__ for a in dashboard.quick_actions],
        "recent_activities": [a.__dict__ for a in dashboard.recent_activities],
        "exchange_preview": dashboard.exchange_preview,
        "status": dashboard.status,
        "version": WORKSPACE_DASHBOARD_VERSION,
    }


if __name__ == "__main__":
    print(workspace_dashboard_status("en"))
    print()
    print(build_workspace_dashboard_answer())
