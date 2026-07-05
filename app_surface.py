# app_surface.py
# NinaOS App Surface V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Unite Web Surface + Mobile Surface into one product app surface
# - Prepare route structure for the first real browser app
# - Defines pages: /, /dashboard, /workers, /office-manager, /exchange, /mobile
#
# Safe standalone import. No database required.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


APP_SURFACE_VERSION = "App Surface V1.0"


try:
    from web_surface import (
        WEB_SURFACE_VERSION,
        build_web_surface_answer,
        build_web_dashboard_answer,
        build_web_office_manager_answer,
        build_web_exchange_answer,
        build_web_clients_answer,
    )
except Exception as e:
    WEB_SURFACE_VERSION = "Web Surface not connected"

    def build_web_surface_answer():
        return f"Web Surface not available: {repr(e)}"

    def build_web_dashboard_answer():
        return f"Web Dashboard not available: {repr(e)}"

    def build_web_office_manager_answer():
        return f"Web Office Manager not available: {repr(e)}"

    def build_web_exchange_answer():
        return f"Web Exchange not available: {repr(e)}"

    def build_web_clients_answer():
        return f"Web Clients not available: {repr(e)}"


try:
    from mobile_surface import (
        MOBILE_SURFACE_VERSION,
        build_mobile_surface_answer,
        build_mobile_dashboard_answer,
        build_mobile_office_manager_answer,
        build_mobile_exchange_answer,
    )
except Exception as e:
    MOBILE_SURFACE_VERSION = "Mobile Surface not connected"

    def build_mobile_surface_answer():
        return f"Mobile Surface not available: {repr(e)}"

    def build_mobile_dashboard_answer():
        return f"Mobile Dashboard not available: {repr(e)}"

    def build_mobile_office_manager_answer():
        return f"Mobile Office Manager not available: {repr(e)}"

    def build_mobile_exchange_answer():
        return f"Mobile Exchange not available: {repr(e)}"


try:
    from workspace_dashboard import (
        WORKSPACE_DASHBOARD_VERSION,
        workspace_dashboard_schema,
        build_workspace_dashboard_answer,
    )
except Exception as e:
    WORKSPACE_DASHBOARD_VERSION = "Workspace Dashboard not connected"

    def workspace_dashboard_schema(workspace_id="demo_small_business", language="en"):
        return {}

    def build_workspace_dashboard_answer(workspace_id="demo_small_business", language="en"):
        return f"Workspace Dashboard not available: {repr(e)}"


try:
    from product_demo import (
        PRODUCT_DEMO_VERSION,
        build_short_product_demo,
        build_customer_pitch_demo,
        build_founder_pitch_demo,
    )
except Exception as e:
    PRODUCT_DEMO_VERSION = "Product Demo not connected"

    def build_short_product_demo(workspace_id="demo_small_business", language="en"):
        return f"Product Demo not available: {repr(e)}"

    def build_customer_pitch_demo(workspace_id="demo_small_business", language="en"):
        return f"Customer Demo not available: {repr(e)}"

    def build_founder_pitch_demo(workspace_id="demo_small_business", language="en"):
        return f"Founder Demo not available: {repr(e)}"


@dataclass(frozen=True)
class AppRoute:
    route_id: str
    path: str
    name: str
    surface: str
    purpose: str
    primary_view: str
    mobile_supported: bool = True
    status: str = "active"


@dataclass(frozen=True)
class AppSurfaceSection:
    section_id: str
    name: str
    purpose: str
    routes: List[str] = field(default_factory=list)
    status: str = "active"


