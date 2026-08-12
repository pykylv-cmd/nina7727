import unittest

from work_initiative_engine import analyze_work_initiative


class WorkInitiativeEngineTests(unittest.TestCase):
    def test_capability_question_returns_registry_answer(self):
        result = analyze_work_initiative("Ko vari man palīdzēt biznesā? Vai manā firmā?", environment={})
        self.assertTrue(result.decision.should_act)
        self.assertEqual(result.response_kind, "capability")
        self.assertIn("sagatavot e-pasta atbildes melnrakstu", result.capability_answer.available_now)
        self.assertIn("nosūtīt apstiprinātu e-pastu pēc konta pieslēgšanas", result.capability_answer.available_after_connection)

    def test_youtube_goal_becomes_project_plan_without_niche_blocker(self):
        result = analyze_work_initiative("Gribu uzsākt YouTube biznesu kur tu taisi monetizāciju, kontentu un soli pa solim līdz bizness ir automatizēts.")
        self.assertTrue(result.project_candidate)
        self.assertEqual(result.goal.scope, "youtube_business")
        self.assertGreaterEqual(len(result.proposed_work), 3)
        self.assertTrue(result.next_best_work.can_start_now)
        self.assertNotIn("nišu gribi", result.next_best_work.owner_question_if_blocked.casefold())

    def test_food_location_continues_previous_goal(self):
        first = analyze_work_initiative("Gribu uzsākt pārtikas biznesu.")
        second = analyze_work_initiative("Lokācija Rīga.", previous_context=first.context_update)
        self.assertEqual(second.decision.reason, "context_continuation")
        self.assertEqual(second.goal.objective, first.goal.objective)
        self.assertIn("Rīga", second.goal.known_context[-1])
        self.assertIn("pārtikas biznesu", second.goal.objective)

    def test_proof_mode_designs_own_demo(self):
        result = analyze_work_initiative("Gribu tevi pārdot, bet vajag lai tu pierādi ko māki")
        self.assertEqual(result.response_kind, "proof")
        self.assertTrue(result.use_research)
        self.assertIn("Izpētīt potenciālos klientus", [work.title for work in result.proposed_work])
        self.assertTrue(result.next_best_work.can_start_now)

    def test_business_trust_request_gets_specific_demo(self):
        result = analyze_work_initiative("iesaki kaut ko dēļ kā es gribētu tev uzticēt savu biznesu")
        self.assertEqual(result.response_kind, "proof")
        self.assertGreaterEqual(len(result.proposed_work), 3)
        self.assertEqual(result.next_best_work.work.title, "Izpētīt potenciālos klientus")

    def test_email_answer_is_honest(self):
        result = analyze_work_initiative("vari atbildēt manā vietā e-pastā?", environment={})
        self.assertEqual(result.response_kind, "email")
        self.assertTrue(result.decision.requires_connection)
        self.assertTrue(result.decision.requires_approval)
        self.assertTrue(result.next_best_work.can_start_now)

    def test_ordinary_chat_is_not_actionable(self):
        self.assertFalse(analyze_work_initiative("kā tev iet?").decision.should_act)


if __name__ == "__main__":
    unittest.main()
