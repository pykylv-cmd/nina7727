import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import managed_migrations
import persistence_backend
import production_schema_adoption as adoption


class ProductionSchemaAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "adoption.sqlite")
        self.backend_patch = patch.multiple(
            persistence_backend,
            HOSTED=False,
            USE_POSTGRES=False,
            DATABASE_URL="",
            DB_FILE=self.db_file,
        )
        self.backend_patch.start()

    def tearDown(self):
        self.backend_patch.stop()
        self.temp_dir.cleanup()

    def connect(self):
        return sqlite3.connect(self.db_file)

    def plan(self):
        return adoption.adoption_plan(require_postgres=False)

    def create_0001(self):
        conn = self.connect()
        managed_migrations._create_conversation_state(conn)
        conn.commit()
        conn.close()

    def create_through_0003_without_ledger(self):
        conn = self.connect()
        managed_migrations._create_conversation_state(conn)
        managed_migrations._create_agent_assignments(conn)
        managed_migrations._create_knowledge_vault(conn)
        conn.commit()
        conn.close()

    def test_empty_database_without_ledger(self):
        result = self.plan()
        self.assertTrue(result["ok"])
        self.assertEqual(
            set(result["requires_expand"]),
            {item.identifier for item in managed_migrations.MIGRATIONS},
        )
        self.assertEqual(result["adoptable_migrations"], [])

    def test_complete_legacy_foundation_without_ledger(self):
        self.create_0001()
        result = self.plan()
        self.assertEqual(
            result["migrations"]["0001_shared_conversation_state"]
            ["classification"],
            adoption.CLASS_EXACT,
        )

    def test_partial_foundation_is_not_adoptable(self):
        conn = self.connect()
        conn.execute(
            "CREATE TABLE conversation_state "
            "(id INTEGER PRIMARY KEY, user_id TEXT)"
        )
        conn.commit()
        conn.close()
        result = self.plan()
        self.assertEqual(
            result["migrations"]["0001_shared_conversation_state"]
            ["classification"],
            adoption.CLASS_PARTIAL,
        )
        self.assertNotIn(
            "0001_shared_conversation_state",
            result["adoptable_migrations"],
        )

    def test_0001_through_0003_exact_without_ledger(self):
        self.create_through_0003_without_ledger()
        result = self.plan()
        self.assertEqual(
            result["adoptable_migrations"],
            [
                "0001_shared_conversation_state",
                "0002_agent_assignment_v1",
                "0003_knowledge_vault_v1",
            ],
        )

    def test_partially_applied_0004_is_safe_expand(self):
        conn = self.connect()
        conn.execute(
            """
            CREATE TABLE nina_work_objects (
              object_id TEXT NOT NULL UNIQUE,
              workspace_id TEXT NOT NULL,
              object_type TEXT NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              source_key TEXT
            )
            """
        )
        conn.commit()
        conn.close()
        result = self.plan()
        self.assertEqual(
            result["migrations"]["0004_universal_work_objects_v1"]
            ["classification"],
            adoption.CLASS_PARTIAL,
        )

    def test_conflicting_column_type_stops_plan(self):
        conn = self.connect()
        conn.execute(
            "CREATE TABLE conversation_state "
            "(id TEXT PRIMARY KEY,user_id TEXT,user_text TEXT,nina_text TEXT,"
            "intent TEXT,emotion TEXT,topic TEXT,created_at TEXT)"
        )
        conn.commit()
        conn.close()
        result = self.plan()
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["migrations"]["0001_shared_conversation_state"]
            ["classification"],
            adoption.CLASS_CONFLICTING,
        )

    def test_duplicate_natural_key_stops_plan(self):
        conn = self.connect()
        conn.execute(
            """
            CREATE TABLE nina_work_objects (
              object_id TEXT NOT NULL UNIQUE,
              workspace_id TEXT NOT NULL,
              object_type TEXT NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              source_key TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO nina_work_objects VALUES (?,?,?,?,?,?)",
            [
                ("one", "tenant", "task", "one", "open", "same"),
                ("two", "tenant", "task", "two", "open", "same"),
            ],
        )
        conn.commit()
        conn.close()
        result = self.plan()
        self.assertFalse(result["ok"])
        self.assertTrue(any(
            item["details"].get("type")
            == "duplicate_workspace_source_key"
            for item in result["conflicts"]
        ))

    def test_existing_correct_ledger_is_preserved(self):
        managed_migrations.run_migrations(
            migrations=managed_migrations.MIGRATIONS[:1]
        )
        result = self.plan()
        applied = adoption.adopt_baseline_apply(
            result["fingerprint"], require_postgres=False
        )
        self.assertEqual(applied["adopted_migrations"], [])

    def test_repeated_apply_is_idempotent(self):
        self.create_0001()
        result = self.plan()
        first = adoption.adopt_baseline_apply(
            result["fingerprint"], require_postgres=False
        )
        second = adoption.adopt_baseline_apply(
            result["fingerprint"], require_postgres=False
        )
        self.assertEqual(
            first["adopted_migrations"],
            ["0001_shared_conversation_state"],
        )
        self.assertEqual(second["adopted_migrations"], [])

    def test_fingerprint_change_between_plan_and_apply_stops(self):
        self.create_0001()
        result = self.plan()
        conn = self.connect()
        conn.execute("CREATE TABLE concurrent_change (id TEXT)")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(
            managed_migrations.MigrationPreflightError,
            "fingerprint_changed",
        ):
            adoption.adopt_baseline_apply(
                result["fingerprint"], require_postgres=False
            )

    def test_failure_rolls_back_ledger_transaction(self):
        self.create_0001()
        result = self.plan()
        with patch.object(
            adoption, "commit_identifier",
            side_effect=RuntimeError("controlled failure"),
        ):
            with self.assertRaises(RuntimeError):
                adoption.adopt_baseline_apply(
                    result["fingerprint"], require_postgres=False
                )
        conn = self.connect()
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()
        self.assertNotIn(managed_migrations.LEDGER_TABLE, tables)

    def test_apply_never_changes_business_data(self):
        self.create_0001()
        conn = self.connect()
        conn.execute(
            "INSERT INTO conversation_state "
            "(user_id,user_text,nina_text) VALUES (?,?,?)",
            ("person", "private input", "private output"),
        )
        conn.commit()
        before = conn.execute(
            "SELECT user_id,user_text,nina_text FROM conversation_state"
        ).fetchall()
        conn.close()
        result = self.plan()
        adoption.adopt_baseline_apply(
            result["fingerprint"], require_postgres=False
        )
        conn = self.connect()
        after = conn.execute(
            "SELECT user_id,user_text,nina_text FROM conversation_state"
        ).fetchall()
        conn.close()
        self.assertEqual(before, after)

    def test_reports_contain_metadata_not_row_content(self):
        self.create_0001()
        result = self.plan()
        json_path = Path(self.temp_dir.name) / "report.json"
        md_path = Path(self.temp_dir.name) / "report.md"
        adoption.write_reports(result, json_path, md_path)
        report = json.loads(json_path.read_text("utf-8"))
        self.assertIn("fingerprint", report)
        self.assertNotIn("private input", json_path.read_text("utf-8"))
        self.assertIn(
            "Production Schema Adoption Report",
            md_path.read_text("utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
