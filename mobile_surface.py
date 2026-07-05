# mobile_surface.py
# NinaOS Mobile Surface V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Define NinaOS mobile-first product surface
# - Make sure NinaOS works comfortably on phones, not only desktop
# - First mobile product target: Nina Office Manager SMB
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


MOBILE_SURFACE_VERSION = "Mobile Surface V1.0"


@dataclass(frozen=True)
class MobileScreen:
    screen_id: str
    name: str
    purpose: str
    primary_blocks: List[str] = field(default_factory=list)
    quick_actions: List[str] = field(default_factory=list)
    bottom_nav_visible: bool = True
    status: str = "active"


@dataclass(frozen=True)
class MobileNavItem:
    nav_id: str
    label: str
    target_screen: str
    icon_hint: str = ""
    priority: int = 1
    status: str = "active"


BOTTOM_NAV: List[MobileNavItem] = [
    MobileNavItem("home", "Home", "mobile_home", "house", 1),
    MobileNavItem("dashboard", "Dashboard", "mobile_dashboard", "chart", 2),
    MobileNavItem("workers", "Workers", "mobile_workers", "users", 3),
    MobileNavItem("chat", "Nina", "mobile_chat", "message", 4),
    MobileNavItem("exchange", "Exchange", "mobile_exchange", "market", 5),
]


MOBILE_SCREENS: Dict[str, MobileScreen] = {
    "mobile_home": MobileScreen(
        screen_id="mobile_home",
        name="Mobile Home",
        purpose="Fast entry point for a small business owner on the phone.",
        primary_blocks=[
            "Today summary",
            "Urgent follow-ups",
            "Invoice reminders",
            "Nina Office Manager SMB card",
            "Quick actions",
        ],
        quick_actions=[
            "New Task",
            "Add Client",
            "Schedule Follow-up",
            "New Estimate",
            "Upload Document",
        ],
    ),

    "mobile_dashboard": MobileScreen(
        screen_id="mobile_dashboard",
        name="Mobile Dashboard",
        purpose="Phone-friendly version of the NinaOS workspace dashboard.",
        primary_blocks=[
            "Tasks Today",
            "Follow-ups",
            "Invoices Due",
            "Estimates in Progress",
            "Active Projects",
            "Recent Activities",
            "Exchange Preview",
        ],
        quick_actions=[
            "New Task",
            "New Estimate",
            "New Invoice",
            "Add Client",
            "Schedule Follow-up",
        ],
    ),

    "mobile_workers": MobileScreen(
        screen_id="mobile_workers",
        name="Mobile Workers",
        purpose="List and manage ready AI workers in the workspace.",
        primary_blocks=[
            "Nina Office Manager SMB",
            "Worker role stack",
            "Worker status",
            "Planned workers",
        ],
        quick_actions=[
            "Open Office Manager",
            "Explore Exchange",
        ],
    ),

    "mobile_office_manager": MobileScreen(
        screen_id="mobile_office_manager",
        name="Nina Office Manager SMB Mobile View",
        purpose="Mobile worker profile and action center for Nina Office Manager SMB.",
        primary_blocks=[
            "Worker summary",
            "Role stack",
            "Today tasks",
            "Client follow-ups",
            "Invoice alerts",
            "Estimate drafts",
            "Documents",
            "Approval required",
        ],
        quick_actions=[
            "Ask Nina",
            "New Task",
            "Follow-up Client",
            "Create Estimate Draft",
            "Add Invoice Reminder",
            "Upload Document",
        ],
    ),

    "mobile_tasks": MobileScreen(
        screen_id="mobile_tasks",
        name="Mobile Tasks",
        purpose="Manage tasks and deadlines from the phone.",
        primary_blocks=[
            "Today",
            "Overdue",
            "Upcoming",
            "Completed",
        ],
        quick_actions=[
            "New Task",
            "Mark Done",
            "Schedule Reminder",
        ],
    ),

    "mobile_clients": MobileScreen(
        screen_id="mobile_clients",
        name="Mobile Clients",
        purpose="Client overview and quick follow-up from the phone.",
        primary_blocks=[
            "Active Clients",
            "Needs Follow-up",
            "Offers Sent",
            "Invoices Due",
        ],
        quick_actions=[
            "Add Client",
            "Send Follow-up Draft",
            "Open Client Work View",
        ],
    ),

    "mobile_estimates": MobileScreen(
        screen_id="mobile_estimates",
        name="Mobile Estimates",
        purpose="Track estimate and offer drafts on mobile.",
        primary_blocks=[
            "Drafts",
            "In Progress",
            "Sent",
            "Waiting for Client",
        ],
        quick_actions=[
            "New Estimate",
            "Add Scope",
            "Schedule Follow-up",
        ],
    ),

    "mobile_invoices": MobileScreen(
        screen_id="mobile_invoices",
        name="Mobile Invoices",
        purpose="Track invoice admin and payment follow-ups on mobile.",
        primary_blocks=[
            "Due Soon",
            "Overdue",
            "Paid",
            "Drafts",
        ],
        quick_actions=[
            "New Invoice",
            "Payment Follow-up",
            "Prepare for Accountant",
        ],
    ),

    "mobile_documents": MobileScreen(
        screen_id="mobile_documents",
        name="Mobile Documents",
        purpose="Upload, organize and link documents from the phone.",
        primary_blocks=[
            "Recent Uploads",
            "Client Files",
            "Invoices",
            "Estimates",
            "Contracts",
        ],
        quick_actions=[
            "Upload Document",
            "Scan Photo",
            "Link to Client",
            "Link to Project",
        ],
    ),

    "mobile_chat": MobileScreen(
        screen_id="mobile_chat",
        name="Chat with Nina",
        purpose="Conversational work entry point for mobile users.",
        primary_blocks=[
            "Chat thread",
            "Suggested actions",
            "Context card",
            "Voice input later",
        ],
        quick_actions=[
            "Ask Nina",
            "Create Task from Message",
            "Save Follow-up",
            "Create Reminder",
        ],
    ),

    "mobile_exchange": MobileScreen(
        screen_id="mobile_exchange",
        name="Mobile Exchange",
        purpose="Mobile marketplace surface for ready AI workers.",
        primary_blocks=[
            "Featured Workers",
            "Categories",
            "Nina Office Manager SMB",
            "Nina Sales",
            "Nina Estimator",
            "Nina Finance",
            "Nina Support",
        ],
        quick_actions=[
            "Explore Worker",
            "Activate Worker",
            "View Pricing",
        ],
    ),
}


