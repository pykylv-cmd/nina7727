"""Typed, persistence-neutral contracts for grounded ONE NINA research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any


class _StableEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ResearchDomain(_StableEnum):
    GENERAL = "general"
    COMPANY = "company"
    COMPETITOR = "competitor"
    MARKET = "market"
    PRICING = "pricing"
    NEWS = "news"
    PRODUCT = "product"
    WEBSITE = "website"
    DOCUMENT = "document"


class FreshnessRequirement(_StableEnum):
    ANY = "any"
    RECENT = "recent"
    CURRENT = "current"


class ResearchJobState(_StableEnum):
    PLANNED = "planned"
    ACQUIRING = "acquiring"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceTrustType(_StableEnum):
    PRIMARY = "primary"
    OFFICIAL = "official"
    REGULATORY = "regulatory"
    NEWS = "news"
    INDUSTRY = "industry"
    COMMERCIAL = "commercial"
    COMMUNITY = "community"
    UNKNOWN = "unknown"


class VerificationState(_StableEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNVERIFIED = "unverified"


class ClaimSupportState(_StableEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class ResearchOutcome(_StableEnum):
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    BUDGET_EXCEEDED = "budget_exceeded"
    VERIFICATION_FAILED = "verification_failed"


def _stable_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_stable_value(item) for item in value]
    if isinstance(value, list):
        return [_stable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stable_value(item) for key, item in sorted(value.items())}
    return value


class StableModel:
    def to_dict(self) -> dict[str, Any]:
        return _stable_value(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ResearchBudget(StableModel):
    max_provider_calls: int
    max_http_requests: int
    max_total_bytes: int
    max_elapsed_seconds: float
    max_evidence_records: int
    cost_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        limits = (
            self.max_provider_calls,
            self.max_http_requests,
            self.max_total_bytes,
            self.max_elapsed_seconds,
            self.max_evidence_records,
        )
        if any(value < 0 for value in limits):
            raise ValueError("research_budget_limit_invalid")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchBudget":
        return cls(**payload)


@dataclass(frozen=True)
class ResearchPlan(StableModel):
    domain: ResearchDomain
    original_query: str
    decomposed_queries: tuple[str, ...]
    freshness: FreshnessRequirement
    minimum_source_count: int
    minimum_distinct_domains: int
    preferred_source_types: tuple[SourceTrustType, ...]
    preferred_domains: tuple[str, ...]
    output_requirement: str
    clarification_state: str
    budget: ResearchBudget

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchPlan":
        data = dict(payload)
        data["domain"] = ResearchDomain(data["domain"])
        data["freshness"] = FreshnessRequirement(data["freshness"])
        data["decomposed_queries"] = tuple(data.get("decomposed_queries") or ())
        data["preferred_source_types"] = tuple(SourceTrustType(item) for item in data.get("preferred_source_types") or ())
        data["preferred_domains"] = tuple(data.get("preferred_domains") or ())
        data["budget"] = ResearchBudget.from_dict(data["budget"])
        return cls(**data)


@dataclass(frozen=True)
class EvidenceFragment(StableModel):
    fragment_id: str
    text: str
    evidence_id: str
    source_url: str
    location: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceFragment":
        return cls(**payload)


@dataclass(frozen=True)
class EvidenceRecord(StableModel):
    evidence_id: str
    canonical_url: str
    final_url: str
    title: str
    domain: str
    source_trust_type: SourceTrustType
    publication_date: str
    fetched_at: str
    content_hash: str
    fragments: tuple[EvidenceFragment, ...]
    verification_state: VerificationState
    rejection_reason: str
    provider_provenance: dict[str, Any]
    freshness: FreshnessRequirement = FreshnessRequirement.ANY
    workspace_id: str = ""
    contact_id: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRecord":
        data = dict(payload)
        data["source_trust_type"] = SourceTrustType(data["source_trust_type"])
        data["verification_state"] = VerificationState(data["verification_state"])
        data["freshness"] = FreshnessRequirement(data.get("freshness", "any"))
        data["fragments"] = tuple(EvidenceFragment.from_dict(item) for item in data.get("fragments") or ())
        return cls(**data)


@dataclass(frozen=True)
class ClaimEvidence(StableModel):
    claim_id: str
    claim_text: str
    evidence_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]
    support_state: ClaimSupportState

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClaimEvidence":
        data = dict(payload)
        data["evidence_ids"] = tuple(data.get("evidence_ids") or ())
        data["fragment_ids"] = tuple(data.get("fragment_ids") or ())
        data["support_state"] = ClaimSupportState(data["support_state"])
        return cls(**data)


@dataclass(frozen=True)
class ResearchResult(StableModel):
    state: ResearchJobState
    outcome: ResearchOutcome
    plan: ResearchPlan
    evidence: tuple[EvidenceRecord, ...]
    failures: tuple[dict[str, Any], ...]
    gaps: tuple[str, ...]
    provider_calls: int
    http_requests: int
    total_bytes: int
    elapsed_seconds: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchResult":
        data = dict(payload)
        data["state"] = ResearchJobState(data["state"])
        data["outcome"] = ResearchOutcome(data["outcome"])
        data["plan"] = ResearchPlan.from_dict(data["plan"])
        data["evidence"] = tuple(EvidenceRecord.from_dict(item) for item in data.get("evidence") or ())
        data["failures"] = tuple(data.get("failures") or ())
        data["gaps"] = tuple(data.get("gaps") or ())
        return cls(**data)


@dataclass(frozen=True)
class VerifiedSourceLink(StableModel):
    title: str
    url: str
    evidence_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    source_trust_type: SourceTrustType

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VerifiedSourceLink":
        data = dict(payload)
        data["evidence_ids"] = tuple(data.get("evidence_ids") or ())
        data["claim_ids"] = tuple(data.get("claim_ids") or ())
        data["source_trust_type"] = SourceTrustType(data["source_trust_type"])
        return cls(**data)


@dataclass(frozen=True)
class GroundedResearchAnswer(StableModel):
    summary: str
    findings: tuple[str, ...]
    claims: tuple[ClaimEvidence, ...]
    risks_or_gaps: tuple[str, ...]
    source_links: tuple[VerifiedSourceLink, ...]
    evidence_ids_used: tuple[str, ...]
    outcome: ResearchOutcome
    freshness_note: str
    insufficient_evidence: bool

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GroundedResearchAnswer":
        data = dict(payload)
        data["findings"] = tuple(data.get("findings") or ())
        data["claims"] = tuple(ClaimEvidence.from_dict(item) for item in data.get("claims") or ())
        data["risks_or_gaps"] = tuple(data.get("risks_or_gaps") or ())
        data["source_links"] = tuple(VerifiedSourceLink.from_dict(item) for item in data.get("source_links") or ())
        data["evidence_ids_used"] = tuple(data.get("evidence_ids_used") or ())
        data["outcome"] = ResearchOutcome(data["outcome"])
        return cls(**data)
