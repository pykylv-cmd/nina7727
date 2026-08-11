from datetime import datetime, timezone
import inspect
import os
import tempfile
import unittest
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()

from business_research_planner import plan_business_research
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
    VerifiedSourceLink,
)
from research_synthesis import synthesize_research


class OneNinaResearchIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "research-one-nina.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import managed_migrations
        import nina_message_service
        import work_objects
        cls.messaging = nina_message_service
        cls.work = work_objects
        cls.original_work = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        cls.original_message = (nina_message_service.DATABASE_URL, nina_message_service.DB_FILE, nina_message_service.USE_POSTGRES)
        work_objects.DATABASE_URL = ""
        work_objects.DB_FILE = cls.db_file
        work_objects.USE_POSTGRES = False
        work_objects._SCHEMA_READY = False
        nina_message_service.DATABASE_URL = ""
        nina_message_service.DB_FILE = cls.db_file
        nina_message_service.USE_POSTGRES = False
        cls.restore = bind_sqlite_database(cls.db_file, work_objects)
        managed_migrations.run_migrations()

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.work.DATABASE_URL, cls.work.DB_FILE, cls.work.USE_POSTGRES = cls.original_work
        cls.messaging.DATABASE_URL, cls.messaging.DB_FILE, cls.messaging.USE_POSTGRES = cls.original_message
        cls.work._SCHEMA_READY = False
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.work.ensure_work_objects_schema()
        conn = self.work._connect()
        conn.execute("DELETE FROM nina_work_objects")
        conn.execute("DELETE FROM conversation_state")
        conn.commit()
        conn.close()

    def evidence(self):
        fragment = EvidenceFragment(
            "fragment-one", "Acme public facts are verified.", "evidence-one",
            "https://official.example/report", {"line": 1},
        )
        return EvidenceRecord(
            "evidence-one", "https://official.example/report", "https://official.example/report",
            "Official report", "official.example", SourceTrustType.OFFICIAL,
            "2026-08-11", "2026-08-11T12:00:00+00:00", "hash-one", (fragment,),
            VerificationState.VERIFIED, "", {
                "provider": "verified_provider", "provenance": "search_provider", "provider_result_index": 0,
            }, FreshnessRequirement.CURRENT, "tenant-a", "contact-linked",
        )

    def result(self, plan=None, outcome=ResearchOutcome.COMPLETED, evidence=None):
        selected = plan or plan_business_research("Atrodi informāciju par Acme")
        rows = (self.evidence(),) if evidence is None else tuple(evidence)
        return ResearchResult(
            ResearchJobState.COMPLETED if outcome is ResearchOutcome.COMPLETED else ResearchJobState.FAILED,
            outcome, selected, rows, (), (), 1, 1 if rows else 0, 100 if rows else 0, 1.0,
        )

    def send(self, text, channel="web"):
        envelope = self.messaging.NinaMessageEnvelope(
            text=text, workspace_id="tenant-a", channel=channel,
            conversation_id=f"contact:contact-linked:{channel}", contact_id="contact-linked",
            canonical_work_workspace_id="tenant-a", delivery_recipient="recipient",
        )
        return self.messaging.route_nina_message(envelope, generator=lambda _: "ordinary shared reply")

    def research_patches(self, fake_run, fake_synthesis=None):
        return (
            patch("web_research.latest_research_session", return_value=None),
            patch("web_research.save_research_session", return_value="session-one"),
            patch("research_orchestrator.run_research", side_effect=fake_run),
            patch("research_synthesis.synthesize_research", side_effect=fake_synthesis or synthesize_research),
        )

    def invoke(self, text, *, channel="web", outcome=ResearchOutcome.COMPLETED, evidence=None, synthesis=None):
        calls = []
        def fake_run(**kwargs):
            calls.append(kwargs)
            return self.result(kwargs["plan"], outcome=outcome, evidence=evidence)
        contexts = self.research_patches(fake_run, synthesis)
        with contexts[0], contexts[1], contexts[2], contexts[3]:
            response = self.send(text, channel)
        return response, calls

    def test_explicit_web_search_invokes_research_v1_and_verified_link(self):
        response, calls = self.invoke("Atrodi informāciju par Acme")
        self.assertEqual(len(calls), 1)
        self.assertEqual(response["source"], "web_research")
        self.assertIn("Acme public facts are verified.", response["text"])
        self.assertIn("https://official.example/report", response["text"])
        self.assertNotIn("evidence-one", response["text"])
        self.assertNotIn("fragment-one", response["text"])

    def test_research_v1_session_adapter_retains_only_verified_links(self):
        import web_research
        payload = web_research.research_result_to_session_payload(self.result())
        verified = web_research.verified_results(payload)
        self.assertEqual([item["source_url"] for item in verified], ["https://official.example/report"])
        self.assertIn("https://official.example/report", web_research.summarize_verified_links(payload))

    def test_business_research_domains_invoke_typed_planner(self):
        cases = (
            ("Atrodi informāciju par uzņēmumu Acme", ResearchDomain.COMPANY),
            ("Atrodi Acme konkurentu salīdzinājumu", ResearchDomain.COMPETITOR),
            ("Atrodi AI CRM tirgus trendus", ResearchDomain.MARKET),
            ("Atrodi Acme cenas", ResearchDomain.PRICING),
            ("Atrodi aktuālās Acme ziņas", ResearchDomain.NEWS),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                response, calls = self.invoke(query)
                self.assertEqual(calls[0]["plan"].domain, expected)
                self.assertTrue(response["ok"])

    def test_fabricated_urls_from_synthesis_cannot_render(self):
        record = self.evidence()
        malicious = GroundedResearchAnswer(
            "Answer https://fabricated.example", ("Fact https://fabricated.example/x",), (), (),
            (VerifiedSourceLink("Fake", "https://fabricated.example/x", ("bad",), ("bad",), SourceTrustType.UNKNOWN),),
            (), ResearchOutcome.COMPLETED, "Current.", False,
        )
        response, _ = self.invoke(
            "Atrodi informāciju par Acme", synthesis=lambda _result: malicious,
        )
        self.assertNotIn("fabricated.example", response["text"])
        self.assertNotIn("evidence-one", response["text"])

    def test_insufficient_evidence_fails_closed(self):
        response, _ = self.invoke(
            "Atrodi informāciju par Acme", outcome=ResearchOutcome.INSUFFICIENT_EVIDENCE, evidence=(),
        )
        self.assertFalse(response["ok"])
        self.assertIn("Neizdomāšu", response["text"])
        self.assertNotIn("https://", response["text"])

    def test_provider_unavailable_fails_closed(self):
        response, _ = self.invoke(
            "Atrodi informāciju par Acme", outcome=ResearchOutcome.PROVIDER_UNAVAILABLE, evidence=(),
        )
        self.assertFalse(response["ok"])
        self.assertEqual(response["research_outcome"], "provider_unavailable")
        self.assertIn("publisko avotu meklēšanu", response["text"])

    def test_renderer_cannot_leak_synthesis_content_for_incomplete_outcomes(self):
        malicious = GroundedResearchAnswer(
            "Completed-looking answer.", ("Leaked partial finding.",), (), (),
            (VerifiedSourceLink(
                "Official report", "https://official.example/report",
                ("evidence-one",), ("claim-one",), SourceTrustType.OFFICIAL,
            ),),
            ("evidence-one",), ResearchOutcome.COMPLETED, "Current.", False,
        )
        for outcome in (
            ResearchOutcome.BUDGET_EXCEEDED,
            ResearchOutcome.PROVIDER_UNAVAILABLE,
            ResearchOutcome.VERIFICATION_FAILED,
            ResearchOutcome.INSUFFICIENT_EVIDENCE,
        ):
            with self.subTest(outcome=outcome.value):
                response, _ = self.invoke(
                    "Atrodi informāciju par Acme", outcome=outcome,
                    synthesis=lambda _result: malicious,
                )
                self.assertFalse(response["ok"])
                self.assertEqual(response["research_outcome"], outcome.value)
                self.assertNotIn("Leaked partial finding", response["text"])
                self.assertNotIn("https://", response["text"])

    def test_contradiction_remains_visible(self):
        record = self.evidence()
        claim = ClaimEvidence(
            "claim-one", record.fragments[0].text, (record.evidence_id,),
            (record.fragments[0].fragment_id,), ClaimSupportState.CONTRADICTED,
        )
        contradictory = synthesize_research(self.result(evidence=(record,)), claims=(claim,))
        response, _ = self.invoke(
            "Atrodi informāciju par Acme", synthesis=lambda _result: contradictory,
        )
        self.assertIn("atšķiras", response["text"])

    def test_normal_chat_does_not_trigger_research(self):
        with patch("research_orchestrator.run_research") as run:
            response = self.send("kā tev iet?")
        run.assert_not_called()
        self.assertEqual(response["text"], "ordinary shared reply")

    def test_reminder_creation_and_pending_continuation_do_not_trigger_research(self):
        with patch("research_orchestrator.run_research") as run:
            pending = self.send("Atgādini man nopirkt pienu")
            completed = self.send("rīt 9:00")
        run.assert_not_called()
        self.assertEqual(pending["source"], "brain_clarification")
        self.assertTrue(completed["ok"])

    def test_all_channels_reach_the_same_shared_capability(self):
        for channel in ("web", "telegram", "whatsapp_company"):
            response, calls = self.invoke("Atrodi informāciju par Acme", channel=channel)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["workspace_id"], "tenant-a")
            self.assertEqual(calls[0]["contact_id"], "contact-linked")
            self.assertEqual(response["source"], "web_research")

    def test_no_channel_specific_research_implementation_exists(self):
        service_source = inspect.getsource(self.messaging.send_message_to_nina)
        self.assertEqual(service_source.count("run_research("), 1)
        self.assertNotIn("channel == \"telegram\"", service_source)
        self.assertNotIn("channel == \"whatsapp_company\"", service_source)


if __name__ == "__main__":
    unittest.main()
