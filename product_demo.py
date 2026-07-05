# product_demo.py
# NinaOS Product Demo V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Short, clean product demo layer for Nina Office Manager SMB
# - Customer / founder / investor friendly
# - Avoids long technical Telegram output
#
# Safe standalone import. No database required.

from typing import Optional, Dict, Any


PRODUCT_DEMO_VERSION = "Product Demo V1.0"


try:
    from work_objects import dashboard_counts, WORK_OBJECTS_VERSION
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


try:
    from activity_feed import list_activity_events, ACTIVITY_FEED_VERSION
except Exception:
    ACTIVITY_FEED_VERSION = "Activity Feed not connected"

    def list_activity_events(workspace_id="demo_small_business", limit=5, event_type=None):
        return []


try:
    from demo_setup import run_demo_setup, DEMO_SETUP_VERSION
except Exception:
    DEMO_SETUP_VERSION = "Demo Setup not connected"

    def run_demo_setup(workspace_id="demo_small_business", language="en"):
        return {"ok": False}


def product_demo_status() -> str:
    return (
        "🚀 NinaOS Product Demo\n\n"
        f"Version: {PRODUCT_DEMO_VERSION}\n"
        f"Work Objects: {WORK_OBJECTS_VERSION}\n"
        f"Activity Feed: {ACTIVITY_FEED_VERSION}\n"
        f"Demo Setup: {DEMO_SETUP_VERSION}\n\n"
        "Purpose: short product-facing demo for Nina Office Manager SMB.\n\n"
        "Status: active ✅"
    )


