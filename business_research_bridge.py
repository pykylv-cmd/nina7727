"""Channel-neutral bridge from Business Thinking ResearchNeed to Research V1."""

from __future__ import annotations

from typing import Callable

from business_research_planner import plan_business_research
from business_thinking_models import (
    BusinessFact, BusinessFactType, BusinessResearchResult, EvidenceConfidence, ResearchNeed,
)
from research_models import ClaimSupportState, ResearchOutcome
from research_orchestrator import run_research
from research_synthesis import synthesize_research


def _fact_type(need: ResearchNeed) -> BusinessFactType:
    text = (need.question + " " + need.why_needed).casefold()
    if "price" in text or "cen" in text:
        return BusinessFactType.PRICING
    if "compet" in text or "konkur" in text:
        return BusinessFactType.COMPETITOR
    if "customer" in text or "klient" in text or "demand" in text or "piepras" in text:
        return BusinessFactType.CUSTOMER
    if "margin" in text or "revenue" in text or "econom" in text or "izmaks" in text:
        return BusinessFactType.ECONOMICS
    if "risk" in text:
        return BusinessFactType.RISK
    return BusinessFactType.MARKET


def execute_business_research_need(
    need: ResearchNeed, *, workspace_id: str, contact_id: str,
    query_context: str = "",
    planner: Callable = plan_business_research,
    runner: Callable = run_research,
    synthesizer: Callable = synthesize_research,
) -> BusinessResearchResult:
    """Run existing Research V1 and expose only completed, verified, URL-bound facts."""
    research_query = need.question
    if str(query_context or "").strip():
        research_query = f"{need.question}\nBiznesa lēmuma konteksts: {str(query_context).strip()}"
    plan = planner(research_query, domain=need.domain, freshness=need.freshness,
                   output_requirement=need.why_needed)
    result = runner(
        query=research_query, workspace_id=workspace_id, contact_id=contact_id,
        domain=need.domain, freshness=need.freshness, output_requirement=need.why_needed,
        plan=plan,
    )
    answer = synthesizer(result)
    completed = result.outcome is ResearchOutcome.COMPLETED and answer.outcome is ResearchOutcome.COMPLETED
    verified_ids = {
        record.evidence_id for record in result.evidence
        if record.verification_state.value == "verified"
        and record.workspace_id == str(workspace_id)
        and record.contact_id == str(contact_id)
    }
    verified_urls = {record.canonical_url for record in result.evidence if record.evidence_id in verified_ids}
    safe_links = tuple(
        link.url for link in answer.source_links
        if link.url in verified_urls and set(link.evidence_ids).issubset(verified_ids)
    ) if completed else ()
    facts = []
    if completed and not answer.insufficient_evidence:
        links_by_evidence = {
            evidence_id: link.url
            for link in answer.source_links
            for evidence_id in link.evidence_ids
            if evidence_id in verified_ids and link.url in verified_urls
        }
        for claim in answer.claims:
            if claim.support_state not in {ClaimSupportState.SUPPORTED, ClaimSupportState.CONTRADICTED}:
                continue
            evidence_ids = tuple(sorted(set(claim.evidence_ids) & verified_ids))
            if not evidence_ids:
                continue
            facts.append(BusinessFact(
                statement=claim.claim_text,
                evidence_ids=evidence_ids,
                source_links=tuple(sorted({links_by_evidence[item] for item in evidence_ids if item in links_by_evidence})),
                confidence=EvidenceConfidence.MEDIUM if claim.support_state is ClaimSupportState.CONTRADICTED else EvidenceConfidence.HIGH,
                freshness=need.freshness,
                fact_type=_fact_type(need),
            ))
    gaps = tuple(dict.fromkeys(tuple(answer.risks_or_gaps) + tuple(result.gaps)))
    failure_reason = "" if completed and facts else (
        result.outcome.value if result.outcome is not ResearchOutcome.COMPLETED else "no_grounded_business_facts"
    )
    return BusinessResearchResult(
        research_need=need, outcome=result.outcome.value,
        verified_evidence_ids=tuple(sorted(verified_ids)) if completed else (),
        facts=tuple(facts), source_links=safe_links,
        confidence=(EvidenceConfidence.HIGH if facts and not any("contradict" in gap for gap in gaps)
                    else EvidenceConfidence.MEDIUM if facts else EvidenceConfidence.UNKNOWN),
        gaps=gaps, failure_reason=failure_reason,
        workspace_id=str(workspace_id), contact_id=str(contact_id),
    )
