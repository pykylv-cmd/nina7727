import os
import tempfile
import unittest
from unittest.mock import patch

from test_runtime_support import bind_sqlite_database, install_test_environment

install_test_environment()


def seller(url, price=17500, text="Dzīvokli pārdod īpašnieks", location="Rīga"):
    return {"source_url": url, "price": price, "title": text, "location": location, "rooms": "2", "area": "40"}


def buyer(url, text="Pērku dzīvokli Rīgā", location="Rīga"):
    return {"source_url": url, "title": text, "location": location, "price": "20000"}


class MarketplaceOpportunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.temp.name, "market.sqlite")
        cls.env = patch.dict(os.environ, {"DATABASE_URL": "", "NINA_DB_FILE": cls.db})
        cls.env.start()
        import managed_migrations
        import marketplace_opportunity
        import nina_message_service
        import work_objects
        cls.market = marketplace_opportunity
        cls.messaging = nina_message_service
        cls.work = work_objects
        cls.original = (work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES)
        work_objects.DATABASE_URL, work_objects.DB_FILE, work_objects.USE_POSTGRES = "", cls.db, False
        work_objects._SCHEMA_READY = False
        cls.restore = bind_sqlite_database(cls.db, work_objects)
        managed_migrations.run_migrations()

    @classmethod
    def tearDownClass(cls):
        cls.restore()
        cls.work.DATABASE_URL, cls.work.DB_FILE, cls.work.USE_POSTGRES = cls.original
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.work.ensure_work_objects_schema()
        conn = self.work._connect(); cur = conn.cursor()
        cur.execute("DELETE FROM nina_work_objects"); cur.execute("DELETE FROM conversation_state")
        conn.commit(); cur.close(); conn.close()

    def send(self, text, contact="owner"):
        return self.messaging.send_message_to_nina(
            text, workspace_id="tenant", canonical_work_workspace_id="tenant",
            contact_id=contact, conversation_id=f"web:{contact}", channel="web",
            generator=lambda _: self.fail("marketplace must not reach generic generation"),
        )

    def project(self, contact="owner"):
        return self.work.get_work_object_by_source_key(self.market._key("tenant", contact), "tenant")

    @patch("marketplace_opportunity._search")
    def test_exact_sale_flow_updates_one_project_and_filters_rental_wanted(self, search):
        search.return_value = ([
            seller("https://www.ss.lv/msg/a", 17500),
            seller("https://www.ss.lv/msg/r", 15000, "Meklēju dzīvokli īrei"),
            buyer("https://www.ss.lv/msg/b"),
        ], {"results": []})
        first = self.send("Tu ss.lv vari atsūtīt dzīvokli lētu")
        same_id = first["work_object_id"]
        self.send("18000 ero budžets")
        result = self.send("Meklē dzīvokli!")
        project = self.project()
        self.assertEqual(result["mode"], "seller_listing")
        self.assertIn("maksimālais", first["text"])
        self.assertIn("17500 EUR", result["text"])
        self.assertNotIn("īrei", result["text"])
        self.assertEqual(project.object_id, same_id)
        self.assertEqual(project.metadata["search_job"]["max_price"], 18000)
        self.assertEqual(self.work.list_work_objects(workspace_id="tenant", limit=50).__len__(), 1)

    @patch("marketplace_opportunity._search")
    def test_owner_preference_and_filter_updates_persist(self, search):
        search.return_value = ([], {"results": []})
        self.send("Mekle dzīvokli līdz 18000 ero kas pārdod")
        object_id = self.project().object_id
        self.send("Skaties cenu es pārējo pats novērtēšu pēc bildēm")
        self.send("Ok atrodi 20000 vērtībā")
        self.send("Turpini meklēt dzīvokli līdz 20000 ero jebkur")
        project = self.project()
        self.assertEqual(project.object_id, object_id)
        self.assertEqual(project.metadata["search_job"]["max_price"], 20000)
        self.assertEqual(project.metadata["search_job"]["location"], "Latvia")
        self.assertEqual(project.metadata["search_job"]["owner_preference"], "prioritize_price_owner_reviews_images")

    @patch("marketplace_opportunity._search")
    def test_continue_deduplicates_canonical_urls(self, search):
        search.side_effect = [
            ([seller("https://www.ss.lv/msg/a")], {"results": []}),
            ([seller("https://www.ss.lv/msg/a"), seller("https://www.ss.lv/msg/c", 19000)], {"results": []}),
        ]
        self.send("Meklē dzīvokli līdz 20000 kas pārdod")
        result = self.send("turpini")
        self.assertNotIn("/msg/a", result["text"])
        self.assertIn("/msg/c", result["text"])
        self.assertEqual(self.project().metadata["seen_listing_urls"], ["https://www.ss.lv/msg/a", "https://www.ss.lv/msg/c"])

    @patch("marketplace_opportunity._search")
    def test_buyer_request_uses_demand_only_and_never_contacts(self, search):
        search.return_value = ([buyer("https://www.ss.lv/msg/b"), seller("https://www.ss.lv/msg/s")], {"results": []})
        self.send("Meklē dzīvokli līdz 20000 kas pārdod")
        result = self.send("atrodi tam pircēju")
        self.assertEqual(result["mode"], "buyer_demand")
        self.assertIn("/msg/b", result["text"])
        self.assertNotIn("/msg/s", result["text"])
        self.assertFalse(result["external_action_executed"])

    @patch("marketplace_opportunity._search")
    def test_another_contact_cannot_inherit_project(self, search):
        search.return_value = ([], {"results": []})
        first = self.send("Meklē dzīvokli līdz 18000 kas pārdod", "a")
        second = self.send("Meklē dzīvokli līdz 20000 kas pārdod", "b")
        self.assertNotEqual(first["work_object_id"], second["work_object_id"])
        self.assertEqual(self.project("a").metadata["search_job"]["max_price"], 18000)
        self.assertEqual(self.project("b").metadata["search_job"]["max_price"], 20000)

    @patch("marketplace_opportunity._search")
    def test_no_result_is_useful_and_contains_no_fabricated_link(self, search):
        search.return_value = ([], {"rejected_results": [{"reason": "robots_disallowed"}]})
        result = self.send("Meklē ss.lv dzīvokli līdz 18000 kas pārdod")
        self.assertIn("nevarēju droši verificēt", result["text"])
        self.assertNotIn("http", result["text"])

    def test_typed_contracts_are_reusable(self):
        match = self.market.OpportunityMatch("seller", "buyer", True, None, True, ("condition",))
        self.assertTrue(match.price_compatible)
        self.assertIn("condition", match.unknowns)

    @patch("marketplace_opportunity._search", side_effect=Exception("unsafe test exception"))
    def test_unexpected_acquisition_exception_is_not_hidden(self, search):
        with self.assertRaises(Exception):
            self.send("Meklē ss.lv dzīvokli līdz 18000 kas pārdod")

    @patch("marketplace_opportunity._search")
    def test_provider_unavailable_is_honest_and_persisted(self, search):
        search.side_effect = self.market.web_research.WebResearchError("search_provider_not_configured")
        result = self.send("Meklē ss.lv dzīvokli līdz 18000 kas pārdod")
        self.assertIn("neatradu nevienu verificētu", result["text"])
        self.assertEqual(self.project().metadata["acquisition_error"], "acquisition_unavailable")


if __name__ == "__main__":
    unittest.main()
