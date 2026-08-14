"""Deterministic evidence enforcement for ONE NINA research."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
import time
from typing import Iterable
from urllib import parse

from research_models import (
    ClaimEvidence,
    ClaimSupportState,
    EvidenceFragment,
    EvidenceRecord,
    FreshnessRequirement,
    ResearchBudget,
    SourceTrustType,
    VerificationState,
)


VERIFIED_PROVENANCE = frozenset({"parsed_html", "search_provider", "parsed_search_html", "direct_user_url"})
SOURCE_TRUST_RANK = {
    SourceTrustType.PRIMARY: 0,
    SourceTrustType.OFFICIAL: 0,
    SourceTrustType.REGULATORY: 0,
    SourceTrustType.NEWS: 1,
    SourceTrustType.INDUSTRY: 1,
    SourceTrustType.COMMERCIAL: 2,
    SourceTrustType.COMMUNITY: 3,
    SourceTrustType.UNKNOWN: 4,
}


class EvidenceContractError(ValueError):
    pass


class ResearchBudgetExceeded(EvidenceContractError):
    pass


def canonicalize_url(value: str) -> str:
    parsed = parse.urlsplit(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EvidenceContractError("verified_https_url_required")
    try:
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise EvidenceContractError("verified_url_host_invalid") from exc
    if not host or parsed.port not in (None, 443):
        raise EvidenceContractError("verified_url_port_invalid")
    path = parsed.path or "/"
    netloc = host
    return parse.urlunsplit(("https", netloc, path, parsed.query, ""))


def stable_content_hash(content: str | bytes) -> str:
    raw = content if isinstance(content, bytes) else str(content or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _trust_type(value: object) -> SourceTrustType:
    try:
        return SourceTrustType(str(value or "unknown").lower())
    except ValueError:
        return SourceTrustType.UNKNOWN


def _freshness(value: object) -> FreshnessRequirement:
    folded = str(value or "").lower()
    if folded in {"current", "today", "now"}:
        return FreshnessRequirement.CURRENT
    if folded in {"recent", "week", "month"}:
        return FreshnessRequirement.RECENT
    return FreshnessRequirement.ANY


def evidence_record_from_verified_result(
    result: dict,
    *,
    workspace_id: str = "",
    contact_id: str = "",
) -> EvidenceRecord:
    item = dict(result or {})
    provenance = str(item.get("source_url_provenance") or "")
    verified_id = str(item.get("verified_result_id") or "")
    if item.get("source_url_verified") is not True or provenance not in VERIFIED_PROVENANCE or not verified_id:
        raise EvidenceContractError("verified_result_provenance_required")
    canonical_url = canonicalize_url(item.get("source_url") or "")
    final_url = canonicalize_url(item.get("final_url") or canonical_url)
    title = str(item.get("page_title") or item.get("title") or "unknown").strip()[:500] or "unknown"
    content = str(item.get("main_text") or item.get("extracted_snippet") or item.get("description_summary") or "")
    content_hash = str(item.get("content_hash") or stable_content_hash(content))
    evidence_id = "evidence_" + hashlib.sha256((verified_id + "\n" + canonical_url + "\n" + content_hash).encode()).hexdigest()[:32]
    fragments = ()
    if content:
        fragment_id = "fragment_" + hashlib.sha256((evidence_id + "\n" + content).encode()).hexdigest()[:32]
        fragments = (EvidenceFragment(fragment_id, content[:4000], evidence_id, canonical_url, {}),)
    return EvidenceRecord(
        evidence_id=evidence_id,
        canonical_url=canonical_url,
        final_url=final_url,
        title=title,
        domain=parse.urlsplit(final_url).hostname or "",
        source_trust_type=_trust_type(item.get("source_trust_type")),
        publication_date=str(item.get("publication_date") or item.get("published_at") or ""),
        fetched_at=str(item.get("fetched_at") or ""),
        content_hash=content_hash,
        fragments=fragments,
        verification_state=VerificationState.VERIFIED,
        rejection_reason="",
        provider_provenance={
            "provider": str(item.get("provider") or ""),
            "provenance": provenance,
            "provider_result_index": item.get("provider_result_index"),
            "verified_result_id": verified_id,
        },
        freshness=_freshness(item.get("freshness")),
        workspace_id=str(workspace_id or ""),
        contact_id=str(contact_id or ""),
    )


def deduplicate_evidence(records: Iterable[EvidenceRecord]) -> tuple[EvidenceRecord, ...]:
    unique: dict[str, EvidenceRecord] = {}
    for record in records:
        if record.verification_state is not VerificationState.VERIFIED:
            continue
        canonical = canonicalize_url(record.canonical_url)
        current = unique.get(canonical)
        if current is None or record.evidence_id < current.evidence_id:
            unique[canonical] = record
    return tuple(unique[url] for url in sorted(unique))


def order_evidence_by_trust(records: Iterable[EvidenceRecord]) -> tuple[EvidenceRecord, ...]:
    return tuple(sorted(
        deduplicate_evidence(records),
        key=lambda record: (SOURCE_TRUST_RANK[record.source_trust_type], record.canonical_url, record.evidence_id),
    ))


@dataclass
class ResearchBudgetGuard:
    budget: ResearchBudget
    started_at: float | None = None
    provider_calls: int = 0
    http_requests: int = 0
    total_bytes: int = 0
    evidence_records: int = 0

    def __post_init__(self) -> None:
        if self.started_at is None:
            self.started_at = time.monotonic()

    def _check(self, name: str, value: float, limit: float) -> None:
        if value > limit:
            raise ResearchBudgetExceeded(f"research_budget_exceeded:{name}")

    def consume_provider_call(self, count: int = 1) -> None:
        self.provider_calls += count
        self._check("provider_calls", self.provider_calls, self.budget.max_provider_calls)

    def consume_http_request(self, count: int = 1) -> None:
        self.http_requests += count
        self._check("http_requests", self.http_requests, self.budget.max_http_requests)

    def consume_bytes(self, count: int) -> None:
        self.total_bytes += count
        self._check("total_bytes", self.total_bytes, self.budget.max_total_bytes)

    def consume_evidence(self, count: int = 1) -> None:
        self.evidence_records += count
        self._check("evidence_records", self.evidence_records, self.budget.max_evidence_records)

    def check_elapsed(self, now: float | None = None) -> None:
        elapsed = (time.monotonic() if now is None else now) - float(self.started_at)
        self._check("elapsed_seconds", elapsed, self.budget.max_elapsed_seconds)

    def enforce_all(self, now: float | None = None) -> None:
        self._check("provider_calls", self.provider_calls, self.budget.max_provider_calls)
        self._check("http_requests", self.http_requests, self.budget.max_http_requests)
        self._check("total_bytes", self.total_bytes, self.budget.max_total_bytes)
        self._check("evidence_records", self.evidence_records, self.budget.max_evidence_records)
        self.check_elapsed(now=now)


def validate_claim_evidence(
    claim_id: str,
    claim_text: str,
    evidence_ids: Iterable[str],
    fragment_ids: Iterable[str],
    evidence_records: Iterable[EvidenceRecord],
    *,
    contradicted: bool = False,
) -> ClaimEvidence:
    records = {record.evidence_id: record for record in evidence_records if record.verification_state is VerificationState.VERIFIED}
    requested_evidence = tuple(dict.fromkeys(str(item) for item in evidence_ids))
    requested_fragments = tuple(dict.fromkeys(str(item) for item in fragment_ids))
    valid_records = [records[item] for item in requested_evidence if item in records]
    valid_fragment_ids = {fragment.fragment_id for record in valid_records for fragment in record.fragments}
    fragments_valid = bool(requested_fragments) and all(item in valid_fragment_ids for item in requested_fragments)
    fully_bound = bool(requested_evidence) and len(valid_records) == len(requested_evidence) and fragments_valid
    state = ClaimSupportState.CONTRADICTED if contradicted and fully_bound else (
        ClaimSupportState.SUPPORTED if fully_bound else ClaimSupportState.INSUFFICIENT
    )
    return ClaimEvidence(str(claim_id), str(claim_text), requested_evidence, requested_fragments, state)


def unsupported_claims(claims: Iterable[ClaimEvidence]) -> tuple[ClaimEvidence, ...]:
    return tuple(claim for claim in claims if claim.support_state is ClaimSupportState.INSUFFICIENT)


def contradictory_claim(
    claim_id: str,
    claim_text: str,
    evidence_ids: Iterable[str],
    fragment_ids: Iterable[str],
    evidence_records: Iterable[EvidenceRecord],
) -> ClaimEvidence:
    return validate_claim_evidence(
        claim_id, claim_text, evidence_ids, fragment_ids, evidence_records, contradicted=True,
    )


def render_verified_links(records: Iterable[EvidenceRecord]) -> str:
    verified = deduplicate_evidence(records)
    return "\n".join(
        f"{index}. [{html.escape(record.title)}]({record.canonical_url})"
        for index, record in enumerate(verified, 1)
    )
