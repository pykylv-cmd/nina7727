import json
import unittest

from research_models import (
    ClaimEvidence,
    ClaimSupportState,
    EvidenceFragment,
    EvidenceRecord,
    FreshnessRequirement,
    ResearchBudget,
    ResearchDomain,
    ResearchPlan,
    SourceTrustType,
    VerificationState,
)


class ResearchModelTests(unittest.TestCase):
    def test_plan_serialization_round_trip_is_stable(self):
        plan = ResearchPlan(
            domain=ResearchDomain.MARKET,
            original_query="AI CRM tirgus",
            decomposed_queries=("AI CRM market", "AI CRM pricing"),
            freshness=FreshnessRequirement.CURRENT,
            minimum_source_count=3,
            minimum_distinct_domains=2,
            preferred_source_types=(SourceTrustType.OFFICIAL, SourceTrustType.INDUSTRY),
            preferred_domains=("example.com",),
            output_requirement="grounded summary",
            clarification_state="complete",
            budget=ResearchBudget(2, 5, 100_000, 10.0, 5, {"currency": "EUR", "maximum": 0}),
        )
        restored = ResearchPlan.from_dict(json.loads(plan.to_json()))
        self.assertEqual(restored, plan)
        self.assertEqual(restored.to_json(), plan.to_json())

    def test_evidence_serialization_round_trip_preserves_trust_and_freshness(self):
        fragment = EvidenceFragment("fragment-1", "Grounded fact", "evidence-1", "https://example.com/", {"line": 2})
        record = EvidenceRecord(
            "evidence-1", "https://example.com/", "https://example.com/final", "Example", "example.com",
            SourceTrustType.REGULATORY, "2026-08-01", "2026-08-11T00:00:00+00:00", "abc", (fragment,),
            VerificationState.VERIFIED, "", {"provider": "test"}, FreshnessRequirement.RECENT, "workspace-a", "contact-a",
        )
        restored = EvidenceRecord.from_dict(json.loads(record.to_json()))
        self.assertEqual(restored, record)
        self.assertEqual(restored.source_trust_type, SourceTrustType.REGULATORY)
        self.assertEqual(restored.freshness, FreshnessRequirement.RECENT)

    def test_claim_serialization_round_trip_is_stable(self):
        claim = ClaimEvidence("claim-1", "Fact", ("evidence-1",), ("fragment-1",), ClaimSupportState.SUPPORTED)
        restored = ClaimEvidence.from_dict(json.loads(claim.to_json()))
        self.assertEqual(restored, claim)
        self.assertEqual(restored.to_json(), claim.to_json())

    def test_negative_budget_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "research_budget_limit_invalid"):
            ResearchBudget(-1, 1, 1, 1, 1)


if __name__ == "__main__":
    unittest.main()
