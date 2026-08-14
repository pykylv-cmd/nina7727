"""Typed, deterministic models for ONE NINA business decision intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
import json
from typing import Any

from research_models import FreshnessRequirement, ResearchDomain


class StableEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class BusinessIntent(StableEnum):
    START_BUSINESS = "start_business"
    GROW_BUSINESS = "grow_business"
    COMPETE = "compete"
    PRICING = "pricing"
    SALES = "sales"
    MARKETING = "marketing"
    PRODUCT = "product"
    COST_REDUCTION = "cost_reduction"
    INVESTMENT = "investment"
    PARTNERSHIP = "partnership"
    MARKET_ENTRY = "market_entry"
    OPERATIONS = "operations"
    GENERAL_DECISION = "general_decision"


class DecisionState(StableEnum):
    READY = "ready"
    NEEDS_RESEARCH = "needs_research"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceConfidence(StableEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class StrategicPriority(StableEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceKind(StableEnum):
    FACT = "fact"
    ASSUMPTION = "assumption"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"
    UNKNOWN = "unknown"


class BusinessFactType(StableEnum):
    CUSTOMER = "customer"
    MARKET = "market"
    COMPETITOR = "competitor"
    PRICING = "pricing"
    ECONOMICS = "economics"
    OPERATIONS = "operations"
    RISK = "risk"
    GENERAL = "general"


def _stable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _stable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_stable(item) for item in value]
    return value


class StableModel:
    def to_dict(self) -> dict[str, Any]:
        return _stable(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class DecisionEvidence(StableModel):
    label: str
    value: str
    kind: EvidenceKind
    source_reference: str = ""
    confidence: EvidenceConfidence = EvidenceConfidence.UNKNOWN


@dataclass(frozen=True)
class BusinessDecisionContext(StableModel):
    original_question: str
    workspace_id: str
    contact_id: str
    intent: BusinessIntent
    objective: str
    constraints: tuple[str, ...] = ()
    known_facts: tuple[DecisionEvidence, ...] = ()
    assumptions: tuple[DecisionEvidence, ...] = ()
    unknowns: tuple[str, ...] = ()
    time_horizon: str = ""
    risk_tolerance: str = ""
    business_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class BusinessMetric(StableModel):
    name: str
    value: str
    unit: str
    source_evidence_reference: str
    confidence: EvidenceConfidence


@dataclass(frozen=True)
class Opportunity(StableModel):
    description: str
    value_driver: str
    estimated_impact: str
    confidence: EvidenceConfidence
    evidence_requirements: tuple[str, ...]
    priority: StrategicPriority
    dimensions: dict[str, int | None]


@dataclass(frozen=True)
class BusinessRisk(StableModel):
    description: str
    probability: str
    impact: str
    mitigation: str
    confidence: EvidenceConfidence
    priority: StrategicPriority


@dataclass(frozen=True)
class StrategicOption(StableModel):
    option: str
    upside: tuple[str, ...]
    downside: tuple[str, ...]
    requirements: tuple[str, ...]
    evidence: tuple[str, ...]
    reversibility: str
    priority: StrategicPriority


@dataclass(frozen=True)
class Recommendation(StableModel):
    decision: str
    rationale: tuple[str, ...]
    evidence_basis: tuple[str, ...]
    assumptions: tuple[str, ...]
    confidence: EvidenceConfidence
    conditions_that_change_decision: tuple[str, ...]


@dataclass(frozen=True)
class NextBestAction(StableModel):
    action: str
    why_now: str
    expected_value: str
    required_input: tuple[str, ...]
    reversible: bool
    approval_required: bool


@dataclass(frozen=True)
class ResearchNeed(StableModel):
    question: str
    domain: ResearchDomain
    freshness: FreshnessRequirement
    importance: StrategicPriority
    why_needed: str


@dataclass(frozen=True)
class BusinessFact(StableModel):
    statement: str
    evidence_ids: tuple[str, ...]
    source_links: tuple[str, ...]
    confidence: EvidenceConfidence
    freshness: FreshnessRequirement
    fact_type: BusinessFactType


@dataclass(frozen=True)
class BusinessResearchResult(StableModel):
    research_need: ResearchNeed
    outcome: str
    verified_evidence_ids: tuple[str, ...]
    facts: tuple[BusinessFact, ...]
    source_links: tuple[str, ...]
    confidence: EvidenceConfidence
    gaps: tuple[str, ...]
    failure_reason: str
    workspace_id: str
    contact_id: str


@dataclass(frozen=True)
class DecisionEvidenceSet(StableModel):
    facts: tuple[BusinessFact, ...]
    unresolved_needs: tuple[ResearchNeed, ...]
    contradictions: tuple[str, ...]
    freshness_gaps: tuple[str, ...]


@dataclass(frozen=True)
class DecisionFrame(StableModel):
    objective: str
    customer_value: tuple[str, ...]
    market: tuple[str, ...]
    competition: tuple[str, ...]
    economics: tuple[str, ...]
    growth: tuple[str, ...]
    execution: tuple[str, ...]
    risk: tuple[str, ...]
    capital_allocation: tuple[str, ...]
    moat: tuple[str, ...]


@dataclass(frozen=True)
class BusinessDecision(StableModel):
    context: BusinessDecisionContext
    state: DecisionState
    frame: DecisionFrame
    hypotheses: tuple[str, ...]
    opportunities: tuple[Opportunity, ...]
    risks: tuple[BusinessRisk, ...]
    options: tuple[StrategicOption, ...]
    recommendation: Recommendation
    next_best_actions: tuple[NextBestAction, ...]
    research_needs: tuple[ResearchNeed, ...]
    missing_information: tuple[str, ...]
    metrics: tuple[BusinessMetric, ...] = ()
    evidence_set: DecisionEvidenceSet | None = None
    competitive_analysis: Any = None