def mobile_surface_status() -> str:
    return (
        "📱 NinaOS Mobile Surface\n\n"
        f"Version: {MOBILE_SURFACE_VERSION}\n"
        f"Screens: {len(MOBILE_SCREENS)}\n"
        f"Bottom nav items: {len(BOTTOM_NAV)}\n\n"
        "Principle: NinaOS must work comfortably on phones from the first web app version.\n\n"
        "Status: active ✅"
    )


def list_mobile_screens() -> List[MobileScreen]:
    return list(MOBILE_SCREENS.values())


def get_mobile_screen(screen_id: str) -> Optional[MobileScreen]:
    return MOBILE_SCREENS.get(screen_id)


def build_mobile_surface_answer() -> str:
    lines = [
        "📱 NinaOS Mobile Surface",
        "",
        "NinaOS must be mobile-first.",
        "",
        "Small business owners do not work only at a desk.",
        "They answer clients, check invoices, send follow-ups and review work from the phone.",
        "",
        "Core mobile surfaces:",
    ]

    for screen in list_mobile_screens():
        lines.append(f"• {screen.name}")
        lines.append(f"  {screen.purpose}")

    lines.extend([
        "",
        "Bottom navigation:",
    ])

    for item in sorted(BOTTOM_NAV, key=lambda x: x.priority):
        lines.append(f"• {item.label} → {item.target_screen}")

    lines.extend([
        "",
        f"Version: {MOBILE_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_mobile_home_answer() -> str:
    screen = get_mobile_screen("mobile_home")

    lines = [
        "📱 Mobile Home",
        "",
        screen.purpose if screen else "",
        "",
        "Primary blocks:",
    ]

    for block in screen.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in screen.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {MOBILE_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_mobile_dashboard_answer() -> str:
    screen = get_mobile_screen("mobile_dashboard")

    lines = [
        "📱 Mobile Dashboard",
        "",
        "Phone-friendly dashboard blocks:",
    ]

    for block in screen.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Mobile rule:",
        "Cards must stack vertically. Every block must be readable with one thumb, without desktop-style dense tables.",
        "",
        "Quick actions:",
    ])

    for action in screen.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {MOBILE_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_mobile_office_manager_answer() -> str:
    screen = get_mobile_screen("mobile_office_manager")

    lines = [
        "📱 Nina Office Manager SMB — Mobile View",
        "",
        "This is the most important first mobile worker screen.",
        "",
        "It must show the owner what Nina is handling right now:",
    ]

    for block in screen.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in screen.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        "Mobile-first principle:",
        "The user should be able to create a task, follow up with a client, check invoices or ask Nina in under 10 seconds.",
        "",
        f"Version: {MOBILE_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_mobile_exchange_answer() -> str:
    screen = get_mobile_screen("mobile_exchange")

    lines = [
        "📱 Mobile Exchange",
        "",
        "Exchange must also work on mobile, because many users will discover and activate workers from the phone.",
        "",
        "Primary blocks:",
    ]

    for block in screen.primary_blocks:
        lines.append(f"• {block}")

    lines.extend([
        "",
        "Quick actions:",
    ])

    for action in screen.quick_actions:
        lines.append(f"• {action}")

    lines.extend([
        "",
        f"Version: {MOBILE_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_mobile_rules_answer() -> str:
    return (
        "📱 NinaOS Mobile Rules\n\n"
        "1. Mobile is first-class, not secondary.\n"
        "2. Dashboard cards must stack vertically.\n"
        "3. Bottom navigation must stay simple: Home, Dashboard, Workers, Nina, Exchange.\n"
        "4. Every main action must be reachable in 1–2 taps.\n"
        "5. No dense desktop tables on phone.\n"
        "6. Quick actions are more important than complex menus.\n"
        "7. Nina chat must always be one tap away.\n"
        "8. Exchange must be visible on mobile.\n"
        "9. Office Manager SMB must have its own mobile worker view.\n"
        "10. The product must feel useful in real business movement, not only office desktop use.\n\n"
        f"Version: {MOBILE_SURFACE_VERSION}"
    )


def route_mobile_surface_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["mobile", "mobile surface", "mobile app", "app mobile"]:
        return build_mobile_surface_answer()

    if lower in ["mobile status", "mobile surface status"]:
        return mobile_surface_status()

    if lower in ["mobile home"]:
        return build_mobile_home_answer()

    if lower in ["mobile dashboard"]:
        return build_mobile_dashboard_answer()

    if lower in ["mobile office manager", "office manager mobile"]:
        return build_mobile_office_manager_answer()

    if lower in ["mobile exchange"]:
        return build_mobile_exchange_answer()

    if lower in ["mobile rules", "mobile principles"]:
        return build_mobile_rules_answer()

    return None


def mobile_surface_schema() -> Dict[str, Any]:
    return {
        "version": MOBILE_SURFACE_VERSION,
        "principle": "mobile-first product surface",
        "bottom_nav": [item.__dict__ for item in BOTTOM_NAV],
        "screens": {
            screen_id: screen.__dict__
            for screen_id, screen in MOBILE_SCREENS.items()
        },
        "commands": [
            "mobile",
            "mobile status",
            "mobile home",
            "mobile dashboard",
            "mobile office manager",
            "mobile exchange",
            "mobile rules",
        ],
    }


if __name__ == "__main__":
    print(mobile_surface_status())
    print()
    print(build_mobile_surface_answer())
