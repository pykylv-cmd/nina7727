# workspace_dashboard.py
# NinaOS Workspace Dashboard V1.1
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - First dashboard surface layer for approved NinaOS product vision
# - Reads dashboard counts from work_objects.py when available
# - Shows Small Business Workspace summary for Nina Office Manager SMB
# - Global-first UI labels through Language Engine
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


WORKSPACE_DASHBOARD_VERSION = "Workspace Dashboard V1.1"


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
        WORKSPACE_ENGINE_VERSION,
    )
except Exception:
    WORKSPACE_ENGINE_VERSION = "Workspace Engine not connected"

    def get_workspace_state(workspace_id):
        return None


try:
    from agent_registry import AGENT_REGISTRY_VERSION
except Exception:
    AGENT_REGISTRY_VERSION = "Agent Registry not connected"


try:
    from work_objects import (
        dashboard_counts,
        list_work_objects,
        WORK_OBJECTS_VERSION,
    )
except Exception:
    WORK_OBJECTS_VERSION = "Work Objects not connected"

    def dashboard_counts(workspace_id="demo_small_business"):
        return {
            "tasks_today": 0,
            "followups": 0,
            "invoices_due": 0,
            "estimates_in_progress": 0,
            "projects_active": 0,
        }

    def list_work_objects(workspace_id=None, object_type=None, status=None):
        return []


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


DEMO_EXCHANGE_WORKERS = [
    "Nina Office Manager SMB — active",
    "Nina Sales — planned",
    "Nina Estimator — planned",
    "Nina Finance — planned",
    "Nina Support — planned",
]


def workspace_dashboard_status(language: Optional[str] = "en") -> str:
    lang = normalize_language(language)

    if lang == "lv":
        return (
            "📊 NinaOS Workspace Dashboard\n\n"
            f"Versija: {WORKSPACE_DASHBOARD_VERSION}\n"
            f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
            f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
            f"Agent Registry: {AGENT_REGISTRY_VERSION}\n"
            f"Work Objects: {WORK_OBJECTS_VERSION}\n\n"
            "Mērķis: dashboard slānis Nina Office Manager SMB, kas lasa Work Objects skaitļus.\n\n"
            "Statuss: aktīvs ✅"
        )

    if lang == "ru":
        return (
            "📊 NinaOS Workspace Dashboard\n\n"
            f"Версия: {WORKSPACE_DASHBOARD_VERSION}\n"
            f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
            f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
            f"Agent Registry: {AGENT_REGISTRY_VERSION}\n"
            f"Work Objects: {WORK_OBJECTS_VERSION}\n\n"
            "Цель: dashboard для Nina Office Manager SMB, который читает Work Objects.\n\n"
            "Статус: активно ✅"
        )

    return (
        "📊 NinaOS Workspace Dashboard\n\n"
        f"Version: {WORKSPACE_DASHBOARD_VERSION}\n"
        f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
        f"Workspace Engine: {WORKSPACE_ENGINE_VERSION}\n"
        f"Agent Registry: {AGENT_REGISTRY_VERSION}\n"
        f"Work Objects: {WORK_OBJECTS_VERSION}\n\n"
        "Goal: product dashboard surface for Nina Office Manager SMB, powered by Work Objects.\n\n"
        "Status: active ✅"
    )


def _metric_descriptions(language: Optional[str] = "en") -> Dict[str, str]:
    lang = normalize_language(language)
    if lang == "lv":
        return {
            "tasks_today": "Taski, kas ir atvērti vai procesā.",
            "followups": "Klientu follow-up, kuri prasa uzmanību.",
            "invoices_due": "Nosūtīti vai nokavēti rēķini.",
            "estimates_in_progress": "Estimate vai offer drafti procesā.",
            "projects_active": "Aktīvie projekti workspace.",
        }
    if lang == "ru":
        return {
            "tasks_today": "Открытые задачи или задачи в работе.",
            "followups": "Клиентские follow-up, требующие внимания.",
            "invoices_due": "Отправленные или просроченные счета.",
            "estimates_in_progress": "Черновики смет или предложений в работе.",
            "projects_active": "Активные проекты в workspace.",
        }
    return {
        "tasks_today": "Open or in-progress tasks.",
        "followups": "Client follow-ups that need attention.",
        "invoices_due": "Sent or overdue invoices.",
        "estimates_in_progress": "Estimate or offer drafts currently in progress.",
        "projects_active": "Active projects in this workspace.",
    }


def build_metrics(workspace_id: str = "demo_small_business", language: Optional[str] = "en") -> List[DashboardMetric]:
    lang = normalize_language(language)
    labels = build_workspace_dashboard_labels(lang)
    counts = dashboard_counts(workspace_id)
    descriptions = _metric_descriptions(lang)

    return [
        DashboardMetric("tasks_today", labels.get("tasks_today", "Tasks Today"), str(counts.get("tasks_today", 0)), descriptions["tasks_today"]),
        DashboardMetric("followups", labels.get("followups", "Follow-ups"), str(counts.get("followups", 0)), descriptions["followups"]),
        DashboardMetric("invoices_due", labels.get("invoices_due", "Invoices Due"), str(counts.get("invoices_due", 0)), descriptions["invoices_due"]),
        DashboardMetric("estimates_in_progress", labels.get("estimates_in_progress", "Estimates in Progress"), str(counts.get("estimates_in_progress", 0)), descriptions["estimates_in_progress"]),
        DashboardMetric("projects_active", labels.get("projects_active", "Active Projects"), str(counts.get("projects_active", 0)), descriptions["projects_active"]),
    ]


