# activity_feed.py
# NinaOS Activity Feed V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Activity/event layer for NinaOS Workspace Dashboard
# - Feeds "Recent Activities" panel
# - Tracks worker, task, estimate, invoice, document, follow-up and exchange events
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


ACTIVITY_FEED_VERSION = "Activity Feed V1.0"


@dataclass
class ActivityEvent:
    event_id: str
    event_type: str
    title: str
    description: str
    workspace_id: str = "demo_small_business"
    agent_id: str = "nina_office_manager_smb"
    object_type: str = ""
    object_id: str = ""
    severity: str = "info"
    source: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


ACTIVITY_STORE: Dict[str, ActivityEvent] = {}


EVENT_TYPES = {
    "worker_activated": "Worker Activated",
    "task_created": "Task Created",
    "task_completed": "Task Completed",
    "followup_scheduled": "Follow-up Scheduled",
    "estimate_created": "Estimate Created",
    "estimate_sent": "Estimate Sent",
    "invoice_created": "Invoice Created",
    "invoice_sent": "Invoice Sent",
    "invoice_overdue": "Invoice Overdue",
    "document_uploaded": "Document Uploaded",
    "document_linked": "Document Linked",
    "client_created": "Client Created",
    "project_created": "Project Created",
    "exchange_viewed": "Exchange Viewed",
    "dashboard_opened": "Dashboard Opened",
    "permission_checked": "Permission Checked",
}


def activity_feed_status() -> str:
    return (
        "🕒 NinaOS Activity Feed\n\n"
        f"Version: {ACTIVITY_FEED_VERSION}\n"
        f"Registered event types: {len(EVENT_TYPES)}\n"
        f"Stored demo events: {len(ACTIVITY_STORE)}\n\n"
        "Purpose: feed Recent Activities in NinaOS Workspace Dashboard.\n\n"
        "Status: active ✅"
    )


def create_activity_event(
    event_type: str,
    title: str,
    description: str,
    workspace_id: str = "demo_small_business",
    agent_id: str = "nina_office_manager_smb",
    object_type: str = "",
    object_id: str = "",
    severity: str = "info",
    source: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
) -> ActivityEvent:
    event_id = f"activity_{len(ACTIVITY_STORE) + 1}"

    event = ActivityEvent(
        event_id=event_id,
        event_type=event_type,
        title=title,
        description=description,
        workspace_id=workspace_id,
        agent_id=agent_id,
        object_type=object_type,
        object_id=object_id,
        severity=severity,
        source=source,
        metadata=metadata or {},
    )

    ACTIVITY_STORE[event_id] = event
    return event


def get_activity_event(event_id: str) -> Optional[ActivityEvent]:
    return ACTIVITY_STORE.get(event_id)


def list_activity_events(
    workspace_id: str = "demo_small_business",
    limit: int = 10,
    event_type: Optional[str] = None,
) -> List[ActivityEvent]:
    events = [
        e for e in ACTIVITY_STORE.values()
        if e.workspace_id == workspace_id
    ]

    if event_type:
        events = [e for e in events if e.event_type == event_type]

    events = sorted(events, key=lambda e: e.created_at, reverse=True)

    return events[: int(limit or 10)]


def clear_activity_events() -> Dict[str, Any]:
    ACTIVITY_STORE.clear()
    return {
        "ok": True,
        "message": "Activity events cleared.",
        "count": 0,
    }


