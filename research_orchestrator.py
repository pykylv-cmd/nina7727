"""Channel-neutral grounded research orchestration for ONE NINA.

This module has no live routing hook. It composes the existing provider, fetch,
verification and EvidenceRecord contracts behind a callable interface.
"""

from __future__ import annotations

from dataclasses import replace
import json
import time
from typing import Callable, Iterable

import web_research
from business_research_planner import plan_business_research
from research_evidence import ResearchBudgetExceeded, ResearchBudgetGuard, order_evidence_by_trust
from research_models import (
    FreshnessRequirement,
    ResearchDomain,
    ResearchJobState,
    ResearchOutcome,
    ResearchPlan,
    ResearchResult,
)


def _emit_execution_diagnostics(
    *, plan: ResearchPlan, outcome: ResearchOutcome, failures, gaps, evidence,
    guard: ResearchBudgetGuard, elapsed: float,
) -> None:
    prefix = "research_budget_exceeded:"
    limit_dimension = next(
        (str(item)[len(prefix):] for item in gaps if str(item).startswith(prefix)), "",
    )
    rejection_count = sum(
        1 for item in failures
        if item.get("stage") == "verification" and bool(item.get("reason"))
    )
    fetch_failure_count = sum(
        1 for item in failures
        if item.get("stage") == "verification"
        and any(token in str(item.get("reason") or item.get("error") or "").casefold()
                for token in ("fetch", "http", "robots", "mime", "size", "ssrf"))
    )
    payload = {
        "event": ("research_budget_exceeded" if outcome is ResearchOutcome.BUDGET_EXCEEDED
                  else "research_execution_summary"),
        "domain": plan.domain.value,
        "decomposed_query_count": len(plan.decomposed_queries),
        "provider_calls": guard.provider_calls,
        "http_requests": guard.http_requests,
        "total_bytes": guard.total_bytes,
        "elapsed_seconds": round(float(elapsed), 3),
        "evidence_records": len(evidence),
        "outcome": outcome.value,
        "limit_dimension": limit_dimension,
        "verified_evidence_count": len(evidence),
        "rejection_count": rejection_count,
        "fetch_failure_count": fetch_failure_count,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")), flush=True)


def _intent(query: str, plan: ResearchPlan) -> web_research.SearchIntent:
    built = web_research.build_search_plan("Atrodi " + query)
    return replace(
        built,
        query=query,
        target_domains=plan.preferred_domains,
        max_results=min(web_research.MAX_RESULTS_HARD, max(plan.minimum_source_count, 5)),
        freshness=plan.freshness.value,
    )


def _verification_intent(plan: ResearchPlan) -> web_research.SearchIntent:
    """Validate candidates against the owner's request, not planner search hints."""
    return _intent(plan.original_query, plan)


def _result(
    *, plan: ResearchPlan, outcome: ResearchOutcome, evidence=(), failures=(), gaps=(),
    guard: ResearchBudgetGuard, clock: Callable[[], float],
) -> ResearchResult:
    elapsed = max(0.0, clock() - float(guard.started_at))
    result = ResearchResult(
        state=ResearchJobState.COMPLETED if outcome is ResearchOutcome.COMPLETED else ResearchJobState.FAILED,
        outcome=outcome,
        plan=plan,
        evidence=tuple(evidence),
        failures=tuple(failures),
        gaps=tuple(gaps),
        provider_calls=guard.provider_calls,
        http_requests=guard.http_requests,
        total_bytes=guard.total_bytes,
        elapsed_seconds=elapsed,
    )
    _emit_execution_diagnostics(
        plan=plan, outcome=outcome, failures=result.failures, gaps=result.gaps,
        evidence=result.evidence, guard=guard, elapsed=elapsed,
    )
    return result


def run_research(
    *,
    query: str,
    workspace_id: str,
    contact_id: str,
    domain: ResearchDomain | str | None = None,
    freshness: FreshnessRequirement | str | None = None,
    output_requirement: str = "",
    business_context: dict | None = None,
    plan: ResearchPlan | None = None,
    providers: Iterable[tuple[str, Callable]] | None = None,
    fetcher: Callable = web_research.fetch_public_page,
    provider_searcher: Callable = web_research.provider_search,
    verification_runner: Callable = web_research.search_verified_web,
    clock: Callable[[], float] = time.monotonic,
) -> ResearchResult:
    selected_plan = plan or plan_business_research(
        query, domain=domain, business_context=business_context, freshness=freshness,
        output_requirement=output_requirement,
    )
    guard = ResearchBudgetGuard(selected_plan.budget, started_at=clock())
    if selected_plan.clarification_state != "complete" or not selected_plan.decomposed_queries:
        return _result(
            plan=selected_plan, outcome=ResearchOutcome.INSUFFICIENT_EVIDENCE,
            gaps=(selected_plan.clarification_state,), guard=guard, clock=clock,
        )
    evidence = []
    failures = []
    provider_had_candidates = False
    verification_rejections = False

    def budget_fetch(url, **kwargs):
        guard.consume_http_request()
        page = fetcher(url, **kwargs)
        body = (page or {}).get("body")
        if body is None:
            body = (page or {}).get("html") or ""
        guard.consume_bytes(len(body if isinstance(body, bytes) else str(body).encode("utf-8")))
        return page

    try:
        configured_providers = list(web_research.configured_search_providers() if providers is None else providers)
        budgeted_providers = []
        for provider_name, provider in configured_providers:
            def budgeted_provider(intent, _provider=provider):
                guard.consume_provider_call()
                return _provider(intent)
            budgeted_providers.append((provider_name, budgeted_provider))
        for decomposed_query in selected_plan.decomposed_queries[:5]:
            guard.check_elapsed(now=clock())
            provider_intent = _intent(decomposed_query, selected_plan)
            verification_intent = _verification_intent(selected_plan)
            try:
                if provider_searcher is web_research.provider_search:
                    candidates, provider_name, provider_failures = provider_searcher(provider_intent, providers=budgeted_providers)
                else:
                    guard.consume_provider_call()
                    candidates, provider_name, provider_failures = provider_searcher(provider_intent, providers=providers)
            except ResearchBudgetExceeded:
                raise
            except (web_research.WebResearchError, OSError, ValueError) as exc:
                failures.append({"query": decomposed_query, "stage": "provider", "error": str(exc)})
                continue
            failures.extend(
                {"query": decomposed_query, "stage": "provider", **dict(item)}
                for item in provider_failures
            )
            provider_had_candidates = provider_had_candidates or bool(candidates)
            try:
                payload = verification_runner(
                    verification_intent,
                    search_provider=lambda _intent, rows=tuple(candidates): list(rows),
                    fetcher=budget_fetch,
                )
            except ResearchBudgetExceeded:
                raise
            except (web_research.WebResearchError, OSError, ValueError) as exc:
                verification_rejections = True
                failures.append({"query": decomposed_query, "stage": "verification", "error": str(exc)})
                continue
            verification_rejections = verification_rejections or bool(payload.get("rejected_results"))
            failures.extend(
                {
                    "query": decomposed_query,
                    "stage": "verification",
                    "reason": str(item.get("reason") or "verification_rejected")[:120],
                    "source_domain": str(item.get("source_domain") or "")[:253],
                }
                for item in payload.get("rejected_results") or ()
            )
            for item in web_research.verified_results(payload):
                enriched = dict(item)
                enriched.setdefault("freshness", selected_plan.freshness.value)
                record = web_research.verified_result_to_evidence(
                    enriched, workspace_id=workspace_id, contact_id=contact_id,
                )
                guard.consume_evidence()
                evidence.append(record)
            guard.enforce_all(now=clock())
    except ResearchBudgetExceeded as exc:
        return _result(
            plan=selected_plan, outcome=ResearchOutcome.BUDGET_EXCEEDED,
            evidence=order_evidence_by_trust(evidence), failures=failures + [{"stage": "budget", "error": str(exc)}],
            gaps=(str(exc),), guard=guard, clock=clock,
        )

    ordered = order_evidence_by_trust(evidence)
    distinct_domains = {record.domain for record in ordered}
    gaps = []
    if len(ordered) < selected_plan.minimum_source_count:
        gaps.append("minimum_source_count_not_met")
    if len(distinct_domains) < selected_plan.minimum_distinct_domains:
        gaps.append("minimum_distinct_domains_not_met")
    if not gaps:
        outcome = ResearchOutcome.COMPLETED
    elif not provider_had_candidates and failures:
        outcome = ResearchOutcome.PROVIDER_UNAVAILABLE
    elif provider_had_candidates and not ordered and verification_rejections:
        outcome = ResearchOutcome.VERIFICATION_FAILED
    else:
        outcome = ResearchOutcome.INSUFFICIENT_EVIDENCE
    return _result(
        plan=selected_plan, outcome=outcome, evidence=ordered,
        failures=failures, gaps=gaps, guard=guard, clock=clock,
    )
