"""
role_pack.py
NinaOS RolePack System V1

Mērķis:
- pārvērst NinaOS amatus par kontrolējamiem RolePack objektiem;
- noteikt, ko katrs gatavais AI darbinieks drīkst / nedrīkst darīt;
- definēt atļautos failus, toolus, darba objektus, atmiņas robežas un approval gates;
- sagatavot pamatu 10 000+ gataviem amatiem, bez 10 000 atsevišķiem kodiem.

Galvenais likums:
Klients neveido botu no nulles.
Klients izvēlas un saņem gatavu AI darbinieku ar kontrolētu RolePack.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import re

ROLEPACK_SYSTEM_VERSION = "NinaOS RolePack System V1"


@dataclass
class RolePack:
    id: str
    name: str
    category: str
    goal: str
    risk_level: str = "medium"
    allowed_work_objects: List[str] = field(default_factory=list)
    allowed_file_types: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    allowed_memory_scopes: List[str] = field(default_factory=list)
    allowed_actions: List[str] = field(default_factory=list)
    denied_actions: List[str] = field(default_factory=list)
    human_approval_required_for: List[str] = field(default_factory=list)
    exchange_permissions: List[str] = field(default_factory=list)
    output_formats: List[str] = field(default_factory=list)
    audit_required: bool = True
    escalation_rules: List[str] = field(default_factory=list)


ROLE_PACKS: List[RolePack] = [
    RolePack(
        id="role_accountant",
        name="Nina Grāmatvede",
        category="finance",
        goal="Apkopot dokumentus, sagatavot atskaišu melnrakstus, pamanīt trūkstošos dokumentus un sagatavot pārskatus cilvēka pārbaudei.",
        risk_level="high",
        allowed_work_objects=["invoice", "expense", "bank_statement", "report", "document_case", "task"],
        allowed_file_types=["pdf", "excel", "image", "bank_statement", "invoice", "receipt", "csv"],
        allowed_tools=["knowledge_vault", "document_parser", "invoice_reader", "expense_classifier", "report_builder", "missing_docs_checker"],
        allowed_memory_scopes=["workspace_memory", "company_memory", "document_memory", "accounting_period_memory", "audit_memory"],
        allowed_actions=["read_documents", "classify_expenses", "prepare_report_draft", "list_missing_documents", "ask_clarifying_questions"],
        denied_actions=["submit_official_declaration_without_approval", "make_tax_decision", "make_payment", "change_bank_details", "delete_financial_records"],
        human_approval_required_for=["official_submission", "tax_decision", "payment_action", "external_accounting_send"],
        exchange_permissions=["can_buy_document_processing_service_with_approval", "cannot_share_sensitive_financial_data_without_permission"],
        output_formats=["missing_documents_list", "accounting_summary", "report_draft", "questions_to_client"],
        escalation_rules=["ja trūkst dokumentu", "ja ir nodokļu risks", "ja jāiesniedz oficiāla atskaite", "ja vajag maksājumu darbību"],
    ),
    RolePack(
        id="role_estimator",
        name="Nina Tāmētāja",
        category="construction",
        goal="No darba apraksta, bildēm un dokumentiem sagatavot tāmes struktūru, jautājumus, materiālu sarakstu un piedāvājuma melnrakstu.",
        risk_level="medium",
        allowed_work_objects=["estimate", "project", "client", "offer", "task", "material_list"],
        allowed_file_types=["pdf", "image", "excel", "project_file", "measurements", "photo"],
        allowed_tools=["estimate_builder", "material_list", "labor_calculator", "offer_builder", "question_builder", "scope_checker"],
        allowed_memory_scopes=["workspace_memory", "project_memory", "client_memory", "document_memory", "estimate_memory"],
        allowed_actions=["read_project_files", "prepare_estimate_draft", "ask_measurement_questions", "prepare_offer_text", "compare_scope_options"],
        denied_actions=["send_binding_final_price_without_approval", "sign_contract", "promise_legal_terms", "change_company_price_policy"],
        human_approval_required_for=["final_price", "contractual_offer_send", "discount_commitment", "binding_deadline_commitment"],
        exchange_permissions=["can_buy_specialist_estimate_review_with_approval", "can_request_legal_review_with_minimal_data"],
        output_formats=["estimate_draft", "material_list", "missing_measurements", "offer_draft", "client_questions"],
        escalation_rules=["ja trūkst izmēru", "ja cena ir gala juridisks piedāvājums", "ja vajag līguma nosacījumus", "ja darbs ir augsta riska"],
    ),
    RolePack(
        id="role_sales",
        name="Nina Pārdevēja",
        category="sales",
        goal="Vadīt klientu no pieprasījuma līdz piedāvājumam, follow-up, objection handling, closing un deal pipeline.",
        risk_level="medium",
        allowed_work_objects=["lead", "client", "deal", "offer", "followup", "call", "task"],
        allowed_file_types=["pdf", "text", "image", "price_list"],
        allowed_tools=["sales_brain", "work_layer", "followup_engine", "client_work_view", "objection_handler", "call_planner"],
        allowed_memory_scopes=["workspace_memory", "client_memory", "deal_memory", "conversation_memory", "audit_memory"],
        allowed_actions=["prepare_offer_message", "prepare_followup", "prepare_call_plan", "classify_objection", "suggest_next_deal_step"],
        denied_actions=["promise_discount_without_approval", "sign_contract", "send_external_message_without_allowed_channel", "misrepresent_terms"],
        human_approval_required_for=["discount_commitment", "binding_contract", "external_message_send", "price_change"],
        exchange_permissions=["can_buy_lead_enrichment_with_permission", "can_request_estimator_or_legal_bot_with_minimal_data"],
        output_formats=["offer_message", "followup_message", "call_plan", "objection_reply", "deal_next_step"],
        escalation_rules=["ja klients prasa juridisku garantiju", "ja jāmaina cena", "ja jāparaksta līgums", "ja sūdzība ir augsta riska"],
    ),
    RolePack(
        id="role_legal_assistant",
        name="Nina Jurista palīgs",
        category="legal",
        goal="Lasīt līgumus, izcelt riskus, sagatavot jautājumus un dokumentu melnrakstus cilvēka vai jurista pārbaudei.",
        risk_level="high",
        allowed_work_objects=["contract", "case", "document_case", "risk_review", "task"],
        allowed_file_types=["pdf", "word", "text", "contract", "email_thread"],
        allowed_tools=["contract_reader", "risk_extractor", "clause_summary", "draft_builder", "question_builder"],
        allowed_memory_scopes=["workspace_memory", "case_memory", "document_memory", "audit_memory"],
        allowed_actions=["summarize_contract", "extract_risks", "prepare_questions", "prepare_draft", "compare_clauses"],
        denied_actions=["provide_final_legal_advice_without_review", "represent_client_in_court", "submit_official_legal_document_without_approval", "guarantee_legal_outcome"],
        human_approval_required_for=["legal_advice", "official_submission", "contract_send", "high_risk_clause_change"],
        exchange_permissions=["can_sell_risk_review_as_service_if_human_review_required", "can_receive_limited_contract_extracts"],
        output_formats=["risk_list", "contract_summary", "questions_for_lawyer", "draft_document"],
        escalation_rules=["ja ir juridisks risks", "ja dokuments ir oficiāli iesniedzams", "ja klients prasa gala juridisku lēmumu"],
    ),
    RolePack(
        id="role_hr",
        name="Nina HR",
        category="people",
        goal="Palīdzēt ar kandidātiem, interviju jautājumiem, onboarding un iekšējām procedūrām.",
        risk_level="medium",
        allowed_work_objects=["candidate", "interview", "onboarding", "policy", "employee_question", "task"],
        allowed_file_types=["pdf", "word", "cv", "text", "policy_doc"],
        allowed_tools=["candidate_summary", "interview_question_builder", "onboarding_checklist", "policy_answer"],
        allowed_memory_scopes=["workspace_memory", "candidate_memory", "policy_memory", "audit_memory"],
        allowed_actions=["summarize_candidate", "prepare_interview_questions", "prepare_onboarding_plan", "answer_policy_questions"],
        denied_actions=["final_hire_reject_decision", "salary_commitment", "discriminatory_filtering", "share_private_employee_data_without_permission"],
        human_approval_required_for=["hire_reject_decision", "salary_commitment", "disciplinary_action", "sensitive_employee_data_export"],
        exchange_permissions=["can_buy_background_check_service_with_approval", "cannot_share_cv_without_permission"],
        output_formats=["candidate_summary", "interview_questions", "onboarding_plan", "policy_answer"],
        escalation_rules=["ja lēmums ietekmē algu vai pieņemšanu", "ja dati ir sensitīvi", "ja ir juridisks HR risks"],
    ),
    RolePack(
        id="role_project_coordinator",
        name="Nina Projektu koordinators",
        category="operations",
        goal="Sekot projektiem, termiņiem, uzdevumiem, riskiem un nākamajiem soļiem.",
        risk_level="medium",
        allowed_work_objects=["project", "task", "deadline", "risk", "status_report", "resource"],
        allowed_file_types=["pdf", "excel", "text", "image", "project_file"],
        allowed_tools=["task_engine", "daily_brief", "status_report", "risk_watch", "timeline_builder"],
        allowed_memory_scopes=["workspace_memory", "project_memory", "team_memory", "audit_memory"],
        allowed_actions=["prepare_status_report", "prioritize_tasks", "detect_risks", "prepare_next_steps", "ask_team_update"],
        denied_actions=["commit_resources_without_approval", "change_contract_deadline_without_approval", "send_external_status_without_allowed_channel"],
        human_approval_required_for=["resource_commitment", "external_status_send", "deadline_change", "budget_change"],
        exchange_permissions=["can_request_specialist_bot_for_project_task_with_approval"],
        output_formats=["status_report", "risk_list", "task_priority", "next_step_plan"],
        escalation_rules=["ja termiņš kavējas", "ja budžets mainās", "ja vajag cilvēka resursu apstiprinājumu"],
    ),
    RolePack(
        id="role_customer_service",
        name="Nina Klientu serviss",
        category="support",
        goal="Atbildēt uz klientu jautājumiem, šķirot sūdzības, veidot ticketus un eskalēt cilvēkam, ja risks ir augsts.",
        risk_level="medium",
        allowed_work_objects=["ticket", "client", "faq", "complaint", "task", "support_case"],
        allowed_file_types=["pdf", "text", "image", "faq_doc"],
        allowed_tools=["faq_answer", "ticket_router", "complaint_classifier", "sentiment_check", "handoff_builder"],
        allowed_memory_scopes=["workspace_memory", "client_memory", "support_memory", "faq_memory", "audit_memory"],
        allowed_actions=["answer_faq", "create_ticket", "classify_complaint", "prepare_handoff", "ask_clarifying_questions"],
        denied_actions=["approve_refund_without_permission", "admit_legal_liability", "share_private_client_data", "close_high_risk_complaint_without_human"],
        human_approval_required_for=["refund_commitment", "legal_claim", "high_risk_complaint", "public_response"],
        exchange_permissions=["can_request_specialist_answer_with_minimal_data"],
        output_formats=["support_reply", "ticket_summary", "handoff_note", "complaint_risk"],
        escalation_rules=["ja klients draud ar juridisku soli", "ja jāatmaksā nauda", "ja sūdzība ir publiska vai augsta riska"],
    ),
]

ROLE_ALIASES = {
    "gramatvedis": "role_accountant",
    "grāmatvedis": "role_accountant",
    "gramatvede": "role_accountant",
    "grāmatvede": "role_accountant",
    "accountant": "role_accountant",
    "tametajs": "role_estimator",
    "tāmētājs": "role_estimator",
    "tametaja": "role_estimator",
    "tāmētāja": "role_estimator",
    "estimator": "role_estimator",
    "pardevējs": "role_sales",
    "pārdevējs": "role_sales",
    "pardeveja": "role_sales",
    "pārdevēja": "role_sales",
    "sales": "role_sales",
    "jurists": "role_legal_assistant",
    "jurista": "role_legal_assistant",
    "legal": "role_legal_assistant",
    "hr": "role_hr",
    "projektu koordinators": "role_project_coordinator",
    "koordinators": "role_project_coordinator",
    "klientu serviss": "role_customer_service",
    "supports": "role_customer_service",
    "support": "role_customer_service",
}


def _clean(text: str) -> str:
    return str(text or "").strip()


def _lower(text: str) -> str:
    return _clean(text).lower()


def _norm_no_accents(text: str) -> str:
    mapping = str.maketrans({
        "ā": "a", "č": "c", "ē": "e", "ģ": "g", "ī": "i", "ķ": "k", "ļ": "l", "ņ": "n", "š": "s", "ū": "u", "ž": "z",
        "Ā": "a", "Č": "c", "Ē": "e", "Ģ": "g", "Ī": "i", "Ķ": "k", "Ļ": "l", "Ņ": "n", "Š": "s", "Ū": "u", "Ž": "z",
    })
    return _lower(text).translate(mapping)


def _role_to_dict(role: RolePack) -> Dict[str, Any]:
    return asdict(role)


def get_role_pack(role_id_or_name: str) -> Dict[str, Any]:
    raw = _clean(role_id_or_name)
    lower = _lower(raw).strip(" .,!?:;\"'")
    noacc = _norm_no_accents(raw).strip(" .,!?:;\"'")

    if lower in ROLE_ALIASES:
        role_id = ROLE_ALIASES[lower]
        for role in ROLE_PACKS:
            if role.id == role_id:
                return _role_to_dict(role)

    if noacc in ROLE_ALIASES:
        role_id = ROLE_ALIASES[noacc]
        for role in ROLE_PACKS:
            if role.id == role_id:
                return _role_to_dict(role)

    for role in ROLE_PACKS:
        role_blob = " ".join([role.id, role.name, role.category, role.goal]).lower()
        role_blob_noacc = _norm_no_accents(role_blob)
        if lower == role.id.lower() or lower == role.name.lower() or lower in role_blob:
            return _role_to_dict(role)
        if noacc and noacc in role_blob_noacc:
            return _role_to_dict(role)
    return {}


def _extract_role_from_text(text: str) -> Dict[str, Any]:
    raw = _clean(text)
    lower = _lower(raw)

    # Direct aliases anywhere in text.
    for alias in sorted(ROLE_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", _norm_no_accents(lower)) or re.search(rf"\b{re.escape(alias)}\b", lower):
            role = get_role_pack(alias)
            if role:
                return role

    # Fallback after known command prefixes.
    prefixes = [
        "parādi amatu", "paradi amatu", "parādi role", "paradi role", "amats", "role",
        "ko drīkst", "ko drikst", "ko nedrīkst", "ko nedrikst", "kādus failus drīkst", "kadus failus drikst",
        "kādus toolus drīkst", "kadus toolus drikst", "vai", "parādi tiesības", "paradi tiesibas",
    ]
    for prefix in prefixes:
        if lower.startswith(prefix):
            tail = raw[len(prefix):].strip(" .,!?:;\"'")
            for noise in ["nina", "drīkst", "drikst", "nedrīkst", "nedrikst", "tirgoties", "exchange", "failus", "toolus"]:
                tail = re.sub(rf"\b{noise}\b", "", tail, flags=re.IGNORECASE).strip()
            role = get_role_pack(tail)
            if role:
                return role

    return {}


def _bullet_list(items: List[str]) -> List[str]:
    return [f"• {item}" for item in (items or [])] or ["• —"]


def is_rolepack_command(text: str) -> bool:
    lower = _lower(text)
    noacc = _norm_no_accents(text)

    exact = {
        "rolepack", "rolepack status", "role pack", "role pack status",
        "role system", "role status", "amatu statuss", "amati system", "amatu kontrole",
        "role matrix", "amatu matrica", "approval gates", "human approval gates",
    }
    if lower in exact or noacc in exact:
        return True

    starts = [
        "parādi amatu", "paradi amatu", "parādi role", "paradi role",
        "ko drīkst", "ko drikst", "ko nedrīkst", "ko nedrikst",
        "kādus failus drīkst", "kadus failus drikst",
        "kādus toolus drīkst", "kadus toolus drikst",
        "vai nina", "vai grāmatved", "vai gramatved", "vai tāmēt", "vai tamet", "vai jurist",
        "parādi tiesības", "paradi tiesibas",
    ]
    return any(lower.startswith(s) or noacc.startswith(_norm_no_accents(s)) for s in starts)


def rolepack_status_answer() -> str:
    lines = [
        "🧩 NinaOS RolePack System V1 ir aktīvs. ✅",
        "",
        "Ko tas dara:",
        "• pārvērš gatavos AI darbiniekus kontrolējamos amatos;",
        "• nosaka, ko katrs amats drīkst un nedrīkst darīt;",
        "• nosaka failu, toolu, WorkObject un atmiņas robežas;",
        "• nosaka human approval gates augsta riska darbībām;",
        "• sagatavo pamatu 10 000+ amatu kontrolei bez haosa.",
        "",
        "Galvenais likums:",
        "• klients neizveido botu no nulles;",
        "• klients izvēlas un saņem gatavu AI darbinieku;",
        "• RolePack nosaka drošās robežas un darba spējas.",
        "",
        "Komandas:",
        "• role status",
        "• parādi amatu grāmatvedis",
        "• parādi amatu tāmētāja",
        "• ko drīkst Nina Tāmētāja",
        "• ko nedrīkst Nina Jurists",
        "• kādus failus drīkst Nina Grāmatvede",
        "• kādus toolus drīkst Nina Pārdevēja",
        "• vai Nina Jurists drīkst tirgoties exchange",
        "• role matrix",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ]
    return "\n".join(lines)


def role_matrix_answer() -> str:
    lines = [
        "🧩 RolePack matrica V1",
        "",
        "Šī matrica parāda pirmos gatavos amatus un to kontroles režīmu.",
        "",
    ]
    for idx, role in enumerate(ROLE_PACKS, 1):
        lines.append(f"{idx}. {role.name}")
        lines.append(f"   Kategorija: {role.category}")
        lines.append(f"   Risks: {role.risk_level}")
        lines.append(f"   WorkObject: {', '.join(role.allowed_work_objects[:5])}")
        lines.append(f"   Approval gates: {', '.join(role.human_approval_required_for[:4])}")
        lines.append("")
    lines.extend([
        "Likums:",
        "• katrs jauns amats jāievieto šajā modelī;",
        "• amats bez allowed_tools / permissions / approval_gates nav gatavs produkcijai;",
        "• Exchange tiesības vienmēr jānošķir no workspace iekšējām tiesībām.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])
    return "\n".join(lines)


def role_detail_answer(role_name: str) -> str:
    role = get_role_pack(role_name) or _extract_role_from_text(role_name)
    if not role:
        return (
            "🧩 RolePack nav atrasts.\n\n"
            "Pamēģini:\n"
            "• parādi amatu grāmatvedis\n"
            "• parādi amatu tāmētāja\n"
            "• parādi amatu jurists\n\n"
            f"Versija: {ROLEPACK_SYSTEM_VERSION}"
        )

    lines = [
        f"🧩 RolePack — {role['name']}",
        "",
        f"ID: {role['id']}",
        f"Kategorija: {role['category']}",
        f"Riska līmenis: {role['risk_level']}",
        "",
        f"Mērķis: {role['goal']}",
        "",
        "Drīkst darīt:",
        *_bullet_list(role.get("allowed_actions", [])),
        "",
        "Nedrīkst darīt:",
        *_bullet_list(role.get("denied_actions", [])),
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
        "Atmiņas robežas:",
        "• " + ", ".join(role.get("allowed_memory_scopes") or []),
        "",
        "Human approval vajadzīgs:",
        "• " + ", ".join(role.get("human_approval_required_for") or []),
        "",
        "Exchange tiesības:",
        * _bullet_list(role.get("exchange_permissions", [])),
        "",
        "Eskalācija cilvēkam:",
        * _bullet_list(role.get("escalation_rules", [])),
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ]
    return "\n".join(lines)


def allowed_actions_answer(role: Dict[str, Any]) -> str:
    return "\n".join([
        f"✅ Ko drīkst — {role['name']}",
        "",
        "Drīkst:",
        *_bullet_list(role.get("allowed_actions", [])),
        "",
        "Drīkst strādāt ar WorkObject:",
        "• " + ", ".join(role.get("allowed_work_objects") or []),
        "",
        "Drīkst lietot toolus:",
        "• " + ", ".join(role.get("allowed_tools") or []),
        "",
        "Svarīgi:",
        "• šīs tiesības darbojas tikai konkrētā workspace robežās;",
        "• ārēja nosūtīšana, cena, juridisks solījums vai maksājumi iet caur approval gates.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])


def denied_actions_answer(role: Dict[str, Any]) -> str:
    return "\n".join([
        f"⛔ Ko nedrīkst — {role['name']}",
        "",
        "Nedrīkst:",
        *_bullet_list(role.get("denied_actions", [])),
        "",
        "Human approval vajadzīgs:",
        "• " + ", ".join(role.get("human_approval_required_for") or []),
        "",
        "Likums:",
        "• augsta riska darbības nedrīkst iziet bez cilvēka apstiprinājuma;",
        "• katrai šādai darbībai jānonāk AuditLog.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])


def files_answer(role: Dict[str, Any]) -> str:
    return "\n".join([
        f"📁 Failu piekļuve — {role['name']}",
        "",
        "Drīkst lietot failu tipus:",
        "• " + ", ".join(role.get("allowed_file_types") or []),
        "",
        "Atmiņas robežas:",
        "• " + ", ".join(role.get("allowed_memory_scopes") or []),
        "",
        "Drošības likums:",
        "• fails pieder workspace;",
        "• amats redz tikai tam atļautos failus;",
        "• sensitīvu failu nodošana Exchange notiek tikai ar minimālu datu principu un atļauju.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])


def tools_answer(role: Dict[str, Any]) -> str:
    return "\n".join([
        f"🛠 Toolu piekļuve — {role['name']}",
        "",
        "Drīkst lietot toolus:",
        "• " + ", ".join(role.get("allowed_tools") or []),
        "",
        "Human approval vajadzīgs:",
        "• " + ", ".join(role.get("human_approval_required_for") or []),
        "",
        "Likums:",
        "• tool access vienmēr ir piesaistīts RolePack + Workspace + Permission;",
        "• tool, kas var sūtīt ārā ziņu, cenu, līgumu vai maksājumu, prasa approval, ja RolePack tā nosaka.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])


def exchange_permission_answer(role: Dict[str, Any]) -> str:
    allowed = role.get("exchange_permissions") or []
    can_trade = bool(allowed)
    lines = [
        f"🔁 Exchange tiesības — {role['name']}",
        "",
        f"Vai drīkst tirgoties / sadarboties Exchange: {'jā, ar noteikumiem' if can_trade else 'nē / nav definēts V1'}",
        "",
        "Noteikumi:",
        *_bullet_list(allowed),
        "",
        "Obligāti:",
        "• minimālais nepieciešamais datu apjoms;",
        "• workspace permission;",
        "• ExchangeDeal audit log;",
        "• komisijas ieraksts CommissionLedger;",
        "• augsta riska datiem cilvēka apstiprinājums.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ]
    return "\n".join(lines)


def approval_gates_answer() -> str:
    lines = [
        "🛡 Human Approval Gates V1",
        "",
        "Šīs darbības nedrīkst iziet automātiski bez cilvēka apstiprinājuma, ja RolePack tā nosaka.",
        "",
    ]
    for role in ROLE_PACKS:
        lines.append(f"{role.name}:")
        for gate in role.human_approval_required_for:
            lines.append(f"• {gate}")
        lines.append("")
    lines.extend([
        "Platformas likums:",
        "• juridiska, finanšu, maksājumu, gala cenas vai ārējas saistības darbība prasa approval;",
        "• approval jāieraksta AuditLog;",
        "• bez approval AI drīkst sagatavot tikai melnrakstu / ieteikumu.",
        "",
        f"Versija: {ROLEPACK_SYSTEM_VERSION}",
    ])
    return "\n".join(lines)


def build_rolepack_answer(text: str) -> str:
    raw = _clean(text)
    lower = _lower(raw)
    noacc = _norm_no_accents(raw)

    if lower in {"rolepack", "rolepack status", "role pack", "role pack status", "role system", "role status", "amatu statuss", "amatu kontrole"} or noacc in {"rolepack", "rolepack status", "role pack", "role pack status", "role system", "role status", "amatu statuss", "amatu kontrole"}:
        return rolepack_status_answer()

    if lower in {"role matrix", "amatu matrica"} or noacc in {"role matrix", "amatu matrica"}:
        return role_matrix_answer()

    if lower in {"approval gates", "human approval gates", "approval status"}:
        return approval_gates_answer()

    role = _extract_role_from_text(raw)

    if any(noacc.startswith(p) for p in ["ko drikst", "ko drikst nina"]):
        return allowed_actions_answer(role) if role else role_detail_answer(raw)

    if any(noacc.startswith(p) for p in ["ko nedrikst", "ko nedrikst nina"]):
        return denied_actions_answer(role) if role else role_detail_answer(raw)

    if any(noacc.startswith(p) for p in ["kadus failus drikst", "faili", "failu piekluve"]):
        return files_answer(role) if role else role_detail_answer(raw)

    if any(noacc.startswith(p) for p in ["kadus toolus drikst", "kadi tooli", "tooli", "toolu piekluve"]):
        return tools_answer(role) if role else role_detail_answer(raw)

    if "exchange" in noacc and (noacc.startswith("vai") or "tirgot" in noacc):
        return exchange_permission_answer(role) if role else role_detail_answer(raw)

    for prefix in ["parādi amatu", "paradi amatu", "parādi role", "paradi role", "amats", "role"]:
        if lower.startswith(prefix):
            name = raw[len(prefix):].strip(" .,!?:;\"'")
            return role_detail_answer(name)

    if role:
        return role_detail_answer(role.get("name", ""))

    return rolepack_status_answer()
