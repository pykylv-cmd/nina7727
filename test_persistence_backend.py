import importlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet


ROOT = Path(__file__).resolve().parent
POSTGRES_ALIASES = (
    "DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRIVATE_URL", "POSTGRES_PUBLIC_URL",
    "DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL", "PGURL", "PG_URL",
    "RAILWAY_DATABASE_URL", "RAILWAY_POSTGRES_URL", "POSTGRES_CONNECTION_URL",
    "DATABASE_CONNECTION_URL",
)


class PersistenceBackendTests(unittest.TestCase):
    def _subprocess(self, code, env_updates, cwd=None):
        env = dict(os.environ)
        env.update(env_updates)
        for key in (*POSTGRES_ALIASES, "NINA_DB_FILE", "NINA_RUNTIME_ENV"):
            if key not in env_updates:
                env.pop(key, None)
            if env_updates.get(key) is None:
                env.pop(key, None)
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH", "")]))
        return subprocess.run(
            [sys.executable, "-c", code], cwd=cwd or ROOT, env=env,
            text=True, capture_output=True, timeout=30,
        )

    def test_hosted_without_database_url_fails_before_sqlite_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._subprocess(
                "import persistence_backend",
                {
                    "NINA_RUNTIME_ENV": "staging",
                    "DATABASE_URL": None,
                    "NINA_DB_FILE": "nina_memory.db",
                },
                cwd=tmp,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("database_url_required_in_hosted_runtime", result.stderr)
            self.assertFalse((Path(tmp) / "nina_memory.db").exists())

    def test_hosted_without_psycopg2_fails_closed(self):
        code = """
import builtins
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'psycopg2':
        raise ImportError('blocked for test')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
import persistence_backend
"""
        result = self._subprocess(
            code,
            {
                "NINA_RUNTIME_ENV": "staging",
                "DATABASE_URL": "postgresql://user:secret@db.internal:5432/nina",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("psycopg2_required", result.stderr)
        self.assertNotIn("secret", result.stderr)

    def test_database_url_has_highest_priority_and_blank_values_are_skipped(self):
        code = """
import persistence_backend as backend
assert backend.DATABASE_URL_SOURCE == 'DATABASE_URL'
assert backend.DATABASE_URL.endswith('/primary')
assert backend.USE_POSTGRES
"""
        result = self._subprocess(
            code,
            {
                "NINA_RUNTIME_ENV": "staging",
                "DATABASE_URL": "postgresql://user:secret@db.internal:5432/primary",
                "POSTGRES_URL": "postgresql://user:other@db.internal:5432/secondary",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        blank_result = self._subprocess(
            "import persistence_backend as b; assert b.DATABASE_URL_SOURCE == 'POSTGRES_URL'; assert b.USE_POSTGRES",
            {
                "NINA_RUNTIME_ENV": "staging",
                "DATABASE_URL": "   ",
                "POSTGRES_URL": "postgresql://user:secret@db.internal:5432/nina",
            },
        )
        self.assertEqual(blank_result.returncode, 0, blank_result.stderr)

    def test_every_historical_postgres_alias_is_accepted_without_exposure(self):
        for alias in POSTGRES_ALIASES:
            with self.subTest(alias=alias):
                value = f"postgresql://user:unique-secret@db.internal:5432/{alias.lower()}"
                result = self._subprocess(
                    "import persistence_backend as b; b.assert_backend_ready=lambda: True; print(b.DATABASE_URL_SOURCE, b.backend_name(), b.safe_backend_diagnostics()['database_url_source'])",
                    {"NINA_RUNTIME_ENV": "staging", alias: value},
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f"{alias} postgresql {alias}")
                self.assertNotIn("unique-secret", result.stdout + result.stderr)

    def test_hosted_malformed_database_url_fails_closed(self):
        result = self._subprocess(
            "import persistence_backend",
            {"NINA_RUNTIME_ENV": "staging", "DATABASE_URL": "sqlite:nina_memory.db"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("database_url_invalid", result.stderr)

    def test_hosted_sqlite_override_remains_forbidden(self):
        result = self._subprocess(
            "import persistence_backend as b; b.connect(database_url='', db_file='nina_memory.db', use_postgres=False)",
            {
                "NINA_RUNTIME_ENV": "staging",
                "POSTGRES_URL": "postgresql://user:secret@db.internal:5432/nina",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hosted_backend_override_forbidden", result.stderr)
        self.assertNotIn("secret", result.stderr)

    def test_hosted_unreachable_database_fails_web_startup(self):
        code = """
import sys, types
driver = types.ModuleType('psycopg2')
def unavailable(_url):
    raise OSError('database unavailable')
driver.connect = unavailable
sys.modules['psycopg2'] = driver
import web_app
"""
        result = self._subprocess(
            code,
            {
                "NINA_RUNTIME_ENV": "staging",
                "DATABASE_URL": "postgresql://user:secret@db.internal:5432/nina",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nina_persistence_backend_unreachable", result.stderr)
        self.assertNotIn("secret", result.stderr)

    def test_all_platform_modules_share_postgres_decision(self):
        code = """
import channel_connections, contact_identity, client_identity, company_whatsapp
import personal_whatsapp, work_objects, nina_message_service
modules = [channel_connections, contact_identity, client_identity, company_whatsapp,
           personal_whatsapp, work_objects, nina_message_service]
assert all(module.USE_POSTGRES for module in modules)
assert len({module.DATABASE_URL for module in modules}) == 1
print('shared-postgresql')
"""
        result = self._subprocess(
            code,
            {
                "NINA_RUNTIME_ENV": "staging",
                "DATABASE_URL": "postgresql://user:secret@db.internal:5432/nina",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "shared-postgresql")

    def test_all_python_entrypoints_import_shared_persistence_decision(self):
        root = Path(__file__).resolve().parent
        for filename in ("app.py", "web_app.py", "daily.py", "sales_engine.py"):
            source = (root / filename).read_text(encoding="utf-8")
            self.assertIn("from persistence_backend import", source, filename)

        for filename in ("app.py", "daily.py", "sales_engine.py"):
            source = (root / filename).read_text(encoding="utf-8")
            self.assertNotIn('os.environ.get("DATABASE_URL")', source, filename)
            self.assertNotIn("USE_POSTGRES = bool(", source, filename)
            self.assertNotIn("sqlite3.connect(", source, filename)
            self.assertIn("return persistence_connect()", source, filename)

        web_source = (root / "web_app.py").read_text(encoding="utf-8")
        self.assertIn("database_url = PLATFORM_DATABASE_URL", web_source)
        self.assertIn("url = PLATFORM_DATABASE_URL", web_source)
        self.assertIn("source = PLATFORM_DATABASE_URL_SOURCE", web_source)

    def test_explicit_local_sqlite_survives_full_python_module_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_file = os.path.join(tmp, "persistent-local-test.db")
            env = {
                "NINA_RUNTIME_ENV": "test",
                "DATABASE_URL": "",
                "NINA_DB_FILE": db_file,
                "NINA_CONTACT_IDENTITY_KEY": "persistence-contact-key-at-least-32-bytes",
                "NINA_CHANNEL_CREDENTIAL_KEY": Fernet.generate_key().decode(),
                "NINA_COMPANY_WHATSAPP_WORKSPACE": "ninaos_company",
            }
            with patch.dict(os.environ, env, clear=False):
                import persistence_backend
                import channel_connections
                import contact_identity
                import client_identity
                import company_whatsapp
                import work_objects

                backend = importlib.reload(persistence_backend)
                connections = importlib.reload(channel_connections)
                contacts = importlib.reload(contact_identity)
                clients = importlib.reload(client_identity)
                company = importlib.reload(company_whatsapp)
                objects = importlib.reload(work_objects)

                contact = contacts.resolve_contact_identity(
                    "ninaos_company", "company_whatsapp", "opaque-provider-id",
                    {"relationship_type": "client"},
                )
                mapping = clients.get_or_create_client_mapping(
                    "ninaos_company", contact["contact_id"]
                )
                company.store_auth_record("ninaos_company", "creds", {"registered": True})
                connections.set_connection_for_test(
                    "ninaos_company", "whatsapp_company", "connected", {"mode": "company_external"}
                )
                work = objects.create_work_object(
                    object_type="task", title="Persistent restart task",
                    workspace_id="ninaos_company",
                    client_id=mapping["canonical_client_id"],
                    source_key="persistence-restart:test",
                )

                backend = importlib.reload(persistence_backend)
                connections = importlib.reload(channel_connections)
                contacts = importlib.reload(contact_identity)
                clients = importlib.reload(client_identity)
                company = importlib.reload(company_whatsapp)
                objects = importlib.reload(work_objects)

                self.assertEqual(backend.backend_name(), "sqlite")
                self.assertEqual(
                    contacts.get_contact(contact["contact_id"], "ninaos_company")["contact_id"],
                    contact["contact_id"],
                )
                self.assertEqual(
                    clients.get_client_mapping("ninaos_company", contact["contact_id"])["canonical_client_id"],
                    mapping["canonical_client_id"],
                )
                self.assertTrue(company.load_auth_records("ninaos_company")["creds"]["registered"])
                self.assertEqual(
                    connections.get_connection("ninaos_company", "whatsapp_company")["status"],
                    "connected",
                )
                self.assertEqual(objects.get_work_object(work.object_id).object_id, work.object_id)
                self.assertTrue(Path(db_file).exists())


if __name__ == "__main__":
    unittest.main()
