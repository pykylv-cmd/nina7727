"""Managed, durable NinaOS schema migrations for pre-deploy execution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend
from deployment_compatibility import commit_identifier


LEDGER_TABLE = "nina_schema_migrations"
MIGRATION_LOCK_KEY = 7727002401
PHASE_EXPAND = "EXPAND"
PHASE_CONTRACT = "CONTRACT"
BASELINE_ID = "0000_current_shared_schema_baseline"
BASELINE_VERSION = 0
BASELINE_NAME = "Verified current NinaOS shared schema"

EXPECTED_CURRENT_SHARED_TABLES = {
    "conversation_state",
    "nina_channel_connections",
    "nina_channel_message_receipts",
    "nina_contacts",
    "nina_contact_channel_identities",
    "nina_contact_link_claims",
    "nina_contact_client_mappings",
    "nina_company_whatsapp_auth",
    "nina_company_whatsapp_pairing",
    "nina_personal_whatsapp_auth",
    "nina_personal_whatsapp_pairing",
    "nina_work_objects",
}


class MigrationError(RuntimeError):
    pass


class AmbiguousSchemaError(MigrationError):
    pass


class MigrationChecksumError(MigrationError):
    pass


class IncompleteMigrationError(MigrationError):
    pass


class ContractMigrationForbidden(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    identifier: str
    version: int
    name: str
    phase: str
    operation: object
    checksum_source: str

    @property
    def checksum(self):
        return hashlib.sha256(self.checksum_source.encode("utf-8")).hexdigest()


def _create_conversation_state(conn):
    cur = conn.cursor()
    id_column = (
        "BIGSERIAL PRIMARY KEY"
        if persistence_backend.USE_POSTGRES
        else "INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS conversation_state (
            id {id_column},
            user_id TEXT,
            user_text TEXT,
            nina_text TEXT DEFAULT '',
            intent TEXT DEFAULT '',
            emotion TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.close()


MIGRATIONS = (
    Migration(
        identifier="0001_shared_conversation_state",
        version=1,
        name="Create shared conversation state",
        phase=PHASE_EXPAND,
        operation=_create_conversation_state,
        checksum_source=(
            "0001|EXPAND|conversation_state|"
            "id,user_id,user_text,nina_text,intent,emotion,topic,created_at"
        ),
    ),
)


def _ledger_ddl():
    return f"""
        CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
            migration_identifier TEXT PRIMARY KEY,
            migration_version INTEGER NOT NULL,
            migration_name TEXT NOT NULL,
            migration_checksum TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            application_commit TEXT NOT NULL,
            migration_phase TEXT NOT NULL,
            success_state INTEGER NOT NULL
        )
    """


def _sql(statement):
    return persistence_backend.sql(statement)


def _begin_and_lock(conn):
    cur = conn.cursor()
    if persistence_backend.USE_POSTGRES:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))
    else:
        cur.execute("BEGIN IMMEDIATE")
    cur.close()


def _table_names(conn):
    cur = conn.cursor()
    if persistence_backend.USE_POSTGRES:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=current_schema()"
        )
    else:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    names = {str(row[0]) for row in (cur.fetchall() or [])}
    cur.close()
    return names


def _ledger_rows(conn):
    cur = conn.cursor()
    cur.execute(
        f"SELECT migration_identifier,migration_version,migration_name,"
        f"migration_checksum,applied_at,application_commit,migration_phase,"
        f"success_state FROM {LEDGER_TABLE} ORDER BY migration_version,migration_identifier"
    )
    rows = cur.fetchall() or []
    cur.close()
    return {
        str(row[0]): {
            "identifier": str(row[0]),
            "version": int(row[1]),
            "name": str(row[2]),
            "checksum": str(row[3]),
            "applied_at": str(row[4]),
            "application_commit": str(row[5]),
            "phase": str(row[6]),
            "success": bool(row[7]),
        }
        for row in rows
    }


def _record_success(conn, migration):
    cur = conn.cursor()
    cur.execute(
        _sql(f"""
            INSERT INTO {LEDGER_TABLE} (
                migration_identifier,migration_version,migration_name,
                migration_checksum,applied_at,application_commit,
                migration_phase,success_state
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """),
        (
            migration.identifier,
            migration.version,
            migration.name,
            migration.checksum,
            datetime.now(timezone.utc).isoformat(),
            commit_identifier(),
            migration.phase,
            1,
        ),
    )
    cur.close()


def _record_baseline(conn):
    baseline = Migration(
        BASELINE_ID,
        BASELINE_VERSION,
        BASELINE_NAME,
        PHASE_EXPAND,
        lambda _conn: None,
        "NinaOS current shared schema baseline V1",
    )
    _record_success(conn, baseline)


def _validate_or_adopt(conn):
    rows = _ledger_rows(conn)
    if rows:
        return "existing-ledger"
    tables = _table_names(conn) - {LEDGER_TABLE}
    if not tables:
        return "empty-database"
    present = EXPECTED_CURRENT_SHARED_TABLES.intersection(tables)
    missing = EXPECTED_CURRENT_SHARED_TABLES - tables
    if present and missing:
        raise AmbiguousSchemaError(
            "nina_migration_ambiguous_existing_schema:"
            f"present={len(present)}:missing={len(missing)}"
        )
    if not EXPECTED_CURRENT_SHARED_TABLES.issubset(tables):
        raise AmbiguousSchemaError(
            "nina_migration_unrecognized_existing_schema"
        )
    _record_baseline(conn)
    return "verified-baseline"


def _ordered(migrations):
    ordered = tuple(sorted(migrations, key=lambda item: (item.version, item.identifier)))
    identities = [item.identifier for item in ordered]
    versions = [item.version for item in ordered]
    if len(set(identities)) != len(identities) or len(set(versions)) != len(versions):
        raise MigrationError("nina_migration_registry_not_unique")
    return ordered


def run_migrations(phase=PHASE_EXPAND, allow_contract=False, migrations=None):
    phase = str(phase or "").upper()
    if phase not in {PHASE_EXPAND, PHASE_CONTRACT}:
        raise MigrationError("nina_migration_phase_invalid")
    if phase == PHASE_CONTRACT and not allow_contract:
        raise ContractMigrationForbidden("nina_contract_migration_requires_explicit_approval")

    registry = _ordered(MIGRATIONS if migrations is None else migrations)
    conn = persistence_backend.connect()
    applied = []
    skipped = []
    adoption = ""
    try:
        _begin_and_lock(conn)
        cur = conn.cursor()
        cur.execute(_ledger_ddl())
        cur.close()
        adoption = _validate_or_adopt(conn)
        existing = _ledger_rows(conn)
        for migration in registry:
            if migration.phase != phase:
                continue
            prior = existing.get(migration.identifier)
            if prior:
                if prior["checksum"] != migration.checksum:
                    raise MigrationChecksumError(
                        f"nina_migration_checksum_mismatch:{migration.identifier}"
                    )
                if not prior["success"]:
                    raise MigrationError(
                        f"nina_migration_prior_failure:{migration.identifier}"
                    )
                skipped.append(migration.identifier)
                continue
            migration.operation(conn)
            _record_success(conn, migration)
            applied.append(migration.identifier)
        conn.commit()
        return {
            "ok": True,
            "phase": phase,
            "adoption": adoption,
            "applied": applied,
            "skipped": skipped,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migration_status(migrations=None):
    registry = _ordered(MIGRATIONS if migrations is None else migrations)
    conn = persistence_backend.connect()
    try:
        required = [
            migration for migration in registry if migration.phase == PHASE_EXPAND
        ]
        if LEDGER_TABLE not in _table_names(conn):
            return {
                "ok": False,
                "ledger_present": False,
                "required_version": max((item.version for item in required), default=0),
                "applied_version": 0,
                "missing": [item.identifier for item in required],
                "checksum_mismatch": [],
            }
        rows = _ledger_rows(conn)
        missing = []
        mismatched = []
        for migration in required:
            row = rows.get(migration.identifier)
            if not row or not row["success"]:
                missing.append(migration.identifier)
            elif row["checksum"] != migration.checksum:
                mismatched.append(migration.identifier)
        return {
            "ok": not missing and not mismatched,
            "ledger_present": True,
            "required_version": max((item.version for item in required), default=0),
            "applied_version": max(
                (row["version"] for row in rows.values() if row["success"]),
                default=0,
            ),
            "missing": missing,
            "checksum_mismatch": mismatched,
        }
    finally:
        conn.close()


def assert_required_migrations_complete():
    status = migration_status()
    if not status["ok"]:
        raise IncompleteMigrationError(
            "nina_required_expand_migrations_incomplete:"
            f"missing={','.join(status['missing'])}:"
            f"checksum_mismatch={','.join(status['checksum_mismatch'])}"
        )
    return True
