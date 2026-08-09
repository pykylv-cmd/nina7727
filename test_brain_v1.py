import unittest
from unittest.mock import patch

from brain import Brain, BrainContext, Decision, build_brain_summary
from brain.executive_brain import classify_message
import nina_message_service as messaging


class BrainDecisionTests(unittest.TestCase):
    def test_legacy_brain_summary_contract_remains_available(self):
        self.assertIsNotNone(build_brain_summary(["klients un projekts"]))

    def test_decision_model_contract(self):
        decision = Decision(create_work_object=True, create_reminder=True, confidence=0.9)
        self.assertEqual(set(decision.to_dict()), {
            "reply_required", "remember", "create_work_object", "create_reminder",
            "follow_up", "initiative", "needs_clarification", "no_action",
            "priority", "confidence", "reason", "reminder_operation",
        })
        with self.assertRaises(ValueError):
            Decision(create_reminder=True)

    def test_reminder_decision(self):
        decision = classify_message("Atgādini rīt 9:00 piezvanīt Jānim.")
        self.assertTrue(decision.reply_required)
        self.assertTrue(decision.remember)
        self.assertTrue(decision.create_work_object)
        self.assertTrue(decision.create_reminder)
        self.assertFalse(decision.initiative)
        self.assertEqual(decision.reason, "scheduled_reminder")

    def test_work_object_decision(self):
        decision = classify_message("Jāsagatavo klienta piedāvājums.")
        self.assertTrue(decision.create_work_object)
        self.assertFalse(decision.create_reminder)
        self.assertEqual(decision.reason, "work_request")

    def test_personal_event_decision(self):
        decision = classify_message("Man jāatceras, ka sievai 8. augustā dzimšanas diena.")
        self.assertTrue(decision.remember)
        self.assertTrue(decision.create_work_object)
        self.assertTrue(decision.create_reminder)
        self.assertEqual(decision.priority, "high")

    def test_scheduled_appointment_uses_existing_work_and_reminder_engines(self):
        decision = classify_message("Rīt 10:00 zobārsts.")
        self.assertTrue(decision.create_work_object)
        self.assertTrue(decision.create_reminder)
        self.assertFalse(decision.needs_clarification)

    def test_clarification_decision(self):
        decision = classify_message("Atgādini piezvanīt Jānim.")
        self.assertTrue(decision.needs_clarification)
        self.assertTrue(decision.create_work_object)
        self.assertTrue(decision.create_reminder)

    def test_all_supported_reminder_times_use_one_decision_contract(self):
        commands = (
            "Atgādini pēc 5 min izvest suni.",
            "Atceries pēc stundas piezvanīt Jānim.",
            "Pēc 5 min pārbaudīt Ninu.",
            "Rīt 10:00 zobārsts.",
            "Parīt 9:00 nosūtīt atskaiti.",
            "Pirmdien 11:00 sapulce.",
            "2026-08-10 15:00 vizīte.",
        )
        for command in commands:
            with self.subTest(command=command):
                decision = classify_message(command)
                self.assertTrue(decision.create_work_object)
                self.assertTrue(decision.create_reminder)
                self.assertFalse(decision.needs_clarification)

    def test_cancel_all_reminders_is_a_brain_decision(self):
        for command in (
            "novāc visus atgādinājumus",
            "izdzēs visus reminderus",
            "izdēs visus",
            "atcel visus manus atgādinājumus",
            "cancel all reminders",
        ):
            with self.subTest(command=command):
                self.assertEqual(
                    classify_message(command).reason,
                    "cancel_all_reminders",
                )

    def test_hourly_recurrence_is_a_complete_reminder_schedule(self):
        for schedule in (
            "ik pēc stundas", "ik pa apaļai stundai",
            "ik pēc apaļas stundas", "katru apaļu stundu",
        ):
            with self.subTest(schedule=schedule):
                decision = classify_message(
                    f"Atgādini man {schedule}: es esmu laimīgs dzīvot miljardiera dzīvi"
                )
                self.assertEqual(decision.reminder_operation, "CREATE")
                self.assertTrue(decision.create_reminder)
                self.assertFalse(decision.needs_clarification)

    def test_reminder_list_and_question_are_not_create(self):
        listed = classify_message("Kādi man ir atgādinājumi?")
        asked = classify_message("Pa dienu kas tev jāatgādina?")
        self.assertEqual(listed.reminder_operation, "LIST")
        self.assertFalse(listed.create_reminder)
        self.assertFalse(listed.needs_clarification)
        self.assertEqual(asked.reminder_operation, "ASK")
        self.assertFalse(asked.create_reminder)
        self.assertFalse(asked.needs_clarification)

    def test_contextual_evening_edit_is_update_not_create(self):
        decision = classify_message("Vakarā arī labrīt nesaki")
        self.assertEqual(decision.reminder_operation, "UPDATE")
        self.assertFalse(decision.create_reminder)
        self.assertFalse(decision.create_work_object)

    def test_no_action_decision(self):
        decision = classify_message("Ok.")
        self.assertTrue(decision.no_action)
        self.assertFalse(decision.reply_required)
        self.assertFalse(decision.create_work_object)

    def test_follow_up_decision(self):
        decision = classify_message("Seko līdzi klienta atbildei.")
        self.assertTrue(decision.follow_up)
        self.assertTrue(decision.create_work_object)

    def test_deterministic_and_channel_neutral(self):
        message = "Atgādini piektdien nosūtīt atskaiti."
        decisions = [
            Brain.decide(message, BrainContext("workspace-a", channel)).to_dict()
            for channel in ("web", "personal_whatsapp", "whatsapp_company", "telegram", "email", "api")
        ]
        self.assertTrue(all(item == decisions[0] for item in decisions))


