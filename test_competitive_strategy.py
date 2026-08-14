import inspect
import unittest

import competitive_strategy
from business_thinking_models import EvidenceConfidence
from competitive_strategy import analyze_competitive_strategy


class CompetitiveStrategyTests(unittest.TestCase):
    def test_competitor_gap_detected(self):
        result = analyze_competitive_strategy({"onboarding": {"own": 1, "competitor": 3, "evidence": ["test"]}})
        self.assertEqual(result.gaps[0].dimension, "onboarding")

    def test_legitimate_attack_surface_detected(self):
        result = analyze_competitive_strategy({"price": {"own": 1, "competitor": 3, "evidence": ["price page"]}})
        self.assertIn("customer", result.attack_surfaces[0].customer_value.casefold())

    def test_no_harmful_action_is_generated(self):
        result = analyze_competitive_strategy({"service": {"own": 1, "competitor": 2, "evidence": ["survey"]}})
        rendered = result.to_json().casefold()
        for prohibited in ("sabotage", "deception", "intrusion", "data theft"):
            self.assertIn(prohibited, rendered)
        self.assertNotIn("perform sabotage", rendered)

    def test_competitor_strength_is_acknowledged(self):
        result = analyze_competitive_strategy({"reliability": {"own": 1, "competitor": 4, "evidence": ["SLA"]}})
        self.assertIn("competitor is stronger", result.gaps[0].description.casefold())

    def test_advantage_requires_evidence(self):
        result = analyze_competitive_strategy({"ux": {"own": 4, "competitor": 1}})
        self.assertEqual(result.advantages, ())
        self.assertIn("ux", result.unknown_dimensions)

    def test_verified_advantage_is_returned(self):
        result = analyze_competitive_strategy({"distribution": {
            "own": 4, "competitor": 2, "evidence": ["channel audit"], "confidence": "high",
        }})
        self.assertEqual(result.advantages[0].confidence, EvidenceConfidence.HIGH)

    def test_defensibility_opportunity_for_compounding_dimension(self):
        result = analyze_competitive_strategy({"data_advantage": {"own": 4, "competitor": 1, "evidence": ["audit"]}})
        self.assertEqual(result.defensibility_opportunities[0].dimension, "data_advantage")

    def test_ninaos_fixture_can_show_one_nina_advantage(self):
        result = analyze_competitive_strategy({"personalization": {
            "own": 4, "competitor": 2, "evidence": ["linked cross-channel context test"],
            "advantage": "ONE persistent employee preserves verified context continuity",
        }})
        self.assertIn("ONE persistent", result.advantages[0].description)

    def test_ninaos_fixture_can_show_competitor_advantage(self):
        result = analyze_competitive_strategy({"integrations": {
            "own": 1, "competitor": 4, "evidence": ["integration catalog"],
        }})
        self.assertEqual(result.gaps[0].dimension, "integrations")

    def test_framework_has_all_required_dimensions(self):
        self.assertEqual(len(competitive_strategy.COMPETITIVE_DIMENSIONS), 20)

    def test_module_is_channel_neutral(self):
        source = inspect.getsource(competitive_strategy).casefold()
        self.assertNotIn("telegram", source)
        self.assertNotIn("whatsapp", source)


if __name__ == "__main__":
    unittest.main()