APP_ROUTES: Dict[str, AppRoute] = {
    "home": AppRoute(
        route_id="home",
        path="/",
        name="NinaOS Home",
        surface="web+mobile",
        purpose="First app entry point and product orientation screen.",
        primary_view="app_home",
    ),
    "dashboard": AppRoute(
        route_id="dashboard",
        path="/dashboard",
        name="Workspace Dashboard",
        surface="web+mobile",
        purpose="Main workspace dashboard with tasks, follow-ups, invoices, estimates and activity.",
        primary_view="workspace_dashboard",
    ),
    "workers": AppRoute(
        route_id="workers",
        path="/workers",
        name="Workers",
        surface="web+mobile",
        purpose="Ready AI workers assigned to the workspace.",
        primary_view="workers",
    ),
    "office_manager": AppRoute(
        route_id="office_manager",
        path="/office-manager",
        name="Nina Office Manager SMB",
        surface="web+mobile",
        purpose="First strategic worker profile and control center.",
        primary_view="nina_office_manager_smb",
    ),
    "clients": AppRoute(
        route_id="clients",
        path="/clients",
        name="Clients",
        surface="web",
        purpose="Client overview and client work view.",
        primary_view="clients",
    ),
    "tasks": AppRoute(
        route_id="tasks",
        path="/tasks",
        name="Tasks",
        surface="web+mobile",
        purpose="Task and deadline management.",
        primary_view="tasks",
    ),
    "estimates": AppRoute(
        route_id="estimates",
        path="/estimates",
        name="Estimates",
        surface="web+mobile",
        purpose="Estimate and offer draft workflow.",
        primary_view="estimates",
    ),
    "invoices": AppRoute(
        route_id="invoices",
        path="/invoices",
        name="Invoices",
        surface="web+mobile",
        purpose="Invoice administration and payment follow-up.",
        primary_view="invoices",
    ),
    "documents": AppRoute(
        route_id="documents",
        path="/documents",
        name="Documents",
        surface="web+mobile",
        purpose="Document upload, linking and Knowledge Vault entry surface.",
        primary_view="documents",
    ),
    "exchange": AppRoute(
        route_id="exchange",
        path="/exchange",
        name="Nina Exchange",
        surface="web+mobile",
        purpose="Marketplace for ready AI workers.",
        primary_view="exchange",
    ),
    "mobile": AppRoute(
        route_id="mobile",
        path="/mobile",
        name="Mobile App Surface",
        surface="mobile",
        purpose="Mobile-first app structure preview.",
        primary_view="mobile_surface",
    ),
    "demo": AppRoute(
        route_id="demo",
        path="/demo",
        name="Product Demo",
        surface="web+mobile",
        purpose="Short product-facing demo for customers and investors.",
        primary_view="product_demo",
    ),
}


APP_SECTIONS: Dict[str, AppSurfaceSection] = {
    "workspace": AppSurfaceSection(
        section_id="workspace",
        name="Workspace",
        purpose="Main work operating surface.",
        routes=["home", "dashboard", "workers", "office_manager", "clients", "tasks"],
    ),
    "business_objects": AppSurfaceSection(
        section_id="business_objects",
        name="Business Objects",
        purpose="Objects that drive real work.",
        routes=["estimates", "invoices", "documents"],
    ),
    "marketplace": AppSurfaceSection(
        section_id="marketplace",
        name="Marketplace",
        purpose="Ready worker discovery and activation.",
        routes=["exchange"],
    ),
    "demo": AppSurfaceSection(
        section_id="demo",
        name="Demo",
        purpose="Product demo and market-facing views.",
        routes=["demo", "mobile"],
    ),
}


def app_surface_status() -> str:
    return (
        "🧭 NinaOS App Surface\n\n"
        f"Version: {APP_SURFACE_VERSION}\n"
        f"Web Surface: {WEB_SURFACE_VERSION}\n"
        f"Mobile Surface: {MOBILE_SURFACE_VERSION}\n"
        f"Workspace Dashboard: {WORKSPACE_DASHBOARD_VERSION}\n"
        f"Product Demo: {PRODUCT_DEMO_VERSION}\n"
        f"Routes: {len(APP_ROUTES)}\n"
        f"Sections: {len(APP_SECTIONS)}\n\n"
        "Purpose: prepare NinaOS for the first real browser application.\n\n"
        "Status: active ✅"
    )


def list_app_routes() -> List[AppRoute]:
    return list(APP_ROUTES.values())


def get_app_route(route_id: str) -> Optional[AppRoute]:
    return APP_ROUTES.get(route_id)


def build_app_surface_answer() -> str:
    lines = [
        "🧭 NinaOS App Surface",
        "",
        "This layer connects the product architecture to the future real browser app.",
        "",
        "Goal:",
        "• make NinaOS easier to navigate",
        "• prepare web routes",
        "• connect mobile and desktop logic",
        "• move from Telegram-only demo to visual web app",
        "",
        "Main app routes:",
    ]

    for route in list_app_routes():
        lines.append(f"• {route.path} — {route.name}")
        lines.append(f"  {route.purpose}")
        lines.append(f"  Surface: {route.surface}")

    lines.extend([
        "",
        f"Version: {APP_SURFACE_VERSION}",
    ])

    return "\n".join(lines)


def build_app_home_answer() -> str:
    return (
        "🏠 NinaOS App Home\n\n"
        "NinaOS is a ready AI worker platform.\n\n"
        "First product:\n"
        "🏢 Nina Office Manager SMB\n\n"
        "Main navigation:\n"
        "• /dashboard — workspace overview\n"
        "• /workers — ready AI workers\n"
        "• /office-manager — first worker control center\n"
        "• /clients — client work\n"
        "• /estimates — estimates and offers\n"
        "• /invoices — invoice admin\n"
        "• /documents — document workspace\n"
        "• /exchange — ready worker marketplace\n"
        "• /demo — short product demo\n\n"
        "The first real visual app should open here.\n\n"
        f"Version: {APP_SURFACE_VERSION}"
    )


