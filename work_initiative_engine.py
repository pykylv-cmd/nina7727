"""Deterministic initiative analysis for the shared ONE NINA runtime."""

from __future__ import annotations

import re
from typing import Mapping

from capability_registry import CapabilityId, CapabilityState, get_capability_registry
from work_initiative_models import (
    CapabilityAnswer, InitiativeDecision, NextBestWork, ProposedWork,
    UserGoal, WorkInitiativeResult,
)


def _fold(value: str) -> str:
    table = str.maketrans("āčēģīķļņšūž", "acegiklnsuz")
    return " ".join(str(value or "").casefold().translate(table).split())


def _capability_query(text: str) -> bool:
    return any(phrase in text for phrase in (
        "ko tu vari", "ko vari man", "kur tevi var", "kapec man tevi",
        "ko tu vari izdarit", "ko vari izdarit", "mana firma", "mana vieta",
    ))


def _capability_answer(registry) -> CapabilityAnswer:
    now, connection, unavailable = [], [], []
    for descriptor in registry.values():
        description = descriptor.safe_user_description
        if not description:
            continue
        if descriptor.state in {CapabilityState.AVAILABLE, CapabilityState.AVAILABLE_WITH_APPROVAL}:
            now.append(description + (" (ar apstiprinājumu)" if descriptor.approval_required else ""))
        elif descriptor.state == CapabilityState.REQUIRES_CONNECTION:
            connection.append(description)
        elif descriptor.state == CapabilityState.NOT_IMPLEMENTED:
            unavailable.append(description)
        elif descriptor.state == CapabilityState.DEGRADED:
            unavailable.append(description + " (runtime pašlaik nav gatavs)")
    return CapabilityAnswer(tuple(now), tuple(connection), tuple(unavailable), "Sāktu ar vienu reālu biznesa vai darba mērķi un sagatavotu pirmo izmērāmo rezultātu.")


def _project_kind(text: str) -> str:
    if "youtube" in text or "kanal" in text:
        return "youtube_business"
    if "ninaos" in text:
        return "ninaos"
    if any(token in text for token in ("partikas biznes", "autoservis", "e-veikal", "biznesu")):
        return "business_launch"
    return ""


def _proof_mode(text: str) -> bool:
    return any(phrase in text for phrase in (
        "pieradi ko maki", "paradi ko vari", "gribu tevi pardot",
        "atrast klient", "atrodi klient", "uzticet savu biznesu",
    ))


def _context_followup(text: str, previous_context: Mapping[str, str]) -> bool:
    return bool(previous_context and (
        re.match(r"^(?:lokacija|vieta)\b", text)
        or len(text.split()) <= 9 and any(
            re.search(rf"\b{token}\b", text)
            for token in ("riga", "bernu", "multenes", "saturs", "aktivs")
        )
    ))


