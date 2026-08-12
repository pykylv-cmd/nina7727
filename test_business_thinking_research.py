import inspect
import unittest

import business_research_bridge
import business_thinking_engine
from business_thinking_engine import analyze_business_decision, analyze_business_decision_with_evidence
from business_thinking_models import (
    BusinessFact, BusinessFactType, BusinessResearchResult, DecisionState,
    EvidenceConfidence, ResearchNeed, StrategicPriority,
)
from research_models import FreshnessRequirement, ResearchDomain


class BusinessThinkingResearchTests(unittest.TestCase):
    def need(self, question, fact_type):
        domain = ResearchDomain.COMPETITOR if fact_type in {BusinessFactType.COMPETITOR, BusinessFactType.PRICING} else ResearchDomain.MARKET
        return ResearchNeed(question, domain, FreshnessRequirement.CURRENT,
                            StrategicPriority.HIGH, "Required for decision quality.")

    def result(self, need, fact_type, statement, *, confidence=EvidenceConfidence.HIGH,
               gaps=(), outcome="completed", workspace="workspace-a", contact="contact-a"):
        facts = () if outcome != "completed" else (BusinessFact(
            statement, ("evidence-1",), ("https://verified.example/source",),
            confidence, need.freshness, fact_type,
        ),)
        return BusinessResearchResult(
            need, outcome, ("evidence-1",) if facts else (), facts,
            ("https://verified.example/source",) if facts else (), confidence if facts else EvidenceConfidence.UNKNOWN,
            tuple(gaps), "" if facts else outcome, workspace, contact,
        )

    def initial_needs(self, question):
        return analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a").research_needs

    def test_competitor_research_enriches_decision(self):
        question = "Vai NinaOS var pārspēt konkurentu X?"
        needs = self.initial_needs(question)
        results = [self.result(need, BusinessFactType.CUSTOMER if "pieprasījums" in need.question else BusinessFactType.PRICING,
                               "Verified customer value" if "pieprasījums" in need.question else "Verified competitor offer") for need in needs]
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
            competitive_comparison={
                "personalization": {"own": 4, "competitor": 2, "evidence": ["continuity audit"]},
                "integrations": {"own": 2, "competitor": 4, "evidence": ["catalog"]},
            },
        )
        self.assertTrue(decision.evidence_set.facts)
        self.assertTrue(decision.competitive_analysis.advantages)
        self.assertTrue(decision.competitive_analysis.gaps)

    def test_verified_named_competitor_facts_affect_recommendation(self):
        question = "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?"
        needs = self.initial_needs(question)
        results = tuple(
            self.result(
                need,
                BusinessFactType.CUSTOMER if "piepras" in need.question.casefold() else BusinessFactType.COMPETITOR,
                f"Verified finding for {need.question}",
            )
            for need in needs
        )
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
        )
        self.assertEqual(len(decision.evidence_set.facts), len(needs))
        self.assertTrue(decision.recommendation.evidence_basis)
        self.assertEqual(decision.recommendation.confidence, EvidenceConfidence.HIGH)
        self.assertIn("Sintra AI", decision.recommendation.decision)

    def test_partial_public_evidence_is_retained_with_private_unknowns(self):
        question = "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?"
        needs = self.initial_needs(question)
        completed = self.result(needs[0], BusinessFactType.COMPETITOR, "Verified Sintra offer")
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=(completed,),
        )
        self.assertIn("Verified Sintra offer", decision.to_json())
        self.assertTrue(decision.research_needs)
        self.assertIn("NinaOS internal economics", decision.to_json())
        self.assertNotEqual(decision.recommendation.confidence, EvidenceConfidence.HIGH)

    def test_pricing_unknown_remains_unresolved(self):
        question = "Vai NinaOS var pārspēt konkurentu X?"
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=(),
        )
        self.assertEqual(decision.state, DecisionState.NEEDS_RESEARCH)
        self.assertTrue(any("cenas" in need.question for need in decision.research_needs))

    def test_market_evidence_can_make_narrow_decision_ready(self):
        question = "Kā audzēt uzņēmumu?"
        needs = self.initial_needs(question)
        results = []
        for need in needs:
            fact_type = BusinessFactType.CUSTOMER if "pieprasījums" in need.question else BusinessFactType.ECONOMICS
            results.append(self.result(need, fact_type, "Verified material fact"))
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
        )
        self.assertEqual(decision.state, DecisionState.READY)

    def test_high_risk_evidence_changes_recommendation(self):
        question = "Vai investēt jaunā biznesā?"
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a",
            business_context={"high_downside": True},
        )
        self.assertIn("validation", decision.recommendation.decision.casefold())

    def test_strong_evidence_raises_confidence_when_all_needs_resolved(self):
        question = "Kā audzēt uzņēmumu?"
        needs = self.initial_needs(question)
        results = [self.result(need, BusinessFactType.CUSTOMER if "pieprasījums" in need.question else BusinessFactType.ECONOMICS,
                               "Verified fact") for need in needs]
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
        )
        self.assertEqual(decision.recommendation.confidence, EvidenceConfidence.HIGH)

    def test_research_failure_blocks_readiness(self):
        question = "Kā audzēt uzņēmumu?"
        need = self.initial_needs(question)[0]
        failure = self.result(need, BusinessFactType.CUSTOMER, "", outcome="provider_unavailable")
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=(failure,),
        )
        self.assertEqual(decision.state, DecisionState.NEEDS_RESEARCH)
        self.assertNotEqual(decision.recommendation.confidence, EvidenceConfidence.HIGH)

    def test_no_invented_financial_numbers(self):
        decision = analyze_business_decision_with_evidence(
            "Kā audzēt uzņēmumu?", workspace_id="workspace-a", contact_id="contact-a", research_results=(),
        )
        self.assertNotRegex(decision.to_json(), r"€\s*\d|\b\d+%")

    def test_explicit_assumptions_remain_assumptions(self):
        decision = analyze_business_decision_with_evidence(
            "Kā augt?", workspace_id="workspace-a", contact_id="contact-a", research_results=(),
            assumptions=({"label": "retention", "value": "will improve"},),
        )
        self.assertIn("will improve", decision.recommendation.assumptions)

    def test_next_action_targets_highest_unresolved_need(self):
        decision = analyze_business_decision_with_evidence(
            "Kā augt?", workspace_id="workspace-a", contact_id="contact-a", research_results=(),
        )
        self.assertIn(decision.research_needs[0].question, decision.next_best_actions[0].action)

    def test_cross_contact_result_is_rejected(self):
        question = "Kā augt?"
        need = self.initial_needs(question)[0]
        wrong = self.result(need, BusinessFactType.CUSTOMER, "Private fact", contact="contact-b")
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=(wrong,),
        )
        self.assertNotIn("Private fact", decision.to_json())

    def test_legal_attack_surfaces_only(self):
        decision = analyze_business_decision_with_evidence(
            "Kā konkurēt?", workspace_id="workspace-a", contact_id="contact-a",
            competitive_comparison={"onboarding": {"own": 1, "competitor": 4, "evidence": ["test"]}},
        )
        surface = decision.competitive_analysis.attack_surfaces[0]
        self.assertIn("customer", surface.customer_value.casefold())

    def test_business_thinking_and_bridge_remain_channel_neutral(self):
        source = (inspect.getsource(business_thinking_engine) + inspect.getsource(business_research_bridge)).casefold()
        self.assertNotIn("telegram", source)
        self.assertNotIn("whatsapp", source)


if __name__ == "__main__":
    unittest.main()
