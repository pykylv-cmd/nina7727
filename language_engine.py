# language_engine.py
# NinaOS Language Engine V1.0
# Build target: NinaOS Constitution V4.2
#
# Purpose:
# - Global-first product language layer
# - Default language: English
# - Supported languages: English, Latvian, Russian
# - Prevent mixed-language product UI text
# - Prepare NinaOS for USA / Europe / global market
#
# Safe standalone import. No database required.

from dataclasses import dataclass
from typing import Dict, Optional, List, Any


LANGUAGE_ENGINE_VERSION = "Language Engine V1.0"

DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "lv": "Latviešu",
    "ru": "Русский",
}


@dataclass(frozen=True)
class LanguageProfile:
    language_code: str
    language_name: str
    market_priority: str
    is_default: bool = False
    status: str = "active"


LANGUAGE_PROFILES: Dict[str, LanguageProfile] = {
    "en": LanguageProfile(
        language_code="en",
        language_name="English",
        market_priority="global_default_usa_europe",
        is_default=True,
        status="active",
    ),
    "lv": LanguageProfile(
        language_code="lv",
        language_name="Latviešu",
        market_priority="founder_local_testing",
        is_default=False,
        status="active",
    ),
    "ru": LanguageProfile(
        language_code="ru",
        language_name="Русский",
        market_priority="telegram_europe_cis",
        is_default=False,
        status="active",
    ),
}


# =========================================================
# Product text dictionary
# =========================================================

