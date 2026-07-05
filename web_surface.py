# web_surface.py
# NinaOS Web Surface V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Define NinaOS desktop/web workspace product surface
# - Prepare the first browser app structure
# - Complements mobile_surface.py
# - First web product target: Nina Office Manager SMB
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


WEB_SURFACE_VERSION = "Web Surface V1.0"


@dataclass(frozen=True)
class WebNavItem:
    nav_id: str
    label: str
    target_view: str
    icon_hint: str = ""
    priority: int = 1
    status: str = "active"


@dataclass(frozen=True)
class WebView:
    view_id: str
    name: str
    purpose: str
    layout: str
    primary_blocks: List[str] = field(default_factory=list)
    right_panel_blocks: List[str] = field(default_factory=list)
    quick_actions: List[str] = field(default_factory=list)
    status: str = "active"


LEFT_SIDEBAR: List[WebNavItem] = [
    WebNavItem("dashboard", "Dashboard", "web_dashboard", "chart", 1),
    WebNavItem("workers", "Workers", "web_workers", "users", 2),
    WebNavItem("clients", "Clients", "web_clients", "briefcase", 3),
    WebNavItem("tasks", "Tasks", "web_tasks", "check", 4),
    WebNavItem("projects", "Projects", "web_projects", "folder", 5),
    WebNavItem("estimates", "Estimates", "web_estimates", "calculator", 6),
    WebNavItem("invoices", "Invoices", "web_invoices", "receipt", 7),
    WebNavItem("documents", "Documents", "web_documents", "file", 8),
    WebNavItem("exchange", "Exchange", "web_exchange", "market", 9),
    WebNavItem("settings", "Settings", "web_settings", "gear", 10),
]


TOP_BAR_BLOCKS = [
    "Workspace switcher",
    "Search",
    "Create button",
    "Notifications",
    "User / company menu",
]


