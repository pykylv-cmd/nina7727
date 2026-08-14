from datetime import datetime, timezone
import unittest

from business_research_bridge import execute_business_research_need
from business_thinking_models import EvidenceConfidence, ResearchNeed, StrategicPriority
from business_research_planner import plan_business_research
from research_models import (
    ClaimEvidence, ClaimSupportState, EvidenceFragment, EvidenceRecord, FreshnessRequirement,
    GroundedResearchAnswer, ResearchJobState, ResearchOutcome, ResearchResult, ResearchDomain,
    SourceTrustType, VerificationState, VerifiedSourceLink,
)
from research_synthesis import synthesize_research


class BusinessResearchBridgeTests(unittest.TestCase):
    def need(self, *, domain=ResearchDomain.COMPETITOR, freshness=FreshnessRequirement.CURRENT):
        return ResearchNeed("Kādas ir konkurenta cenas?", domain, freshness,
                            StrategicPriority.HIGH, "Pricing affects market entry.")

    def result(self, *, outcome=ResearchOutcome.COMPLETED, url="https://verified.example/pricing",
               fetched_at=None, workspace="workspace-a", contact="contact-a"):
        plan = plan_business_research("Kādas ir konkurenta cenas?", domain=ResearchDomain.COMPETITOR,
                                      freshness=FreshnessRequirement.CURRENT)
        fragment = EvidenceFragment("fragment-1", "Konkurenta cena ir publicēta cenu lapā.", "body", {})
        record = EvidenceRecord(
            "evidence-1", url, url, "Pricing", "verified.example", SourceTrustType.OFFICIAL,
            "", fetched_at or datetime.now(timezone.utc).isoformat(), "hash", (fragment,),
            VerificationState.VERIFIED, "", {"provider": "fixture"}, FreshnessRequirement.CURRENT,
            workspace, contact,
        )
        return ResearchResult(
            ResearchJobState.COMPLETED if outcome is ResearchOutcome.COMPLETED else ResearchJobState.FAILED,
            outcome, plan, (record,), (), (), 1, 1, 100, .1,
        )

    def execute(self, result=None, **kwargs):
        fixed = result or self.result()
        return execute_business_research_need(
            self.need(), workspace_id="workspace-a", contact_id="contact-a",
            runner=lambda **_kwargs: fixed, **kwargs,
        )

    def test_research_need_maps_domain_and_freshness(self):
        seen = {}
        def planner(query, **kwargs):
            seen.update(kwargs)
            return plan_business_research(query, **kwargs)
        self.execute(planner=planner)
        self.assertEqual(seen["domain"], ResearchDomain.COMPETITOR)
        self.assertEqual(seen["freshness"], FreshnessRequirement.CURRENT)

    def test_public_research_keeps_owner_context_out_of_verification_query(self):
        seen = {}
        fixed = self.result()
        def planner(query, **kwargs):
            seen["planner_query"] = query
            return plan_business_research(query, **kwargs)
        def runner(**kwargs):
            seen["runner_query"] = kwargs["query"]
            return fixed
        execute_business_research_need(
            self.need(), workspace_id="workspace-a", contact_id="contact-a",
            query_context="Kā NinaOS var pārspēt Sintra AI?", planner=planner, runner=runner,
        )
        self.assertEqual(seen["planner_query"], "Kādas ir konkurenta cenas?")
        self.assertNotIn("NinaOS", seen["planner_query"])
        self.assertEqual(seen["planner_query"], seen["runner_query"])

    def test_named_competitor_offer_and_pricing_queries_are_focused(self):
        from business_research_bridge import _focused_research_query
        offer = ResearchNeed("Ko Sintra AI pašlaik piedāvā klientiem?", ResearchDomain.COMPETITOR,
                             FreshnessRequirement.CURRENT, StrategicPriority.HIGH, "verify offer")
        pricing = ResearchNeed("Kādas ir Sintra AI pašreizējās publiskās cenas?", ResearchDomain.COMPETITOR,
                               FreshnessRequirement.CURRENT, StrategicPriority.HIGH, "verify pricing")
        features = ResearchNeed("Kādas publiski verificējamas Sintra AI funkcijas, integrācijas un ierobežojumi ir būtiski?",
                                ResearchDomain.COMPETITOR, FreshnessRequirement.CURRENT,
                                StrategicPriority.HIGH, "verify capabilities")
        self.assertEqual(_focused_research_query(offer), "Sintra AI offer")
        self.assertEqual(_focused_research_query(pricing), "Sintra AI pricing")
        self.assertEqual(_focused_research_query(features), "Sintra AI features integrations")

    def test_focused_query_is_not_sintra_hard_coded(self):
        from business_research_bridge import _focused_research_query
        need = ResearchNeed("Kādas ir Acme Cloud pašreizējās publiskās cenas?", ResearchDomain.COMPETITOR,
                            FreshnessRequirement.CURRENT, StrategicPriority.HIGH, "verify pricing")
        self.assertEqual(_focused_research_query(need), "Acme Cloud pricing")

    def test_completed_research_creates_business_fact(self):
        bridged = self.execute()
        self.assertEqual(len(bridged.facts), 1)
        self.assertEqual(bridged.confidence, EvidenceConfidence.HIGH)

    def test_non_completed_research_creates_no_fact(self):
        bridged = self.execute(self.result(outcome=ResearchOutcome.BUDGET_EXCEEDED))
        self.assertEqual(bridged.facts, ())
        self.assertEqual(bridged.source_links, ())

    def test_fabricated_url_cannot_cross_bridge(self):
        result = self.result()
        answer = synthesize_research(result)
        fake = VerifiedSourceLink("Fake", "https://fabricated.example", ("evidence-1",), ("claim-1",), SourceTrustType.OFFICIAL)
        tampered = GroundedResearchAnswer(
            answer.summary, answer.findings, answer.claims, answer.risks_or_gaps,
            answer.source_links + (fake,), answer.evidence_ids_used, answer.outcome,
            answer.freshness_note, answer.insufficient_evidence,
        )
        bridged = self.execute(result, synthesizer=lambda _result: tampered)
        self.assertNotIn("https://fabricated.example", bridged.to_json())

    def test_evidence_ids_are_preserved(self):
        self.assertEqual(self.execute().facts[0].evidence_ids, ("evidence-1",))

    def test_source_links_are_verified_only(self):
        self.assertEqual(self.execute().source_links, ("https://verified.example/pricing",))

    def test_workspace_and_contact_scope_are_preserved(self):
        bridged = self.execute()
        self.assertEqual((bridged.workspace_id, bridged.contact_id), ("workspace-a", "contact-a"))

    def test_cross_contact_evidence_cannot_become_business_fact(self):
        bridged = self.execute(self.result(contact="contact-b"))
        self.assertEqual(bridged.facts, ())
        self.assertEqual(bridged.source_links, ())

    def test_contradictory_evidence_is_preserved(self):
        result = self.result()
        answer = synthesize_research(result)
        contradicted = GroundedResearchAnswer(
            "Verified sources disagree.", answer.findings,
            (ClaimEvidence("claim-1", "Pricing differs.", ("evidence-1",), ("fragment-1",), ClaimSupportState.CONTRADICTED),),
            ("verified_sources_contradict",), answer.source_links, ("evidence-1",),
            ResearchOutcome.COMPLETED, answer.freshness_note, False,
        )
        bridged = self.execute(result, synthesizer=lambda _result: contradicted)
        self.assertIn("verified_sources_contradict", bridged.gaps)
        self.assertEqual(bridged.facts[0].confidence, EvidenceConfidence.MEDIUM)

    def test_stale_current_evidence_cannot_become_current_fact(self):
        stale = self.result(fetched_at="2020-01-01T00:00:00+00:00")
        bridged = self.execute(stale)
        self.assertEqual(bridged.facts, ())
        self.assertTrue(any("freshness" in gap for gap in bridged.gaps))

    def test_failure_reason_is_explicit(self):
        bridged = self.execute(self.result(outcome=ResearchOutcome.PROVIDER_UNAVAILABLE))
        self.assertEqual(bridged.failure_reason, "provider_unavailable")


if __name__ == "__main__":
    unittest.main()
