"""Deterministic, fail-closed routing for the ONE NINA Developer surface."""

import re

DEVELOPER_INTENTS = (
    "repository_analysis", "ui_analysis", "architecture_analysis", "risk_analysis",
    "code_search", "diff_request", "release_request",
)


def developer_intents(command):
    normalized = " ".join(str(command or "").strip().casefold().split())
    tokens = set(normalized.replace(":", " ").replace(",", " ").replace(".", " ").split())
    found = []

    def add(intent, condition):
        if condition and intent not in found:
            found.append(intent)

    analytical = any(term in normalized for term in (
        "analiz", "izskaidro", "parādi", "show", "explain", "review", "uzlab", "piedāv",
    ))
    add("repository_analysis", analytical and any(term in normalized for term in (
        "repository", "repo", "projekta fail", "koda bāz",
    )) or any(term in normalized for term in ("git status", "projekta fail")))
    add("ui_analysis", analytical and any(term in normalized for term in (
        " ui", "interfeis", "developer console", "statusu kart", "status card", "lapa",
    )))
    add("architecture_analysis", any(term in normalized for term in (
        "arhitekt", "architecture", "call chain", "message flow", "plūsma", "moduļi", "modules",
    )) or (
        "developer" in normalized and "web research" in normalized
        and any(term in normalized for term in ("kāpēc", "kapec", "why"))
    ))
    add("risk_analysis", any(term in normalized for term in (
        "risks", "risku", "riskanti", "risk analysis", "blakusefekt", "side effect", "regresij",
    )))
    add("code_search", (
        any(term in normalized for term in ("atrodi", "meklē", "search", "find", "kur tiek defin", "where is"))
        and ("_" in normalized or any(term in normalized for term in (
            "kod", "defin", "funkc", "class", "fail", "send_message_to_nina",
        )))
    ))
    add("diff_request", any(term in normalized for term in (
        "diff", "patch", "izmaiņu priekšlik", "proposed change", "sagatavo laboj",
        "prepare change", "sagatavo minim", "minimālo drošo risinājumu", "piedāvā minim",
    )))
    add("release_request", bool(tokens & {
        "release", "deploy", "deployment", "commit", "push", "izlaid", "deployo", "commitot", "pushot",
    }))
    return tuple(intent for intent in DEVELOPER_INTENTS if intent in found)


def developer_command(command):
    """Map an intent to an existing deterministic read-only operation."""
    original = str(command or "").strip()
    normalized = " ".join(original.casefold().split()).rstrip(".?!")
    intents = set(developer_intents(original))
    if "repository_analysis" in intents and "git status" in normalized:
        return "git_status", {}
    if "repository_analysis" in intents and "projekta fail" in normalized:
        return "list_root", {}
    if "code_search" in intents:
        target = re.sub(
            r"^(?:developer:\s*)?(?:atrodi|meklē|find|search)\s+", "", original,
            count=1, flags=re.IGNORECASE,
        ).strip(" .?!")
        return ("search_text", {"query": target}) if target else ("", {})
    return "", {}


def developer_investigation_plan(command):
    """Map analytical intents to existing evidence-backed Developer Brain plans."""
    normalized = " ".join(str(command or "").strip().casefold().split())
    intents = set(developer_intents(command))
    ui_change = "ui_analysis" in intents and (
        "diff_request" in intents or any(term in normalized for term in ("zema riska", "uzlaboj"))
    )
    if ui_change:
        return "developer_status_diff_preview", (
            ("backend_status", "def connection_" + "status", "developer_control.py"),
            ("freshness_gate", "connected = seen >=", "developer_control.py"),
            ("readiness_helper", "def _developer_" + "connection_ready", "web_app.py"),
            ("render_gate", "developer_ready = _developer_" + "connection_ready(connection)", "web_app.py"),
            ("send_gate", "if not _developer_" + "connection_ready(status):", "web_app.py"),
            ("approval_gate", "if not _developer_" + "connection_ready(approval_status):", "web_app.py"),
            ("agent_card", "(\"Local Developer Agent\", \"Connected\"", "web_app.py"),
            ("repository_card", "(\"Repository\", \"Connected\"", "web_app.py"),
            ("regression_test", "def test_repository_disconnected_blocks_" + "diff_approval", "test_admin_developer_console.py"),
        )
    if "architecture_analysis" in intents and "developer console" in normalized:
        return "developer_console_architecture", (
            ("admin_route", "def admin_" + "developer", "web_app.py"),
            ("brain_plan", "def developer_" + "investigation_plan", "developer_router.py"),
            ("brain_answer", "def _developer_" + "investigation_answer", "web_app.py"),
            ("control_plane", "def create_" + "job", "developer_control.py"),
            ("local_agent", "class ReadOnly" + "DeveloperAgent", "nina_developer_agent.py"),
        )
    if ("risk_analysis" in intents and "send_message_to_nina" in normalized
            and "company whatsapp" not in normalized):
        return "send_message_risk_analysis", (
            ("main_definition", "def send_message_" + "to_nina", "nina_message_service.py"),
            ("web_call", "nina_result = send_message_" + "to_nina(", "web_app.py"),
            ("media_call", "return send_message_" + "to_nina(", "nina_media_service.py"),
        )
    if "repository_analysis" in intents and any(term in normalized for term in ("analiz", "izskaidro", "explain")):
        return "repository_structure_analysis", (
            ("web_entry", "def admin_" + "developer", "web_app.py"),
            ("router", "def developer_" + "intents", "developer_router.py"),
            ("control_plane", "def create_" + "job", "developer_control.py"),
            ("local_agent", "class ReadOnly" + "DeveloperAgent", "nina_developer_agent.py"),
        )
    if "code_search" in intents and "send_message_to_nina" in normalized:
        return "send_message_definition", (("main_definition", "def send_message_to_nina", "nina_message_service.py"),)
    if "company whatsapp" in normalized and "architecture_analysis" in intents:
        return "company_whatsapp_flow", (
            ("bridge_event", "messages.upsert", "personal_whatsapp_bridge/src/company_session_manager.js"),
            ("bridge_intake", "export async function processCompanyMessageUpsert", "personal_whatsapp_bridge/src/company_session_manager.js"),
            ("web_endpoint", "def internal_" + "company_whatsapp_inbound", "web_app.py"),
            ("shared_nina_call", "delivery_" + "recipient=sender_jid", "web_app.py"),
            ("shared_definition", "def send_message_to_nina", "nina_message_service.py"),
            ("bridge_reply", "socket.sendMessage(remote", "personal_whatsapp_bridge/src/company_session_manager.js"),
        )
    if "developer" in normalized and "web research" in normalized and (
            "architecture_analysis" in intents or "risk_analysis" in intents):
        return "developer_routing", (
            ("developer_route", "def admin_" + "developer", "web_app.py"),
            ("developer_router", "def developer_" + "command", "developer_router.py"),
            ("generic_nina_call", "nina_result = send_message_" + "to_nina(", "web_app.py"),
            ("research_router", "intent = build_search_" + "plan(clean", "nina_message_service.py"),
        )
    return "", ()