def build_quick_actions(language: Optional[str] = "en") -> List[DashboardAction]:
    return [
        DashboardAction("new_task", "New Task", "Create a new task.", "write_task"),
        DashboardAction("new_estimate", "New Estimate", "Create an estimate or offer draft.", "write_estimate"),
        DashboardAction("new_invoice", "New Invoice", "Create an invoice admin record.", "write_invoice"),
        DashboardAction("add_client", "Add Client", "Add a client to this workspace.", "write_client"),
        DashboardAction("upload_document", "Upload Document", "Upload and link a document.", "write_document"),
        DashboardAction("schedule_followup", "Schedule Follow-up", "Schedule a client follow-up.", "write_task"),
    ]


def build_recent_activities(workspace_id: str = "demo_small_business", language: Optional[str] = "en") -> List[DashboardActivity]:
    objects = list_work_objects(workspace_id=workspace_id)
    activities: List[DashboardActivity] = [
        DashboardActivity(
            "dashboard_initialized",
            "Dashboard initialized",
            "Small Business Workspace dashboard surface is connected.",
            "system",
            "success",
        ),
        DashboardActivity(
            "office_manager_active",
            "Nina Office Manager SMB active",
            "The first NinaOS ready worker is visible inside the product.",
            "agent",
            "success",
        ),
    ]

    for obj in objects[-5:]:
        activities.append(
            DashboardActivity(
                activity_id=f"object_{obj.object_id}",
                title=f"{obj.object_type}: {obj.title}",
                description=f"Status: {obj.status} · Priority: {obj.priority}",
                object_type=obj.object_type,
                status=obj.status,
            )
        )

    return activities


def build_workspace_dashboard(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> WorkspaceDashboard:
    workspace = get_workspace_state(workspace_id)

    if workspace:
        title = "NinaOS Small Business Workspace"
        subtitle = f"{workspace.name} · {workspace.workspace_type}"
    else:
        title = "NinaOS Small Business Workspace"
        subtitle = "Demo workspace · small_business"

    return WorkspaceDashboard(
        dashboard_id="small_business_dashboard_v1_1",
        workspace_id=workspace_id,
        title=title,
        subtitle=subtitle,
        metrics=build_metrics(workspace_id, language),
        quick_actions=build_quick_actions(language),
        recent_activities=build_recent_activities(workspace_id, language),
        exchange_preview=list(DEMO_EXCHANGE_WORKERS),
        status="active",
    )


def build_workspace_dashboard_answer(workspace_id: str = "demo_small_business", language: Optional[str] = "en") -> str:
    dashboard = build_workspace_dashboard(workspace_id, language)

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

    lines.extend(["", "Quick actions:"])
    for action in dashboard.quick_actions:
        lines.append(f"• {action.label}")
        lines.append(f"  {action.description}")
        if action.permission_hint:
            lines.append(f"  Permission: {action.permission_hint}")

    lines.extend(["", "Recent activities:"])
    for activity in dashboard.recent_activities:
        lines.append(f"• {activity.title}")
        lines.append(f"  {activity.description}")

    lines.extend(["", "Exchange preview:"])
    for worker in dashboard.exchange_preview:
        lines.append(f"• {worker}")

    lines.extend(["", f"Version: {WORKSPACE_DASHBOARD_VERSION}"])
    return "\n".join(lines)


def build_dashboard_schema_answer(workspace_id: str = "demo_small_business", language: Optional[str] = "en") -> str:
    dashboard = build_workspace_dashboard(workspace_id, language)
    data = workspace_dashboard_schema(workspace_id, language)
    import json
    return json.dumps(data, ensure_ascii=False, indent=2)


def route_workspace_dashboard_command(text: str, language: Optional[str] = "en") -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["dashboard", "workspace dashboard", "ninaos dashboard", "office dashboard", "small business dashboard"]:
        return build_workspace_dashboard_answer("demo_small_business", language)

    if lower in ["dashboard status", "workspace dashboard status", "dashboard engine"]:
        return workspace_dashboard_status(language)

    if lower in ["dashboard schema", "workspace dashboard schema"]:
        return build_dashboard_schema_answer("demo_small_business", language)

    return None


def workspace_dashboard_schema(workspace_id: str = "demo_small_business", language: Optional[str] = "en") -> Dict[str, Any]:
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
        "work_objects_version": WORK_OBJECTS_VERSION,
    }


if __name__ == "__main__":
    print(workspace_dashboard_status("en"))
    print()
    print(build_workspace_dashboard_answer())