def build_short_product_demo(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    run_demo_setup(workspace_id=workspace_id, language=language)
    counts = dashboard_counts(workspace_id)
    events = list_activity_events(workspace_id=workspace_id, limit=3)

    lines = [
        "🚀 NinaOS Product Demo",
        "",
        "NinaOS gives small businesses ready AI workers — not bot builders.",
        "",
        "First ready worker:",
        "🏢 Nina Office Manager SMB",
        "",
        "What she does:",
        "• manages tasks and deadlines",
        "• tracks client follow-ups",
        "• supports invoice administration",
        "• helps prepare estimate and offer drafts",
        "• organizes documents and files",
        "",
        "Live workspace snapshot:",
        f"• Tasks Today: {counts.get('tasks_today', 0)}",
        f"• Follow-ups: {counts.get('followups', 0)}",
        f"• Invoices Due: {counts.get('invoices_due', 0)}",
        f"• Estimates in Progress: {counts.get('estimates_in_progress', 0)}",
        f"• Active Projects: {counts.get('projects_active', 0)}",
        "",
        "Recent activity:",
    ]

    if events:
        for event in events:
            lines.append(f"• {event.title}")
    else:
        lines.append("• Demo workspace initialized")

    lines.extend([
        "",
        "Exchange preview:",
        "• Nina Office Manager SMB — active",
        "• Nina Sales — planned",
        "• Nina Estimator — planned",
        "• Nina Finance — planned",
        "• Nina Support — planned",
        "",
        f"Version: {PRODUCT_DEMO_VERSION}",
    ])

    return "\n".join(lines)


def build_customer_pitch_demo(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    run_demo_setup(workspace_id=workspace_id, language=language)
    counts = dashboard_counts(workspace_id)

    return (
        "🏢 Nina Office Manager SMB — Customer Demo\n\n"
        "For small businesses that cannot hire a full office team, Nina becomes the first AI office worker.\n\n"
        "She helps the owner keep control over:\n"
        "• tasks\n"
        "• clients\n"
        "• follow-ups\n"
        "• invoices\n"
        "• estimates\n"
        "• documents\n\n"
        "Demo workspace now shows:\n"
        f"• {counts.get('tasks_today', 0)} task needing attention\n"
        f"• {counts.get('followups', 0)} client follow-up\n"
        f"• {counts.get('invoices_due', 0)} invoice to watch\n"
        f"• {counts.get('estimates_in_progress', 0)} estimate in progress\n"
        f"• {counts.get('projects_active', 0)} active project\n\n"
        "The customer does not build a bot.\n"
        "The customer receives a ready AI worker.\n\n"
        f"Version: {PRODUCT_DEMO_VERSION}"
    )


def build_founder_pitch_demo(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    run_demo_setup(workspace_id=workspace_id, language=language)

    return (
        "🌐 NinaOS Founder Pitch\n\n"
        "NinaOS is an AI workforce operating system.\n\n"
        "The market is moving from chatbots to AI workers.\n"
        "But most products are either too narrow, or too complex for small businesses.\n\n"
        "NinaOS solves this by giving customers ready AI workers.\n\n"
        "Our first wedge:\n"
        "🏢 Nina Office Manager SMB\n\n"
        "She combines five roles:\n"
        "• Office Manager Core\n"
        "• Finance Admin Assistant\n"
        "• Estimating Assistant Basic\n"
        "• Client Follow-up Manager\n"
        "• Document Admin\n\n"
        "Under the hood, NinaOS already has:\n"
        "• Role Registry\n"
        "• Agent Registry\n"
        "• Workspace Engine\n"
        "• Permission Engine\n"
        "• Work Objects\n"
        "• Activity Feed\n"
        "• Dashboard Surface\n"
        "• Exchange Preview\n\n"
        "The long-term goal is a global marketplace where AI workers, bots and agents can work, trade and cooperate.\n\n"
        f"Version: {PRODUCT_DEMO_VERSION}"
    )


def build_dashboard_pitch_demo(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    run_demo_setup(workspace_id=workspace_id, language=language)
    counts = dashboard_counts(workspace_id)

    return (
        "📊 NinaOS Dashboard Demo\n\n"
        "The approved NinaOS product surface is built around a business dashboard, not an empty chat box.\n\n"
        "Dashboard blocks:\n"
        f"• Tasks Today: {counts.get('tasks_today', 0)}\n"
        f"• Follow-ups: {counts.get('followups', 0)}\n"
        f"• Invoices Due: {counts.get('invoices_due', 0)}\n"
        f"• Estimates in Progress: {counts.get('estimates_in_progress', 0)}\n"
        f"• Active Projects: {counts.get('projects_active', 0)}\n\n"
        "The dashboard is fed by Work Objects and Activity Feed.\n\n"
        "This is the path toward the visual web app approved in the NinaOS product vision.\n\n"
        f"Version: {PRODUCT_DEMO_VERSION}"
    )


def build_exchange_pitch_demo(language: Optional[str] = "en") -> str:
    return (
        "🛒 NinaOS Exchange Demo\n\n"
        "NinaOS is not only one AI worker.\n"
        "It is a ready-worker platform and future AI worker marketplace.\n\n"
        "First Exchange catalog:\n"
        "• Nina Office Manager SMB — active\n"
        "• Nina Sales — planned\n"
        "• Nina Estimator — planned\n"
        "• Nina Finance — planned\n"
        "• Nina Support — planned\n\n"
        "Exchange will allow:\n"
        "• customers to activate ready AI workers\n"
        "• AI workers to cooperate\n"
        "• bot-to-bot deals\n"
        "• NinaOS to earn commissions\n\n"
        f"Version: {PRODUCT_DEMO_VERSION}"
    )


def route_product_demo_command(text: str, language: Optional[str] = "en") -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["short demo", "product demo short", "demo short"]:
        return build_short_product_demo(language=language)

    if lower in ["product demo", "ninaos demo"]:
        return build_short_product_demo(language=language)

    if lower in ["customer demo", "client demo"]:
        return build_customer_pitch_demo(language=language)

    if lower in ["founder pitch", "founder demo", "investor demo", "investor pitch"]:
        return build_founder_pitch_demo(language=language)

    if lower in ["dashboard demo", "dashboard pitch"]:
        return build_dashboard_pitch_demo(language=language)

    if lower in ["exchange demo", "exchange pitch"]:
        return build_exchange_pitch_demo(language=language)

    if lower in ["product demo status", "demo pitch status"]:
        return product_demo_status()

    return None


def product_demo_schema() -> Dict[str, Any]:
    return {
        "version": PRODUCT_DEMO_VERSION,
        "purpose": "short product-facing demo for Nina Office Manager SMB",
        "commands": [
            "product demo",
            "short demo",
            "customer demo",
            "founder pitch",
            "dashboard demo",
            "exchange demo",
            "product demo status",
        ],
        "connected_layers": {
            "work_objects": WORK_OBJECTS_VERSION,
            "activity_feed": ACTIVITY_FEED_VERSION,
            "demo_setup": DEMO_SETUP_VERSION,
        },
    }


if __name__ == "__main__":
    print(product_demo_status())
    print()
    print(build_short_product_demo())
