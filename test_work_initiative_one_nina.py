import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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
        self.assertIn("Sāktu tagad", clients["text"])
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


if __name__ == "__main__":
    unittest.main()