WEB_VIEWS: Dict[str, WebView] = {
    "web_dashboard": WebView(
        view_id="web_dashboard",
        name="Web Dashboard",
        purpose="Main business overview for NinaOS workspace.",
        layout="left_sidebar + top_bar + dashboard_grid + right_context_panel",
        primary_blocks=[
            "Tasks Today",
            "Follow-ups",
            "Invoices Due",
            "Estimates in Progress",
            "Active Projects",
            "Recent Activities",
            "Exchange Preview",
        ],
        right_panel_blocks=[
            "Nina Office Manager SMB card",
            "System Status",
            "Upcoming & Due",
            "Quick Actions",
        ],
        quick_actions=[
            "New Task",
            "New Estimate",
            "New Invoice",
            "Add Client",
            "Upload Document",
            "Schedule Follow-up",
        ],
    ),

    "web_workers": WebView(
        view_id="web_workers",
        name="Workers",
        purpose="Manage ready AI workers assigned to the workspace.",
        layout="worker_cards_grid + worker_detail_panel",
        primary_blocks=[
            "Nina Office Manager SMB",
            "Worker role stack",
            "Worker permissions",
            "Worker channels",
            "Planned workers",
        ],
        right_panel_blocks=[
            "Selected worker details",
            "Role stack",
            "Approval rules",
            "Exchange listing status",
        ],
        quick_actions=[
            "Open Worker",
            "Assign Worker",
            "Explore Exchange",
        ],
    ),

    "web_office_manager": WebView(
        view_id="web_office_manager",
        name="Nina Office Manager SMB",
        purpose="Full desktop worker profile and control center for Nina Office Manager SMB.",
        layout="worker_header + role_stack + work_panels + approval_panel",
        primary_blocks=[
            "Worker summary",
            "Role stack",
            "Tasks",
            "Client follow-ups",
            "Invoices",
            "Estimates",
            "Documents",
            "Recent activity",
        ],
        right_panel_blocks=[
            "Approval required",
            "Allowed tools",
            "Memory scopes",
            "Permissions",
        ],
        quick_actions=[
            "Ask Nina",
            "New Task",
            "Follow-up Client",
            "Create Estimate Draft",
            "Create Invoice Admin Record",
            "Upload Document",
        ],
    ),

    "web_clients": WebView(
        view_id="web_clients",
        name="Clients",
        purpose="CRM-style client overview for small business workspace.",
        layout="client_table + client_work_panel",
        primary_blocks=[
            "Active clients",
            "Needs follow-up",
            "Offers sent",
            "Invoices due",
            "Client work view",
        ],
        right_panel_blocks=[
            "Selected client context",
            "Open tasks",
            "Related estimates",
            "Related invoices",
            "Files",
        ],
        quick_actions=[
            "Add Client",
            "Open Client",
            "Schedule Follow-up",
            "Create Offer",
        ],
    ),

    "web_tasks": WebView(
        view_id="web_tasks",
        name="Tasks",
        purpose="Task and deadline management for workspace.",
        layout="task_list + filters + detail_panel",
        primary_blocks=[
            "Today",
            "Overdue",
            "Upcoming",
            "In progress",
            "Completed",
        ],
        right_panel_blocks=[
            "Task details",
            "Linked client",
            "Linked project",
            "Reminder",
        ],
        quick_actions=[
            "New Task",
            "Mark Done",
            "Reschedule",
            "Assign to Worker",
        ],
    ),

    "web_projects": WebView(
        view_id="web_projects",
        name="Projects",
        purpose="Project overview connecting clients, tasks, estimates, invoices and documents.",
        layout="project_cards + project_timeline + project_detail_panel",
        primary_blocks=[
            "Active projects",
            "On hold",
            "Completed",
            "Project timelines",
            "Project files",
        ],
        right_panel_blocks=[
            "Selected project summary",
            "Open tasks",
            "Estimates",
            "Invoices",
            "Documents",
        ],
        quick_actions=[
            "New Project",
            "Add Task",
            "Create Estimate",
            "Upload Document",
        ],
    ),

    "web_estimates": WebView(
        view_id="web_estimates",
        name="Estimates",
        purpose="Estimate and offer draft workflow.",
        layout="estimate_pipeline + estimate_detail_panel",
        primary_blocks=[
            "Drafts",
            "In progress",
            "Sent",
            "Approved",
            "Rejected",
        ],
        right_panel_blocks=[
            "Estimate details",
            "Client request",
            "Project scope",
            "Linked documents",
            "Approval status",
        ],
        quick_actions=[
            "New Estimate",
            "Add Scope",
            "Prepare Offer",
            "Schedule Follow-up",
        ],
    ),

    "web_invoices": WebView(
        view_id="web_invoices",
        name="Invoices",
        purpose="Invoice administration and payment follow-up workspace.",
        layout="invoice_table + status_filters + invoice_detail_panel",
        primary_blocks=[
            "Drafts",
            "Sent",
            "Due soon",
            "Overdue",
            "Paid",
        ],
        right_panel_blocks=[
            "Invoice details",
            "Payment status",
            "Client context",
            "Follow-up actions",
            "Accounting document case",
        ],
        quick_actions=[
            "New Invoice",
            "Payment Follow-up",
            "Prepare Documents",
            "Mark Paid",
        ],
    ),

    "web_documents": WebView(
        view_id="web_documents",
        name="Documents",
        purpose="Knowledge Vault entry surface for files, invoices, estimates and contracts.",
        layout="document_library + filters + document_context_panel",
        primary_blocks=[
            "Recent uploads",
            "Client files",
            "Project files",
            "Invoices",
            "Estimates",
            "Contracts",
            "Accounting document cases",
        ],
        right_panel_blocks=[
            "Selected document metadata",
            "Linked work objects",
            "Sensitivity level",
            "Allowed roles",
        ],
        quick_actions=[
            "Upload Document",
            "Link to Client",
            "Link to Project",
            "Prepare for Nina",
        ],
    ),

    "web_exchange": WebView(
        view_id="web_exchange",
        name="Nina Exchange",
        purpose="Marketplace surface for ready AI workers.",
        layout="marketplace_cards + category_filters + listing_detail_panel",
        primary_blocks=[
            "Featured workers",
            "Office workers",
            "Sales workers",
            "Estimating workers",
            "Finance workers",
            "Support workers",
        ],
        right_panel_blocks=[
            "Selected worker listing",
            "Role stack",
            "Pricing placeholder",
            "Activation flow",
        ],
        quick_actions=[
            "Explore Worker",
            "Activate Worker",
            "View Demo",
        ],
    ),

    "web_chat": WebView(
        view_id="web_chat",
        name="Chat with Nina",
        purpose="Desktop conversational work entry point.",
        layout="chat_thread + context_panel + suggested_actions",
        primary_blocks=[
            "Conversation",
            "Workspace context",
            "Suggested actions",
            "Linked work objects",
        ],
        right_panel_blocks=[
            "Current client",
            "Current project",
            "Task suggestions",
            "Approval prompts",
        ],
        quick_actions=[
            "Ask Nina",
            "Create Task",
            "Create Follow-up",
            "Create Estimate Draft",
            "Save Note",
        ],
    ),

    "web_settings": WebView(
        view_id="web_settings",
        name="Settings",
        purpose="Workspace, company, billing, language and channel settings.",
        layout="settings_sections + detail_panel",
        primary_blocks=[
            "Workspace settings",
            "Company profile",
            "Language",
            "Channels",
            "Billing",
            "Permissions",
            "Team members",
        ],
        right_panel_blocks=[
            "Selected settings section",
            "Audit / status",
        ],
        quick_actions=[
            "Change Language",
            "Connect Channel",
            "Manage Billing",
        ],
    ),
}


