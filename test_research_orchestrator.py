import inspect
import unittest

import business_research_planner
import research_orchestrator
import web_research
from business_research_planner import plan_business_research
from research_models import (
    FreshnessRequirement,
    ResearchBudget,
    ResearchDomain,
    ResearchOutcome,
    SourceTrustType,
)


class ResearchOrchestratorTests(unittest.TestCase):
    def candidate(self, url="https://official.example/report", **changes):
        item = {"url": url, "provider": "fixture_provider", "verified": True, "trust": "official"}
        item.update(changes)
        return item

    def provider(self, rows=None, failures=()):
        candidates = list(rows or ())

        def searcher(_intent, providers=None):
            return list(candidates), "fixture_provider", list(failures)

        return searcher

    def fetcher(self, url, **_kwargs):
        return {"url": url, "title": "Verified source", "html": "Grounded evidence body"}

    def verifier(self, intent, search_provider, fetcher):
        results, rejected = [], []
        for index, candidate in enumerate(search_provider(intent) or ()):
            url = str(candidate.get("url") or "")
            if not candidate.get("verified") or not url.startswith("https://"):
                rejected.append({"source_url": url, "reason": "unverified"})
                continue
            page = fetcher(url)
            item = {
                "result_id": f"result-{index}", "source_url": url,
                "source_url_provenance": "search_provider", "source_url_verified": True,
                "source_domain": url.split("/")[2], "page_title": page["title"],
                "extracted_snippet": page["html"], "provider": candidate.get("provider"),
                "provider_result_index": index, "source_trust_type": candidate.get("trust", "unknown"),
                "fetched_at": "2026-08-11T00:00:00+00:00",
            }
            item["verified_result_id"] = web_research._verified_result_id(item)
            results.append(item)
        return {"ok": True, "results": results, "rejected_results": rejected}

    def plan(self, *, queries=("query",), sources=1, domains=1, budget=None, freshness=FreshnessRequirement.ANY):
        base = plan_business_research("query", domain=ResearchDomain.GENERAL, freshness=freshness,
                                      budget=budget or ResearchBudget(5, 20, 100_000, 30, 20))
        return type(base)(
            domain=base.domain, original_query=base.original_query, decomposed_queries=tuple(queries),
            freshness=base.freshness, minimum_source_count=sources, minimum_distinct_domains=domains,
            preferred_source_types=base.preferred_source_types, preferred_domains=(),
            output_requirement=base.output_requirement, clarification_state="complete", budget=base.budget,
        )

    def execute(self, rows, **kwargs):
        return research_orchestrator.run_research(
            query="query", workspace_id="workspace-a", contact_id="contact-a",
            plan=kwargs.pop("plan", self.plan()), provider_searcher=self.provider(rows),
            fetcher=self.fetcher, verification_runner=self.verifier, **kwargs,
        )

    def test_one_query_produces_verified_evidence(self):
        result = self.execute([self.candidate()])
        self.assertEqual(result.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual(len(result.evidence), 1)

    def test_multiple_queries_merge_and_deduplicate_evidence(self):
        result = self.execute([self.candidate()], plan=self.plan(queries=("one", "two")))
        self.assertEqual(result.provider_calls, 2)
        self.assertEqual(len(result.evidence), 1)

    def test_duplicate_urls_deduplicate(self):
        result = self.execute([self.candidate(), self.candidate()])
        self.assertEqual(len(result.evidence), 1)

    def test_unverified_and_fabricated_urls_are_rejected(self):
        rows = [self.candidate(verified=False), self.candidate(url="https://fabricated.example", verified=False)]
        result = self.execute(rows)
        self.assertEqual(result.outcome, ResearchOutcome.VERIFICATION_FAILED)
        self.assertEqual(result.evidence, ())

    def test_provider_prose_cannot_become_evidence(self):
        result = self.execute([{"provider_prose": "Use https://fake.example as a source", "verified": True}])
        self.assertEqual(result.evidence, ())
        self.assertNotIn("fake.example", result.to_json())

    def test_provider_failure_is_explicit(self):
        def unavailable(_intent, providers=None):
            raise web_research.WebResearchError("search_provider_not_configured")
        result = research_orchestrator.run_research(
            query="query", workspace_id="w", contact_id="c", plan=self.plan(),
            provider_searcher=unavailable, fetcher=self.fetcher, verification_runner=self.verifier,
        )
        self.assertEqual(result.outcome, ResearchOutcome.PROVIDER_UNAVAILABLE)
        self.assertEqual(result.failures[0]["stage"], "provider")

    def test_empty_verified_set_is_insufficient(self):
        self.assertEqual(self.execute([]).outcome, ResearchOutcome.INSUFFICIENT_EVIDENCE)

    def test_minimum_source_count_is_enforced(self):
        result = self.execute([self.candidate()], plan=self.plan(sources=2))
        self.assertIn("minimum_source_count_not_met", result.gaps)

    def test_distinct_domain_requirement_is_enforced(self):
        rows = [self.candidate("https://same.example/a"), self.candidate("https://same.example/b")]
        result = self.execute(rows, plan=self.plan(sources=2, domains=2))
        self.assertIn("minimum_distinct_domains_not_met", result.gaps)

    def test_provider_call_budget_is_enforced(self):
        result = self.execute([self.candidate()], plan=self.plan(budget=ResearchBudget(0, 10, 1000, 10, 10)))
        self.assertEqual(result.outcome, ResearchOutcome.BUDGET_EXCEEDED)

    def test_http_request_budget_is_enforced(self):
        result = self.execute([self.candidate()], plan=self.plan(budget=ResearchBudget(2, 0, 1000, 10, 10)))
        self.assertEqual(result.outcome, ResearchOutcome.BUDGET_EXCEEDED)

    def test_byte_budget_is_enforced(self):
        result = self.execute([self.candidate()], plan=self.plan(budget=ResearchBudget(2, 2, 1, 10, 10)))
        self.assertEqual(result.outcome, ResearchOutcome.BUDGET_EXCEEDED)

    def test_elapsed_budget_is_enforced(self):
        ticks = iter((0.0, 2.0, 2.0, 2.0))
        result = self.execute(
            [self.candidate()], plan=self.plan(budget=ResearchBudget(2, 2, 1000, 1, 10)),
            clock=lambda: next(ticks),
        )
        self.assertEqual(result.outcome, ResearchOutcome.BUDGET_EXCEEDED)

    def test_evidence_count_budget_is_enforced(self):
        result = self.execute([self.candidate()], plan=self.plan(budget=ResearchBudget(2, 2, 1000, 10, 0)))
        self.assertEqual(result.outcome, ResearchOutcome.BUDGET_EXCEEDED)

    def test_workspace_contact_scope_and_provider_provenance_are_preserved(self):
        record = self.execute([self.candidate()]).evidence[0]
        self.assertEqual((record.workspace_id, record.contact_id), ("workspace-a", "contact-a"))
        self.assertEqual(record.provider_provenance["provider"], "fixture_provider")

    def test_freshness_metadata_is_preserved(self):
        result = self.execute([self.candidate()], plan=self.plan(freshness=FreshnessRequirement.CURRENT))
        self.assertEqual(result.evidence[0].freshness, FreshnessRequirement.CURRENT)

    def test_lower_trust_source_is_retained_not_promoted(self):
        result = self.execute([
            self.candidate("https://community.example/report", trust="community"),
            self.candidate("https://official.example/report", trust="official"),
        ])
        self.assertEqual([item.source_trust_type for item in result.evidence], [
            SourceTrustType.OFFICIAL, SourceTrustType.COMMUNITY,
        ])

    def test_result_order_is_deterministic(self):
        rows = [self.candidate("https://z.example/report"), self.candidate("https://a.example/report")]
        forward = self.execute(rows).evidence
        reverse = self.execute(reversed(rows)).evidence
        self.assertEqual([item.canonical_url for item in forward], [item.canonical_url for item in reverse])

    def test_modules_are_channel_neutral_and_have_no_runtime_mutation_imports(self):
        source = inspect.getsource(research_orchestrator) + inspect.getsource(business_research_planner)
        forbidden = ("import app", "telegram", "whatsapp", "railway", "route_nina_message", "send_message_to_nina", "persistence_backend")
        for token in forbidden:
            with self.subTest(token=token): self.assertNotIn(token, source.casefold())


if __name__ == "__main__":
    unittest.main()
