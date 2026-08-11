"""Deterministic business research planning for the shared ONE NINA capability."""

from __future__ import annotations

import re
from typing import Any

from research_models import (
    FreshnessRequirement,
    ResearchBudget,
    ResearchDomain,
    ResearchPlan,
    SourceTrustType,
)


MAX_DECOMPOSED_QUERIES = 5
_SECRET_PATTERNS = (
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|secret|password|parole)\s*[:=]\s*\S+", re.I),
    re.compile(r"\b(?:sk|pk|ghp|xox[baprs])_[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def contains_obvious_secret(text: str) -> bool:
    return any(pattern.search(str(text or "")) for pattern in _SECRET_PATTERNS)


def _domain(value: ResearchDomain | str | None, query: str) -> ResearchDomain:
    if isinstance(value, ResearchDomain):
        return value
    if value:
        try:
            return ResearchDomain(str(value).lower())
        except ValueError:
            return ResearchDomain.GENERAL
    folded = query.casefold()
    signals = (
        (ResearchDomain.COMPETITOR, ("konkurent", "competitor", " versus ", " vs ")),
        (ResearchDomain.PRICING, ("cena", "cenas", "pricing", "price")),
        (ResearchDomain.NEWS, ("ziņas", "zinas", "news", "aktuāl")),
        (ResearchDomain.MARKET, ("tirgus", "market", "segment", "trend")),
        (ResearchDomain.PRODUCT, ("produkts", "product", "modelis")),
        (ResearchDomain.COMPANY, ("uzņēmum", "uznemum", "company")),
    )
    return next((domain for domain, tokens in signals if any(token in folded for token in tokens)), ResearchDomain.GENERAL)


def _freshness(value: FreshnessRequirement | str | None, domain: ResearchDomain, query: str) -> FreshnessRequirement:
    if isinstance(value, FreshnessRequirement):
        return value
    if value:
        folded = str(value).lower()
        if folded in {"current", "today", "live", "now"}:
            return FreshnessRequirement.CURRENT
        if folded in {"recent", "latest"}:
            return FreshnessRequirement.RECENT
    if domain in {ResearchDomain.PRICING, ResearchDomain.NEWS}:
        return FreshnessRequirement.CURRENT
    if any(token in query.casefold() for token in ("aktuāl", "current", "latest", "šodien", "sodien")):
        return FreshnessRequirement.CURRENT
    if domain is ResearchDomain.COMPANY:
        return FreshnessRequirement.RECENT
    return FreshnessRequirement.ANY


def _queries(query: str, domain: ResearchDomain) -> tuple[str, ...]:
    suffixes = {
        ResearchDomain.COMPANY: ("", " official company information", " public registry facts"),
        ResearchDomain.COMPETITOR: ("", " official product information", " pricing", " independent comparison"),
        ResearchDomain.MARKET: ("", " market size", " market trends", " market segments", " industry report"),
        ResearchDomain.PRICING: ("", " official pricing", " current price"),
        ResearchDomain.NEWS: ("", " latest news", " official announcement"),
        ResearchDomain.PRODUCT: ("", " official manufacturer product page", " independent product review"),
        ResearchDomain.GENERAL: ("",),
    }[domain]
    return tuple(dict.fromkeys((query + suffix).strip() for suffix in suffixes))[:MAX_DECOMPOSED_QUERIES]


def plan_business_research(
    query: str,
    *,
    domain: ResearchDomain | str | None = None,
    business_context: dict[str, Any] | None = None,
    freshness: FreshnessRequirement | str | None = None,
    output_requirement: str = "",
    budget: ResearchBudget | None = None,
) -> ResearchPlan:
    clean = re.sub(r"\s+", " ", str(query or "")).strip()
    selected_domain = _domain(domain, clean)
    selected_freshness = _freshness(freshness, selected_domain, clean)
    default_budget = ResearchBudget(5, 25, 5_000_000, 30.0, 20, {"new_recurring_cost_eur": 0})
    if not clean:
        clarification = "query_required"
        decomposed = ()
    elif contains_obvious_secret(clean) or contains_obvious_secret(str(business_context or "")):
        clarification = "sensitive_input_refused"
        decomposed = ()
    else:
        clarification = "complete"
        decomposed = _queries(clean, selected_domain)
    policy = {
        ResearchDomain.COMPANY: (2, 1, (SourceTrustType.OFFICIAL, SourceTrustType.REGULATORY, SourceTrustType.PRIMARY)),
        ResearchDomain.COMPETITOR: (3, 2, (SourceTrustType.OFFICIAL, SourceTrustType.INDUSTRY, SourceTrustType.COMMERCIAL)),
        ResearchDomain.MARKET: (3, 2, (SourceTrustType.REGULATORY, SourceTrustType.INDUSTRY, SourceTrustType.OFFICIAL)),
        ResearchDomain.PRICING: (2, 1, (SourceTrustType.OFFICIAL, SourceTrustType.PRIMARY, SourceTrustType.COMMERCIAL)),
        ResearchDomain.NEWS: (3, 2, (SourceTrustType.NEWS, SourceTrustType.PRIMARY, SourceTrustType.OFFICIAL)),
        ResearchDomain.PRODUCT: (2, 2, (SourceTrustType.OFFICIAL, SourceTrustType.PRIMARY, SourceTrustType.COMMERCIAL)),
        ResearchDomain.GENERAL: (2, 1, (SourceTrustType.PRIMARY, SourceTrustType.OFFICIAL, SourceTrustType.INDUSTRY)),
    }
    minimum_sources, minimum_domains, preferred_types = policy[selected_domain]
    preferred_domains = tuple(
        str(item).lower().strip()
        for item in (business_context or {}).get("preferred_domains", ())
        if re.fullmatch(r"[a-z0-9.-]+", str(item or ""), re.I)
    )[:5]
    return ResearchPlan(
        domain=selected_domain,
        original_query=clean,
        decomposed_queries=decomposed,
        freshness=selected_freshness,
        minimum_source_count=minimum_sources,
        minimum_distinct_domains=minimum_domains,
        preferred_source_types=preferred_types,
        preferred_domains=preferred_domains,
        output_requirement=str(output_requirement or "claim-ready evidence set"),
        clarification_state=clarification,
        budget=budget or default_budget,
    )