class BrainIntegrationTests(unittest.TestCase):
    def test_no_action_skips_work_and_generation(self):
        with patch.object(messaging, "_save_turn") as save, patch.object(
            messaging, "execute_natural_work_request"
        ) as work:
            result = messaging.send_message_to_nina(
                "Ok.", workspace_id="workspace-a", conversation_id="conversation-a",
                generator=lambda _: self.fail("generator must not run"),
            )
        self.assertEqual(result["source"], "brain_no_action")
        self.assertEqual(result["text"], "")
        self.assertTrue(result["decision"]["no_action"])
        work.assert_not_called()
        save.assert_called_once()

    def test_clarification_skips_existing_engines(self):
        with patch.object(messaging, "_save_turn"), patch.object(
            messaging, "execute_natural_work_request"
        ) as work:
            result = messaging.send_message_to_nina("Atgādini piezvanīt Jānim.")
        self.assertEqual(result["source"], "brain_clarification")
        self.assertIn("Kad tieši", result["text"])
        work.assert_not_called()

    def test_reminder_decision_delegates_to_existing_work_engine(self):
        handled = {"handled": True, "text": "Atgādinājums saglabāts."}
        with patch.object(messaging, "_save_turn"), patch.object(
            messaging, "_save_natural_memory"
        ), patch.object(
            messaging, "execute_natural_work_request", return_value=handled
        ) as work:
            result = messaging.send_message_to_nina(
                "Atgādini rīt 9:00 piezvanīt Jānim.",
                workspace_id="workspace-a", channel="whatsapp_company",
                contact_id="contact-a",
            )
        self.assertEqual(result["source"], "shared_work")
        self.assertTrue(result["decision"]["create_reminder"])
        work.assert_called_once()
        self.assertTrue(work.call_args.kwargs["reminder_requested"])

    def test_scheduled_reminder_failure_never_falls_through_to_clarification(self):
        with patch.object(messaging, "_save_turn"), patch.object(
            messaging, "_save_natural_memory"
        ), patch.object(
            messaging, "execute_natural_work_request", return_value=None,
        ):
            result = messaging.send_message_to_nina(
                "Atgādini pēc 5 min izvest suni.",
                workspace_id="workspace-a", channel="web",
                contact_id="contact-a",
                generator=lambda _: self.fail("provider must not handle reminders"),
            )
        self.assertEqual(result["error"], "reminder_creation_failed")
        self.assertNotIn("Kad tieši", result["text"])

    def test_general_reply_uses_existing_provider_not_work_engine(self):
        with patch.object(messaging, "_save_turn"), patch.object(
            messaging, "execute_natural_work_request"
        ) as work, patch.object(
            messaging, "_load_conversation", return_value=[]
        ), patch.object(
            messaging, "_memory_context", return_value=""
        ), patch.object(
            messaging, "_work_context", return_value=""
        ):
            result = messaging.send_message_to_nina(
                "Kā tev klājas?", workspace_id="workspace-a",
                conversation_id="conversation-a", generator=lambda _: "Labi.",
            )
        self.assertEqual(result["source"], "nina")
        self.assertEqual(result["text"], "Labi.")
        work.assert_not_called()


if __name__ == "__main__":
    unittest.main()
