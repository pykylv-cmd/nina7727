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
        folded = need.question.casefold()
        fact_type = BusinessFactType.CUSTOMER if "pieprasījums" in folded else (
            BusinessFactType.PRICING if "cenas" in folded else
            BusinessFactType.COMPETITOR if "sintra" in folded or "konkur" in folded else
            BusinessFactType.ECONOMICS
        )
        statement = (
            "Sintra publiski piedāvā mēneša abonēšanas cenu plānus."
            if fact_type is BusinessFactType.PRICING else
            "Sintra publiski piedāvā integrācijas ar klientu darba rīkiem."
            if "funkcijas" in folded or "integrācijas" in folded else
            "Sintra publiski piedāvā vairākus specializētus AI palīgus."
            if fact_type is BusinessFactType.COMPETITOR else
            "Publiskie avoti rāda pieprasījumu pēc AI darbaspēka risinājumiem."
            if fact_type is BusinessFactType.CUSTOMER else
            "Klienta ekonomiskais nosacījums ir verificēts."
        )
        facts = (BusinessFact(
            statement, (f"evidence-{fact_type.value}",),
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

    def test_live_competitor_phrasings_trigger_without_channel_specific_logic(self):
        for text in (
            "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?",
            "Kā pārspēt Sintra AI?",
            "Kā mēs varam pārspēt konkurentus?",
            "Ko darīt, lai būtu labāki par konkurentiem?",
            "Kā iegūt priekšrocību pār konkurentiem?",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.trigger(text))

    def test_sintra_information_requests_do_not_trigger(self):
        for text in (
            "kas ir Sintra AI?",
            "atrodi internetā Sintra AI",
            "atsūti Sintra AI mājaslapu",
        ):
            with self.subTest(text=text):
                self.assertFalse(self.trigger(text))

    def test_pricing_question_triggers(self):
        self.assertTrue(self.trigger("Vai vajag celt cenu?"))

    def test_market_entry_question_triggers(self):
        self.assertTrue(self.trigger("Vai ir vērts ieiet šajā tirgū?"))

    def test_strategic_business_decision_phrasings_trigger(self):
        for text in (
            "Kādu biznesa stratēģiju izvēlēties?",
            "Kāda būtu labākā stratēģija manam biznesam?",
            "Ko mums stratēģiski darīt tālāk?",
            "Kādu virzienu biznesam izvēlēties?",
            "Kāds būtu gudrākais biznesa lēmums šajā situācijā?",
        ):
            with self.subTest(text=text):
                self.assertTrue(self.trigger(text))

    def test_strategy_information_and_existing_capabilities_do_not_trigger(self):
        for text, changes in (
            ("kas ir stratēģija?", {}),
            ("izskaidro biznesa stratēģiju", {}),
            ("kā tev iet?", {}),
            ("atrodi internetā biznesa stratēģijas", {}),
            ("izlasi https://example.com/strategy", {}),
            ("Atgādini man rīt izvēlēties stratēģiju", {"create_reminder": True, "create_work_object": True}),
            ("Uztaisi uzdevumu izvēlēties biznesa stratēģiju", {"create_work_object": True}),
            ("Atceries, ka mana biznesa stratēģija ir izaugsme", {}),
        ):
            with self.subTest(text=text):
                self.assertFalse(self.trigger(text, **changes))

    def test_enough_evidence_renders_recommendation_and_action(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("Mans lēmums", rendered)
        self.assertIn("Ko darīt tagad", rendered)

    def test_missing_evidence_is_cautious(self):
        rendered = messaging._render_business_decision(self.enriched(completed=False))
        self.assertIn("vēl nav pietiekami verificēti", rendered)
        self.assertIn("Ko mēs vēl nezinām", rendered)

    def test_research_need_invokes_existing_bridge(self):
        initial = analyze_business_decision("Vai vajag celt cenu?", workspace_id="workspace-a", contact_id="contact-a")
        calls = []
        def execute(need, **scope):
            calls.append((need, scope))
            return self.result_for_need(need)
        with patch("business_research_bridge.execute_business_research_need", side_effect=execute):
            messaging._run_business_thinking("Vai vajag celt cenu?", "workspace-a", "contact-a")
        public_needs = tuple(need for need in initial.research_needs if messaging._is_public_business_research_need(need))
        self.assertEqual(tuple(need for need, _scope in calls), public_needs)
        self.assertTrue(all(scope["query_context"] == "Vai vajag celt cenu?" for _need, scope in calls))

    def test_exact_live_questions_attempt_every_public_need(self):
        for question in (
            "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?",
            "Kādu biznesa stratēģiju mums izvēlēties, lai NinaOS augtu ātrāk par konkurentiem?",
        ):
            initial = analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a")
            public_needs = tuple(need for need in initial.research_needs if messaging._is_public_business_research_need(need))
            calls = []
            with self.subTest(question=question), patch(
                "business_research_bridge.execute_business_research_need",
                side_effect=lambda need, **_scope: calls.append(need) or self.result_for_need(need),
            ):
                decision = messaging._run_business_thinking(question, "workspace-a", "contact-a")
            self.assertEqual(tuple(calls), public_needs)
            self.assertEqual(len(calls), len(initial.research_needs))
            self.assertTrue(decision.evidence_set.facts)

    def test_private_economics_is_not_auto_researched_while_public_facts_survive(self):
        question = "Vai vajag celt cenu?"
        initial = analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a")
        calls = []
        with patch(
            "business_research_bridge.execute_business_research_need",
            side_effect=lambda need, **_scope: calls.append(need) or self.result_for_need(need),
        ):
            decision = messaging._run_business_thinking(question, "workspace-a", "contact-a")
        self.assertTrue(all(messaging._is_public_business_research_need(need) for need in calls))
        self.assertTrue(any(not messaging._is_public_business_research_need(need) for need in initial.research_needs))
        self.assertTrue(decision.evidence_set.facts)

    def test_failed_public_research_is_rendered_as_attempted(self):
        question = "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?"
        initial = analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a")
        failures = tuple(self.result_for_need(need, completed=False) for need in initial.research_needs)
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=failures,
        )
        rendered = messaging._render_business_decision(decision)
        self.assertIn("Ko mēs vēl nezinām", rendered)
        self.assertNotIn("provider_unavailable", rendered)

    def test_failed_need_does_not_erase_successful_business_fact(self):
        question = "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?"
        initial = analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a")
        results = (self.result_for_need(initial.research_needs[0]),) + tuple(
            self.result_for_need(need, completed=False) for need in initial.research_needs[1:]
        )
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a", research_results=results,
        )
        rendered = messaging._render_business_decision(decision)
        self.assertIn("Sintra publiski piedāvā", rendered)
        self.assertIn("Ko mēs vēl nezinām", rendered)
        self.assertIn("https://verified.example/", rendered)

    def test_public_demand_competitor_and_pricing_needs_use_research_v1(self):
        initial = analyze_business_decision(
            "Kā pārspēt konkurentus ar labāku cenu?", workspace_id="workspace-a", contact_id="contact-a",
        )
        public_questions = tuple(
            need.question for need in initial.research_needs if messaging._is_public_business_research_need(need)
        )
        self.assertTrue(any("pieprasījums" in question for question in public_questions))
        self.assertTrue(any("konkurentu" in question and "cenas" in question for question in public_questions))

    def test_private_unit_economics_need_does_not_use_public_research(self):
        initial = analyze_business_decision(
            "Vai vajag celt cenu?", workspace_id="workspace-a", contact_id="contact-a",
        )
        private_needs = tuple(need for need in initial.research_needs if not messaging._is_public_business_research_need(need))
        self.assertTrue(any("ekonomika" in need.question for need in private_needs))
        with patch(
            "business_research_bridge.execute_business_research_need",
            side_effect=lambda need, **_scope: self.result_for_need(need),
        ) as execute:
            messaging._run_business_thinking(
                "Vai vajag celt cenu?", "workspace-a", "contact-a",
            )
        self.assertNotIn(private_needs[0], tuple(call.args[0] for call in execute.call_args_list))

    def test_private_margin_need_is_not_publicly_researched(self):
        need = type("PrivateNeed", (), {
            "question": "Kāda ir mūsu privātā bruto marža un iekšējā konversija?",
            "why_needed": "Confidential internal sales numbers are required.",
        })()
        self.assertFalse(messaging._is_public_business_research_need(need))

    def test_latvian_renderer_hides_deterministic_english_engine_prose(self):
        rendered = messaging._render_business_decision(self.enriched(completed=False))
        self.assertNotIn("Run the reversible validation first", rendered)
        self.assertNotIn("Validate the highest-value customer problem", rendered)
        self.assertNotIn("Verify:", rendered)
        self.assertNotIn("Material assumptions may be wrong", rendered)
        self.assertIn("Būtiskie pieņēmumi var būt kļūdaini", rendered)

    def test_named_competitor_and_strategy_render_different_next_actions(self):
        named = analyze_business_decision(
            "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?",
            workspace_id="workspace-a", contact_id="contact-a",
        )
        strategy = analyze_business_decision(
            "Kādu biznesa stratēģiju mums izvēlēties, lai NinaOS augtu ātrāk par konkurentiem?",
            workspace_id="workspace-a", contact_id="contact-a",
        )
        named_text = messaging._render_business_decision(named)
        strategy_text = messaging._render_business_decision(strategy)
        self.assertIn("Sintra AI", named_text)
        self.assertIn("mērķa klienta", strategy_text)
        self.assertNotEqual(named_text, strategy_text)

    def test_failed_research_creates_no_rendered_fact(self):
        rendered = messaging._render_business_decision(self.enriched(completed=False))
        self.assertNotIn("Publiskie avoti rāda pieprasījumu", rendered)

    def test_executive_renderer_hides_internal_outcomes_and_raw_english_snippets(self):
        rendered = messaging._render_business_decision(self.enriched())
        for forbidden in (
            "budget_exceeded", "verification_failed", "provider_unavailable",
            "revolutionary all-in-one",
        ):
            self.assertNotIn(forbidden, rendered)
        for section in (
            "Ko mēs zinām", "Kur konkurents ir stiprs", "Kur NinaOS var uzvarēt",
            "Mans lēmums", "Ko darīt tagad", "Verificēti avoti",
        ):
            self.assertIn(section, rendered)

    def test_sintra_three_completed_one_unresolved_renders_substantive_latvian_answer(self):
        question = "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?"
        initial = analyze_business_decision(question, workspace_id="workspace-a", contact_id="contact-a")
        results = tuple(
            self.result_for_need(need, completed=index < 3)
            for index, need in enumerate(initial.research_needs)
        )
        decision = analyze_business_decision_with_evidence(
            question, workspace_id="workspace-a", contact_id="contact-a",
            research_results=results,
        )
        rendered = messaging._render_business_decision(decision)
        self.assertIn("Sintra publiski piedāvā vairākus specializētus AI palīgus", rendered)
        self.assertIn("Sintra publiski piedāvā mēneša abonēšanas cenu plānus", rendered)
        self.assertIn("Sintra publiski piedāvā integrācijas ar klientu darba rīkiem", rendered)
        self.assertIn("Verificēta stiprā puse", rendered)
        self.assertIn("Secinājums, kas vēl jāpārbauda", rendered)
        self.assertIn("pieprasījumu pēc AI darbinieku", rendered)
        self.assertIn("Mans lēmums", rendered)
        self.assertIn("1. Pārbaudi neatrisināto tirgus pieprasījumu", rendered)
        self.assertIn("2. Salīdzini NinaOS onboarding laiku un darba plūsmu ar Sintra AI", rendered)
        self.assertIn("3. Izvēlies vienu klientu segmentu", rendered)
        self.assertGreaterEqual(rendered.count("https://verified.example/"), 2)
        for forbidden in (
            "budget_exceeded", "verification_failed", "provider_unavailable",
            "insufficient_evidence", "EvidenceRecord", "BusinessFact", "ResearchNeed",
            "Jāpārbauda", "Verified", "revolutionary all-in-one",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_supported_english_fact_is_paraphrased_without_marketing_dump(self):
        self.assertEqual(
            messaging._concise_business_fact(
                "Sintra AI offers a suite of AI-powered helpers. Revolutionary all-in-one marketing follows."
            ),
            "Sintra AI piedāvā AI palīgus.",
        )

    def test_verified_links_only_are_rendered(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("https://verified.example/", rendered)
        self.assertNotIn("fabricated.example", rendered)

    def test_next_best_action_rendered(self):
        self.assertIn("Ko darīt tagad", messaging._render_business_decision(self.enriched()))

    def test_assumptions_remain_labeled(self):
        rendered = messaging._render_business_decision(self.enriched())
        self.assertIn("Pieņēmumi", rendered)
        self.assertIn("klientu noturēšana uzlabosies", rendered)
        self.assertNotIn("retention will improve", rendered)

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

    def test_both_exact_live_messages_share_business_runtime_across_channels(self):
        messages = (
            "Vai NinaOS var pārspēt Sintra AI un ko mums darīt, lai viņus pārspētu?",
            "Kādu biznesa stratēģiju mums izvēlēties, lai NinaOS augtu ātrāk par konkurentiem?",
        )
        for question in messages:
            decision = self.enriched(question)
            with self.subTest(question=question), \
                 patch.object(messaging, "_run_business_thinking", return_value=decision), \
                 patch.object(messaging, "_save_turn"), \
                 patch.object(messaging, "_pending_reminder_context", return_value={}), \
                 patch.object(messaging, "_pending_destructive_context", return_value={}), \
                 patch.object(messaging, "_action_context", return_value={}):
                outputs = tuple(
                    messaging.route_nina_message(
                        messaging.NinaMessageEnvelope(
                            question, "workspace-a", channel, f"conversation-{channel}", "contact-a",
                        ),
                        generator=lambda _prompt: "unused",
                    )
                    for channel in ("web", "telegram", "company_whatsapp")
                )
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