TEXTS: Dict[str, Dict[str, str]] = {
    # Core product
    "ninaos_platform_core_status": {
        "en": "🌐 NinaOS Platform Core Status",
        "lv": "🌐 NinaOS Platform Core statuss",
        "ru": "🌐 Статус ядра платформы NinaOS",
    },
    "ninaos_platform_visibility": {
        "en": "🌐 NinaOS Platform Visibility",
        "lv": "🌐 NinaOS Platform Visibility",
        "ru": "🌐 Видимость платформы NinaOS",
    },
    "platform_visibility_goal": {
        "en": "Goal: make NinaOS Platform Core visible inside the product.",
        "lv": "Mērķis: padarīt NinaOS Platform Core redzamu produktā.",
        "ru": "Цель: сделать ядро NinaOS видимым внутри продукта.",
    },
    "visible_layers": {
        "en": "Visible layers:",
        "lv": "Redzamie slāņi:",
        "ru": "Видимые слои:",
    },
    "status_active": {
        "en": "Status: active ✅",
        "lv": "Statuss: aktīvs ✅",
        "ru": "Статус: активно ✅",
    },

    # Workers / agents
    "ready_workers": {
        "en": "👥 NinaOS Ready Workers",
        "lv": "👥 NinaOS gatavie darbinieki",
        "ru": "👥 Готовые AI-сотрудники NinaOS",
    },
    "first_strategic_worker": {
        "en": "First strategic ready worker:",
        "lv": "Pirmais stratēģiskais gatavais darbinieks:",
        "ru": "Первый стратегический готовый сотрудник:",
    },
    "planned_next_workers": {
        "en": "Planned next workers:",
        "lv": "Plānotie nākamie darbinieki:",
        "ru": "Следующие запланированные сотрудники:",
    },

    # Office Manager
    "office_manager_title": {
        "en": "🏢 Nina Office Manager SMB",
        "lv": "🏢 Nina Office Manager SMB",
        "ru": "🏢 Nina Office Manager SMB",
    },
    "office_manager_short": {
        "en": "AI office manager for small businesses.",
        "lv": "AI biroja vadītāja mazajiem uzņēmumiem.",
        "ru": "AI-офис-менеджер для малого бизнеса.",
    },
    "office_manager_role_intro": {
        "en": "She combines 5 roles in one ready AI worker:",
        "lv": "Viņa apvieno 5 amatus vienā gatavā AI darbiniekā:",
        "ru": "Она объединяет 5 ролей в одном готовом AI-сотруднике:",
    },
    "office_manager_helps": {
        "en": "She helps a small business:",
        "lv": "Viņa palīdz mazam uzņēmumam:",
        "ru": "Она помогает малому бизнесу:",
    },
    "help_tasks": {
        "en": "keep tasks and deadlines under control",
        "lv": "turēt kārtībā taskus un termiņus",
        "ru": "держать задачи и сроки под контролем",
    },
    "help_followups": {
        "en": "track clients and follow-ups",
        "lv": "sekot klientiem un follow-up",
        "ru": "следить за клиентами и follow-up",
    },
    "help_invoice": {
        "en": "assist with invoice administration",
        "lv": "palīdzēt ar rēķinu administrēšanu",
        "ru": "помогать с администрированием счетов",
    },
    "help_estimate": {
        "en": "assist with estimate and offer drafts",
        "lv": "palīdzēt ar tāmes un piedāvājuma melnrakstiem",
        "ru": "помогать с черновиками смет и предложений",
    },
    "help_documents": {
        "en": "organize documents and files",
        "lv": "sakārtot dokumentus un failus",
        "ru": "организовывать документы и файлы",
    },

    # Role names
    "role_office_manager_core": {
        "en": "Office Manager Core",
        "lv": "Biroja vadības pamatslānis",
        "ru": "Базовый офис-менеджер",
    },
    "role_finance_admin_assistant": {
        "en": "Finance Admin Assistant",
        "lv": "Finanšu administrēšanas asistents",
        "ru": "Финансовый административный ассистент",
    },
    "role_estimating_assistant_basic": {
        "en": "Estimating Assistant Basic",
        "lv": "Tāmēšanas palīgs",
        "ru": "Помощник по сметам",
    },
    "role_client_followup_manager": {
        "en": "Client Follow-up Manager",
        "lv": "Klientu follow-up vadītājs",
        "ru": "Менеджер клиентских follow-up",
    },
    "role_document_admin": {
        "en": "Document Admin",
        "lv": "Dokumentu administrators",
        "ru": "Администратор документов",
    },

    # Workspace / dashboard
    "small_business_workspace": {
        "en": "🏢 NinaOS Small Business Workspace",
        "lv": "🏢 NinaOS mazā uzņēmuma workspace",
        "ru": "🏢 Рабочее пространство малого бизнеса NinaOS",
    },
    "dashboard_future_blocks": {
        "en": "The dashboard will show:",
        "lv": "Dashboard vēlāk rādīs:",
        "ru": "Dashboard будет показывать:",
    },
    "tasks_today": {
        "en": "Tasks Today",
        "lv": "Šodienas taski",
        "ru": "Задачи на сегодня",
    },
    "followups": {
        "en": "Follow-ups",
        "lv": "Follow-up",
        "ru": "Follow-up",
    },
    "invoices_due": {
        "en": "Invoices Due",
        "lv": "Rēķini ar termiņu",
        "ru": "Счета к оплате",
    },
    "estimates_in_progress": {
        "en": "Estimates in Progress",
        "lv": "Tāmes procesā",
        "ru": "Сметы в работе",
    },
    "projects_active": {
        "en": "Active Projects",
        "lv": "Aktīvie projekti",
        "ru": "Активные проекты",
    },
    "recent_activities": {
        "en": "Recent Activities",
        "lv": "Pēdējās aktivitātes",
        "ru": "Последние действия",
    },
    "exchange_preview": {
        "en": "Exchange Preview",
        "lv": "Exchange priekšskatījums",
        "ru": "Предпросмотр Exchange",
    },

    # Exchange
    "exchange_title": {
        "en": "🛒 NinaOS Exchange Preview",
        "lv": "🛒 NinaOS Exchange priekšskatījums",
        "ru": "🛒 Предпросмотр NinaOS Exchange",
    },
    "exchange_description": {
        "en": "Exchange is the marketplace for NinaOS AI workers.",
        "lv": "Exchange ir NinaOS AI darbinieku tirgus.",
        "ru": "Exchange — это рынок AI-сотрудников NinaOS.",
    },
    "first_exchange_catalog": {
        "en": "First Exchange catalog:",
        "lv": "Pirmais Exchange katalogs:",
        "ru": "Первый каталог Exchange:",
    },
    "exchange_goal": {
        "en": "Exchange goal:",
        "lv": "Exchange mērķis:",
        "ru": "Цель Exchange:",
    },
    "exchange_goal_workers": {
        "en": "sell ready AI workers",
        "lv": "pārdot gatavus AI darbiniekus",
        "ru": "продавать готовых AI-сотрудников",
    },
    "exchange_goal_collaboration": {
        "en": "allow agents to collaborate",
        "lv": "ļaut aģentiem sadarboties",
        "ru": "позволять агентам сотрудничать",
    },
    "exchange_goal_bot_deals": {
        "en": "enable bot-to-bot deals",
        "lv": "veidot bot-to-bot darījumus",
        "ru": "создавать bot-to-bot сделки",
    },
    "exchange_goal_commissions": {
        "en": "earn platform commissions for NinaOS",
        "lv": "pelnīt komisijas NinaOS platformai",
        "ru": "зарабатывать комиссии для платформы NinaOS",
    },

    # Common labels
    "version": {
        "en": "Version",
        "lv": "Versija",
        "ru": "Версия",
    },
    "active": {
        "en": "active",
        "lv": "aktīvs",
        "ru": "активно",
    },
    "planned": {
        "en": "planned",
        "lv": "plānots",
        "ru": "запланировано",
    },
}


