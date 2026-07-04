"""
platform_core.py
NinaOS Platform Core V1

Mērķis:
- sākt NinaOS pārbūvi no pareizā gala: platformas pamata;
- definēt objektus, uz kuriem vēlāk balstās 10 000+ gatavi AI darbinieki;
- nostiprināt principu: klients neizveido botu no nulles, klients saņem gatavu AI darbinieku;
- sagatavot pamatu Workspace, RolePack, Agent, Permissions, Channels, Billing un Nina Exchange.

Šis modulis šobrīd nemaina datubāzi.
Tas ir V1 platformas shēmas, statusa un kontroles slānis.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

PLATFORM_CORE_VERSION = "NinaOS Platform Core V1"


# -----------------------------------------------------------------------------
# Core data models
# -----------------------------------------------------------------------------

@dataclass
class UserModel:
    id: str
    type: str = "person"
    name: str = ""
    roles: List[str] = field(default_factory=list)


@dataclass
class CompanyModel:
    id: str
    name: str
    industry: str = ""
    owner_user_id: str = ""


@dataclass
class WorkspaceModel:
    id: str
    name: str
    owner_user_id: str = ""
    company_id: str = ""
    workspace_type: str = "private_or_company"


@dataclass
class RolePackModel:
    id: str
    name: str
    category: str
    goal: str
    allowed_work_objects: List[str] = field(default_factory=list)
    allowed_file_types: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    human_approval_required_for: List[str] = field(default_factory=list)
    risk_level: str = "medium"


@dataclass
class AgentModel:
    id: str
    name: str
    workspace_id: str
    role_pack_ids: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    status: str = "ready"


@dataclass
class PermissionModel:
    id: str
    subject_type: str
    subject_id: str
    workspace_id: str
    permission: str
    scope: str = "workspace"
    requires_human_approval: bool = False


@dataclass
class ChannelConnectionModel:
    id: str
    agent_id: str
    channel_type: str
    status: str = "available"


@dataclass
class SubscriptionModel:
    id: str
    workspace_id: str
    plan: str
    active_agents_limit: int = 1
    usage_policy: str = "starter"


@dataclass
class WorkObjectModel:
    id: str
    workspace_id: str
    object_type: str
    title: str
    owner_agent_id: str = ""
    status: str = "open"


# -----------------------------------------------------------------------------
# V1 ready worker / role blueprint
# -----------------------------------------------------------------------------

ROLE_PACKS: List[RolePackModel] = [
    RolePackModel(
        id="role_accountant",
        name="Nina Grāmatvede",
        category="finance",
        goal="Apkopot dokumentus, sagatavot atskaišu melnrakstus un pamanīt trūkstošos grāmatvedības dokumentus.",
        allowed_work_objects=["invoice", "expense", "report", "document_case", "task"],
        allowed_file_types=["pdf", "excel", "image", "bank_statement", "invoice"],
        allowed_tools=["knowledge_vault", "document_parser", "report_builder", "missing_docs_checker"],
        human_approval_required_for=["official_submission", "tax_decision", "payment_action"],
        risk_level="high",
    ),
    RolePackModel(
        id="role_estimator",
        name="Nina Tāmētāja",
        category="construction",
        goal="No darba apraksta, bildēm un dokumentiem sagatavot tāmes struktūru, jautājumus un piedāvājuma melnrakstu.",
        allowed_work_objects=["estimate", "project", "client", "offer", "task"],
        allowed_file_types=["pdf", "image", "excel", "project_file"],
        allowed_tools=["estimate_builder", "material_list", "offer_builder", "question_builder"],
        human_approval_required_for=["final_price", "contractual_offer_send"],
        risk_level="medium",
    ),
    RolePackModel(
        id="role_sales",
        name="Nina Pārdevēja",
        category="sales",
        goal="Vadīt klientu no pieprasījuma līdz piedāvājumam, follow-up, objection handling un closing.",
        allowed_work_objects=["lead", "client", "deal", "offer", "followup", "task"],
        allowed_file_types=["pdf", "text", "image"],
        allowed_tools=["sales_brain", "work_layer", "followup_engine", "client_work_view"],
        human_approval_required_for=["discount_commitment", "binding_contract", "external_message_send"],
        risk_level="medium",
    ),
    RolePackModel(
        id="role_legal_assistant",
        name="Nina Jurista palīgs",
        category="legal",
        goal="Lasīt līgumus, izcelt riskus, sagatavot jautājumus un juridisku dokumentu melnrakstus cilvēka pārbaudei.",
        allowed_work_objects=["contract", "case", "document_case", "task"],
        allowed_file_types=["pdf", "word", "text"],
        allowed_tools=["contract_reader", "risk_extractor", "draft_builder"],
        human_approval_required_for=["legal_advice", "official_submission", "contract_send"],
        risk_level="high",
    ),
    RolePackModel(
        id="role_hr",
        name="Nina HR",
        category="people",
        goal="Palīdzēt ar kandidātiem, interviju jautājumiem, onboarding un iekšējo procedūru atbildēm.",
        allowed_work_objects=["candidate", "interview", "onboarding", "policy", "task"],
        allowed_file_types=["pdf", "word", "cv", "text"],
        allowed_tools=["candidate_summary", "question_builder", "onboarding_checklist"],
        human_approval_required_for=["hire_reject_decision", "salary_commitment"],
        risk_level="medium",
    ),
    RolePackModel(
        id="role_project_coordinator",
        name="Nina Projektu koordinators",
        category="operations",
        goal="Sekot projektiem, termiņiem, uzdevumiem, riskiem un nākamajiem soļiem.",
        allowed_work_objects=["project", "task", "deadline", "risk", "status_report"],
        allowed_file_types=["pdf", "excel", "text", "image"],
        allowed_tools=["task_engine", "daily_brief", "status_report", "risk_watch"],
        human_approval_required_for=["resource_commitment", "external_status_send"],
        risk_level="medium",
    ),
    RolePackModel(
        id="role_customer_service",
        name="Nina Klientu serviss",
        category="support",
        goal="Atbildēt uz klientu jautājumiem, šķirot sūdzības, veidot ticketus un eskalēt cilvēkam, ja risks ir augsts.",
        allowed_work_objects=["ticket", "client", "faq", "complaint", "task"],
        allowed_file_types=["pdf", "text", "image"],
        allowed_tools=["faq_answer", "ticket_router", "complaint_classifier"],
        human_approval_required_for=["refund_commitment", "legal_claim", "high_risk_complaint"],
        risk_level="medium",
    ),
]

PLATFORM_OBJECTS = [
    "User",
    "Company",
    "Workspace",
    "Agent",
    "RolePack",
    "AgentRole",
    "Permission",
    "MemoryScope",
    "KnowledgeVault",
    "WorkObject",
    "ChannelConnection",
    "Subscription",
    "AuditLog",
    "ExchangeListing",
    "ExchangeDeal",
    "CommissionLedger",
]

BUILD_PHASES = [
    "Phase 1 — Platform Core V1",
    "Phase 2 — RolePack System V1",
    "Phase 3 — Ready Worker Catalog V1",
    "Phase 4 — Agent Assignment V1",
    "Phase 5 — Knowledge Vault V1",
    "Phase 6 — Universal Work Objects V1",
    "Phase 7 — Channel Layer V1",
    "Phase 8 — Billing V1",
    "Phase 9 — Nina Exchange V1",
    "Phase 10 — Mobile + Web Product V1",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _clean(text: str) -> str:
    return str(text or "").strip()


def _lower(text: str) -> str:
    return _clean(text).lower()


def _role_lines() -> List[str]:
    lines = []
    for idx, role in enumerate(ROLE_PACKS, 1):
        lines.append(f"{idx}. {role.name} — {role.category} — risks: {role.risk_level}")
        lines.append(f"   Mērķis: {role.goal}")
    return lines


def get_role_pack(role_id_or_name: str) -> Dict[str, Any]:
    needle = _lower(role_id_or_name)
    for role in ROLE_PACKS:
        if needle in [_lower(role.id), _lower(role.name)] or needle in _lower(role.name):
            return asdict(role)
    return {}


# -----------------------------------------------------------------------------
# Command detection
# -----------------------------------------------------------------------------

def is_platform_command(text: str) -> bool:
    lower = _lower(text)
    if lower in {
        "platform",
        "platform status",
        "platform schema",
        "platform core",
        "platform core status",
        "ninaos platform",
        "ninaos platform status",
        "workspaces",
        "workspace status",
        "agents",
        "agent status",
        "roles",
        "role status",
        "amati",
        "permissions status",
        "permission status",
        "tiesības",
        "tiesibu statuss",
        "exchange status",
        "nina exchange status",
    }:
        return True

    starts = [
        "parādi amatu",
        "paradi amatu",
        "parādi role",
        "paradi role",
        "role ",
        "amats ",
    ]
    return any(lower.startswith(s) for s in starts)


# -----------------------------------------------------------------------------
# Answers
# -----------------------------------------------------------------------------

def platform_status_answer() -> str:
    lines = [
        "🧱 NinaOS Platform Core V1 ir aktīvs. ✅",
        "",
        "Galvenais princips:",
        "• klients neizveido botu no nulles;",
        "• klients izvēlas un saņem gatavu AI darbinieku;",
        "• NinaOS kontrolē workspace, amatus, tiesības, kanālus, failus, maksājumus un Exchange.",
        "",
        "Platform Core atbild uz jautājumiem:",
        "• kam pieder AI darbinieks;",
        "• kur glabājas dati;",
        "• kuram workspace dati pieder;",
        "• kurš drīkst ko redzēt;",
        "• kāds amats darbiniekam ir;",
        "• kādi tooli un faili viņam pieejami;",
        "• caur kādu kanālu viņš strādā;",
        "• kā tiek logotas darbības;",
        "• kā par to maksā;",
        "• kā darbinieks var tirgoties Nina Exchange.",
        "",
        "V1 objekti:",
        "• " + ", ".join(PLATFORM_OBJECTS),
        "",
        "Komandas:",
        "• platform status",
        "• platform schema",
        "• roles / amati",
        "• agents",
        "• workspaces",
        "• permissions status",
        "• exchange status",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ]
    return "\n".join(lines)


def platform_schema_answer() -> str:
    lines = [
        "🧱 NinaOS Platform Schema V1",
        "",
        "Datu īpašuma hierarhija:",
        "1. User",
        "2. Company",
        "3. Workspace",
        "4. Agent",
        "5. RolePack / AgentRole",
        "6. Permission / MemoryScope",
        "7. KnowledgeVault / Files",
        "8. WorkObject",
        "9. ChannelConnection",
        "10. Subscription / Billing",
        "11. ExchangeListing / ExchangeDeal / CommissionLedger",
        "12. AuditLog",
        "",
        "Likums:",
        "• nekas nedrīkst būt vienkārši global memory;",
        "• katram datam jāzina owner_user_id, company_id, workspace_id un permissions;",
        "• katrai AI darbībai jābūt audit log;",
        "• augsta riska lomām vajag human approval gates.",
        "",
        "Būvēšanas secība:",
    ]
    for phase in BUILD_PHASES:
        lines.append(f"• {phase}")
    lines.extend(["", f"Versija: {PLATFORM_CORE_VERSION}"])
    return "\n".join(lines)


def roles_answer() -> str:
    lines = [
        "🧩 Ready Worker / RolePack katalogs V1",
        "",
        "Šie nav boti, ko klients pats būvē.",
        "Tie ir gatavi AI darbinieku amati, ko klients izvēlas un saņem.",
        "",
    ]
    lines.extend(_role_lines())
    lines.extend([
        "",
        "Tālāk RolePack sistēma kontrolēs:",
        "• ko katrs amats drīkst darīt;",
        "• kādus failus drīkst lietot;",
        "• kādus toolus drīkst lietot;",
        "• kad jāprasa cilvēka apstiprinājums;",
        "• vai amats drīkst tirgoties Nina Exchange.",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])
    return "\n".join(lines)


def role_detail_answer(role_name: str) -> str:
    role = get_role_pack(role_name)
    if not role:
        return (
            "🧩 RolePack nav atrasts.\n\n"
            "Pamēģini, piemēram:\n"
            "• parādi amatu grāmatvede\n"
            "• parādi amatu tāmētāja\n"
            "• parādi amatu pārdevēja\n\n"
            f"Versija: {PLATFORM_CORE_VERSION}"
        )

    return "\n".join([
        f"🧩 RolePack — {role['name']}",
        "",
        f"ID: {role['id']}",
        f"Kategorija: {role['category']}",
        f"Riska līmenis: {role['risk_level']}",
        "",
        f"Mērķis: {role['goal']}",
        "",
        "Darba objekti:",
        "• " + ", ".join(role.get("allowed_work_objects") or []),
        "",
        "Failu tipi:",
        "• " + ", ".join(role.get("allowed_file_types") or []),
        "",
        "Tooli:",
        "• " + ", ".join(role.get("allowed_tools") or []),
        "",
        "Cilvēka apstiprinājums vajadzīgs:",
        "• " + ", ".join(role.get("human_approval_required_for") or []),
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])


def agents_answer() -> str:
    return "\n".join([
        "🤖 Agent Registry V1 — platformas skats",
        "",
        "V1 princips:",
        "• Agent ir gatavs AI darbinieks, nevis tukšs bots;",
        "• Agent pieder konkrētam Workspace;",
        "• Agent var saturēt vienu vai vairākus RolePack;",
        "• Agent darbojas caur ChannelConnection;",
        "• Agent darbības iet caur Permission un AuditLog.",
        "",
        "Piemēri:",
        "• Nina Grāmatvede = Agent + role_accountant + KnowledgeVault + human approval;",
        "• Nina Tāmētāja = Agent + role_estimator + estimate tools;",
        "• Nina Office Manager = Agent + vairāki RolePack vienlaikus.",
        "",
        "Nākamais modulis pēc Platform Core:",
        "• agent_registry.py",
        "• ready_worker_catalog.py",
        "• agent_assignment.py",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])


def workspaces_answer() -> str:
    return "\n".join([
        "🏢 Workspace Engine V1 — platformas skats",
        "",
        "Workspace ir galvenā datu māja.",
        "",
        "Workspace satur:",
        "• AI darbiniekus;",
        "• failus un KnowledgeVault;",
        "• klientus, projektus, taskus un darījumus;",
        "• kanālu pieslēgumus;",
        "• abonementus;",
        "• audit log;",
        "• Exchange darījumu tiesības.",
        "",
        "Likums:",
        "• visi dati jāglabā ar workspace_id;",
        "• AI darbinieks nedrīkst redzēt ārpus sava workspace bez skaidras atļaujas;",
        "• uzņēmumam un privātpersonai var būt atšķirīgi workspace tipi.",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])


def permissions_status_answer() -> str:
    return "\n".join([
        "🔐 Permission Engine V1 — platformas skats",
        "",
        "Permission nosaka, ko AI darbinieks drīkst darīt.",
        "",
        "Kontroles punkti:",
        "• lasīt failus;",
        "• rakstīt / mainīt WorkObject;",
        "• sūtīt ziņas ārējos kanālos;",
        "• slēgt Exchange darījumus;",
        "• izmantot sensitīvus dokumentus;",
        "• pieprasīt maksājumus;",
        "• eksportēt datus;",
        "• prasīt cilvēka apstiprinājumu augsta riska darbībām.",
        "",
        "Svarīgi:",
        "• grāmatvedim, juristam un maksājumu darbībām jābūt human approval gates;",
        "• Exchange datu nodošanai jābūt minimālai un atļautai;",
        "• katrai darbībai jānonāk AuditLog.",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])


def exchange_status_answer() -> str:
    return "\n".join([
        "🔁 Nina Exchange V1 — platformas virziens",
        "",
        "Nina Exchange nav tikai marketplace.",
        "Tas ir AI darbinieku un botu ekonomikas tirgus.",
        "",
        "Exchange ļaus:",
        "• NinaOS darbiniekiem satikties ar citiem botiem;",
        "• pirkt un pārdot pakalpojumus;",
        "• nodot darbu citam botam;",
        "• apmainīties ar informāciju pēc atļaujām;",
        "• slēgt ExchangeDeal;",
        "• NinaOS ņemt komisiju no darījumiem.",
        "",
        "Obligātie objekti:",
        "• ExchangeListing;",
        "• ExchangeDeal;",
        "• ExchangePermission;",
        "• CommissionLedger;",
        "• Reputation / Trust Score;",
        "• AuditLog.",
        "",
        f"Versija: {PLATFORM_CORE_VERSION}",
    ])


def build_platform_answer(text: str) -> str:
    lower = _lower(text)

    if lower in {"platform", "platform status", "platform core", "platform core status", "ninaos platform", "ninaos platform status"}:
        return platform_status_answer()

    if lower in {"platform schema", "schema", "platformas shēma", "platformas shema"}:
        return platform_schema_answer()

    if lower in {"roles", "role status", "amati"}:
        return roles_answer()

    if lower in {"agents", "agent status"}:
        return agents_answer()

    if lower in {"workspaces", "workspace status"}:
        return workspaces_answer()

    if lower in {"permissions status", "permission status", "tiesības", "tiesibu statuss"}:
        return permissions_status_answer()

    if lower in {"exchange status", "nina exchange status"}:
        return exchange_status_answer()

    for prefix in ["parādi amatu", "paradi amatu", "parādi role", "paradi role", "role", "amats"]:
        if lower.startswith(prefix):
            name = _clean(text[len(prefix):])
            return role_detail_answer(name)

    return platform_status_answer()
