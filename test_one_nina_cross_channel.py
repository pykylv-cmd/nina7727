import ast
import os
import tempfile
import unittest
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


class OneNinaCrossChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_file = os.path.join(cls.temp_dir.name, "one-nina.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db_file})
        cls.env.start()
        import managed_migrations
        import nina_message_service
        import work_objects

        cls.messaging = nina_message_service
        cls.work = work_objects
        cls.original_work = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        cls.original_message = (
            nina_message_service.DATABASE_URL,
            nina_message_service.DB_FILE,
            nina_message_service.USE_POSTGRES,
        )
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
        cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects")
        cur.execute("DELETE FROM conversation_state")
        conn.commit()
        cur.close()
        conn.close()

    def send(self, channel, text, contact_id="contact-linked", generator=None):
        recipient = "123456" if channel == "telegram" else "37120000000@s.whatsapp.net"
        envelope = self.messaging.NinaMessageEnvelope(
            text=text,
            workspace_id="tenant-a",
            channel=channel,
            conversation_id=f"contact:{contact_id}:{channel}",
            contact_id=contact_id,
            canonical_work_workspace_id="tenant-a",
            delivery_recipient=recipient,
        )
        return self.messaging.route_nina_message(
            envelope,
            generator=generator or (lambda _: "shared ordinary reply"),
        )

    def reminders(self, contact_id="contact-linked"):
        return [
            obj for obj in self.work.list_work_objects(workspace_id="tenant-a", limit=500)
            if (obj.metadata or {}).get("reminder_state") == "scheduled"
            and (obj.metadata or {}).get("contact_id") == contact_id
        ]

    def test_reminder_create_list_ask_and_update_share_one_canonical_truth(self):
        created = self.send("web", "Katru dienu 12.00 atgādini: Tu esi miljardieris")
        self.assertTrue(created["ok"])
        original_id = self.reminders()[0].object_id

        listed = self.send("telegram", "Kādi man ir atgādinājumi?")
        self.assertEqual(listed["decision"]["reminder_operation"], "LIST")
        self.assertIn("12:00", listed["text"])
        self.assertIn("Tu esi miljardieris", listed["text"])

        asked = self.send("whatsapp_company", "Pa dienu kas tev jāatgādina?")
        self.assertEqual(asked["decision"]["reminder_operation"], "ASK")
        self.assertIn("Tu esi miljardieris", asked["text"])

        updated = self.send("telegram", "Pa dienu saki: Tu esi miljardiere")
        self.assertTrue(updated["ok"])
        current = self.reminders()
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0].object_id, original_id)
        self.assertEqual(current[0].metadata["reminder_text"], "Tu esi miljardiere")

    def test_explicit_linked_contact_shares_pending_context_but_other_contact_does_not(self):
        pending = self.send("web", "Atgādini saskaitīt naudu")
        self.assertEqual(pending["source"], "brain_clarification")
        continued = self.send("telegram", "Rīt 11.00")
        self.assertTrue(continued["ok"])
        self.assertEqual(len(self.reminders()), 1)
        self.assertEqual(self.reminders()[0].metadata["reminder_text"], "saskaitīt naudu")

        isolated = self.send("web", "Atgādini izvest suni", contact_id="contact-other")
        self.assertEqual(isolated["source"], "brain_clarification")
        unrelated = self.send("telegram", "Rīt 12.00", contact_id="contact-linked")
        self.assertTrue(unrelated.get("object_ids"))
        self.assertNotEqual(self.reminders()[0].metadata["reminder_text"], "izvest suni")
        self.assertEqual(len(self.reminders("contact-other")), 0)

    def test_full_explicit_cross_channel_create_supersedes_only_same_contact_pending(self):
        pending = self.send("web", "Atgādini man rīt piezvanīt Jānim")
        self.assertEqual(pending["source"], "brain_clarification")

        created = self.send(
            "telegram",
            "Atgādini man ik pēc apaļas stundas — man ļoti patīk kad es esmu miljardieris",
        )
        linked = self.reminders()
        self.assertTrue(created["ok"])
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0].metadata["reminder_text"], "man ļoti patīk kad es esmu miljardieris")
        self.assertNotIn("Jānim", linked[0].metadata["reminder_text"])

        other_pending = self.send("web", "Atgādini man rīt izvest suni", contact_id="contact-other")
        self.assertEqual(other_pending["source"], "brain_clarification")
        self.send("whatsapp_company", "Atgādini man rīt 15 piezvanīt Pēterim")
        continued = self.send("telegram", "11:30", contact_id="contact-other")
        self.assertTrue(continued["ok"])
        other = self.reminders("contact-other")
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0].metadata["reminder_text"], "izvest suni")

    def test_duplicate_inbound_across_channels_is_idempotent(self):
        text = "Atgādini man rīt 11.00 saskaitīt naudu"
        first = self.send("web", text)
        second = self.send("telegram", text)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(first["object_ids"], second["object_ids"])
        self.assertEqual(len(self.reminders()), 1)

        self.setUp()
        first = self.send("telegram", text)
        second = self.send("whatsapp_company", text)
        self.assertEqual(first["object_ids"], second["object_ids"])
        self.assertEqual(len(self.reminders()), 1)

        different_person = self.send("web", text, contact_id="contact-other")
        self.assertNotEqual(first["object_ids"], different_person["object_ids"])
        self.assertEqual(len(self.reminders("contact-other")), 1)

        different_time = self.send("web", "Atgādini man rīt 12.00 saskaitīt naudu")
        self.assertNotEqual(first["object_ids"], different_time["object_ids"])

    def test_explicit_clock_create_precedes_daypart_word_in_content(self):
        result = self.send("telegram", "Katru dienu 19.00 atgādini: Labrīt vakarā")
        self.assertEqual(result["decision"]["reminder_operation"], "CREATE")
        self.assertTrue(result["ok"])
        self.assertEqual(len(self.reminders()), 1)
        self.assertEqual(self.reminders()[0].metadata["reminder_text"], "Labrīt vakarā")

    def test_different_people_in_same_workspace_do_not_share_private_context(self):
        self.send("web", "slepena alfa", contact_id="contact-a", generator=lambda _: "A")
        prompts = []
        result = self.send(
            "telegram", "parasta saruna", contact_id="contact-b",
            generator=lambda prompt: prompts.append(prompt) or "B",
        )
        self.assertEqual(result["text"], "B")
        self.assertNotIn("slepena alfa", "\n".join(prompts))

    def test_ordinary_chat_uses_same_shared_reply_boundary(self):
        for channel in ("web", "telegram", "whatsapp_company"):
            result = self.send(channel, "Sveika, Nina", generator=lambda _: "viena Nina")
            self.assertEqual(result["text"], "viena Nina")
            self.assertEqual(result["source"], "nina")

    def test_web_research_capability_is_shared_across_channels(self):
        payload = {
            "ok": True,
            "intent": {"search_type": "SOURCE_PAGE_ANALYSIS"},
            "verified_results": [{"title": "Example", "source_url": "https://example.com/x"}],
            "results": [{"title": "Example", "source_url": "https://example.com/x"}],
        }
        for channel in ("web", "telegram", "whatsapp_company"):
            with patch("web_research.read_public_websites", return_value=payload), \
                 patch("web_research.answer_page_content", return_value="Verified Example https://example.com/x"), \
                 patch("web_research.save_research_session", return_value=f"session-{channel}"):
                result = self.send(channel, "Izlasi https://example.com/x")
            self.assertEqual(result["source"], "web_research")
            self.assertIn("https://example.com/x", result["text"])

    def test_persistence_failure_never_claims_reminder_success(self):
        with patch("nina_message_service.execute_natural_work_request", side_effect=RuntimeError("db down")):
            result = self.send("telegram", "Atgādini man rīt 11.00 saskaitīt naudu")
        self.assertFalse(result["ok"])
        self.assertNotIn("izveid", result["text"].casefold())
        self.assertEqual(self.reminders(), [])

    def test_hourly_clarification_and_cancel_all_share_one_cross_channel_truth(self):
        first = self.send(
            "web", "Atgādini man: es esmu laimīgs dzīvot miljardiera dzīvi",
        )
        self.assertEqual(first["source"], "brain_clarification")
        created = self.send("telegram", "Ik pa apaļai stundai")
        self.assertTrue(created["ok"])
        self.assertEqual(len(self.reminders()), 1)
        source_id = self.reminders()[0].object_id
        listed = self.send("whatsapp_company", "Kādi man ir atgādinājumi?")
        self.assertIn("katru apaļu stundu", listed["text"])
        self.assertIn("es esmu laimīgs dzīvot miljardiera dzīvi", listed["text"])
        self.assertEqual(self.reminders()[0].object_id, source_id)
        requested = self.send("whatsapp_company", "Izdzēs visus")
        self.assertTrue(requested["confirmation_required"])
        self.assertEqual(self.reminders()[0].object_id, source_id)
        deleted = self.send("web", "jā")
        self.assertTrue(deleted["ok"])
        self.assertEqual(deleted["remaining_reminders"], 0)
        self.assertEqual(self.reminders(), [])

        other = self.send("web", "Atgādini man rīt 11.00 svešs", contact_id="contact-other")
        self.assertTrue(other["ok"])
        self.assertEqual(len(self.reminders("contact-other")), 1)

    def test_destructive_confirmation_is_contact_scoped_across_channels(self):
        created = self.send("web", "Atgādini man rīt 11.00 slepens reminders")
        self.assertTrue(created["ok"])
        source_id = self.reminders()[0].object_id
        requested = self.send("telegram", "Izdzēs visus")
        self.assertTrue(requested["confirmation_required"])

        other_yes = self.send("whatsapp_company", "jā", contact_id="contact-other")
        self.assertEqual(other_yes["decision"]["reason"], "destructive_confirmation_absent")
        self.assertEqual(self.reminders()[0].object_id, source_id)

        confirmed = self.send("whatsapp_company", "jā")
        self.assertTrue(confirmed["ok"])
        self.assertEqual(confirmed["remaining_reminders"], 0)
        self.assertEqual(self.reminders(), [])

    def test_each_channel_uses_the_same_confirmation_before_bulk_cancel_contract(self):
        for channel in ("web", "telegram", "whatsapp_company"):
            with self.subTest(channel=channel):
                self.setUp()
                created = self.send(channel, "Atgādini man rīt 11.00 pārbaudīt Ninu")
                self.assertTrue(created["ok"])
                source_id = self.reminders()[0].object_id
                requested = self.send(channel, "Izdzēs visus")
                self.assertTrue(requested["confirmation_required"])
                self.assertEqual(self.reminders()[0].object_id, source_id)
                confirmed = self.send(channel, "jā, visus")
                self.assertTrue(confirmed["ok"])
                self.assertEqual(confirmed["remaining_reminders"], 0)
                self.assertEqual(self.reminders(), [])

    def test_hourly_next_occurrence_uses_same_reference_across_channels(self):
        created = self.send(
            "web",
            "Atgādini man ik pēc apaļas stundas — man ļoti patīk kad es esmu miljardieris",
        )
        object_id = created["object_ids"][0]
        before_count = len(self.reminders())

        no_generic = lambda _: self.fail("NEXT_OCCURRENCE reached generic generation")
        telegram = self.send("telegram", "Pēc 19.00 nākamais kad?", generator=no_generic)
        whatsapp = self.send("whatsapp_company", "Un pēc tam?", generator=no_generic)
        web = self.send("web", "Pēc 23.00?", generator=no_generic)

        self.assertEqual(telegram["text"], "20:00.")
        self.assertEqual(whatsapp["text"], "21:00.")
        self.assertEqual(web["text"], "00:00.")
        self.assertEqual(telegram["reminder_object_id"], object_id)
        self.assertEqual(whatsapp["reminder_object_id"], object_id)
        self.assertEqual(web["reminder_object_id"], object_id)
        self.assertEqual(len(self.reminders()), before_count)
        self.assertEqual(self.reminders()[0].object_id, object_id)

    def test_telegram_reply_routes_ordinary_messages_before_legacy_branches(self):
        with open("app.py", encoding="utf-8") as handle:
            source = handle.read()
        tree = ast.parse(source)
        reply = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "reply")
        route_calls = [node for node in ast.walk(reply) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "route_nina_message"]
        self.assertEqual(len(route_calls), 1)
        legacy_calls = [
            node for node in ast.walk(reply)
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "add_reminder"
        ]
        self.assertTrue(legacy_calls)
        self.assertLess(route_calls[0].lineno, min(node.lineno for node in legacy_calls))
        self.assertIn("telegram_owner_only_command(user_text)", ast.unparse(reply))

    def test_owner_only_classifier_is_narrow_and_public_commands_are_not_shared(self):
        with open("app.py", encoding="utf-8") as handle:
            source = handle.read()
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "telegram_owner_only_command")
        self.assertTrue(function)
        namespace = {"re": __import__("re")}
        relevant = [
            node for node in tree.body
            if isinstance(node, (ast.Assign, ast.FunctionDef))
            and (
                isinstance(node, ast.FunctionDef) and node.name == "telegram_owner_only_command"
                or isinstance(node, ast.Assign) and any(
                    getattr(target, "id", "").startswith("_TELEGRAM_OWNER_ONLY_") for target in node.targets
                )
            )
        ]
        exec(compile(ast.Module(body=relevant, type_ignores=[]), "app.py", "exec"), namespace)
        classifier = namespace["telegram_owner_only_command"]
        self.assertTrue(classifier("admin stats"))
        self.assertTrue(classifier("grant premium 123"))
        self.assertFalse(classifier("Atgādini man rīt 11.00"))
        self.assertFalse(classifier("Atrodi informāciju par X"))


if __name__ == "__main__":
    unittest.main()
