import unittest

from business_research_planner import MAX_DECOMPOSED_QUERIES, plan_business_research
from research_models import FreshnessRequirement, ResearchDomain, SourceTrustType


class BusinessResearchPlannerTests(unittest.TestCase):
    def test_company_plan_is_official_first(self):
        plan = plan_business_research("Izpēti uzņēmumu Acme", domain=ResearchDomain.COMPANY)
        self.assertEqual(plan.preferred_source_types[0], SourceTrustType.OFFICIAL)
        self.assertIn("Acme", plan.original_query)

    def test_competitor_plan_decomposes_queries(self):
        plan = plan_business_research("Salīdzini Acme un Beta konkurentus", domain="competitor")
        self.assertGreaterEqual(len(plan.decomposed_queries), 3)
        self.assertGreaterEqual(plan.minimum_distinct_domains, 2)

    def test_market_plan_requires_source_diversity(self):
        plan = plan_business_research("AI CRM tirgus", domain="market")
        self.assertGreaterEqual(plan.minimum_source_count, 3)
        self.assertGreaterEqual(plan.minimum_distinct_domains, 2)
        self.assertEqual(plan.preferred_source_types[0], SourceTrustType.REGULATORY)

    def test_pricing_defaults_to_current(self):
        self.assertEqual(plan_business_research("Acme cenas", domain="pricing").freshness, FreshnessRequirement.CURRENT)

    def test_news_defaults_to_current(self):
        self.assertEqual(plan_business_research("Acme ziņas", domain="news").freshness, FreshnessRequirement.CURRENT)

    def test_product_prefers_official_manufacturer(self):
        plan = plan_business_research("Acme produkts", domain="product")
        self.assertEqual(plan.preferred_source_types[0], SourceTrustType.OFFICIAL)
        self.assertTrue(any("manufacturer" in query for query in plan.decomposed_queries))

    def test_general_uses_conservative_defaults(self):
        plan = plan_business_research("Izpēti šo tēmu", domain="general")
        self.assertEqual(plan.domain, ResearchDomain.GENERAL)
        self.assertEqual(plan.freshness, FreshnessRequirement.ANY)
        self.assertGreaterEqual(plan.minimum_source_count, 2)

    def test_decomposed_queries_never_exceed_five(self):
        plan = plan_business_research("CRM tirgus", domain="market")
        self.assertLessEqual(len(plan.decomposed_queries), MAX_DECOMPOSED_QUERIES)

    def test_secrets_are_refused_and_not_sent_to_provider(self):
        secret = "api_key=sk_abcdefghijklmnopqrstuvwxyz"
        plan = plan_business_research("Research Acme " + secret)
        self.assertEqual(plan.clarification_state, "sensitive_input_refused")
        self.assertEqual(plan.decomposed_queries, ())

    def test_empty_query_yields_clarification(self):
        plan = plan_business_research("   ")
        self.assertEqual(plan.clarification_state, "query_required")
        self.assertEqual(plan.decomposed_queries, ())

    def test_business_context_does_not_override_user_intent(self):
        plan = plan_business_research(
            "Research Acme pricing", domain="pricing",
            business_context={"company": "Different Corp", "preferred_domains": ["acme.example"]},
        )
        self.assertEqual(plan.original_query, "Research Acme pricing")
        self.assertTrue(all("Different Corp" not in query for query in plan.decomposed_queries))
        self.assertEqual(plan.preferred_domains, ("acme.example",))


if __name__ == "__main__":
    unittest.main()
