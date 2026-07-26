import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import managed_migrations
import persistence_backend
import runtime_readiness


class ManagedMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = str(Path(self.temp_dir.name) / "migrations.sqlite")
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

    def _tables(self):
        conn = sqlite3.connect(self.db_file)
        try:
            return {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()

    def _ledger(self):
        conn = sqlite3.connect(self.db_file)
        try:
            return conn.execute(
                f"SELECT migration_identifier,migration_checksum,success_state "
                f"FROM {managed_migrations.LEDGER_TABLE} "
                f"ORDER BY migration_version"
            ).fetchall()
        finally:
            conn.close()

    def test_empty_database_initializes_ledger_and_expand_migration(self):
        result = managed_migrations.run_migrations()
        self.assertEqual(result["adoption"], "empty-database")
        self.assertEqual(result["applied"], ["0001_shared_conversation_state"])
        self.assertIn(managed_migrations.LEDGER_TABLE, self._tables())
        self.assertIn("conversation_state", self._tables())
        self.assertEqual(self._ledger()[0][2], 1)

    def test_compatible_existing_database_is_verified_and_baselined(self):
        conn = sqlite3.connect(self.db_file)
        for table in managed_migrations.EXPECTED_CURRENT_SHARED_TABLES:
            conn.execute(f"CREATE TABLE {table} (id TEXT)")
        conn.commit()
        conn.close()
        result = managed_migrations.run_migrations()
        self.assertEqual(result["adoption"], "verified-baseline")
        identifiers = [row[0] for row in self._ledger()]
        self.assertEqual(
            identifiers,
            [managed_migrations.BASELINE_ID, "0001_shared_conversation_state"],
        )

    def test_ambiguous_existing_schema_fails_closed(self):
        conn = sqlite3.connect(self.db_file)
        conn.execute("CREATE TABLE nina_contacts (id TEXT)")
        conn.commit()
        conn.close()
        with self.assertRaises(managed_migrations.AmbiguousSchemaError):
            managed_migrations.run_migrations()
        self.assertNotIn(managed_migrations.LEDGER_TABLE, self._tables())

    def test_deterministic_order_and_already_applied_skip(self):
        order = []
        migrations = (
            managed_migrations.Migration("m2", 2, "second", "EXPAND",
                                         lambda _conn: order.append("m2"), "m2"),
            managed_migrations.Migration("m1", 1, "first", "EXPAND",
                                         lambda _conn: order.append("m1"), "m1"),
        )
        first = managed_migrations.run_migrations(migrations=migrations)
        second = managed_migrations.run_migrations(migrations=migrations)
        self.assertEqual(order, ["m1", "m2"])
        self.assertEqual(first["applied"], ["m1", "m2"])
        self.assertEqual(second["skipped"], ["m1", "m2"])

    def test_checksum_mismatch_fails(self):
        managed_migrations.run_migrations()
        conn = sqlite3.connect(self.db_file)
        conn.execute(
            f"UPDATE {managed_migrations.LEDGER_TABLE} "
            f"SET migration_checksum='tampered' "
            f"WHERE migration_identifier='0001_shared_conversation_state'"
        )
        conn.commit()
        conn.close()
        with self.assertRaises(managed_migrations.MigrationChecksumError):
            managed_migrations.run_migrations()

    def test_failed_migration_is_rolled_back_and_not_successful(self):
        def fail(conn):
            conn.execute("CREATE TABLE must_rollback (id TEXT)")
            raise ValueError("migration failed")

        migration = managed_migrations.Migration(
            "fail1", 1, "failure", "EXPAND", fail, "failure-v1"
        )
        with self.assertRaises(ValueError):
            managed_migrations.run_migrations(migrations=(migration,))
        self.assertNotIn("must_rollback", self._tables())
        self.assertNotIn(managed_migrations.LEDGER_TABLE, self._tables())

    def test_concurrent_attempts_apply_once(self):
        apply_count = []

        def operation(conn):
            conn.execute("CREATE TABLE concurrency_proof (value TEXT)")
            conn.execute("INSERT INTO concurrency_proof(value) VALUES ('applied')")
            apply_count.append(1)

        migration = managed_migrations.Migration(
            "concurrent1", 1, "concurrent", "EXPAND",
            operation, "concurrent-v1",
        )
        errors = []

        def run():
            try:
                managed_migrations.run_migrations(migrations=(migration,))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(apply_count), 1)
        conn = sqlite3.connect(self.db_file)
        count = conn.execute("SELECT COUNT(*) FROM concurrency_proof").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_incomplete_blocks_readiness_and_complete_allows_ready(self):
        state = runtime_readiness.RuntimeReadiness("migration-gate")
        state.register(
            "migrations", managed_migrations.assert_required_migrations_complete
        )
        state.begin_startup()
        with self.assertRaises(managed_migrations.IncompleteMigrationError):
            state.run_checks()
        self.assertFalse(state.ready)

        managed_migrations.run_migrations()
        ready = runtime_readiness.RuntimeReadiness("migration-gate-complete")
        ready.register(
            "migrations", managed_migrations.assert_required_migrations_complete
        )
        ready.begin_startup()
        ready.run_checks()
        ready.complete_startup()
        self.assertTrue(ready.ready)

    def test_contract_requires_explicit_approval(self):
        contract = managed_migrations.Migration(
            "contract1", 2, "future contract", "CONTRACT",
            lambda _conn: None, "contract-v1",
        )
        with self.assertRaises(managed_migrations.ContractMigrationForbidden):
            managed_migrations.run_migrations(
                phase="CONTRACT", migrations=(contract,)
            )


if __name__ == "__main__":
    unittest.main()
