# demo_setup.py
# NinaOS Demo Setup V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - One-command demo setup for Nina Office Manager SMB
# - Seeds Work Objects + Activity Feed
# - Returns dashboard-ready summary
#
# Safe standalone import. No database required.

from typing import Optional, Dict, Any


DEMO_SETUP_VERSION = "Demo Setup V1.0"


try:
    from work_objects import (
        seed_demo_work_objects,
        build_work_object_counts_answer,
        work_objects_status,
        WORK_OBJECTS_VERSION,
    )
except Exception as e:
    WORK_OBJECTS_VERSION = "Work Objects not connected"

    def seed_demo_work_objects():
        return {"ok": False, "message": f"Work Objects not available: {repr(e)}", "count": 0}

    def build_work_object_counts_answer(workspace_id="demo_small_business"):
        return f"Work Objects not available: {repr(e)}"

    def work_objects_status():
        return f"Work Objects not available: {repr(e)}"


try:
    from activity_feed import (
        seed_demo_activity_events,
        build_activity_feed_answer,
        activity_feed_status,
        ACTIVITY_FEED_VERSION,
    )
except Exception as e:
    ACTIVITY_FEED_VERSION = "Activity Feed not connected"

    def seed_demo_activity_events():
        return {"ok": False, "message": f"Activity Feed not available: {repr(e)}", "count": 0}

    def build_activity_feed_answer(workspace_id="demo_small_business", limit=10):
        return f"Activity Feed not available: {repr(e)}"

    def activity_feed_status():
        return f"Activity Feed not available: {repr(e)}"


try:
    from workspace_dashboard import (
        build_workspace_dashboard_answer,
        workspace_dashboard_status,
        WORKSPACE_DASHBOARD_VERSION,
    )
except Exception as e:
    WORKSPACE_DASHBOARD_VERSION = "Workspace Dashboard not connected"

    def build_workspace_dashboard_answer(workspace_id="demo_small_business", language="en"):
        return f"Workspace Dashboard not available: {repr(e)}"

    def workspace_dashboard_status(language="en"):
        return f"Workspace Dashboard not available: {repr(e)}"


try:
    from platform_visibility import (
        build_nina_office_manager_product_answer,
        build_platform_status_answer,
        PLATFORM_VISIBILITY_VERSION,
    )
except Exception as e:
    PLATFORM_VISIBILITY_VERSION = "Platform Visibility not connected"

    def build_nina_office_manager_product_answer(language="en"):
        return f"Platform Visibility not available: {repr(e)}"

    def build_platform_status_answer(language="en"):
        return f"Platform Visibility not available: {repr(e)}"


def demo_setup_status() -> str:
    return (
        "🧪 NinaOS Demo Setup\n\n"
        f"Version: {DEMO_SETUP_VERSION}\n"
        f"Work Objects: {WORK_OBJECTS_VERSION}\n"
        f"Activity Feed: {ACTIVITY_FEED_VERSION}\n"
        f"Workspace Dashboard: {WORKSPACE_DASHBOARD_VERSION}\n"
        f"Platform Visibility: {PLATFORM_VISIBILITY_VERSION}\n\n"
        "Purpose: one-command demo setup for Nina Office Manager SMB.\n\n"
        "Status: active ✅"
    )


def run_demo_setup(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> Dict[str, Any]:
    objects_result = seed_demo_work_objects()
    activity_result = seed_demo_activity_events()

    return {
        "ok": bool(objects_result.get("ok")) and bool(activity_result.get("ok")),
        "workspace_id": workspace_id,
        "language": language or "en",
        "objects": objects_result,
        "activity": activity_result,
        "version": DEMO_SETUP_VERSION,
    }


def build_demo_setup_answer(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    result = run_demo_setup(workspace_id=workspace_id, language=language)

    objects = result.get("objects", {})
    activity = result.get("activity", {})

    return (
        "🧪 NinaOS Demo Setup Complete\n\n"
        "Nina Office Manager SMB demo workspace is ready.\n\n"
        "Seeded layers:\n"
        f"• Work Objects: {objects.get('message')} ({objects.get('count')} objects)\n"
        f"• Activity Feed: {activity.get('message')} ({activity.get('count')} events)\n\n"
        "Now you can test:\n"
        "• dashboard\n"
        "• dashboard counts\n"
        "• activity\n"
        "• office manager\n"
        "• exchange\n\n"
        f"Version: {DEMO_SETUP_VERSION}"
    )


def build_demo_overview_answer(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    return (
        "🧪 NinaOS Demo Overview\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_demo_setup_answer(workspace_id, language)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_work_object_counts_answer(workspace_id)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_activity_feed_answer(workspace_id, limit=6)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_workspace_dashboard_answer(workspace_id, language)}"
    )


def build_demo_product_answer(
    workspace_id: str = "demo_small_business",
    language: Optional[str] = "en",
) -> str:
    return (
        "🚀 NinaOS Product Demo\n\n"
        "This is the first visible product demo path for Nina Office Manager SMB.\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_nina_office_manager_product_answer(language)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_demo_overview_answer(workspace_id, language)}"
    )


def route_demo_setup_command(text: str, language: Optional[str] = "en") -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["demo setup", "setup demo", "prepare demo"]:
        return build_demo_setup_answer(language=language)

    if lower in ["demo overview", "demo dashboard", "full demo"]:
        return build_demo_overview_answer(language=language)

    if lower in ["product demo", "ninaos demo", "office manager demo"]:
        return build_demo_product_answer(language=language)

    if lower in ["demo setup status", "demo status"]:
        return demo_setup_status()

    return None


def demo_setup_schema() -> Dict[str, Any]:
    return {
        "version": DEMO_SETUP_VERSION,
        "purpose": "one-command demo setup for Nina Office Manager SMB",
        "commands": [
            "demo setup",
            "demo overview",
            "product demo",
            "demo setup status",
        ],
        "connected_layers": {
            "work_objects": WORK_OBJECTS_VERSION,
            "activity_feed": ACTIVITY_FEED_VERSION,
            "workspace_dashboard": WORKSPACE_DASHBOARD_VERSION,
            "platform_visibility": PLATFORM_VISIBILITY_VERSION,
        },
    }


if __name__ == "__main__":
    print(demo_setup_status())
    print()
    print(build_demo_setup_answer())
