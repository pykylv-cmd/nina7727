import inspect
import unittest

import business_thinking_engine
from business_thinking_engine import analyze_business_decision, classify_business_intent
from business_thinking_models import BusinessIntent, DecisionState, EvidenceConfidence, EvidenceKind


class BusinessThinkingEngineTests(unittest.TestCase):
    def analyze(self, question, **kwargs):
        return analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a", **kwargs)

    def facts(self):
        return (
            {"label": "customer demand", "value": "12 verified interviews", "kind": "fact", "source_reference": "ev-demand", "confidence": "high"},
            {"label": "gross margin", "value": "verified positive", "kind": "fact", "source_reference": "ev-economics", "confidence": "high"},
            {"label": "competitor pricing", "value": "verified current pages", "kind": "fact", "source_reference": "ev-pricing", "confidence": "high"},
        )

    def test_business_intent_classification(self):
        cases = {
            "Kā sākt biznesu?": BusinessIntent.START_BUSINESS,
            "Kā audzēt uzņēmumu?": BusinessIntent.GROW_BUSINESS,
            "Kā konkurēt tirgū?": BusinessIntent.COMPETE,
            "Kādu cenu noteikt?": BusinessIntent.PRICING,
            "Kā uzlabot pārdošanu?": BusinessIntent.SALES,
            "Kāds mārketings strādās?": BusinessIntent.MARKETING,
            "Kā uzlabot produktu?": BusinessIntent.PRODUCT,
            "Kā samazināt izmaksas?": BusinessIntent.COST_REDUCTION,
            "Kur investēt?": BusinessIntent.INVESTMENT,
            "Vai veidot partnerību?": BusinessIntent.PARTNERSHIP,
            "Kā ieiet tirgū?": BusinessIntent.MARKET_ENTRY,
            "Kā uzlabot operācijas?": BusinessIntent.OPERATIONS,
            "Ko mums darīt tālāk?": BusinessIntent.GENERAL_DECISION,
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(classify_business_intent(question), expected)

    def test_startup_decision_framing(self):
        decision = self.analyze("Kā sākt biznesu?")
        self.assertEqual(decision.context.intent, BusinessIntent.START_BUSINESS)
        self.assertTrue(decision.frame.customer_value)

    def test_growth_decision_framing(self):
        decision = self.analyze("Kā audzēt uzņēmumu?", business_context={"bottleneck": "retention"})
        self.assertIn("retention", decision.frame.execution[0])

    def test_competitor_decision_framing(self):
        decision = self.analyze("Kā konkurēt tirgū?")
        self.assertTrue(any(need.domain.value == "competitor" for need in decision.research_needs))

    def test_named_competitor_is_preserved_in_specific_research_needs(self):
        decision = self.analyze("Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?")
        questions = tuple(need.question for need in decision.research_needs)
        self.assertTrue(any("Sintra AI" in question and "cenas" in question for question in questions))
        self.assertTrue(any("Sintra AI" in question and "integrācijas" in question for question in questions))
        self.assertTrue(any("AI darbaspēka" in question for question in questions))

    def test_named_competitor_is_extracted_not_hard_coded(self):
        questions = tuple(need.question for need in self.analyze("Kā pārspēt Acme Cloud?").research_needs)
        self.assertTrue(any("Acme Cloud" in question for question in questions))
        self.assertFalse(any("Sintra" in question for question in questions))

    def test_generic_competitor_question_remains_generic(self):
        questions = tuple(need.question for need in self.analyze("Kā pārspēt konkurentus?").research_needs)
        self.assertTrue(any("konkurentu piedāvājumi" in question for question in questions))

    def test_strategy_question_has_strategy_specific_research_needs(self):
        decision = self.analyze("Kādu biznesa stratēģiju mums izvēlēties, lai NinaOS augtu ātrāk par konkurentiem?")
        questions = " ".join(need.question for need in decision.research_needs)
        self.assertIn("mērķa klientam", questions)
        self.assertIn("izplatīšanas", questions)
        self.assertIn("aizsargājamas", questions)

    def test_live_questions_do_not_collapse_to_identical_analysis(self):
        named = self.analyze("Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?")
        strategy = self.analyze("Kādu biznesa stratēģiju mums izvēlēties, lai NinaOS augtu ātrāk par konkurentiem?")
        self.assertNotEqual(named.research_needs, strategy.research_needs)
        self.assertNotEqual(named.recommendation.decision, strategy.recommendation.decision)
        self.assertNotEqual(named.next_best_actions, strategy.next_best_actions)

    def test_pricing_decision_framing(self):
        decision = self.analyze("Kādu cenu noteikt?")
        self.assertTrue(any("cenas" in need.question for need in decision.research_needs))

    def test_unknown_facts_remain_unknown(self):
        decision = self.analyze("Vai investēt?", unknowns=("market size",))
        self.assertIn("market size", decision.missing_information)

    def test_assumptions_remain_labeled(self):
        decision = self.analyze("Vai investēt?", assumptions=({"label": "growth", "value": "will double"},))
        self.assertEqual(decision.context.assumptions[0].kind, EvidenceKind.ASSUMPTION)
        self.assertIn("will double", decision.recommendation.assumptions)

    def test_missing_market_evidence_creates_research_need(self):
        self.assertTrue(self.analyze("Kā augt?").research_needs)

    def test_missing_competitor_pricing_creates_research_need(self):
        needs = self.analyze("Kā konkurēt ar cenu?").research_needs
        self.assertTrue(any("konkurentu" in need.question for need in needs))

    def test_evidence_backed_fact_remains_fact(self):
        decision = self.analyze("Kā augt?", known_facts=self.facts())
        self.assertTrue(all(item.kind is EvidenceKind.FACT for item in decision.context.known_facts))

    def test_unsupported_financial_number_cannot_become_fact(self):
        decision = self.analyze("Kā augt?", assumptions=({"label": "revenue", "value": "€1m"},))
        self.assertFalse(any(item.value == "€1m" for item in decision.context.known_facts))
        self.assertEqual(decision.metrics, ())

    def test_opportunities_are_prioritized(self):
        self.assertEqual(self.analyze("Kā augt?").opportunities[0].priority.value, "high")

    def test_risks_are_prioritized(self):
        risks = self.analyze("Vai investēt?", business_context={"high_downside": True}).risks
        self.assertEqual(risks[0].priority.value, "critical")

    def test_options_include_upside_and_downside(self):
        option = self.analyze("Kā augt?").options[0]
        self.assertTrue(option.upside)
        self.assertTrue(option.downside)

    def test_recommendation_preserves_assumptions(self):
        decision = self.analyze("Kā augt?", assumptions=({"label": "retention", "value": "stable"},))
        self.assertEqual(decision.recommendation.assumptions, ("stable",))

    def test_recommendation_confidence_reflects_evidence(self):
        self.assertEqual(self.analyze("Kā augt?", known_facts=self.facts()).recommendation.confidence, EvidenceConfidence.HIGH)

    def test_conditions_that_change_decision_are_preserved(self):
        self.assertTrue(self.analyze("Kā augt?", known_facts=self.facts()).recommendation.conditions_that_change_decision)

    def test_ready_produces_next_best_action(self):
        decision = self.analyze("Kā augt?", known_facts=self.facts())
        self.assertEqual(decision.state, DecisionState.READY)
        self.assertTrue(decision.next_best_actions)

    def test_needs_research_does_not_pretend_certainty(self):
        decision = self.analyze("Kā sākt biznesu?")
        self.assertEqual(decision.state, DecisionState.NEEDS_RESEARCH)
        self.assertIn(decision.recommendation.confidence, (EvidenceConfidence.UNKNOWN, EvidenceConfidence.LOW))

    def test_reversible_experiment_preferred_when_uncertain(self):
        decision = self.analyze("Kā sākt biznesu?")
        self.assertEqual(decision.options[0].reversibility, "high")
        self.assertIn("reversible", decision.recommendation.decision.casefold())

    def test_high_downside_changes_recommendation(self):
        decision = self.analyze("Vai investēt?", known_facts=self.facts(), business_context={"high_downside": True})
        self.assertIn("validation", decision.recommendation.decision.casefold())

    def test_customer_value_lens_works(self):
        self.assertIn("Who pays", self.analyze("Kā sākt biznesu?").frame.customer_value[0])

    def test_economics_lens_works(self):
        self.assertIn("Revenue", self.analyze("Kā sākt biznesu?").frame.economics[0])

    def test_growth_lens_works(self):
        self.assertIn("acquisition", self.analyze("Kā augt?").frame.growth[0])

    def test_execution_bottleneck_is_surfaced(self):
        self.assertIn("sales capacity", self.analyze("Kā augt?", business_context={"bottleneck": "sales capacity"}).frame.execution[0])

    def test_capital_allocation_lens_works(self):
        self.assertIn("next euro/hour", self.analyze("Kur investēt?").frame.capital_allocation[0])

    def test_moat_dimensions_are_represented(self):
        moat = self.analyze("Kā konkurēt?").frame.moat[0]
        self.assertIn("data", moat)
        self.assertIn("switching", moat)

    def test_empty_question_needs_clarification(self):
        self.assertEqual(self.analyze("").state, DecisionState.NEEDS_CLARIFICATION)

    def test_engine_is_channel_neutral(self):
        source = inspect.getsource(business_thinking_engine).casefold()
        self.assertNotIn("telegram", source)
        self.assertNotIn("whatsapp", source)

    def test_engine_has_no_provider_or_web_search_implementation(self):
        source = inspect.getsource(business_thinking_engine).casefold()
        self.assertNotIn("openai", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("fetch_public", source)

    def test_output_is_deterministic(self):
        first = self.analyze("Kā augt?", known_facts=self.facts()).to_json()
        second = self.analyze("Kā augt?", known_facts=reversed(self.facts())).to_json()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