def web_surface_status() -> str:
    return (
        "🖥️ NinaOS Web Surface\n\n"
        f"Version: {WEB_SURFACE_VERSION}\n"
        f"Views: {len(WEB_VIEWS)}\n"
        f"Sidebar items: {len(LEFT_SIDEBAR)}\n\n"
        "Purpose: define the first browser workspace surface for NinaOS.\n\n"
        "Status: active ✅"
    )


def list_web_views() -> List[WebView]:
    return list(WEB_VIEWS.values())


def get_web_view(view_id: str) -> Optional[WebView]:
    return WEB_VIEWS.get(view_id)


def build_web_surface_answer() -> str:
    lines = [
        "🖥️ NinaOS Web Surface",
        "",
        "The web app is the main workspace surface for companies.",
        "",
        "It must match the approved dark premium NinaOS dashboard vision:",
        "• left sidebar",
        "• top bar",
        "• dashboard cards",
        "• worker cards",
        "• Exchange visible",
        "• Nina chat available",
        "",
        "Main web views:",
    ]

    for view in list_web_views():
        lines.append(f"• {view.name}")
        lines.append(f"  {view.purpose}")

    lines.extend([
        "",
        "Left sidebar:",
    ])

    for item in sorted(LEFT_SIDEBAR, key=lambda x: x.priority):
        lines.append(f"• {item.label} → {item.target_view}")

    lines.extend([
        "",
        "Top bar:",
    ])

    for block in TOP_BAR_BLOCKS:
        lines.append(f"• {block}")

    lines.extend([
        "",
        f"Version: {WEB_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_web_dashboard_answer() -> str:
    view = get_web_view("web_dashboard")

    lines = [
        "🖥️ Web Dashboard",
        "",
        view.purpose if view else "",
        "",
        "Layout:",
        view.layout if view else "",
        "",
        "Primary blocks:",
    ]

    for block in view.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Right panel:",
    ])

    for block in view.right_panel_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in view.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {WEB_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_web_office_manager_answer() -> str:
    view = get_web_view("web_office_manager")

    lines = [
        "🖥️ Nina Office Manager SMB — Web View",
        "",
        "This is the main desktop control center for the first ready AI worker.",
        "",
        "Primary blocks:",
    ]

    for block in view.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Right panel:",
    ])

    for block in view.right_panel_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in view.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {WEB_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_web_exchange_answer() -> str:
    view = get_web_view("web_exchange")

    lines = [
        "🖥️ Nina Exchange — Web View",
        "",
        "Exchange must be visible in the desktop workspace from the beginning.",
        "",
        "Primary blocks:",
    ]

    for block in view.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Right panel:",
    ])

    for block in view.right_panel_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in view.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {WEB_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_web_clients_answer() -> str:
    view = get_web_view("web_clients")

    lines = [
        "🖥️ Clients — Web View",
        "",
        view.purpose,
        "",
        "Primary blocks:",
    ]

    for block in view.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Right panel:",
    ])

    for block in view.right_panel_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in view.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {WEB_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_web_rules_answer() -> str:
    return (
        "🖥️ NinaOS Web Rules\n\n"
        "1. Web Workspace is the main company control surface.\n"
        "2. Dashboard must show work objects, not empty chat.\n"
        "3. Workers must be visible as real product cards.\n"
        "4. Exchange must be in the sidebar from the beginning.\n"
        "5. Nina Chat must be available but not replace the workspace.\n"
        "6. Every dashboard card must map to a backend object or activity source.\n"
        "7. Web and mobile surfaces must share the same product logic.\n"
        "8. The product must look premium, global and business-ready.\n"
        "9. Office Manager SMB is the first priority worker.\n"
        "10. The web app must later become the main demo link for customers and investors.\n\n"
        f"Version: {WEB_SURFACE_VERSION}"
    )


def route_web_surface_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["web", "web surface", "web app", "workspace surface"]:
        return build_web_surface_answer()

    if lower in ["web status", "web surface status"]:
        return web_surface_status()

    if lower in ["web dashboard", "desktop dashboard"]:
        return build_web_dashboard_answer()

    if lower in ["web office manager", "office manager web"]:
        return build_web_office_manager_answer()

    if lower in ["web exchange", "exchange web"]:
        return build_web_exchange_answer()

    if lower in ["web clients", "clients web"]:
        return build_web_clients_answer()

    if lower in ["web rules", "desktop rules"]:
        return build_web_rules_answer()

    return None


def web_surface_schema() -> Dict[str, Any]:
    return {
        "version": WEB_SURFACE_VERSION,
        "principle": "web workspace product surface",
        "left_sidebar": [item.__dict__ for item in LEFT_SIDEBAR],
        "top_bar": TOP_BAR_BLOCKS,
        "views": {
            view_id: view.__dict__
            for view_id, view in WEB_VIEWS.items()
        },
        "commands": [
            "web",
            "web status",
            "web dashboard",
            "web office manager",
            "web exchange",
            "web clients",
            "web rules",
        ],
    }


if __name__ == "__main__":
    print(web_surface_status())
    print()
    print(build_web_surface_answer())
