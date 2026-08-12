"""Deterministic, channel-neutral executive decision core for ONE NINA."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any, Iterable

from business_thinking_models import (
    BusinessDecision, BusinessDecisionContext, BusinessFact, BusinessIntent, BusinessMetric, BusinessResearchResult, BusinessRisk,
    DecisionEvidence, DecisionFrame, DecisionState, EvidenceConfidence, EvidenceKind,
    DecisionEvidenceSet, NextBestAction, Opportunity, Recommendation, ResearchNeed, StrategicOption, StrategicPriority,
)
from competitive_strategy import analyze_competitive_strategy
from research_models import FreshnessRequirement, ResearchDomain


_INTENT_SIGNALS = (
    (BusinessIntent.START_BUSINESS, ("sākt biznes", "start business", "jaunu biznes")),
    (BusinessIntent.GROW_BUSINESS, ("audzēt", "izaugs", "grow", "scale")),
    (BusinessIntent.COMPETE, ("konkur", "compete", "pārspēt")),
    (BusinessIntent.PRICING, ("cen", "pricing", "price")),
    (BusinessIntent.SALES, ("pārdo", "sales")),
    (BusinessIntent.MARKETING, ("mārketing", "marketing")),
    (BusinessIntent.PRODUCT, ("produkt", "product")),
    (BusinessIntent.COST_REDUCTION, ("samazināt izmaks", "cost reduction", "ietaup")),
    (BusinessIntent.INVESTMENT, ("invest", "ieguld")),
    (BusinessIntent.PARTNERSHIP, ("partner", "sadarb")),
    (BusinessIntent.MARKET_ENTRY, ("ieiet tirg", "market entry", "jaunā tirg")),
    (BusinessIntent.OPERATIONS, ("operāc", "operations", "process", "bottleneck")),
)


def classify_business_intent(question: str) -> BusinessIntent:
    folded = str(question or "").casefold()
    return next((intent for intent, tokens in _INTENT_SIGNALS if any(token in folded for token in tokens)), BusinessIntent.GENERAL_DECISION)


def _evidence(rows: Iterable[DecisionEvidence | dict[str, Any]], kind: EvidenceKind) -> tuple[DecisionEvidence, ...]:
    normalized = []
    for row in rows or ():
        if isinstance(row, DecisionEvidence):
            item = row
        else:
            item = DecisionEvidence(
                label=str(row.get("label") or "").strip(), value=str(row.get("value") or "").strip(),
                kind=EvidenceKind(str(row.get("kind") or kind.value)),
                source_reference=str(row.get("source_reference") or "").strip(),
                confidence=EvidenceConfidence(str(row.get("confidence") or "unknown")),
            )
        normalized.append(item if item.kind is kind else DecisionEvidence(
            item.label, item.value, kind, item.source_reference, item.confidence,
        ))
    return tuple(sorted(normalized, key=lambda item: (item.label.casefold(), item.value.casefold())))


def _has(facts: tuple[DecisionEvidence, ...], *tokens: str) -> bool:
    text = " ".join(f"{item.label} {item.value}" for item in facts).casefold()
    return any(token in text for token in tokens)


def _named_competitor(question: str) -> str:
    """Extract a named comparison target without treating generic nouns as names."""
    clean = re.sub(r"\s+", " ", str(question or "")).strip()
    patterns = (
        r"\bpārsp(?:ēt|ētu)\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž.-]*(?:\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž.-]*){0,2})",
        r"\b(?:pret|vs\.?|salīdzinot ar)\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž.-]*(?:\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ][\wĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž.-]*){0,2})",
    )
    for pattern in patterns:
        match = re.search(pattern, clean, re.IGNORECASE)
        if not match:
            continue
        candidate = re.split(r"\s+(?:un|lai|kas|kur|kā|ko)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,.?!")
        if candidate.casefold().split()[0] not in {"konkurents", "konkurentu", "konkurentus", "konkurentiem", "competition", "competitor", "competitors"}:
            return candidate
    return ""


def _research_needs(question: str, intent: BusinessIntent, facts: tuple[DecisionEvidence, ...]) -> tuple[ResearchNeed, ...]:
    needs = []
    competitor = _named_competitor(question) if intent is BusinessIntent.COMPETE else ""
    folded = str(question or "").casefold()
    strategic_growth = intent is BusinessIntent.COMPETE and any(
        token in folded for token in ("stratēģ", "augt", "izaugs", "virzien", "biznesa lēm")
    ) and not competitor
    if competitor and not _has(facts, competitor.casefold(), "competitor", "konkur"):
        for need_question, domain, freshness, why_needed in (
            (f"Ko {competitor} pašlaik piedāvā klientiem?", ResearchDomain.COMPETITOR, FreshnessRequirement.CURRENT,
             "Named competitor offer and customer value must be verified."),
            (f"Kādas ir {competitor} pašreizējās publiskās cenas?", ResearchDomain.COMPETITOR, FreshnessRequirement.CURRENT,
             "Named competitor pricing must be verified, not inferred."),
            (f"Kādas publiski verificējamas {competitor} funkcijas, integrācijas, stiprās puses un ierobežojumi ir būtiski šim lēmumam?",
             ResearchDomain.COMPETITOR, FreshnessRequirement.CURRENT,
             "Capabilities, integrations, strengths and limitations define lawful competitive opportunities."),
        ):
            needs.append(ResearchNeed(need_question, domain, freshness, StrategicPriority.HIGH, why_needed))
    elif strategic_growth:
        for need_question, domain, freshness, why_needed in (
            ("Kuram mērķa klientam un problēmai ir spēcīgākais publiski pierādāmais pieprasījums?", ResearchDomain.MARKET,
             FreshnessRequirement.RECENT, "Target customer and highest-value problem determine strategic focus."),
            ("Kādi diferenciācijas, izplatīšanas, monetizācijas un noturēšanas modeļi darbojas šajā konkurences vidē?",
             ResearchDomain.MARKET, FreshnessRequirement.RECENT,
             "Growth strategy needs evidence about distribution, monetization and retention."),
            ("Kādas konkurentu priekšrocības, tirgus nepilnības un aizsargājamas pozīcijas ir publiski verificējamas?",
             ResearchDomain.COMPETITOR, FreshnessRequirement.CURRENT,
             "Strategy must account for competitor strengths, learning speed and defensibility."),
        ):
            needs.append(ResearchNeed(need_question, domain, freshness, StrategicPriority.HIGH, why_needed))
    if not _has(facts, "customer", "klient", "demand", "piepras"):
        demand_question = (
            "Kādi pierādījumi ir par pieprasījumu pēc AI darbinieku un AI darbaspēka produktiem?"
            if competitor else "Kāds ir pierādītais klientu pieprasījums?"
        )
        needs.append(ResearchNeed(demand_question, ResearchDomain.MARKET,
                                  FreshnessRequirement.RECENT, StrategicPriority.CRITICAL,
                                  "Customer value and demand must be evidenced before committing resources."))
    if not competitor and not strategic_growth and intent in {BusinessIntent.COMPETE, BusinessIntent.PRICING, BusinessIntent.MARKET_ENTRY} and not _has(facts, "competitor", "konkur", "price", "cen"):
        needs.append(ResearchNeed("Kādi ir aktuālie konkurentu piedāvājumi un cenas?", ResearchDomain.COMPETITOR,
                                  FreshnessRequirement.CURRENT, StrategicPriority.HIGH,
                                  "Competitive position and pricing cannot be inferred safely."))
    if intent in {BusinessIntent.START_BUSINESS, BusinessIntent.GROW_BUSINESS, BusinessIntent.INVESTMENT, BusinessIntent.PRICING} and not _has(facts, "economics", "economic", "ekonom", "margin", "revenue", "cost", "izmaks", "ieņēm"):
        needs.append(ResearchNeed("Kāda ir pierādāmā vienības ekonomika un naudas nepieciešamība?", ResearchDomain.MARKET,
                                  FreshnessRequirement.RECENT, StrategicPriority.HIGH,
                                  "Capital allocation requires evidence-backed economics."))
    return tuple(needs)


def _confidence(facts: tuple[DecisionEvidence, ...], needs: tuple[ResearchNeed, ...]) -> EvidenceConfidence:
    if needs:
        return EvidenceConfidence.LOW if facts else EvidenceConfidence.UNKNOWN
    if facts and all(item.confidence is EvidenceConfidence.HIGH for item in facts):
        return EvidenceConfidence.HIGH
    return EvidenceConfidence.MEDIUM if facts else EvidenceConfidence.UNKNOWN


def analyze_business_decision(
    question: str, *, workspace_id: str, contact_id: str,
    objective: str = "", constraints: Iterable[str] = (), known_facts: Iterable[DecisionEvidence | dict[str, Any]] = (),
    assumptions: Iterable[DecisionEvidence | dict[str, Any]] = (), unknowns: Iterable[str] = (),
    time_horizon: str = "", risk_tolerance: str = "", business_context: dict[str, Any] | None = None,
) -> BusinessDecision:
    clean = re.sub(r"\s+", " ", str(question or "")).strip()
    intent = classify_business_intent(clean)
    facts = _evidence(known_facts, EvidenceKind.FACT)
    assumed = _evidence(assumptions, EvidenceKind.ASSUMPTION)
    unknown = tuple(sorted({str(item).strip() for item in unknowns if str(item).strip()}))
    context = BusinessDecisionContext(
        clean, str(workspace_id), str(contact_id), intent, str(objective or clean).strip(),
        tuple(sorted({str(item).strip() for item in constraints if str(item).strip()})), facts, assumed,
        unknown, str(time_horizon), str(risk_tolerance), dict(business_context or {}),
    )
    competitor = _named_competitor(clean) if intent is BusinessIntent.COMPETE else ""
    strategic_growth = intent is BusinessIntent.COMPETE and not competitor and any(
        token in clean.casefold() for token in ("stratēģ", "augt", "izaugs", "virzien", "biznesa lēm")
    )
    if intent is BusinessIntent.COMPETE:
        comparison_unknowns = (
            "NinaOS internal economics, retention and delivery performance",
            "NinaOS capability evidence for a like-for-like comparison",
        )
        unknown = tuple(sorted(set(unknown + comparison_unknowns)))
        context = replace(context, unknowns=unknown)
    needs = _research_needs(clean, intent, facts) if clean else ()
    confidence = _confidence(facts, needs)
    high_downside = bool((business_context or {}).get("high_downside"))
    bottleneck = str((business_context or {}).get("bottleneck") or "Evidence-backed customer validation")
    customer = "Known paying-customer evidence is available." if _has(facts, "customer", "klient") else "Who pays and why they switch remains unknown."
    economics = "Economics are evidence-backed." if _has(facts, "margin", "revenue", "cost", "izmaks", "ieņēm") else "Revenue, margin, acquisition cost and payback remain unknown."
    frame = DecisionFrame(
        context.objective,
        (customer, "Retention requires durable, repeated customer value."),
        ("Validate demand, segment attractiveness, timing and barriers.",),
        ("Compare direct competitors, substitutes, differentiation, distribution and switching costs.",),
        (economics, "Never infer financial numbers without evidence."),
        ("Examine acquisition, conversion, retention, expansion and partnerships.",),
        (f"Current bottleneck: {bottleneck}.", "Prefer fast learning with controlled complexity."),
        ("Assess market, financial, execution, dependency, regulatory, concentration and reputation risk.",),
        ("Use the next euro/hour where expected learning-adjusted value is highest.",),
        ("Evaluate data, workflow lock-in, integrations, brand, distribution, cost and switching advantages.",),
    )
    opportunity_description = (
        f"Pirms konkurences virziena izvēles atrodi likumīgas klientu vērtības nepilnības {competitor} verificētajā piedāvājumā."
        if competitor else
        "Pirms mērogošanas izvēlies fokusētu mērķa klienta, diferenciācijas un izplatīšanas hipotēzi."
        if strategic_growth else
        "Validate the highest-value customer problem before scaling commitment."
    )
    opportunity = Opportunity(
        opportunity_description, "customer_value",
        str((business_context or {}).get("estimated_impact") or "unknown"), confidence,
        tuple(need.question for need in needs), StrategicPriority.HIGH,
        {"customer_value": 3 if _has(facts, "customer", "klient") else None,
         "market_attractiveness": None, "differentiation": None, "economics": None,
         "scalability": None, "defensibility": None, "execution_difficulty": 2,
         "downside_risk": 3 if high_downside else None, "evidence_confidence": 3 if confidence is EvidenceConfidence.HIGH else 1},
    )
    risks = [BusinessRisk(
        "Būtiskie pieņēmumi var būt kļūdaini.", "unknown", "high" if high_downside else "unknown",
        "Run a bounded reversible validation before irreversible commitment.", confidence,
        StrategicPriority.CRITICAL if high_downside else StrategicPriority.HIGH,
    )]
    if needs:
        risks.append(BusinessRisk("Material evidence is missing.", "unknown", "unknown",
                                  "Resolve typed ResearchNeed items.", EvidenceConfidence.HIGH, StrategicPriority.HIGH))
    option_experiment = StrategicOption(
        "Run a reversible customer/economics validation experiment.",
        ("Fast learning", "Controlled downside"), ("May delay full rollout",),
        tuple(need.question for need in needs) or ("Owner-approved experiment boundary",),
        tuple(item.source_reference for item in facts if item.source_reference), "high", StrategicPriority.HIGH,
    )
    option_commit = StrategicOption(
        "Commit resources to full execution.", ("Potentially faster scale",),
        ("Higher irreversible downside", "Assumption exposure"), ("Sufficient evidence", "Owner approval"),
        tuple(item.source_reference for item in facts if item.source_reference), "low", StrategicPriority.LOW if needs or high_downside else StrategicPriority.HIGH,
    )
    state = DecisionState.NEEDS_CLARIFICATION if not clean else (DecisionState.NEEDS_RESEARCH if needs else DecisionState.READY)
    if competitor:
        decision_text = (
            f"Izmanto verificētus pierādījumus par {competitor}, lai izvēlētos vienu aizsargājamu klientu vērtības nišu; neapgalvo, ka NinaOS ir pārāks, kamēr to neapstiprina salīdzināms tests."
        )
    elif strategic_growth:
        decision_text = "Izvēlies fokusētu izaugsmes hipotēzi par mērķa klientu, diferenciāciju un izplatīšanu, pēc tam pārbaudi to ar atgriezenisku tirgus testu."
    else:
        decision_text = "Run the reversible validation first." if needs or high_downside else "Proceed with the evidence-backed option under stated constraints."
    recommendation = Recommendation(
        decision_text,
        ("Prioritizes customer value, fast learning and controlled downside.", f"Execution bottleneck is {bottleneck}."),
        tuple(item.source_reference for item in facts if item.source_reference),
        tuple(item.value for item in assumed), confidence,
        tuple(need.question for need in needs) or ("New contradictory evidence", "Material economics deterioration"),
    )
    if competitor:
        action_text = f"Sagatavo pierādījumos balstītu {competitor} salīdzinājumu par piedāvājumu, cenām, ieviešanu, integrācijām un klientu vērtību, tad izvēlies vienu atgriezenisku diferenciācijas testu."
    elif strategic_growth:
        action_text = "Izvēlies vienu mērķa klienta un izplatīšanas hipotēzi, nosaki noturēšanas signālu un veic mazāko atgriezenisko izaugsmes testu."
    else:
        action_text = "Resolve the highest-priority evidence gap with a bounded validation." if needs else "Execute the recommended option and monitor its stated conditions."
    actions = () if state is DecisionState.NEEDS_CLARIFICATION else (NextBestAction(
        action_text,
        "It unlocks the next decision while limiting irreversible cost.",
        "Faster validated learning; no unsupported monetary estimate.",
        (needs[0].question,) if needs else ("Owner approval",), True, True,
    ),)
    metrics = tuple(BusinessMetric(
        item.label, item.value, "as supplied", item.source_reference, item.confidence,
    ) for item in facts if item.source_reference and any(token in item.label.casefold() for token in ("revenue", "margin", "cost", "price", "ieņēm", "izmaks", "cen")))
    return BusinessDecision(
        context, state, frame,
        tuple(f"Hypothesis: {item.value}" for item in assumed), (opportunity,), tuple(risks),
        (option_experiment, option_commit), recommendation, actions, needs,
        tuple(dict.fromkeys(unknown + tuple(need.question for need in needs))), metrics,
    )


def analyze_business_decision_with_evidence(
    question: str, *, workspace_id: str, contact_id: str,
    research_results: Iterable[BusinessResearchResult] = (),
    competitive_comparison: dict[str, dict[str, Any]] | None = None,
    **kwargs,
) -> BusinessDecision:
    """Recompute a decision using completed, scope-matched BusinessResearchResult facts."""
    initial = analyze_business_decision(
        question, workspace_id=workspace_id, contact_id=contact_id, **kwargs,
    )
    accepted_facts: list[BusinessFact] = []
    unresolved: list[ResearchNeed] = []
    contradictions: list[str] = []
    freshness_gaps: list[str] = []
    result_by_need = {item.research_need: item for item in research_results}
    for need in initial.research_needs:
        result = result_by_need.get(need)
        if result is None or result.workspace_id != workspace_id or result.contact_id != contact_id:
            unresolved.append(need)
            continue
        if result.outcome != "completed" or not result.facts:
            unresolved.append(need)
            freshness_gaps.extend(gap for gap in result.gaps if "freshness" in gap)
            freshness_gaps.append(
                f"research_attempt_failed:{need.question}:{result.failure_reason or result.outcome}"
            )
            continue
        accepted_facts.extend(result.facts)
        contradictions.extend(gap for gap in result.gaps if "contradict" in gap)
    supplied = tuple(kwargs.get("known_facts") or ())
    research_evidence = tuple(
        DecisionEvidence(
            label=fact.fact_type.value, value=fact.statement, kind=EvidenceKind.FACT,
            source_reference=",".join(fact.evidence_ids), confidence=fact.confidence,
        )
        for fact in accepted_facts
    )
    recompute_kwargs = dict(kwargs)
    recompute_kwargs["known_facts"] = supplied + research_evidence
    recomputed = analyze_business_decision(
        question, workspace_id=workspace_id, contact_id=contact_id, **recompute_kwargs,
    )
    still_unresolved = tuple(dict.fromkeys(tuple(unresolved) + tuple(recomputed.research_needs)))
    evidence_set = DecisionEvidenceSet(
        facts=tuple(accepted_facts), unresolved_needs=still_unresolved,
        contradictions=tuple(dict.fromkeys(contradictions)),
        freshness_gaps=tuple(dict.fromkeys(freshness_gaps)),
    )
    confidence = recomputed.recommendation.confidence
    state = recomputed.state
    if still_unresolved:
        state = DecisionState.NEEDS_RESEARCH
        confidence = EvidenceConfidence.LOW if accepted_facts else EvidenceConfidence.UNKNOWN
    if contradictions and confidence is EvidenceConfidence.HIGH:
        confidence = EvidenceConfidence.MEDIUM
    highest_need = still_unresolved[0] if still_unresolved else None
    next_actions = recomputed.next_best_actions
    if highest_need:
        next_actions = (NextBestAction(
            action=f"Verify: {highest_need.question}",
            why_now=highest_need.why_needed,
            expected_value="Resolve the highest-value uncertainty without inventing business facts.",
            required_input=(highest_need.question,), reversible=True, approval_required=True,
        ),)
    recommendation = replace(
        recomputed.recommendation,
        confidence=confidence,
        evidence_basis=tuple(sorted({evidence_id for fact in accepted_facts for evidence_id in fact.evidence_ids})),
        conditions_that_change_decision=tuple(dict.fromkeys(
            recomputed.recommendation.conditions_that_change_decision
            + tuple(need.question for need in still_unresolved)
        )),
    )
    competitive = analyze_competitive_strategy(competitive_comparison or {}) if (
        recomputed.context.intent in {BusinessIntent.COMPETE, BusinessIntent.MARKET_ENTRY}
        or competitive_comparison
    ) else None
    return replace(
        recomputed, state=state, recommendation=recommendation,
        next_best_actions=next_actions, research_needs=still_unresolved,
        missing_information=tuple(dict.fromkeys(
            recomputed.missing_information + tuple(need.question for need in still_unresolved)
        )),
        evidence_set=evidence_set, competitive_analysis=competitive,
    )
