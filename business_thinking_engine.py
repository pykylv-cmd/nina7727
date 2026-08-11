"""Deterministic, channel-neutral executive decision core for ONE NINA."""

from __future__ import annotations

import re
from typing import Any, Iterable

from business_thinking_models import (
    BusinessDecision, BusinessDecisionContext, BusinessIntent, BusinessMetric, BusinessRisk,
    DecisionEvidence, DecisionFrame, DecisionState, EvidenceConfidence, EvidenceKind,
    NextBestAction, Opportunity, Recommendation, ResearchNeed, StrategicOption, StrategicPriority,
)
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


def _research_needs(intent: BusinessIntent, facts: tuple[DecisionEvidence, ...]) -> tuple[ResearchNeed, ...]:
    needs = []
    if not _has(facts, "customer", "klient", "demand", "piepras"):
        needs.append(ResearchNeed("Kāds ir pierādītais klientu pieprasījums?", ResearchDomain.MARKET,
                                  FreshnessRequirement.RECENT, StrategicPriority.CRITICAL,
                                  "Customer value and demand must be evidenced before committing resources."))
    if intent in {BusinessIntent.COMPETE, BusinessIntent.PRICING, BusinessIntent.MARKET_ENTRY} and not _has(facts, "competitor", "konkur", "price", "cen"):
        needs.append(ResearchNeed("Kādi ir aktuālie konkurentu piedāvājumi un cenas?", ResearchDomain.COMPETITOR,
                                  FreshnessRequirement.CURRENT, StrategicPriority.HIGH,
                                  "Competitive position and pricing cannot be inferred safely."))
    if intent in {BusinessIntent.START_BUSINESS, BusinessIntent.GROW_BUSINESS, BusinessIntent.INVESTMENT, BusinessIntent.PRICING} and not _has(facts, "margin", "revenue", "cost", "izmaks", "ieņēm"):
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
    needs = _research_needs(intent, facts) if clean else ()
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
    opportunity = Opportunity(
        "Validate the highest-value customer problem before scaling commitment.", "customer_value",
        str((business_context or {}).get("estimated_impact") or "unknown"), confidence,
        tuple(need.question for need in needs), StrategicPriority.HIGH,
        {"customer_value": 3 if _has(facts, "customer", "klient") else None,
         "market_attractiveness": None, "differentiation": None, "economics": None,
         "scalability": None, "defensibility": None, "execution_difficulty": 2,
         "downside_risk": 3 if high_downside else None, "evidence_confidence": 3 if confidence is EvidenceConfidence.HIGH else 1},
    )
    risks = [BusinessRisk(
        "Material assumptions may be wrong.", "unknown", "high" if high_downside else "unknown",
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
    decision_text = "Run the reversible validation first." if needs or high_downside else "Proceed with the evidence-backed option under stated constraints."
    recommendation = Recommendation(
        decision_text,
        ("Prioritizes customer value, fast learning and controlled downside.", f"Execution bottleneck is {bottleneck}."),
        tuple(item.source_reference for item in facts if item.source_reference),
        tuple(item.value for item in assumed), confidence,
        tuple(need.question for need in needs) or ("New contradictory evidence", "Material economics deterioration"),
    )
    actions = () if state is DecisionState.NEEDS_CLARIFICATION else (NextBestAction(
        "Resolve the highest-priority evidence gap with a bounded validation." if needs else "Execute the recommended option and monitor its stated conditions.",
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
