"""Deterministic grounded synthesis over an existing ResearchResult.

External evidence is untrusted data. This module performs no acquisition,
network access, persistence, model calls, or live ONE NINA routing.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Iterable

from research_evidence import (
    SOURCE_TRUST_RANK,
    contradictory_claim,
    order_evidence_by_trust,
    validate_claim_evidence,
)
from research_models import (
    ClaimEvidence,
    ClaimSupportState,
    EvidenceRecord,
    FreshnessRequirement,
    GroundedResearchAnswer,
    ResearchOutcome,
    ResearchResult,
    VerificationState,
    VerifiedSourceLink,
)


_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)
_CURRENT_MAX_AGE_SECONDS = 2 * 24 * 60 * 60
_RECENT_MAX_AGE_SECONDS = 90 * 24 * 60 * 60


def _plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", _URL_PATTERN.sub("", str(value or ""))).strip()


def _timestamp(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text[:10])
        except ValueError:
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _record_date(record: EvidenceRecord) -> datetime | None:
    return _timestamp(record.publication_date) or _timestamp(record.fetched_at)


def _freshness_eligible(record: EvidenceRecord, requirement: FreshnessRequirement, as_of: datetime) -> bool:
    if requirement is FreshnessRequirement.ANY:
        return True
    dated = _record_date(record)
    if dated is None:
        return False
    age = max(0.0, (as_of - dated).total_seconds())
    limit = _CURRENT_MAX_AGE_SECONDS if requirement is FreshnessRequirement.CURRENT else _RECENT_MAX_AGE_SECONDS
    return age <= limit


def _candidate_claims(records: Iterable[EvidenceRecord]) -> tuple[ClaimEvidence, ...]:
    claims = []
    for record in records:
        for fragment in record.fragments:
            claim_id = "claim_" + fragment.fragment_id.removeprefix("fragment_")
            claims.append(ClaimEvidence(
                claim_id=claim_id,
                claim_text=fragment.text,
                evidence_ids=(record.evidence_id,),
                fragment_ids=(fragment.fragment_id,),
                support_state=ClaimSupportState.SUPPORTED,
            ))
    return tuple(claims)


def _validate_claim(
    claim: ClaimEvidence,
    records: tuple[EvidenceRecord, ...],
) -> ClaimEvidence:
    bound_records = {record.evidence_id: record for record in records}
    allowed_urls = {
        record.canonical_url
        for evidence_id in claim.evidence_ids
        for record in (bound_records.get(evidence_id),)
        if record is not None
    }
    claim_urls = {url.rstrip(".,;:!?)]}") for url in _URL_PATTERN.findall(claim.claim_text)}
    if claim_urls - allowed_urls:
        return ClaimEvidence(
            claim.claim_id, claim.claim_text, claim.evidence_ids, claim.fragment_ids,
            ClaimSupportState.INSUFFICIENT,
        )
    if claim.support_state is ClaimSupportState.CONTRADICTED:
        return contradictory_claim(
            claim.claim_id, claim.claim_text, claim.evidence_ids, claim.fragment_ids, records,
        )
    return validate_claim_evidence(
        claim.claim_id, claim.claim_text, claim.evidence_ids, claim.fragment_ids, records,
    )


def render_claim_citations(
    claims: Iterable[ClaimEvidence],
    evidence_records: Iterable[EvidenceRecord],
) -> tuple[VerifiedSourceLink, ...]:
    records = {
        record.evidence_id: record
        for record in order_evidence_by_trust(evidence_records)
        if record.verification_state is VerificationState.VERIFIED
    }
    links: dict[str, dict] = {}
    for claim in claims:
        if claim.support_state not in {ClaimSupportState.SUPPORTED, ClaimSupportState.CONTRADICTED}:
            continue
        for evidence_id in claim.evidence_ids:
            record = records.get(evidence_id)
            if record is None:
                continue
            entry = links.setdefault(record.canonical_url, {"record": record, "claims": set(), "evidence": set()})
            entry["claims"].add(claim.claim_id)
            entry["evidence"].add(record.evidence_id)
    return tuple(
        VerifiedSourceLink(
            title=entry["record"].title,
            url=entry["record"].canonical_url,
            evidence_ids=tuple(sorted(entry["evidence"])),
            claim_ids=tuple(sorted(entry["claims"])),
            source_trust_type=entry["record"].source_trust_type,
        )
        for _, entry in sorted(
            links.items(),
            key=lambda item: (
                SOURCE_TRUST_RANK[item[1]["record"].source_trust_type],
                item[0],
            ),
        )
    )


def synthesize_research(
    result: ResearchResult,
    *,
    claims: Iterable[ClaimEvidence] | None = None,
    as_of: datetime | None = None,
) -> GroundedResearchAnswer:
    current_time = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    verified = tuple(
        record for record in order_evidence_by_trust(result.evidence)
        if record.verification_state is VerificationState.VERIFIED
    )
    eligible = tuple(
        record for record in verified
        if _freshness_eligible(record, result.plan.freshness, current_time)
    )
    stale_count = len(verified) - len(eligible)
    supplied_claims = tuple(claims) if claims is not None else _candidate_claims(eligible)
    evidence_order = {record.evidence_id: index for index, record in enumerate(eligible)}
    checked = tuple(sorted(
        (_validate_claim(claim, eligible) for claim in supplied_claims),
        key=lambda claim: (
            min((evidence_order.get(item, len(evidence_order)) for item in claim.evidence_ids), default=len(evidence_order)),
            claim.claim_id,
        ),
    ))
    grounded = tuple(
        claim for claim in checked
        if claim.support_state in {ClaimSupportState.SUPPORTED, ClaimSupportState.CONTRADICTED}
    )
    findings = tuple(
        _plain_text(claim.claim_text)
        for claim in grounded
        if _plain_text(claim.claim_text)
    )
    evidence_ids_used = tuple(sorted({evidence_id for claim in grounded for evidence_id in claim.evidence_ids}))
    links = render_claim_citations(grounded, eligible)
    gaps = list(result.gaps)
    gaps.extend(str(item.get("error") or item.get("stage") or "research_failure") for item in result.failures)
    unsupported_count = len(checked) - len(grounded)
    if unsupported_count:
        gaps.append(f"unsupported_claims:{unsupported_count}")
    contradicted = any(claim.support_state is ClaimSupportState.CONTRADICTED for claim in grounded)
    if contradicted:
        gaps.append("verified_sources_contradict")
    if stale_count:
        gaps.append(f"freshness_excluded_evidence:{stale_count}")
    if result.plan.freshness is FreshnessRequirement.CURRENT:
        freshness_note = (
            "Current freshness requirement met by dated verified evidence."
            if eligible and not stale_count else
            "Current freshness requirement was not met by all verified evidence."
        )
    elif result.plan.freshness is FreshnessRequirement.RECENT:
        freshness_note = (
            "Recent evidence requirement met."
            if eligible and not stale_count else
            "Recent evidence is incomplete or contains undated/stale sources."
        )
    else:
        freshness_note = "No freshness constraint was requested."
    insufficient = not grounded or (
        result.plan.freshness is FreshnessRequirement.CURRENT and bool(stale_count)
    )
    if contradicted:
        summary = f"Verified sources disagree. {len(grounded)} grounded findings are available."
    elif grounded:
        summary = f"{len(grounded)} grounded findings from {len(links)} verified sources."
    else:
        summary = "Insufficient verified evidence for a grounded factual answer."
    outcome = ResearchOutcome.INSUFFICIENT_EVIDENCE if insufficient else result.outcome
    return GroundedResearchAnswer(
        summary=summary,
        findings=findings,
        claims=checked,
        risks_or_gaps=tuple(dict.fromkeys(gaps)),
        source_links=links,
        evidence_ids_used=evidence_ids_used,
        outcome=outcome,
        freshness_note=freshness_note,
        insufficient_evidence=insufficient,
    )
