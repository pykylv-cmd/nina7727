# platform_visibility.py
# NinaOS Platform Visibility V1.1
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Make NinaOS Platform Core visible in the product
# - Global-first language support
# - Default product language: English

PLATFORM_VISIBILITY_VERSION = "Platform Visibility V1.1"

try:
    from language_engine import (
        t,
        normalize_language,
        build_office_manager_intro,
        build_exchange_intro,
        route_language_command,
        LANGUAGE_ENGINE_VERSION,
    )
except Exception as e:
    LANGUAGE_ENGINE_VERSION = "Language Engine not connected"

    def normalize_language(language=None):
        return "en"

    def t(key, language=None, fallback=None):
        return fallback if fallback is not None else key

    def build_office_manager_intro(language=None):
        return "🏢 Nina Office Manager SMB\n\nAI office manager for small businesses."

    def build_exchange_intro(language=None):
        return "🛒 NinaOS Exchange Preview\n\nExchange is the marketplace for NinaOS AI workers."

    def route_language_command(text, language=None):
        return None


try:
    from role_registry import (
        role_registry_status,
        build_roles_answer,
        build_composite_workers_answer,
        build_office_manager_smb_answer,
    )
except Exception as e:
    def role_registry_status():
        return f"Role Registry not available: {repr(e)}"

    def build_roles_answer(include_planned=False):
        return f"Role Registry not available: {repr(e)}"

    def build_composite_workers_answer():
        return f"Composite Workers not available: {repr(e)}"

    def build_office_manager_smb_answer():
        return f"Nina Office Manager SMB not available: {repr(e)}"


try:
    from agent_registry import (
        agent_registry_status,
        build_agents_answer,
        build_office_manager_agent_answer,
    )
except Exception as e:
    def agent_registry_status():
        return f"Agent Registry not available: {repr(e)}"

    def build_agents_answer(include_planned=False):
        return f"Agent Registry not available: {repr(e)}"

    def build_office_manager_agent_answer():
        return f"Nina Office Manager Agent not available: {repr(e)}"


try:
    from workspace_engine import (
        workspace_engine_status,
        build_workspaces_answer,
        build_small_business_workspace_answer,
    )
except Exception as e:
    def workspace_engine_status():
        return f"Workspace Engine not available: {repr(e)}"

    def build_workspaces_answer():
        return f"Workspace Engine not available: {repr(e)}"

    def build_small_business_workspace_answer():
        return f"Small Business Workspace not available: {repr(e)}"


try:
    from permission_engine import (
        permission_engine_status,
        build_permissions_answer,
        build_office_manager_permissions_answer,
        build_workspace_permissions_answer,
    )
except Exception as e:
    def permission_engine_status():
        return f"Permission Engine not available: {repr(e)}"

    def build_permissions_answer():
        return f"Permission Engine not available: {repr(e)}"

    def build_office_manager_permissions_answer():
        return f"Office Manager permissions not available: {repr(e)}"

    def build_workspace_permissions_answer(workspace_id):
        return f"Workspace permissions not available: {repr(e)}"


def platform_visibility_status(language="en"):
    lang = normalize_language(language)

    return (
        f"{t('ninaos_platform_visibility', lang)}\n\n"
        f"Version: {PLATFORM_VISIBILITY_VERSION}\n"
        f"Language Engine: {LANGUAGE_ENGINE_VERSION}\n"
        f"{t('platform_visibility_goal', lang)}\n\n"
        f"{t('visible_layers', lang)}\n"
        "• Role Registry\n"
        "• Agent Registry\n"
        "• Workspace Engine\n"
        "• Permission Engine\n"
        "• Nina Office Manager SMB\n"
        "• Language Engine\n\n"
        f"{t('status_active', lang)}"
    )


def build_platform_status_answer(language="en"):
    lang = normalize_language(language)

    return (
        f"{t('ninaos_platform_core_status', lang)}\n\n"
        f"{platform_visibility_status(lang)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{role_registry_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{agent_registry_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{workspace_engine_status()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{permission_engine_status()}"
    )


def build_ninaos_workers_answer(language="en"):
    lang = normalize_language(language)

    return (
        f"{t('ready_workers', lang)}\n\n"
        f"{t('first_strategic_worker', lang)}\n"
        "• Nina Office Manager SMB\n\n"
        f"{t('planned_next_workers', lang)}\n"
        "• Nina Sales\n"
        "• Nina Estimator\n"
        "• Nina Finance\n"
        "• Nina Support\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_agents_answer(include_planned=True)}"
    )


def build_nina_office_manager_product_answer(language="en"):
    lang = normalize_language(language)

    return (
        f"{build_office_manager_intro(lang)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_office_manager_agent_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_office_manager_permissions_answer()}"
    )


def build_ninaos_workspace_product_answer(language="en"):
    lang = normalize_language(language)

    return (
        f"{t('small_business_workspace', lang)}\n\n"
        "This is the first workspace type for Nina Office Manager SMB.\n\n"
        f"{t('dashboard_future_blocks', lang)}\n"
        f"• {t('tasks_today', lang)}\n"
        f"• {t('followups', lang)}\n"
        f"• {t('invoices_due', lang)}\n"
        f"• {t('estimates_in_progress', lang)}\n"
        f"• {t('projects_active', lang)}\n"
        f"• {t('recent_activities', lang)}\n"
        f"• {t('exchange_preview', lang)}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_small_business_workspace_answer()}\n\n"
        "━━━━━━━━━━━━━━\n"
        f"{build_workspace_permissions_answer('demo_small_business')}"
    )


def build_ninaos_exchange_preview_answer(language="en"):
    lang = normalize_language(language)
    return build_exchange_intro(lang)


def route_platform_visibility_command(text: str, language="en"):
    t_raw = (text or "").strip().lower()
    lang = normalize_language(language)

    language_answer = route_language_command(t_raw, lang)
    if language_answer:
        return language_answer

    if t_raw in ["platform status", "ninaos status", "platform"]:
        return build_platform_status_answer(lang)

    if t_raw in ["roles", "role registry", "role status"]:
        return build_roles_answer(include_planned=True)

    if t_raw in ["workers", "agents", "ready workers", "darbinieki"]:
        return build_ninaos_workers_answer(lang)

    if t_raw in ["workspaces", "workspace", "small business workspace"]:
        return build_ninaos_workspace_product_answer(lang)

    if t_raw in ["permissions", "permission status", "tiesības", "tiesibas"]:
        return build_permissions_answer()

    if t_raw in ["office manager", "nina office manager", "nina office manager smb"]:
        return build_nina_office_manager_product_answer(lang)

    if t_raw in ["exchange", "nina exchange", "exchange preview"]:
        return build_ninaos_exchange_preview_answer(lang)

    return None


if __name__ == "__main__":
    print(build_platform_status_answer("en"))
