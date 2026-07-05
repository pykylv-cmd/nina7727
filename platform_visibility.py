# platform_visibility.py
# NinaOS Platform Visibility V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# Make NinaOS Platform Core visible in the product.

PLATFORM_VISIBILITY_VERSION = "Platform Visibility V1.0"

try:
    from role_registry import (
        role_registry_status,
        build_roles_answer,
        build_composite_workers_answer,
        build_office_manager_smb_answer,
    )
except Exception as e:
    def role_registry_status():
        return f"Role Registry nav pieejams: {repr(e)}"

    def build_roles_answer(include_planned=False):
        return f"Role Registry nav pieejams: {repr(e)}"

    def build_composite_workers_answer():
        return f"Composite Workers nav pieejami: {repr(e)}"

    def build_office_manager_smb_answer():
        return f"Nina Office Manager SMB nav pieejama: {repr(e)}"


try:
    from agent_registry import (
        agent_registry_status,
        build_agents_answer,
        build_office_manager_agent_answer,
    )
except Exception as e:
    def agent_registry_status():
        return f"Agent Registry nav pieejams: {repr(e)}"

    def build_agents_answer(include_planned=False):
        return f"Agent Registry nav pieejams: {repr(e)}"

    def build_office_manager_agent_answer():
        return f"Nina Office Manager Agent nav pieejams: {repr(e)}"


try:
    from workspace_engine import (
        workspace_engine_status,
        build_workspaces_answer,
        build_small_business_workspace_answer,
    )
except Exception as e:
    def workspace_engine_status():
        return f"Workspace Engine nav pieejams: {repr(e)}"

    def build_workspaces_answer():
        return f"Workspace Engine nav pieejams: {repr(e)}"

    def build_small_business_workspace_answer():
        return f"Small Business Workspace nav pieejams: {repr(e)}"


try:
    from permission_engine import (
        permission_engine_status,
        build_permissions_answer,
        build_office_manager_permissions_answer,
        build_workspace_permissions_answer,
    )
except Exception as e:
    def permission_engine_status():
        return f"Permission Engine nav pieejams: {repr(e)}"

    def build_permissions_answer():
        return f"Permission Engine nav pieejams: {repr(e)}"

    def build_office_manager_permissions_answer():
        return f"Office Manager permissions nav pieejamas: {repr(e)}"

    def build_workspace_permissions_answer(workspace_id):
        return f"Workspace permissions nav pieejamas: {repr(e)}"


def platform_visibility_status():
    return (
        "🌐 NinaOS Platform Visibility\n\n"
        f"Versija: {PLATFORM_VISIBILITY_VERSION}\n"
        "Mērķis: padarīt NinaOS Platform Core redzamu produktā.\n\n"
        "Redzamie slāņi:\n"
        "• Role Registry\n"
        "• Agent Registry\n"
        "• Workspace Engine\n"
        "• Permission Engine\n"
        "• Nina Office Manager SMB\n\n"
        "Statuss: aktīvs ✅"
    )


def build_platform_status_answer():
    return (
        "🌐 NinaOS Platform Core Status\n\n"
        f"{platform_visibility_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{role_registry_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{agent_registry_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{workspace_engine_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{permission_engine_status()}"
    )


def build_ninaos_workers_answer():
    return (
        "👥 NinaOS Ready Workers\n\n"
        "Pirmais stratēģiskais gatavais darbinieks:\n"
        "• Nina Office Manager SMB\n\n"
        "Plānotie nākamie workers:\n"
        "• Nina Sales\n"
        "• Nina Estimator\n"
        "• Nina Finance\n"
        "• Nina Support\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_agents_answer(include_planned=True)}"
    )


def build_nina_office_manager_product_answer():
    return (
        "🏢 Nina Office Manager SMB\n\n"
        "AI biroja vadītāja mazajiem uzņēmumiem.\n\n"
        "Viņa apvieno 5 amatus vienā gatavā darbiniekā:\n"
        "• Office Manager Core\n"
        "• Finance Admin Assistant\n"
        "• Estimating Assistant Basic\n"
        "• Client Follow-up Manager\n"
        "• Document Admin\n\n"
        "Viņa palīdz mazam uzņēmumam:\n"
        "• turēt kārtībā taskus un termiņus\n"
        "• sekot klientiem un follow-up\n"
        "• palīdzēt ar invoice admin\n"
        "• palīdzēt ar estimate / offer draftiem\n"
        "• sakārtot dokumentus\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_office_manager_agent_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_office_manager_permissions_answer()}"
    )


def build_ninaos_workspace_product_answer():
    return (
        "🏢 NinaOS Small Business Workspace\n\n"
        "Šis ir pirmais workspace tips Nina Office Manager SMB produktam.\n\n"
        "Dashboardam vēlāk jāparāda:\n"
        "• Tasks Today\n"
        "• Follow-ups\n"
        "• Invoices Due\n"
        "• Estimates in Progress\n"
        "• Projects Active\n"
        "• Recent Activities\n"
        "• Exchange Preview\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_small_business_workspace_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_workspace_permissions_answer('demo_small_business')}"
    )


def build_ninaos_exchange_preview_answer():
    return (
        "🛒 NinaOS Exchange Preview\n\n"
        "Exchange ir NinaOS AI darbinieku tirgus.\n\n"
        "Pirmais Exchange katalogs:\n"
        "• Nina Office Manager SMB — aktīvs\n"
        "• Nina Sales — plānots\n"
        "• Nina Estimator — plānots\n"
        "• Nina Finance — plānots\n"
        "• Nina Support — plānots\n\n"
        "Exchange mērķis:\n"
        "• pārdot gatavus AI darbiniekus\n"
        "• ļaut aģentiem sadarboties\n"
        "• veidot bot-to-bot darījumus\n"
        "• pelnīt komisijas NinaOS platformai\n\n"
        f"Versija: {PLATFORM_VISIBILITY_VERSION}"
    )


def route_platform_visibility_command(text: str):
    t = (text or "").strip().lower()

    if t in ["platform status", "ninaos status", "platform"]:
        return build_platform_status_answer()

    if t in ["roles", "role registry", "role status"]:
        return build_roles_answer(include_planned=True)

    if t in ["workers", "agents", "ready workers", "darbinieki"]:
        return build_ninaos_workers_answer()

    if t in ["workspaces", "workspace", "small business workspace"]:
        return build_ninaos_workspace_product_answer()

    if t in ["permissions", "permission status", "tiesības"]:
        return build_permissions_answer()

    if t in ["office manager", "nina office manager", "nina office manager smb"]:
        return build_nina_office_manager_product_answer()

    if t in ["exchange", "nina exchange", "exchange preview"]:
        return build_ninaos_exchange_preview_answer()

    return None


if __name__ == "__main__":
    print(build_platform_status_answer())
