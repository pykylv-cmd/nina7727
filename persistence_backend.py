"""One fail-closed persistence backend decision for the NinaOS platform."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from urllib.parse import urlparse

try:
    import psycopg2
except Exception:
    psycopg2 = None


class PersistenceConfigurationError(RuntimeError):
    pass


RUNTIME_ENV = (os.environ.get("NINA_RUNTIME_ENV") or "").strip().lower()
_RAILWAY_MARKERS = (
    "RAILWAY_ENVIRONMENT", "RAILWAY_ENVIRONMENT_ID", "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID", "RAILWAY_SERVICE_NAME",
)
HOSTED = RUNTIME_ENV in {"hosted", "railway", "staging", "production"} or any(
    (os.environ.get(name) or "").strip() for name in _RAILWAY_MARKERS
)
DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()
DB_FILE = (os.environ.get("NINA_DB_FILE") or "nina_memory.db").strip()


def _validated_postgres_url(value):
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/"):
        raise PersistenceConfigurationError("nina_persistence_database_url_invalid")
    return value


DATABASE_URL = _validated_postgres_url(DATABASE_URL)
if HOSTED and not DATABASE_URL:
    raise PersistenceConfigurationError("nina_persistence_database_url_required_in_hosted_runtime")
if DATABASE_URL and psycopg2 is None:
    raise PersistenceConfigurationError("nina_persistence_psycopg2_required")
if HOSTED and psycopg2 is None:
    raise PersistenceConfigurationError("nina_persistence_psycopg2_required_in_hosted_runtime")

USE_POSTGRES = bool(DATABASE_URL)


def module_settings():
    """Return the single hosted decision, with explicit local test isolation."""
    if HOSTED:
        return DATABASE_URL, DB_FILE, USE_POSTGRES
    local_url = _validated_postgres_url((os.environ.get("DATABASE_URL") or "").strip())
    if local_url and psycopg2 is None:
        raise PersistenceConfigurationError("nina_persistence_psycopg2_required")
    local_file = (os.environ.get("NINA_DB_FILE") or "nina_memory.db").strip()
    return local_url, local_file, bool(local_url)


def backend_name():
    return "postgresql" if USE_POSTGRES else "sqlite"


def runtime_environment():
    if RUNTIME_ENV:
        return RUNTIME_ENV
    return "railway" if HOSTED else "local"


def sql(statement):
    return statement if USE_POSTGRES else statement.replace("%s", "?")


def connect(database_url=None, db_file=None, use_postgres=None):
    """Connect through the governing decision.

    Explicit arguments are retained only for existing local test isolation.
    Hosted processes cannot override or diverge from the governing backend.
    """
    selected_postgres = USE_POSTGRES if use_postgres is None else bool(use_postgres)
    selected_url = DATABASE_URL if database_url is None else str(database_url or "").strip()
    selected_file = DB_FILE if db_file is None else str(db_file or "").strip()
    if HOSTED and (
        not selected_postgres or selected_url != DATABASE_URL or selected_file != DB_FILE
    ):
        raise PersistenceConfigurationError("nina_persistence_hosted_backend_override_forbidden")
    if selected_postgres:
        _validated_postgres_url(selected_url)
        if psycopg2 is None:
            raise PersistenceConfigurationError("nina_persistence_psycopg2_required")
        return psycopg2.connect(selected_url)
    if HOSTED:
        raise PersistenceConfigurationError("nina_persistence_sqlite_forbidden_in_hosted_runtime")
    return sqlite3.connect(selected_file)


def assert_backend_ready():
    conn = None
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
    except Exception as exc:
        raise PersistenceConfigurationError(
            f"nina_persistence_backend_unreachable:{type(exc).__name__}"
        ) from exc
    finally:
        if conn is not None:
            conn.close()
    return True


def database_identity_fingerprint():
    if USE_POSTGRES:
        parsed = urlparse(DATABASE_URL)
        identity = f"{parsed.hostname or ''}:{parsed.port or 5432}/{parsed.path.strip('/')}"
    else:
        identity = f"sqlite:{os.path.abspath(DB_FILE)}"
    return hashlib.sha256(identity.encode()).hexdigest()[:16]


def safe_backend_diagnostics():
    reachable = False
    error_class = ""
    try:
        assert_backend_ready()
        reachable = True
    except Exception as exc:
        error_class = type(exc).__name__
    return {
        "runtime_environment": runtime_environment(),
        "backend": backend_name(),
        "reachable": reachable,
        "database_fingerprint": database_identity_fingerprint(),
        "error_class": error_class,
    }


_DIAGNOSTIC_TABLES = {
    "nina_contacts", "nina_contact_client_mappings",
    "nina_company_whatsapp_auth", "nina_channel_connections",
    "nina_work_objects",
}


def safe_table_count(table_name, where_sql="", params=()):
    if table_name not in _DIAGNOSTIC_TABLES:
        raise ValueError("unsupported_diagnostic_table")
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(sql(f"SELECT COUNT(*) FROM {table_name}{where_sql}"), tuple(params))
        count = int((cur.fetchone() or [0])[0] or 0)
        cur.close()
        return count
    except Exception:
        return None
    finally:
        conn.close()