def seed_demo_activity_events() -> Dict[str, Any]:
    if ACTIVITY_STORE:
        return {
            "ok": True,
            "message": "Demo activity events already exist.",
            "count": len(ACTIVITY_STORE),
        }

    create_activity_event(
        event_type="worker_activated",
        title="Nina Office Manager SMB activated",
        description="The first NinaOS ready worker is active in Small Business Workspace.",
        object_type="agent",
        object_id="nina_office_manager_smb",
        severity="success",
        source="agent_registry",
    )

    create_activity_event(
        event_type="dashboard_opened",
        title="Workspace dashboard initialized",
        description="Small Business Workspace dashboard surface is connected.",
        object_type="dashboard",
        object_id="small_business_dashboard_v1",
        severity="success",
        source="workspace_dashboard",
    )

    create_activity_event(
        event_type="task_created",
        title="Task created",
        description="Prepare today workspace priorities.",
        object_type="task",
        object_id="task_1",
        severity="info",
        source="work_objects",
    )

    create_activity_event(
        event_type="followup_scheduled",
        title="Client follow-up scheduled",
        description="Follow up with Demo Client about offer.",
        object_type="followup_task",
        object_id="followup_task_3",
        severity="info",
        source="work_objects",
    )

    create_activity_event(
        event_type="estimate_created",
        title="Estimate draft created",
        description="Demo estimate draft is now in progress.",
        object_type="estimate",
        object_id="estimate_4",
        severity="info",
        source="work_objects",
    )

    create_activity_event(
        event_type="invoice_created",
        title="Invoice admin record created",
        description="Demo invoice follow-up was added to the workspace.",
        object_type="invoice",
        object_id="invoice_5",
        severity="warning",
        source="work_objects",
    )

    create_activity_event(
        event_type="document_uploaded",
        title="Document package created",
        description="Demo client document package is ready for organization.",
        object_type="document_case",
        object_id="document_case_7",
        severity="info",
        source="knowledge_vault_future",
    )

    create_activity_event(
        event_type="exchange_viewed",
        title="Exchange preview available",
        description="NinaOS Exchange preview is visible inside the dashboard.",
        object_type="exchange",
        object_id="exchange_preview",
        severity="info",
        source="platform_visibility",
    )

    return {
        "ok": True,
        "message": "Demo activity events created.",
        "count": len(ACTIVITY_STORE),
    }


def build_activity_feed_answer(
    workspace_id: str = "demo_small_business",
    limit: int = 10,
) -> str:
    events = list_activity_events(workspace_id=workspace_id, limit=limit)

    lines = [
        "🕒 NinaOS Recent Activities",
        "",
        f"Workspace: {workspace_id}",
        f"Events: {len(events)}",
        "",
    ]

    if not events:
        lines.append("No activity events yet.")
        lines.append("")
        lines.append("Try: demo activity")
    else:
        for event in events:
            lines.append(f"• {event.title}")
            lines.append(f"  {event.description}")
            lines.append(f"  Type: {event.event_type}")
            if event.object_type:
                lines.append(f"  Object: {event.object_type} / {event.object_id}")
            lines.append(f"  Severity: {event.severity}")
            lines.append("")

    lines.append(f"Version: {ACTIVITY_FEED_VERSION}")
    return "\n".join(lines).strip()


def build_activity_types_answer() -> str:
    lines = [
        "🕒 NinaOS Activity Event Types",
        "",
        f"Version: {ACTIVITY_FEED_VERSION}",
        "",
    ]

    for event_type, label in EVENT_TYPES.items():
        lines.append(f"• {event_type}")
        lines.append(f"  Label: {label}")
        lines.append("")

    return "\n".join(lines).strip()


def build_demo_activity_answer() -> str:
    result = seed_demo_activity_events()

    return (
        "🧪 NinaOS Demo Activity\n\n"
        f"{result.get('message')}\n"
        f"Events: {result.get('count')}\n\n"
        f"Version: {ACTIVITY_FEED_VERSION}"
    )


def build_clear_activity_answer() -> str:
    result = clear_activity_events()

    return (
        "🧹 NinaOS Activity Feed\n\n"
        f"{result.get('message')}\n"
        f"Events: {result.get('count')}\n\n"
        f"Version: {ACTIVITY_FEED_VERSION}"
    )


def activity_feed_for_dashboard(
    workspace_id: str = "demo_small_business",
    limit: int = 5,
) -> List[Dict[str, str]]:
    events = list_activity_events(workspace_id=workspace_id, limit=limit)

    return [
        {
            "activity_id": event.event_id,
            "title": event.title,
            "description": event.description,
            "object_type": event.object_type,
            "status": event.severity,
        }
        for event in events
    ]


def route_activity_feed_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["activity", "activity feed", "recent activities"]:
        return build_activity_feed_answer()

    if lower in ["activity status", "activity feed status"]:
        return activity_feed_status()

    if lower in ["activity types", "event types"]:
        return build_activity_types_answer()

    if lower in ["demo activity", "seed activity", "create demo activity"]:
        return build_demo_activity_answer()

    if lower in ["clear activity", "delete activity"]:
        return build_clear_activity_answer()

    return None


def activity_feed_schema() -> Dict[str, Any]:
    return {
        "version": ACTIVITY_FEED_VERSION,
        "event_types": EVENT_TYPES,
        "events": {
            event_id: event.__dict__
            for event_id, event in ACTIVITY_STORE.items()
        },
    }


if __name__ == "__main__":
    print(activity_feed_status())
    print()
    print(build_demo_activity_answer())
    print()
    print(build_activity_feed_answer())
