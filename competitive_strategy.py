"""Evidence-bound, lawful competitive analysis for ONE NINA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from business_thinking_models import EvidenceConfidence, StableModel, StrategicPriority


COMPETITIVE_DIMENSIONS = (
    "product_capability", "customer_outcome", "price", "speed", "ux", "onboarding",
    "service", "reliability", "distribution", "integrations", "automation",
    "personalization", "trust", "switching_cost", "data_advantage", "brand",
    "business_model", "cost_structure", "geographic_advantage", "vertical_specialization",
)


@dataclass(frozen=True)
class CompetitiveGap(StableModel):
    dimension: str
    description: str
    evidence: tuple[str, ...]
    confidence: EvidenceConfidence


@dataclass(frozen=True)
class CompetitiveAdvantage(StableModel):
    dimension: str
    description: str
    evidence: tuple[str, ...]
    defensibility: str
    confidence: EvidenceConfidence


@dataclass(frozen=True)
class AttackSurface(StableModel):
    dimension: str
    legitimate_opportunity: str
    customer_value: str
    prohibited_methods: tuple[str, ...] = (
        "sabotage", "deception", "intrusion", "harassment", "data theft", "review manipulation",
    )


@dataclass(frozen=True)
class DefensibilityOpportunity(StableModel):
    dimension: str
    opportunity: str
    compounding_mechanism: str
    priority: StrategicPriority


@dataclass(frozen=True)
class CompetitiveAnalysis(StableModel):
    gaps: tuple[CompetitiveGap, ...]
    advantages: tuple[CompetitiveAdvantage, ...]
    attack_surfaces: tuple[AttackSurface, ...]
    defensibility_opportunities: tuple[DefensibilityOpportunity, ...]
    unknown_dimensions: tuple[str, ...]


def analyze_competitive_strategy(comparison: dict[str, dict[str, Any]]) -> CompetitiveAnalysis:
    """Compare only supplied ordinal evidence; unknown inputs stay unknown."""
    gaps, advantages, surfaces, defensibility, unknowns = [], [], [], [], []
    for dimension in COMPETITIVE_DIMENSIONS:
        row = dict(comparison.get(dimension) or {})
        own, competitor = row.get("own"), row.get("competitor")
        evidence = tuple(str(item) for item in row.get("evidence") or () if str(item).strip())
        if own is None or competitor is None or not evidence:
            unknowns.append(dimension)
            continue
        confidence = EvidenceConfidence(str(row.get("confidence") or "medium"))
        if own > competitor:
            advantages.append(CompetitiveAdvantage(
                dimension, str(row.get("advantage") or f"Stronger {dimension.replace('_', ' ')}"),
                evidence, str(row.get("defensibility") or "unproven"), confidence,
            ))
            if dimension in {"data_advantage", "switching_cost", "distribution", "integrations", "brand"}:
                defensibility.append(DefensibilityOpportunity(
                    dimension, f"Compound the verified {dimension.replace('_', ' ')} advantage",
                    str(row.get("compounding_mechanism") or "repeatable customer value"), StrategicPriority.HIGH,
                ))
        elif own < competitor:
            description = str(row.get("gap") or f"Competitor is stronger in {dimension.replace('_', ' ')}")
            gaps.append(CompetitiveGap(dimension, description, evidence, confidence))
            surfaces.append(AttackSurface(
                dimension,
                str(row.get("legitimate_opportunity") or f"Improve {dimension.replace('_', ' ')} for customers"),
                str(row.get("customer_value") or "Reduce customer friction or improve outcomes"),
            ))
    return CompetitiveAnalysis(tuple(gaps), tuple(advantages), tuple(surfaces), tuple(defensibility), tuple(unknowns))
