import inspect
import os
import tempfile
import unittest
from unittest.mock import patch

import nina_message_service as messaging
from brain import Decision
from business_thinking_engine import analyze_business_decision, analyze_business_decision_with_evidence
from business_thinking_models import BusinessFact, BusinessFactType, BusinessResearchResult, EvidenceConfidence


class BusinessThinkingOneNinaTests(unittest.TestCase):
    def decision(self, **changes):
        values = dict(reply_required=True, priority="normal", confidence=1.0, reason="general_reply")
        values.update(changes)
        return Decision(**values)

    def result_for_need(self, need, workspace="workspace-a", contact="contact-a", *, completed=True):
        fact_type = BusinessFactType.CUSTOMER if "pieprasījums" in need.question else (
            BusinessFactType.PRICING if "cenas" in need.question else BusinessFactType.ECONOMICS
        )
        facts = (BusinessFact(
            f"Verified {fact_type.value} fact", (f"evidence-{fact_type.value}",),
            (f"https://verified.example/{fact_type.value}",), EvidenceConfidence.HIGH,
            need.freshness, fact_type,
        ),) if completed else ()
        return BusinessResearchResult(
            need, "completed" if completed else "provider_unavailable",
            tuple(fact.evidence_ids[0] for fact in facts), facts,
            tuple(url for fact in facts for url in fact.source_links),
            EvidenceConfidence.HIGH if facts else EvidenceConfidence.UNKNOWN,
            (), "" if facts else "provider_unavailable", workspace, contact,
        )

    def enriched(self, text="Kā mēs varam pārspēt konkurentus?", *, completed=True):
        initial = analyze_business_decision(text, workspace_id="workspace-a", contact_id="contact-a")
        results = tuple(self.result_for_need(need, completed=completed) for need in initial.research_needs)
        return analyze_business_decision_with_evidence(
            text, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
            competitive_comparison={"integrations": {"own": 2, "competitor": 4, "evidence": ["catalog"]}},
            assumptions=({"label": "retention", "value": "retention will improve"},),
        )

    def trigger(self, text, **decision_changes):
        return messaging._is_business_decision_request(text, self.decision(**decision_changes))

    def test_startup_question_triggers(self):
        self.assertTrue(self.trigger("Vai man ir vērts sākt šo biznesu?"))

    def test_competitor_question_triggers(self):
        self.assertTrue(self.trigger("Kā mēs varam pārspēt konkurentus?"))

    def test_pricing_question_triggers(self):
        self.assertTrue(self.trigger("Vai vajag celt cenu?"))

    def test_market_entry_question_triggers(self):
        self.assertTrue(self.trigger("Vai ir vērts ieiet šajā tirgū?"))

    def test_enough_evidence_renders_recommendation_and_action(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("Mans lēmums", rendered)
        self.assertIn("Ko darīt tagad", rendered)

    def test_missing_evidence_is_cautious(self):
        rendered = messaging._render_business_decision(self.enriched(completed=False))
        self.assertIn("vēl nav pietiekami verificēti", rendered)
        self.assertIn("Vēl jāpārbauda", rendered)

    def test_research_need_invokes_existing_bridge(self):
        initial = analyze_business_decision("Vai vajag celt cenu?", workspace_id="workspace-a", contact_id="contact-a")
        calls = []
        def execute(need, **scope):
            calls.append((need, scope))
            return self.result_for_need(need)
        with patch("business_research_bridge.execute_business_research_need", side_effect=execute):
            messaging._run_business_thinking("Vai vajag celt cenu?", "workspace-a", "contact-a")
        self.assertEqual(len(calls), len(initial.research_needs))

    def test_failed_research_creates_no_rendered_fact(self):
        rendered = messaging._render_business_decision(self.enriched(completed=False))
        self.assertNotIn("Verified customer fact", rendered)

    def test_verified_links_only_are_rendered(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("https://verified.example/", rendered)
        self.assertNotIn("fabricated.example", rendered)

    def test_next_best_action_rendered(self):
        self.assertIn("Ko darīt tagad", messaging._render_business_decision(self.enriched()))

    def test_assumptions_remain_labeled(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("Pieņēmumi", rendered)
        self.assertIn("retention will improve", rendered)

    def test_competitor_strength_can_be_acknowledged(self):
        decision = self.enriched()
        self.assertTrue(decision.competitive_analysis.gaps)

    def test_no_ninaos_always_wins_text(self):
        self.assertNotIn("always wins", messaging._render_business_decision(self.enriched()).casefold())

    def test_normal_chat_does_not_trigger(self):
        self.assertFalse(self.trigger("Kā tev iet?"))

    def test_reminder_creation_does_not_trigger(self):
        self.assertFalse(self.trigger("Atgādini pēc 2 minūtēm piezvanīt", create_reminder=True, create_work_object=True))

    def test_pending_reminder_continuation_does_not_trigger(self):
        self.assertFalse(self.trigger("rīt 9:00", create_reminder=True, create_work_object=True))

    def test_explicit_research_stays_research(self):
        self.assertFalse(self.trigger("Atrodi internetā konkurentu cenas un atsūti avotus"))

    def test_url_reader_does_not_trigger(self):
        self.assertFalse(self.trigger("Izlasi https://example.com un pasaki cenu"))

    def test_task_command_does_not_trigger(self):
        self.assertFalse(self.trigger("Uztaisi uzdevumu analizēt tirgu", create_work_object=True))

    def test_memory_profile_statement_does_not_trigger(self):
        self.assertFalse(self.trigger("Atceries, ka mans bizness ir Rīgā"))

    def test_all_channels_use_same_shared_runtime(self):
        question = "Vai vajag celt cenu?"
        decision = self.enriched(question)
        with patch.object(messaging, "_run_business_thinking", return_value=decision), \
             patch.object(messaging, "_save_turn"), \
             patch.object(messaging, "_pending_reminder_context", return_value={}), \
             patch.object(messaging, "_pending_destructive_context", return_value={}), \
             patch.object(messaging, "_action_context", return_value={}):
            outputs = []
            for channel in ("web", "telegram", "company_whatsapp"):
                envelope = messaging.NinaMessageEnvelope(question, "workspace-a", channel, f"conversation-{channel}", "contact-a")
                outputs.append(messaging.route_nina_message(envelope, generator=lambda _prompt: "unused"))
        self.assertEqual({item["source"] for item in outputs}, {"business_thinking"})
        self.assertEqual(len({item["text"] for item in outputs}), 1)
        self.assertTrue(all(item["external_action_executed"] is False for item in outputs))

    def test_no_channel_specific_business_code(self):
        source = inspect.getsource(messaging._run_business_thinking).casefold()
        self.assertNotIn("telegram", source)
        self.assertNotIn("whatsapp", source)

    def test_external_action_is_never_executed(self):
        decision = self.enriched("Vai vajag celt cenu?")
        with patch.object(messaging, "_run_business_thinking", return_value=decision), \
             patch.object(messaging, "_save_turn"), \
             patch.object(messaging, "_pending_reminder_context", return_value={}), \
             patch.object(messaging, "_pending_destructive_context", return_value={}), \
             patch.object(messaging, "_action_context", return_value={}):
            response = messaging.send_message_to_nina(
                "Vai vajag celt cenu?", workspace_id="workspace-a", channel="web",
                conversation_id="conversation-a", contact_id="contact-a",
            )
        self.assertFalse(response["external_action_executed"])


if __name__ == "__main__":
    unittest.main()