def analyze_work_initiative(
    user_text: str,
    *,
    previous_context: Mapping[str, str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> WorkInitiativeResult:
    clean = str(user_text or "").strip()
    text = _fold(clean)
    context = dict(previous_context or {})
    registry = get_capability_registry(environment)

    if _context_followup(text, context):
        objective = context.get("objective", "Turpināt iepriekšējo mērķi")
        project = context.get("project_kind", "")
        known = tuple(filter(None, (context.get("known_context", ""), clean)))
        goal = UserGoal(clean, objective, scope=project, business_context=clean, known_context=known)
        work = ProposedWork("Atjaunināt projekta kontekstu", objective, "project_context", "Jaunā detaļa precizē esošo projektu", (CapabilityId.MEMORY.value, CapabilityId.WORK_OBJECTS.value), expected_output="Precizēts nākamais projekta solis")
        update = {**context, "known_context": " | ".join(known)}
        return WorkInitiativeResult(goal, InitiativeDecision(True, "context_continuation", .97, True), (work,), NextBestWork(work, "Saglabā darba nepārtrauktību", True), project_candidate=bool(project), context_update=update)

    project_kind = _project_kind(text)
    proof = _proof_mode(text)
    durable = bool(project_kind and any(token in text for token in ("gribu", "uzsakt", "uztaisit", "atvert", "palaist", "pabeigt")))
    email_question = "e-past" in text and any(token in text for token in ("atbild", "mana vieta", "vari"))
    calendar_question = "kalendar" in text and any(token in text for token in ("sakartot", "plan", "vari"))
    if (_capability_query(text) and not email_question) or "kur tevi var integret" in text:
        answer = _capability_answer(registry)
        goal = UserGoal(clean, "Saprast Nina reālās iespējas", scope="capability_discovery")
        work = ProposedWork("Pirmais pierādāmais darbs", "Izvēlēties un paveikt vienu reālu darbu", "capability_demo", "Rezultāts parāda vērtību labāk par funkciju sarakstu", (CapabilityId.WORK_OBJECTS.value,), expected_output="Viens izmērāms darba rezultāts")
        return WorkInitiativeResult(goal, InitiativeDecision(True, "capability_question", .99, True), (work,), NextBestWork(work, "Ātrākais ceļš uz praktisku vērtību", True), answer, response_kind="capability")
    if not durable and not proof and not email_question and not calendar_question:
        return WorkInitiativeResult(UserGoal(clean, ""), InitiativeDecision(False, "no_durable_actionable_goal", .9, False))

    if calendar_question:
        work = ProposedWork(
            "Sagatavot kalendāra plānu", "Sakārtot datumus, adreses un prioritātes",
            "calendar_plan", "Plānu var sagatavot bez ārējas kalendāra mutācijas",
            (CapabilityId.DOCUMENT_GENERATION.value,), required_inputs=("datumi un prioritātes",),
            expected_output="Strukturēts kalendāra plāns",
        )
        return WorkInitiativeResult(
            UserGoal(clean, "Sakārtot kalendāra plānu", scope="calendar"),
            InitiativeDecision(True, "calendar_capability", .99, True),
            (work,), NextBestWork(work, "Plānošana ir pieejama bez ārējas darbības", True),
            response_kind="calendar",
        )

    if email_question:
        email = registry[CapabilityId.EMAIL_SEND]
        work = ProposedWork("Sagatavot e-pasta atbildi", "Sagatavot drošu atbildes melnrakstu", "email_draft", "Melnrakstu var sagatavot bez ārējas nosūtīšanas", (CapabilityId.EMAIL_DRAFT.value,), required_inputs=("e-pasta saturs",), expected_output="Gatavs atbildes melnraksts")
        blocked = email.state == CapabilityState.REQUIRES_CONNECTION
        return WorkInitiativeResult(UserGoal(clean, "Atbildēt e-pastā", scope="email"), InitiativeDecision(True, "email_capability", .99, True, requires_connection=blocked, requires_approval=True), (work,), NextBestWork(work, "Melnrakstu var sagatavot uzreiz", True, "Ielīmē e-pastu, uz kuru jāatbild."), response_kind="email")

    if proof:
        objective = "Pierādīt NinaOS vērtību ar reālu klientu izpētes darbu"
        works = (
            ProposedWork("Definēt mērķa klienta hipotēzi", objective, "analysis", "Dod skaidru pārbaudes fokusu", (CapabilityId.BUSINESS_THINKING.value,), expected_output="Mērķa klienta hipotēze"),
            ProposedWork("Izpētīt potenciālos klientus", objective, "research", "Publiski verificēts kandidātu saraksts rada demonstrējamu vērtību", (CapabilityId.WEB_RESEARCH.value,), expected_output="Verificēts klientu segments un kandidāti"),
            ProposedWork("Sagatavot outreach un follow-up plānu", objective, "work_plan", "Pārvērš izpēti izpildāmā darbā", (CapabilityId.DOCUMENT_GENERATION.value, CapabilityId.TASKS.value), approval_required=True, expected_output="Outreach melnraksti un follow-up plāns"),
        )
        return WorkInitiativeResult(UserGoal(clean, objective, scope="proof_of_value"), InitiativeDecision(True, "proof_mode", .98, True), works, NextBestWork(works[1], "Var sākt ar publisku izpēti bez ārējas darbības", True), response_kind="proof", use_business_thinking=True, use_research=True, context_update={"objective": objective, "project_kind": "proof_of_value", "known_context": clean})

    business_objective = (
        "Izveidot dzīvotspējīgu pārtikas biznesu" if "partikas biznes" in text else
        "Atvērt dzīvotspējīgu autoservisu" if "autoservis" in text else
        "Palaist dzīvotspējīgu e-veikalu" if "e-veikal" in text else
        "Izveidot dzīvotspējīgu biznesu"
    )
    objective = {
        "youtube_business": "Izveidot un attīstīt YouTube biznesu",
        "ninaos": "Pabeigt NinaOS",
        "business_launch": business_objective,
    }.get(project_kind, clean)
    if project_kind == "youtube_business":
        works = (
            ProposedWork("Izpētīt nišas un auditoriju", objective, "research", "Samazina minējumus pirms satura ieguldījuma", (CapabilityId.WEB_RESEARCH.value, CapabilityId.BUSINESS_THINKING.value), expected_output="Nišu, auditoriju un konkurentu salīdzinājums"),
            ProposedWork("Izveidot monetizācijas un satura stratēģiju", objective, "strategy", "Savieno saturu ar biznesa rezultātu", (CapabilityId.BUSINESS_THINKING.value,), expected_output="Monetizācijas un satura plāns"),
            ProposedWork("Sakārtot pirmo 30 dienu darba plānu", objective, "project_plan", "Pārvērš ideju izpildāmos soļos", (CapabilityId.WORK_OBJECTS.value, CapabilityId.TASKS.value), expected_output="Pirmie 3–5 darba posmi"),
        )
    elif project_kind == "ninaos":
        works = (
            ProposedWork("Noteikt NinaOS tuvāko pabeigšanas atskaites punktu", objective, "project_plan", "Fokuss pasargā no nesaistītu darbu pabeigšanas", (CapabilityId.WORK_OBJECTS.value,), expected_output="Tuvākais atskaites punkts un prioritātes"),
            ProposedWork("Sakārtot atlikušos NinaOS darbus", objective, "task_plan", "Veido vienu canonical darba patiesību", (CapabilityId.TASKS.value, CapabilityId.WORK_OBJECTS.value), expected_output="Prioritizēts darbu saraksts"),
        )
    else:
        works = (
            ProposedWork("Izpētīt tirgu un konkurentus", objective, "research", "Pirms ieguldījuma vajag publiskus pierādījumus", (CapabilityId.WEB_RESEARCH.value,), expected_output="Tirgus un konkurentu kopsavilkums"),
            ProposedWork("Izvērtēt biznesa modeli", objective, "strategy", "Nosaka vērtību, riskus un monetizāciju", (CapabilityId.BUSINESS_THINKING.value,), expected_output="Biznesa modeļa varianti un rekomendācija"),
            ProposedWork("Izveidot pirmo projekta plānu", objective, "project_plan", "Pārvērš mērķi izpildāmos posmos", (CapabilityId.WORK_OBJECTS.value, CapabilityId.TASKS.value), expected_output="Pirmie 3–5 darba posmi"),
        )
    update = {"objective": objective, "project_kind": project_kind, "known_context": clean}
    return WorkInitiativeResult(UserGoal(clean, objective, scope=project_kind, known_context=(clean,), missing_context=("private preferences",)), InitiativeDecision(True, "durable_project_goal", .96, True), works, NextBestWork(works[0], "Drošākais augstas vērtības sākums ir atgriezeniska izpēte vai strukturēšana", True), project_candidate=True, use_business_thinking=project_kind in {"business_launch", "youtube_business"}, use_research=True, context_update=update)