# =========================================================
# Language helpers
# =========================================================

def normalize_language(language: Optional[str] = None) -> str:
    code = (language or DEFAULT_LANGUAGE or "en").strip().lower()

    aliases = {
        "english": "en",
        "en-us": "en",
        "en_us": "en",
        "usa": "en",
        "us": "en",
        "american": "en",
        "latvian": "lv",
        "latviešu": "lv",
        "latviesu": "lv",
        "lv-lv": "lv",
        "russian": "ru",
        "русский": "ru",
        "ru-ru": "ru",
    }

    code = aliases.get(code, code)

    if code not in SUPPORTED_LANGUAGES:
        return DEFAULT_LANGUAGE

    return code


def t(key: str, language: Optional[str] = None, fallback: Optional[str] = None) -> str:
    lang = normalize_language(language)

    item = TEXTS.get(key)
    if not item:
        return fallback if fallback is not None else key

    if lang in item:
        return item[lang]

    if DEFAULT_LANGUAGE in item:
        return item[DEFAULT_LANGUAGE]

    return fallback if fallback is not None else key


def supported_languages_answer(language: Optional[str] = None) -> str:
    lang = normalize_language(language)

    if lang == "lv":
        return (
            "🌍 NinaOS valodas\n\n"
            "NinaOS ir global-first produkts.\n\n"
            "Galvenā valoda: English\n"
            "Atbalstītās valodas:\n"
            "• en — English\n"
            "• lv — Latviešu\n"
            "• ru — Русский\n\n"
            "Vēlāk pievienosim arī citas valodas pēc tirgus vajadzības.\n\n"
            f"Versija: {LANGUAGE_ENGINE_VERSION}"
        )

    if lang == "ru":
        return (
            "🌍 Языки NinaOS\n\n"
            "NinaOS — global-first продукт.\n\n"
            "Основной язык: English\n"
            "Поддерживаемые языки:\n"
            "• en — English\n"
            "• lv — Latviešu\n"
            "• ru — Русский\n\n"
            "Позже добавим другие языки по потребностям рынка.\n\n"
            f"Версия: {LANGUAGE_ENGINE_VERSION}"
        )

    return (
        "🌍 NinaOS Languages\n\n"
        "NinaOS is a global-first product.\n\n"
        "Default language: English\n"
        "Supported languages:\n"
        "• en — English\n"
        "• lv — Latviešu\n"
        "• ru — Русский\n\n"
        "More languages will be added later based on market demand.\n\n"
        f"Version: {LANGUAGE_ENGINE_VERSION}"
    )


def language_engine_status(language: Optional[str] = None) -> str:
    lang = normalize_language(language)

    if lang == "lv":
        return (
            "🌍 NinaOS Language Engine\n\n"
            f"Versija: {LANGUAGE_ENGINE_VERSION}\n"
            "Default valoda: English\n"
            "Aktīvās valodas: en, lv, ru\n"
            "Tirgus prioritāte: USA / Europe / global B2B\n\n"
            "Statuss: aktīvs ✅"
        )

    if lang == "ru":
        return (
            "🌍 NinaOS Language Engine\n\n"
            f"Версия: {LANGUAGE_ENGINE_VERSION}\n"
            "Язык по умолчанию: English\n"
            "Активные языки: en, lv, ru\n"
            "Приоритет рынка: USA / Europe / global B2B\n\n"
            "Статус: активно ✅"
        )

    return (
        "🌍 NinaOS Language Engine\n\n"
        f"Version: {LANGUAGE_ENGINE_VERSION}\n"
        "Default language: English\n"
        "Active languages: en, lv, ru\n"
        "Market priority: USA / Europe / global B2B\n\n"
        "Status: active ✅"
    )


