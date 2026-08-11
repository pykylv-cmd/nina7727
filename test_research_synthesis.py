from dataclasses import replace
from datetime import datetime, timezone
import inspect
import json
import unittest

from research_models import (
    ClaimEvidence,
    ClaimSupportState,
    EvidenceFragment,
    EvidenceRecord,
    FreshnessRequirement,
    GroundedResearchAnswer,
    ResearchBudget,
    ResearchDomain,
    ResearchJobState,
    ResearchOutcome,
    ResearchPlan,
    ResearchResult,
    SourceTrustType,
    VerificationState,
)
import research_synthesis


AS_OF = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


class ResearchSynthesisTests(unittest.TestCase):
    def plan(self, freshness=FreshnessRequirement.ANY):
        return ResearchPlan(
            ResearchDomain.GENERAL, "query", ("query",), freshness, 1, 1,
            (SourceTrustType.OFFICIAL,), (), "answer", "complete",
            ResearchBudget(1, 1, 1000, 10, 5),
        )

    def evidence(self, suffix="one", *, trust=SourceTrustType.OFFICIAL,
                 published="2026-08-11", fetched="2026-08-11T10:00:00+00:00",
                 text="Supported factual finding."):
        evidence_id = "evidence_" + suffix
        fragment = EvidenceFragment("fragment_" + suffix, text, evidence_id, f"https://{suffix}.example/report", {"line": 1})
        return EvidenceRecord(
            evidence_id, f"https://{suffix}.example/report", f"https://{suffix}.example/report",
            suffix.title(), f"{suffix}.example", trust, published, fetched, "hash-" + suffix,
            (fragment,), VerificationState.VERIFIED, "", {"provider": "verified"},
            FreshnessRequirement.CURRENT, "workspace-a", "contact-a",
        )

    def result(self, evidence=(), *, freshness=FreshnessRequirement.ANY, gaps=(), failures=()):
        return ResearchResult(
            ResearchJobState.COMPLETED, ResearchOutcome.COMPLETED, self.plan(freshness),
            tuple(evidence), tuple(failures), tuple(gaps), 1, len(tuple(evidence)), 100, 1.0,
        )

    def claim(self, record, *, state=ClaimSupportState.SUPPORTED, text="Supported factual finding.", claim_id="claim-one"):
        return ClaimEvidence(claim_id, text, (record.evidence_id,), (record.fragments[0].fragment_id,), state)

    def synthesize(self, result, claims=None):
        return research_synthesis.synthesize_research(result, claims=claims, as_of=AS_OF)

    def test_supported_single_claim_renders(self):
        record = self.evidence()
        answer = self.synthesize(self.result((record,)), (self.claim(record),))
        self.assertEqual(answer.findings, ("Supported factual finding.",))
        self.assertFalse(answer.insufficient_evidence)

    def test_unsupported_claim_is_excluded_and_flagged(self):
        record = self.evidence()
        unsupported = replace(self.claim(record), fragment_ids=("fragment_missing",))
        answer = self.synthesize(self.result((record,)), (unsupported,))
        self.assertEqual(answer.findings, ())
        self.assertTrue(answer.insufficient_evidence)
        self.assertIn("unsupported_claims:1", answer.risks_or_gaps)

    def test_fabricated_url_is_rejected(self):
        record = self.evidence()
        claim = self.claim(record, text="Claim from https://fabricated.example/report")
        answer = self.synthesize(self.result((record,)), (claim,))
        self.assertEqual(answer.findings, ())
        self.assertNotIn("fabricated.example", json.dumps([link.to_dict() for link in answer.source_links]))

    def test_generated_url_not_in_evidence_is_rejected(self):
        record = self.evidence()
        claim = self.claim(record, text="Generated https://one.example/guessed")
        self.assertTrue(self.synthesize(self.result((record,)), (claim,)).insufficient_evidence)

    def test_multi_source_synthesis(self):
        one, two = self.evidence("one"), self.evidence("two", text="Second fact.")
        claims = (self.claim(one), self.claim(two, text="Second fact.", claim_id="claim-two"))
        answer = self.synthesize(self.result((one, two)), claims)
        self.assertEqual(len(answer.findings), 2)
        self.assertEqual(len(answer.source_links), 2)

    def test_duplicate_citations_deduplicate(self):
        record = self.evidence()
        claims = (self.claim(record), self.claim(record, claim_id="claim-two"))
        answer = self.synthesize(self.result((record,)), claims)
        self.assertEqual(len(answer.source_links), 1)
        self.assertEqual(answer.source_links[0].claim_ids, ("claim-one", "claim-two"))

    def test_contradictory_evidence_is_surfaced(self):
        record = self.evidence()
        claim = self.claim(record, state=ClaimSupportState.CONTRADICTED)
        answer = self.synthesize(self.result((record,)), (claim,))
        self.assertIn("verified_sources_contradict", answer.risks_or_gaps)
        self.assertIn("disagree", answer.summary)

    def test_insufficient_research_result_is_surfaced(self):
        result = replace(self.result(), outcome=ResearchOutcome.INSUFFICIENT_EVIDENCE, gaps=("minimum_source_count_not_met",))
        answer = self.synthesize(result)
        self.assertTrue(answer.insufficient_evidence)
        self.assertIn("minimum_source_count_not_met", answer.risks_or_gaps)

    def test_current_research_with_stale_evidence_fails_freshness(self):
        stale = self.evidence(published="2025-01-01", fetched="2025-01-02T00:00:00+00:00")
        answer = self.synthesize(self.result((stale,), freshness=FreshnessRequirement.CURRENT), (self.claim(stale),))
        self.assertTrue(answer.insufficient_evidence)
        self.assertEqual(answer.findings, ())
        self.assertIn("freshness_excluded_evidence:1", answer.risks_or_gaps)

    def test_recent_evidence_note_works(self):
        record = self.evidence(published="2026-07-15")
        answer = self.synthesize(self.result((record,), freshness=FreshnessRequirement.RECENT), (self.claim(record),))
        self.assertEqual(answer.freshness_note, "Recent evidence requirement met.")

    def test_lower_trust_source_does_not_outrank_official(self):
        community = self.evidence("a-community", trust=SourceTrustType.COMMUNITY)
        official = self.evidence("z-official", trust=SourceTrustType.OFFICIAL)
        claims = (self.claim(community, claim_id="community"), self.claim(official, claim_id="official"))
        answer = self.synthesize(self.result((community, official)), claims)
        self.assertEqual([link.source_trust_type for link in answer.source_links], [
            SourceTrustType.OFFICIAL, SourceTrustType.COMMUNITY,
        ])

    def test_source_links_only_use_verified_evidence(self):
        record = self.evidence()
        rejected = replace(self.evidence("rejected"), verification_state=VerificationState.REJECTED)
        answer = self.synthesize(self.result((record, rejected)), (self.claim(record), self.claim(rejected, claim_id="bad")))
        self.assertEqual([link.url for link in answer.source_links], [record.canonical_url])

    def test_claim_evidence_fragment_binding_is_preserved(self):
        record = self.evidence()
        answer = self.synthesize(self.result((record,)), (self.claim(record),))
        self.assertEqual(answer.claims[0].evidence_ids, (record.evidence_id,))
        self.assertEqual(answer.claims[0].fragment_ids, (record.fragments[0].fragment_id,))
        self.assertEqual(answer.source_links[0].claim_ids, ("claim-one",))

    def test_output_ordering_is_deterministic(self):
        one, two = self.evidence("one"), self.evidence("two")
        claims = (self.claim(two, claim_id="two"), self.claim(one, claim_id="one"))
        first = self.synthesize(self.result((two, one)), claims)
        second = self.synthesize(self.result((one, two)), tuple(reversed(claims)))
        self.assertEqual(first.source_links, second.source_links)
        self.assertEqual(first.evidence_ids_used, second.evidence_ids_used)
        self.assertEqual(first.findings, second.findings)
        self.assertEqual(first.claims, second.claims)

    def test_serialization_round_trip(self):
        record = self.evidence()
        answer = self.synthesize(self.result((record,)), (self.claim(record),))
        restored = GroundedResearchAnswer.from_dict(json.loads(answer.to_json()))
        self.assertEqual(restored, answer)
        self.assertEqual(restored.to_json(), answer.to_json())

    def test_synthesis_has_no_provider_or_http_call_path(self):
        source = inspect.getsource(research_synthesis)
        for token in ("provider_search", "fetch_public_page", "urlopen", "requests.", "httpx."):
            with self.subTest(token=token): self.assertNotIn(token, source)

    def test_synthesis_has_no_database_mutation_path(self):
        source = inspect.getsource(research_synthesis)
        for token in ("persistence_backend", "connect(", "execute(", "commit(", "insert ", "update ", "delete "):
            with self.subTest(token=token): self.assertNotIn(token, source.casefold())

    def test_result_failures_are_preserved_as_gaps(self):
        record = self.evidence()
        result = self.result((record,), gaps=("diversity_gap",), failures=({"stage": "provider", "error": "provider_timeout"},))
        answer = self.synthesize(result, (self.claim(record),))
        self.assertIn("diversity_gap", answer.risks_or_gaps)
        self.assertIn("provider_timeout", answer.risks_or_gaps)


if __name__ == "__main__":
    unittest.main()
