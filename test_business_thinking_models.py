import json
import unittest

from business_thinking_models import (
    BusinessDecisionContext, BusinessIntent, DecisionEvidence, DecisionState,
    EvidenceConfidence, EvidenceKind, NextBestAction, ResearchNeed, StrategicPriority,
)
from research_models import FreshnessRequirement, ResearchDomain


class BusinessThinkingModelTests(unittest.TestCase):
    def test_all_required_business_intents_exist(self):
        self.assertEqual(len(BusinessIntent), 13)
        self.assertIn(BusinessIntent.GENERAL_DECISION, BusinessIntent)

    def test_decision_states_are_stable(self):
        self.assertEqual(DecisionState.NEEDS_RESEARCH.value, "needs_research")

    def test_fact_and_assumption_are_distinct(self):
        fact = DecisionEvidence("demand", "10 interviews", EvidenceKind.FACT, "ev-1", EvidenceConfidence.HIGH)
        assumption = DecisionEvidence("demand", "large", EvidenceKind.ASSUMPTION)
        self.assertNotEqual(fact.kind, assumption.kind)

    def test_research_need_reuses_research_v1_types(self):
        need = ResearchNeed("Price?", ResearchDomain.PRICING, FreshnessRequirement.CURRENT,
                            StrategicPriority.HIGH, "Decision input")
        self.assertEqual(need.domain, ResearchDomain.PRICING)

    def test_context_preserves_owner_scope(self):
        context = BusinessDecisionContext("Q", "workspace-a", "contact-a", BusinessIntent.PRICING, "Q")
        self.assertEqual((context.workspace_id, context.contact_id), ("workspace-a", "contact-a"))

    def test_next_action_has_approval_boundary(self):
        action = NextBestAction("Validate", "Now", "Learning", (), True, True)
        self.assertTrue(action.approval_required)

    def test_serialization_is_deterministic(self):
        context = BusinessDecisionContext("Q", "w", "c", BusinessIntent.GROW_BUSINESS, "Grow",
                                          business_context={"z": 1, "a": 2})
        self.assertEqual(context.to_json(), context.to_json())
        self.assertEqual(list(json.loads(context.to_json())["business_context"]), ["a", "z"])

    def test_serialization_uses_enum_values(self):
        context = BusinessDecisionContext("Q", "w", "c", BusinessIntent.SALES, "Sell")
        self.assertEqual(context.to_dict()["intent"], "sales")


if __name__ == "__main__":
    unittest.main()