def detect_language_command(text: str) -> Optional[str]:
    lower = (text or "").strip().lower()

    if lower in ["language", "languages", "valodas", "valoda", "язык", "языки"]:
        return "languages"

    if lower in ["language status", "valodu statuss", "language engine", "язык статус"]:
        return "status"

    return None


def route_language_command(text: str, language: Optional[str] = None) -> Optional[str]:
    cmd = detect_language_command(text)

    if cmd == "languages":
        return supported_languages_answer(language)

    if cmd == "status":
        return language_engine_status(language)

    return None


# =========================================================
# Localized product builders
# =========================================================

def build_office_manager_intro(language: Optional[str] = None) -> str:
    lang = normalize_language(language)

    role_lines = [
        t("role_office_manager_core", lang),
        t("role_finance_admin_assistant", lang),
        t("role_estimating_assistant_basic", lang),
        t("role_client_followup_manager", lang),
        t("role_document_admin", lang),
    ]

    help_lines = [
        t("help_tasks", lang),
        t("help_followups", lang),
        t("help_invoice", lang),
        t("help_estimate", lang),
        t("help_documents", lang),
    ]

    version_label = t("version", lang)

    lines = [
        t("office_manager_title", lang),
        "",
        t("office_manager_short", lang),
        "",
        t("office_manager_role_intro", lang),
    ]

    for role in role_lines:
        lines.append(f"• {role}")

    lines.extend([
        "",
        t("office_manager_helps", lang),
    ])

    for item in help_lines:
        lines.append(f"• {item}")

    lines.extend([
        "",
        f"{version_label}: {LANGUAGE_ENGINE_VERSION}",
    ])

    return "\n".join(lines)


def build_exchange_intro(language: Optional[str] = None) -> str:
    lang = normalize_language(language)
    version_label = t("version", lang)

    lines = [
        t("exchange_title", lang),
        "",
        t("exchange_description", lang),
        "",
        t("first_exchange_catalog", lang),
        "• Nina Office Manager SMB — active",
        "• Nina Sales — planned",
        "• Nina Estimator — planned",
        "• Nina Finance — planned",
        "• Nina Support — planned",
        "",
        t("exchange_goal", lang),
        f"• {t('exchange_goal_workers', lang)}",
        f"• {t('exchange_goal_collaboration', lang)}",
        f"• {t('exchange_goal_bot_deals', lang)}",
        f"• {t('exchange_goal_commissions', lang)}",
        "",
        f"{version_label}: {LANGUAGE_ENGINE_VERSION}",
    ]

    return "\n".join(lines)


def build_workspace_dashboard_labels(language: Optional[str] = None) -> Dict[str, str]:
    lang = normalize_language(language)

    return {
        "tasks_today": t("tasks_today", lang),
        "followups": t("followups", lang),
        "invoices_due": t("invoices_due", lang),
        "estimates_in_progress": t("estimates_in_progress", lang),
        "projects_active": t("projects_active", lang),
        "recent_activities": t("recent_activities", lang),
        "exchange_preview": t("exchange_preview", lang),
    }


def language_engine_schema() -> Dict[str, Any]:
    return {
        "version": LANGUAGE_ENGINE_VERSION,
        "default_language": DEFAULT_LANGUAGE,
        "supported_languages": SUPPORTED_LANGUAGES,
        "language_profiles": {
            code: profile.__dict__
            for code, profile in LANGUAGE_PROFILES.items()
        },
        "text_keys": sorted(TEXTS.keys()),
    }


if __name__ == "__main__":
    print(language_engine_status("en"))
    print()
    print(build_office_manager_intro("en"))
    print()
    print(build_office_manager_intro("lv"))
    print()
    print(build_office_manager_intro("ru"))
