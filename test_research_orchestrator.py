import inspect
import json
import unittest
from unittest import mock

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
    def logged_payload(self, callback):
        with self.assertLogs("research_orchestrator", level="INFO") as captured:
            result = callback()
        return result, json.loads(captured.output[-1].split(":", 2)[-1])

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

    def test_provider_hints_do_not_become_required_verification_terms(self):
        base = self.plan(queries=("AI companies official company information",))
        plan = type(base)(
            domain=base.domain, original_query="AI companies", decomposed_queries=base.decomposed_queries,
            freshness=base.freshness, minimum_source_count=base.minimum_source_count,
            minimum_distinct_domains=base.minimum_distinct_domains,
            preferred_source_types=base.preferred_source_types, preferred_domains=base.preferred_domains,
            output_requirement=base.output_requirement, clarification_state=base.clarification_state,
            budget=base.budget,
        )
        seen = {}

        def provider(intent, providers=None):
            seen["provider_query"] = intent.query
            return [self.candidate()], "fixture_provider", []

        def verifier(intent, search_provider, fetcher):
            seen["verification_query"] = intent.query
            return self.verifier(intent, search_provider, fetcher)

        result = research_orchestrator.run_research(
            query=plan.original_query, workspace_id="workspace-a", contact_id="contact-a",
            plan=plan, provider_searcher=provider, fetcher=self.fetcher,
            verification_runner=verifier,
        )
        self.assertEqual(result.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual(seen["provider_query"], "AI companies official company information")
        self.assertEqual(seen["verification_query"], "AI companies")

    def test_exact_latvian_company_query_produces_multiple_evidence_records(self):
        query = "Atrodi internetā 3 AI uzņēmumus Latvijā un atsūti avotu saites."
        plan = plan_business_research(query)
        candidates = [
            self.candidate("https://company-one.example/about"),
            self.candidate("https://company-two.example/about"),
            self.candidate("https://company-three.example/about"),
        ]

        def fetcher(url, **_kwargs):
            return {
                "url": url,
                "title": "AI uzņēmums Latvijā",
                "html": "<main>Latvijas AI uzņēmums un tā pakalpojumi.</main>",
            }

        result = research_orchestrator.run_research(
            query=query, workspace_id="workspace-a", contact_id="contact-a",
            plan=plan, provider_searcher=self.provider(candidates), fetcher=fetcher,
            verification_runner=web_research.search_verified_web,
        )
        self.assertEqual(result.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual(len(result.evidence), 3)
        self.assertEqual(len({record.canonical_url for record in result.evidence}), 3)

    def test_focused_sintra_pricing_query_accepts_relevant_verified_page(self):
        plan = self.plan(queries=("Sintra AI pricing",))
        plan = type(plan)(
            domain=ResearchDomain.COMPETITOR, original_query="Sintra AI pricing",
            decomposed_queries=plan.decomposed_queries, freshness=plan.freshness,
            minimum_source_count=1, minimum_distinct_domains=1,
            preferred_source_types=plan.preferred_source_types, preferred_domains=(),
            output_requirement=plan.output_requirement, clarification_state="complete", budget=plan.budget,
        )

        def fetcher(url, **_kwargs):
            return {
                "url": url,
                "title": "Sintra AI Pricing",
                "html": "<main>Sintra AI pricing plans for customers.</main>",
            }

        result = research_orchestrator.run_research(
            query=plan.original_query, workspace_id="workspace-a", contact_id="contact-a",
            plan=plan, provider_searcher=self.provider([
                self.candidate("https://sintra.example/pricing"),
            ]), fetcher=fetcher, verification_runner=web_research.search_verified_web,
        )
        self.assertEqual(result.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0].canonical_url, "https://sintra.example/pricing")

    def test_focused_sintra_query_still_rejects_irrelevant_page(self):
        plan = self.plan(queries=("Sintra AI pricing",))
        plan = type(plan)(
            domain=ResearchDomain.COMPETITOR, original_query="Sintra AI pricing",
            decomposed_queries=plan.decomposed_queries, freshness=plan.freshness,
            minimum_source_count=1, minimum_distinct_domains=1,
            preferred_source_types=plan.preferred_source_types, preferred_domains=(),
            output_requirement=plan.output_requirement, clarification_state="complete", budget=plan.budget,
        )

        def fetcher(url, **_kwargs):
            return {"url": url, "title": "Unrelated page", "html": "<main>Unrelated public content.</main>"}

        result = research_orchestrator.run_research(
            query=plan.original_query, workspace_id="workspace-a", contact_id="contact-a",
            plan=plan, provider_searcher=self.provider([
                self.candidate("https://irrelevant.example/page"),
            ]), fetcher=fetcher, verification_runner=web_research.search_verified_web,
        )
        self.assertEqual(result.outcome, ResearchOutcome.VERIFICATION_FAILED)
        self.assertEqual(result.evidence, ())
        self.assertTrue(any(item.get("reason") == "query_terms_absent" for item in result.failures))

    def test_duplicate_urls_deduplicate(self):
        result = self.execute([self.candidate(), self.candidate()])
        self.assertEqual(len(result.evidence), 1)

    def test_unverified_and_fabricated_urls_are_rejected(self):
        rows = [self.candidate(verified=False), self.candidate(url="https://fabricated.example", verified=False)]
        result = self.execute(rows)
        self.assertEqual(result.outcome, ResearchOutcome.VERIFICATION_FAILED)
        self.assertEqual(result.evidence, ())

    def test_safe_verification_rejection_reason_is_retained(self):
        result = self.execute([self.candidate(url="https://irrelevant.example/page", verified=False)])
        rejection = next(item for item in result.failures if item.get("stage") == "verification")
        self.assertEqual(rejection["reason"], "unverified")
        self.assertEqual(set(rejection), {"query", "stage", "reason", "source_domain"})
        self.assertNotIn("source_url", rejection)

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

    def test_each_budget_dimension_is_logged_exactly(self):
        cases = (
            (ResearchBudget(0, 10, 1000, 10, 10), "provider_calls", None),
            (ResearchBudget(2, 0, 1000, 10, 10), "http_requests", None),
            (ResearchBudget(2, 2, 1, 10, 10), "total_bytes", None),
            (ResearchBudget(2, 2, 1000, 1, 10), "elapsed_seconds", iter((0.0, 2.0, 2.0, 2.0, 2.0))),
            (ResearchBudget(2, 2, 1000, 10, 0), "evidence_records", None),
        )
        for budget, expected, ticks in cases:
            with self.subTest(dimension=expected):
                kwargs = {"clock": lambda: next(ticks)} if ticks is not None else {}
                _, payload = self.logged_payload(lambda b=budget, k=kwargs: self.execute(
                    [self.candidate()], plan=self.plan(budget=b), **k))
                self.assertEqual(payload["event"], "research_budget_exceeded")
                self.assertEqual(payload["limit_dimension"], expected)

    def test_success_logs_safe_counters_without_identity_or_secrets(self):
        result, payload = self.logged_payload(lambda: self.execute([self.candidate()]))
        self.assertEqual(payload["event"], "research_execution_summary")
        self.assertEqual(payload["outcome"], "completed")
        self.assertEqual(payload["verified_evidence_count"], len(result.evidence))
        self.assertEqual(payload["decomposed_query_count"], 1)
        serialized = json.dumps(payload)
        for forbidden in ("workspace-a", "contact-a", "token", "credential", "source_url"):
            self.assertNotIn(forbidden, serialized)

    def test_observability_does_not_change_research_result(self):
        with self.assertLogs("research_orchestrator", level="INFO"):
            observed = self.execute([self.candidate()])
        with mock.patch.object(research_orchestrator.LOGGER, "info"):
            silent = self.execute([self.candidate()])
        self.assertEqual(observed, silent)

    def test_each_research_need_gets_a_fresh_bounded_budget(self):
        plan = self.plan(budget=ResearchBudget(1, 1, 1000, 10, 1))
        first = self.execute([self.candidate()], plan=plan)
        second = self.execute([self.candidate()], plan=plan)
        self.assertEqual(first.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual(second.outcome, ResearchOutcome.COMPLETED)
        self.assertEqual((first.provider_calls, second.provider_calls), (1, 1))
        self.assertEqual((first.http_requests, second.http_requests), (1, 1))

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
