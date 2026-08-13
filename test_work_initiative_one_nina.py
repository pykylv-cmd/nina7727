import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from work_initiative_models import WorkExecutionDisposition, WorkExecutionResult

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class WorkInitiativeOneNinaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "initiative.sqlite")
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
        conn = self.work._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM conversation_state")
        conn.commit()
        cur.close()
        conn.close()

    def send(self, text, channel="web", contact="person-a"):
        return self.messaging.route_nina_message(self.messaging.NinaMessageEnvelope(
            text=text, workspace_id="tenant-a", channel=channel,
            conversation_id=f"{channel}:{contact}", contact_id=contact,
            canonical_work_workspace_id="tenant-a",
        ), generator=lambda _: "generic reply")

    def projects(self, contact="person-a"):
        return [obj for obj in self.work.list_work_objects(workspace_id="tenant-a", object_type="project", limit=100)
                if obj.origin_user_id == contact]

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    def test_food_business_then_riga_keeps_context_and_one_project(self, _business):
        first = self.send("Gribu uzsākt pārtikas biznesu.")
        self.assertEqual(first["source"], "work_initiative")
        self.assertEqual(len(self.projects()), 1)
        project_id = self.projects()[0].object_id
        second = self.send("Lokācija Rīga.")
        self.assertIn("Izveidot dzīvotspējīgu pārtikas biznesu", second["text"])
        self.assertEqual(len(self.projects()), 1)
        self.assertEqual(self.projects()[0].object_id, project_id)

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    def test_youtube_project_is_deduplicated_and_followup_updates_context(self, _business):
        text = "Gribu uzsākt YouTube biznesu kur tu taisi monetizāciju, kontentu un soli pa solim līdz bizness ir automatizēts."
        first = self.send(text)
        repeated = self.send(text, channel="telegram")
        self.assertEqual(first["work_object_id"], repeated["work_object_id"])
        self.assertEqual(len(self.projects()), 1)
        followup = self.send("bērnu kanāli, multenes/pamācošs veselīgs saturs", channel="whatsapp_company")
        self.assertEqual(followup["initiative"]["decision"]["reason"], "context_continuation")
        self.assertEqual(len(self.projects()), 1)

    def test_ninaos_priority_does_not_complete_unrelated_task(self):
        task = self.work.create_work_object(object_type="task", title="Unrelated", workspace_id="tenant-a", origin_user_id="person-a")
        response = self.send("vispirms NinaOS gribu pabeigt")
        self.assertEqual(response["work_object_type"], "project")
        self.assertEqual(self.work.get_work_object(task.object_id).status, "open")

    def test_capability_and_integration_answers_are_concrete(self):
        capabilities = self.send("Ko vari man palīdzēt biznesā? Vai manā firmā?")
        self.assertIn("VARU TAGAD", capabilities["text"])
        self.assertIn("VARU PĒC PIESLĒGŠANAS / APSTIPRINĀJUMA", capabilities["text"])
        integrations = self.send("kur tevi var integrēt?")
        self.assertEqual(integrations["source"], "work_initiative")
        self.assertNotIn("varu visu", integrations["text"].casefold())

    def test_capability_answer_has_four_honest_categories(self):
        response = self.send("Ko tu vari manā firmā?")
        self.assertIn("VARU TAGAD", response["text"])
        self.assertIn("VARU SAGATAVOT", response["text"])
        self.assertIn("VARU PĒC PIESLĒGŠANAS / APSTIPRINĀJUMA", response["text"])
        self.assertIn("VĒL NEVARU", response["text"])
        self.assertIn("e-pasta atbildes melnrakstu", response["text"])
        self.assertIn("lasīt ārēju e-pasta iesūtni", response["text"])

    def test_calendar_answer_is_honest_and_not_generic(self):
        response = self.send("Vari sakārtot manu kalendāru?")
        self.assertEqual(response["source"], "work_initiative")
        self.assertIn("sagatavot strukturētu kalendāra plānu", response["text"])
        self.assertIn("calendar connector nav ieviests", response["text"])
        self.assertFalse(response["external_action_executed"])

    def test_email_answer_does_not_claim_send(self):
        response = self.send("vari atbildēt manā vietā e-pastā?")
        self.assertIn("melnrakstu", response["text"])
        self.assertIn("connector nav ieviests", response["text"])
        self.assertIn("Nekāda ārēja darbība nav veikta", response["text"])
        self.assertFalse(response["external_action_executed"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    def test_expired_initiative_context_does_not_capture_followup(self, _business):
        self.send("Gribu YouTube biznesu.")
        conn = self.work._connect()
        cur = conn.cursor()
        expired = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat(" ")
        cur.execute(
            "UPDATE conversation_state SET created_at=? WHERE intent='work_initiative_context'",
            (expired,),
        )
        conn.commit()
        cur.close()
        conn.close()
        response = self.send("Lokācija Rīga.")
        self.assertNotEqual(response.get("source"), "work_initiative")
        self.assertEqual(len(self.projects()), 1)

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    def test_new_durable_goal_supersedes_previous_context(self, _business):
        first = self.send("Gribu YouTube biznesu.")
        second = self.send("Tagad svarīgāk pabeigt NinaOS.")
        self.assertNotEqual(first["work_object_id"], second["work_object_id"])
        self.assertIn("Pabeigt NinaOS", second["text"])
        followup = self.send("Lokācija Rīga.")
        self.assertIn("Pabeigt NinaOS", followup["text"])
        self.assertNotIn("YouTube", followup["text"])

    def test_proof_and_customer_search_offer_concrete_work(self):
        proof = self.send("gribu tevi pārdot, bet vajag lai tu pierādi ko māki")
        self.assertIn("Izpētīt potenciālos klientus", proof["text"])
        clients = self.send("tu vari atrast klientus kas tevi lietos?")
        self.assertIn("work_execution", clients)
        self.assertNotIn("ko tu gribi, lai es daru", clients["text"].casefold())
        trust = self.send("iesaki kaut ko dēļ kā es gribētu tev uzticēt savu biznesu")
        self.assertIn("Izpētīt potenciālos klientus", trust["text"])
        self.assertNotIn("Precizē atgādinājuma", trust["text"])

    def test_context_is_isolated_by_canonical_contact(self):
        with patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline")):
            self.send("Gribu uzsākt pārtikas biznesu.", contact="person-a")
        other = self.send("Lokācija Rīga.", contact="person-b")
        self.assertNotEqual(other.get("source"), "work_initiative")
        self.assertEqual(len(self.projects("person-b")), 0)

    def test_reminder_and_task_routes_are_not_hijacked(self):
        reminder = self.send("Atgādini man rīt 11 piezvanīt Jānim")
        self.assertNotEqual(reminder["source"], "work_initiative")
        task = self.send("Uztaisi uzdevumu piezvanīt klientam")
        self.assertNotEqual(task["source"], "work_initiative")

    def completed_research(self, title="Izpētīt potenciālos klientus"):
        return WorkExecutionResult(
            WorkExecutionDisposition.EXECUTABLE_NOW, "completed", title,
            summary="Atradu divus verificētus klientu segmentus.",
            evidence_references=("https://example.com/evidence",),
        )

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_proof_of_value_executes_and_persists_real_result(self, research, _business):
        research.return_value = self.completed_research()
        response = self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        self.assertEqual(research.call_count, 1)
        self.assertEqual(response["work_execution"]["state"], "completed")
        self.assertIn("Izdarīju: Izpētīt potenciālos klientus", response["text"])
        self.assertIn("https://example.com/evidence", response["text"])
        project = self.projects()[0]
        self.assertEqual(project.metadata["initiative_state"], "completed")
        self.assertEqual(project.metadata["evidence_references"], ["https://example.com/evidence"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_nu_nu_does_not_duplicate_completed_work(self, research, _business):
        research.return_value = self.completed_research()
        first = self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        second = self.send("nu nu?", channel="telegram")
        self.assertEqual(research.call_count, 1)
        self.assertEqual(second["work_object_id"], first["work_object_id"])
        self.assertEqual(second["execution_classification"], "requires_approval")
        self.assertIn("Sagatavot outreach", second["text"])
        self.assertNotIn("Ko tieši vēlies", second["text"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_other_contact_cannot_continue_selected_work(self, research, _business):
        research.return_value = self.completed_research()
        self.send("Gribu tevi pārdot. Pierādi, ko tu māki.", contact="person-a")
        other = self.send("dari", channel="telegram", contact="person-b")
        self.assertNotEqual(other.get("source"), "work_initiative")
        self.assertEqual(research.call_count, 1)

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_expired_context_cannot_execute_dari(self, research, _business):
        research.return_value = self.completed_research()
        self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        conn = self.work._connect()
        cur = conn.cursor()
        expired = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat(" ")
        cur.execute("UPDATE conversation_state SET created_at=? WHERE intent='work_initiative_context'", (expired,))
        conn.commit()
        cur.close()
        conn.close()
        response = self.send("dari")
        self.assertNotEqual(response.get("source"), "work_initiative")
        self.assertEqual(research.call_count, 1)

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_youtube_goal_returns_one_executed_answer_and_keeps_objective(self, research, _business):
        research.return_value = self.completed_research("Izpētīt nišas un auditoriju")
        response = self.send(
            "Gribu uzsākt bērnu YouTube biznesu, kur tu soli pa solim palīdzi līdz tas strādā un ir automatizēts."
        )
        self.assertEqual(response["work_execution"]["state"], "completed")
        project = self.projects()[0]
        self.assertIn("bērnu", project.metadata["goal_original_text"].casefold())
        self.assertEqual(project.metadata["automation_target"], "automatizēts")
        self.assertNotIn("Sāktu tagad", response["text"])
        self.assertNotIn("Ko mēs zinām", response["text"])
        self.assertNotIn("Kur konkurents ir stiprs", response["text"])
        self.assertNotIn("generic reply", response["text"])
        self.assertFalse(response["external_action_executed"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_youtube_dari_advances_to_internal_strategy_without_repeating_research(self, research, _business):
        research.return_value = self.completed_research("Izpētīt nišas un auditoriju")
        first = self.send("Gribu uzsākt bērnu YouTube biznesu līdz tas strādā un ir automatizēts.")
        second = self.send("dari", channel="whatsapp_company")
        self.assertEqual(research.call_count, 1)
        self.assertIn("work_execution", second, second)
        self.assertEqual(second["work_execution"]["work_title"], "Izveidot monetizācijas un satura stratēģiju")
        self.assertEqual(second["work_execution"]["state"], "completed")
        self.assertEqual(second["work_object_id"], first["work_object_id"])
        self.assertFalse(second["external_action_executed"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_started_is_persisted_before_research_and_success_transitions(self, research, _business):
        observed = {}
        def inspect_started(**kwargs):
            project = self.projects()[0]
            observed.update({
                "state": project.metadata["initiative_state"],
                "attempt_id": project.metadata["execution_attempt_id"],
                "started_at": project.metadata["started_at"],
                "active_work_type": project.metadata["active_work_type"],
            })
            return self.completed_research()
        research.side_effect = inspect_started
        response = self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        self.assertEqual(observed["state"], "started")
        self.assertTrue(observed["attempt_id"].startswith("initiative-attempt:"))
        self.assertTrue(observed["started_at"])
        self.assertEqual(observed["active_work_type"], "research")
        states = self.projects()[0].metadata["initiative_work_states"]
        self.assertIn("completed", {item["state"] for item in states.values()})
        self.assertEqual(response["work_execution"]["state"], "completed")

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research", side_effect=KeyboardInterrupt())
    def test_interrupted_execution_remains_observable_as_started(self, _research, _business):
        with self.assertRaises(KeyboardInterrupt):
            self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        project = self.projects()[0]
        self.assertEqual(project.metadata["initiative_state"], "started")
        self.assertTrue(project.metadata["execution_attempt_id"])

    @patch("nina_message_service._execute_initiative_research")
    def test_legacy_context_without_execution_fields_reconstructs_safe_work(self, research):
        from work_initiative_engine import analyze_work_initiative
        initiative = analyze_work_initiative("Gribu tevi pārdot. Pierādi, ko tu māki.")
        project = self.messaging._initiative_project_object(initiative, "tenant-a", "person-a", "web")
        self.messaging._save_work_initiative_context("contact:tenant-a:person-a:one_nina", {
            "objective": initiative.goal.objective, "project_kind": "proof_of_value",
            "known_context": initiative.goal.original_text, "object_id": project.object_id,
        })
        research.return_value = self.completed_research()
        response = self.send("nu nu?", channel="telegram")
        self.assertEqual(research.call_count, 1)
        self.assertEqual(response["work_execution"]["state"], "completed")
        self.assertEqual(response["work_object_id"], project.object_id)

    def test_ambiguous_legacy_context_fails_safely(self):
        from work_initiative_engine import analyze_work_initiative
        initiative = analyze_work_initiative("Gribu YouTube biznesu.")
        project = self.messaging._initiative_project_object(initiative, "tenant-a", "person-a", "web")
        metadata = dict(project.metadata)
        metadata.pop("goal_original_text", None)
        research_work = dict(metadata["work_plan"][0])
        second = dict(research_work)
        second["title"] = "Izpētīt otru tirgus virzienu"
        metadata["work_plan"] = [research_work, second]
        self.work.update_work_object(project.object_id, metadata=metadata)
        self.messaging._save_work_initiative_context("contact:tenant-a:person-a:one_nina", {
            "objective": initiative.goal.objective, "project_kind": "youtube_business",
            "object_id": project.object_id,
        })
        response = self.send("nu nu?")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"], "legacy_next_work_ambiguous")
        self.assertIn("Kuru", response["text"])

    @patch("nina_message_service._execute_initiative_research")
    def test_project_with_no_remaining_work_reports_step_complete(self, research):
        from work_initiative_engine import analyze_work_initiative
        initiative = analyze_work_initiative("Gribu tevi pārdot. Pierādi, ko tu māki.")
        project = self.messaging._initiative_project_object(initiative, "tenant-a", "person-a", "web")
        metadata = dict(project.metadata)
        selected = initiative.next_best_work.work
        metadata["work_plan"] = [selected.to_dict()]
        self.work.update_work_object(project.object_id, metadata=metadata)
        self.messaging._save_work_initiative_context("contact:tenant-a:person-a:one_nina", {
            "objective": initiative.goal.objective, "project_kind": "proof_of_value",
            "known_context": initiative.goal.original_text, "object_id": project.object_id,
        })
        research.return_value = self.completed_research()
        first = self.send("nu nu?")
        second = self.send("dari", channel="telegram")
        self.assertEqual(first["work_execution"]["state"], "completed")
        self.assertEqual(research.call_count, 1)
        self.assertIn("duplicate_execution_prevented", second, second)
        self.assertTrue(second["duplicate_execution_prevented"])
        self.assertTrue(second["project_step_completed"])
        self.assertIn("posms jau ir pabeigts", second["text"])

    @patch("nina_message_service._run_business_thinking", side_effect=RuntimeError("offline"))
    @patch("nina_message_service._execute_initiative_research")
    def test_research_failure_is_honest_and_persisted(self, research, _business):
        research.return_value = WorkExecutionResult(
            WorkExecutionDisposition.EXECUTABLE_NOW, "failed", "Izpētīt potenciālos klientus",
            summary="Izpēti sāku, bet nepabeidzu ar pietiekami verificētiem avotiem.",
            failure_reason="verification_failed",
        )
        response = self.send("Gribu tevi pārdot. Pierādi, ko tu māki.")
        self.assertIn("nepabeidzu", response["text"])
        self.assertNotIn("Atradu", response["text"])
        project = self.projects()[0]
        self.assertEqual(project.metadata["initiative_state"], "failed")
        self.assertEqual(
            [item["state"] for item in project.metadata["initiative_execution_history"][-2:]],
            ["started", "failed"],
        )

    def test_external_email_and_calendar_remain_non_executing(self):
        email = self.send("atbildi manā vietā e-pastā")
        calendar = self.send("Vari sak\u0101rtot manu kalend\u0101ru?")
        self.assertFalse(email["external_action_executed"])
        self.assertFalse(calendar["external_action_executed"])
        self.assertNotIn("work_execution", email)
        self.assertNotIn("work_execution", calendar)


if __name__ == "__main__":
    unittest.main()