def build_app_routes_answer() -> str:
    lines = [
        "🧭 NinaOS App Routes",
        "",
        f"Version: {APP_SURFACE_VERSION}",
        "",
    ]

    for route in list_app_routes():
        lines.append(f"• {route.path}")
        lines.append(f"  Route ID: {route.route_id}")
        lines.append(f"  Name: {route.name}")
        lines.append(f"  Surface: {route.surface}")
        lines.append(f"  Mobile supported: {'yes' if route.mobile_supported else 'no'}")
        lines.append("")

    return "\n".join(lines).strip()


def build_app_sections_answer() -> str:
    lines = [
        "🧩 NinaOS App Sections",
        "",
    ]

    for section in APP_SECTIONS.values():
        lines.append(f"• {section.name}")
        lines.append(f"  {section.purpose}")
        lines.append(f"  Routes: {', '.join(section.routes)}")
        lines.append("")

    lines.append(f"Version: {APP_SURFACE_VERSION}")
    return "\n".join(lines).strip()


def build_app_preview_answer() -> str:
    return (
        "👀 NinaOS App Preview\n\n"
        "The first visual browser app should look like this:\n\n"
        "Desktop:\n"
        "• Left sidebar: Dashboard, Workers, Clients, Tasks, Projects, Estimates, Invoices, Documents, Exchange\n"
        "• Top bar: Workspace switcher, Search, Create, Notifications, User menu\n"
        "• Main grid: dashboard cards and activity feed\n"
        "• Right panel: Nina Office Manager SMB card and quick actions\n\n"
        "Mobile:\n"
        "• Bottom navigation: Home, Dashboard, Workers, Nina, Exchange\n"
        "• Cards stacked vertically\n"
        "• One-thumb quick actions\n"
        "• Chat with Nina always one tap away\n\n"
        "First real pages to build:\n"
        "1. /\n"
        "2. /dashboard\n"
        "3. /workers\n"
        "4. /office-manager\n"
        "5. /exchange\n\n"
        f"Version: {APP_SURFACE_VERSION}"
    )


def build_app_dashboard_preview_answer() -> str:
    return (
        "📊 App Dashboard Preview\n\n"
        "This is the route that will become /dashboard in the browser app.\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_workspace_dashboard_answer('demo_small_business', 'en')}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_web_dashboard_answer()}"
    )


def build_app_office_manager_preview_answer() -> str:
    return (
        "🏢 App Office Manager Preview\n\n"
        "This is the route that will become /office-manager in the browser app.\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_web_office_manager_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_mobile_office_manager_answer()}"
    )


def build_app_exchange_preview_answer() -> str:
    return (
        "🛒 App Exchange Preview\n\n"
        "This is the route that will become /exchange in the browser app.\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_web_exchange_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_mobile_exchange_answer()}"
    )


def route_app_surface_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["app surface", "app", "ninaos app"]:
        return build_app_surface_answer()

    if lower in ["app status", "app surface status"]:
        return app_surface_status()

    if lower in ["app home", "home route"]:
        return build_app_home_answer()

    if lower in ["app routes", "routes"]:
        return build_app_routes_answer()

    if lower in ["app sections", "sections"]:
        return build_app_sections_answer()

    if lower in ["app preview", "visual app preview"]:
        return build_app_preview_answer()

    if lower in ["app dashboard", "dashboard route"]:
        return build_app_dashboard_preview_answer()

    if lower in ["app office manager", "office manager route"]:
        return build_app_office_manager_preview_answer()

    if lower in ["app exchange", "exchange route"]:
        return build_app_exchange_preview_answer()

    return None


def app_surface_schema() -> Dict[str, Any]:
    return {
        "version": APP_SURFACE_VERSION,
        "purpose": "prepare first real browser app",
        "routes": {
            route_id: route.__dict__
            for route_id, route in APP_ROUTES.items()
        },
        "sections": {
            section_id: section.__dict__
            for section_id, section in APP_SECTIONS.items()
        },
        "connected_layers": {
            "web_surface": WEB_SURFACE_VERSION,
            "mobile_surface": MOBILE_SURFACE_VERSION,
            "workspace_dashboard": WORKSPACE_DASHBOARD_VERSION,
            "product_demo": PRODUCT_DEMO_VERSION,
        },
        "first_pages_to_build": [
            "/",
            "/dashboard",
            "/workers",
            "/office-manager",
            "/exchange",
        ],
        "commands": [
            "app",
            "app status",
            "app home",
            "app routes",
            "app sections",
            "app preview",
            "app dashboard",
            "app office manager",
            "app exchange",
        ],
    }


if __name__ == "__main__":
    print(app_surface_status())
    print()
    print(build_app_surface_answer())
