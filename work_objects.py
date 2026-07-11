# work_objects.py
# NinaOS Persistent Work Objects V2.0
# ONE NINA CORE V1 — Persistent Work Objects
# Build target: NinaOS Constitution V4 / V4.2
#
# Purpose:
# - one canonical Work Object language for NinaOS
# - Postgres-backed persistent truth in Railway
# - SQLite-backed persistent truth for local development
# - shared by Telegram runtime, Web runtime and future channels
# - source_key deduplication so one intake event creates one canonical object
#
# IMPORTANT:
# - WORK_OBJECT_STORE remains only as a compatibility cache.
# - It is NOT the source of truth.
# - nina_work_objects database table is the source of truth.
# - Existing memory_backups / conversation_state data is not deleted or modified.

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg2
except Exception:
    psycopg2 = None


WORK_OBJECTS_VERSION = "Persistent Work Objects V2.1 — ONE NINA Canonical Work Mapping V2"
DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()
DB_FILE = (os.environ.get("NINA_DB_FILE") or "nina_memory.db").strip()
USE_POSTGRES = bool(DATABASE_URL and psycopg2)

_TABLE_NAME = "nina_work_objects"
_SCHEMA_READY = False


class WorkObjectPersistenceError(RuntimeError):
    """Raised when NinaOS cannot safely reach persistent Work Object storage."""


@dataclass(frozen=True)
class WorkObjectType:
    type_id: str
    name: str
    category: str
    description: str
    default_statuses: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    risk_level: str = "low"
    status: str = "active"


@dataclass
class WorkObject:
    object_id: str
    object_type: str
    title: str
    status: str = "open"
    workspace_id: str = "demo_small_business"
    assigned_agent_id: str = "nina_office_manager_smb"
    client_id: str = ""
    project_id: str = ""
    priority: str = "normal"
    due_date: str = ""
    linked_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    origin_channel: str = ""
    origin_user_id: str = ""
    source_key: str = ""
    created_at: str = field(default_factory=lambda: _utc_now())
    updated_at: str = field(default_factory=lambda: _utc_now())


# =========================================================
# Work Object Type Registry
# =========================================================

WORK_OBJECT_TYPES: Dict[str, WorkObjectType] = {
    "task": WorkObjectType(
        type_id="task",
        name="Task",
        category="operations",
        description="A work task with owner, status, priority and due date.",
        default_statuses=["open", "in_progress", "done", "cancelled"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "client": WorkObjectType(
        type_id="client",
        name="Client",
        category="crm",
        description="A client or customer record inside a workspace.",
        default_statuses=["active", "lead", "inactive", "archived"],
        allowed_roles=["client_followup_manager", "finance_admin_assistant", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "project": WorkObjectType(
        type_id="project",
        name="Project",
        category="operations",
        description="A client or internal project with tasks, estimates, files and invoices.",
        default_statuses=["open", "active", "on_hold", "completed", "cancelled"],
        allowed_roles=["office_manager_core", "estimating_assistant_basic", "document_admin"],
        risk_level="medium",
    ),

    "estimate": WorkObjectType(
        type_id="estimate",
        name="Estimate",
        category="estimating",
        description="An estimate or pricing draft for client work.",
        default_statuses=["draft", "in_progress", "sent", "approved", "rejected", "cancelled"],
        allowed_roles=["estimating_assistant_basic", "client_followup_manager", "document_admin"],
        risk_level="medium",
    ),

    "offer": WorkObjectType(
        type_id="offer",
        name="Offer",
        category="sales",
        description="A client offer or proposal draft.",
        default_statuses=["draft", "sent", "accepted", "rejected", "expired"],
        allowed_roles=["estimating_assistant_basic", "client_followup_manager"],
        risk_level="medium",
    ),

    "invoice": WorkObjectType(
        type_id="invoice",
        name="Invoice",
        category="finance",
        description="Invoice administration object for payment tracking.",
        default_statuses=["draft", "sent", "paid", "overdue", "cancelled"],
        allowed_roles=["finance_admin_assistant", "client_followup_manager", "document_admin"],
        risk_level="high",
    ),

    "payment_request": WorkObjectType(
        type_id="payment_request",
        name="Payment Request",
        category="finance",
        description="Payment request or payment follow-up object.",
        default_statuses=["open", "sent", "paid", "overdue", "cancelled"],
        allowed_roles=["finance_admin_assistant"],
        risk_level="high",
    ),

    "followup_task": WorkObjectType(
        type_id="followup_task",
        name="Follow-up Task",
        category="crm",
        description="Follow-up item connected to client, invoice, estimate, meeting or offer.",
        default_statuses=["open", "scheduled", "done", "cancelled"],
        allowed_roles=["client_followup_manager", "office_manager_core"],
        risk_level="medium",
    ),

    "reminder": WorkObjectType(
        type_id="reminder",
        name="Reminder",
        category="operations",
        description="Reminder object for user, workspace, client or project.",
        default_statuses=["active", "sent", "cancelled"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "document_case": WorkObjectType(
        type_id="document_case",
        name="Document Case",
        category="documents",
        description="Document bundle connected to client, project, estimate, invoice or contract.",
        default_statuses=["open", "processing", "ready", "archived"],
        allowed_roles=["document_admin", "finance_admin_assistant", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "contract": WorkObjectType(
        type_id="contract",
        name="Contract",
        category="legal_documents",
        description="Contract document object requiring careful approval before sending.",
        default_statuses=["draft", "review", "approved", "sent", "signed", "archived"],
        allowed_roles=["document_admin"],
        risk_level="high",
    ),

    "daily_plan": WorkObjectType(
        type_id="daily_plan",
        name="Daily Plan",
        category="operations",
        description="Daily work plan for a workspace or user.",
        default_statuses=["draft", "active", "completed"],
        allowed_roles=["office_manager_core"],
        risk_level="low",
    ),

    "expense_record": WorkObjectType(
        type_id="expense_record",
        name="Expense Record",
        category="finance",
        description="Basic expense administration record.",
        default_statuses=["draft", "categorized", "sent_to_accountant", "archived"],
        allowed_roles=["finance_admin_assistant"],
        risk_level="medium",
    ),

    "meeting_note": WorkObjectType(
        type_id="meeting_note",
        name="Meeting Note",
        category="operations",
        description="Meeting notes connected to client, project or follow-up.",
        default_statuses=["draft", "saved", "linked"],
        allowed_roles=["office_manager_core", "client_followup_manager"],
        risk_level="low",
    ),

    "client_request": WorkObjectType(
        type_id="client_request",
        name="Client Request",
        category="crm",
        description="Incoming client request that may become task, project, estimate or offer.",
        default_statuses=["new", "reviewed", "converted", "closed"],
        allowed_roles=["client_followup_manager", "estimating_assistant_basic"],
        risk_level="medium",
    ),

    "project_scope": WorkObjectType(
        type_id="project_scope",
        name="Project Scope",
        category="estimating",
        description="Structured scope of work for project or estimate.",
        default_statuses=["draft", "review", "approved"],
        allowed_roles=["estimating_assistant_basic"],
        risk_level="medium",
    ),

    "client_file_bundle": WorkObjectType(
        type_id="client_file_bundle",
        name="Client File Bundle",
        category="documents",
        description="File bundle connected to one client.",
        default_statuses=["open", "organized", "archived"],
        allowed_roles=["document_admin"],
        risk_level="medium",
    ),

    "accounting_document_case": WorkObjectType(
        type_id="accounting_document_case",
        name="Accounting Document Case",
        category="finance_documents",
        description="Document package prepared for accountant or finance review.",
        default_statuses=["open", "prepared", "sent_to_accountant", "archived"],
        allowed_roles=["finance_admin_assistant", "document_admin"],
        risk_level="high",
    ),
}


# =========================================================
# Compatibility cache — NOT source of truth
# =========================================================

WORK_OBJECT_STORE: Dict[str, WorkObject] = {}


# =========================================================
# Persistence helpers
# =========================================================

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return json.dumps({"raw": str(value)}, ensure_ascii=False)


def _json_loads(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return fallback


def _sql(sql: str) -> str:
    return sql if USE_POSTGRES else sql.replace("%s", "?")


def _connect():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE)


def _execute(cursor, sql: str, params: Tuple[Any, ...] = ()):
    return cursor.execute(_sql(sql), params)


def _table_columns(conn) -> List[str]:
    cur = conn.cursor()
    try:
        if USE_POSTGRES:
            _execute(
                cur,
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
                """,
                (_TABLE_NAME,),
            )
            return [str(row[0]) for row in cur.fetchall()]
        _execute(cur, f"PRAGMA table_info({_TABLE_NAME})")
        return [str(row[1]) for row in cur.fetchall()]
    finally:
        cur.close()


def _add_missing_columns(conn) -> None:
    columns = set(_table_columns(conn))
    additions = {
        "origin_channel": "TEXT DEFAULT ''",
        "origin_user_id": "TEXT DEFAULT ''",
        "source_key": "TEXT NULL",
        "linked_files_json": "TEXT DEFAULT '[]'",
        "metadata_json": "TEXT DEFAULT '{}'",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }
    cur = conn.cursor()
    try:
        for name, sql_type in additions.items():
            if name not in columns:
                cur.execute(f"ALTER TABLE {_TABLE_NAME} ADD COLUMN {name} {sql_type}")
        conn.commit()
    finally:
        cur.close()


def ensure_work_objects_schema() -> bool:
    """Create the canonical Work Object table safely.

    The operation is additive only. Existing NinaOS memory tables are untouched.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return True

    conn = None
    try:
        conn = _connect()
        cur = conn.cursor()
        try:
            id_type = "BIGSERIAL" if USE_POSTGRES else "INTEGER"
            id_pk = "PRIMARY KEY" if USE_POSTGRES else "PRIMARY KEY AUTOINCREMENT"
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                    id {id_type} {id_pk},
                    object_id TEXT NOT NULL UNIQUE,
                    workspace_id TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_agent_id TEXT DEFAULT '',
                    client_id TEXT DEFAULT '',
                    project_id TEXT DEFAULT '',
                    priority TEXT DEFAULT 'normal',
                    due_date TEXT DEFAULT '',
                    linked_files_json TEXT DEFAULT '[]',
                    metadata_json TEXT DEFAULT '{{}}',
                    origin_channel TEXT DEFAULT '',
                    origin_user_id TEXT DEFAULT '',
                    source_key TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            cur.close()

        _add_missing_columns(conn)

        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_source_key
                ON {_TABLE_NAME} (workspace_id, source_key)
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_type
                ON {_TABLE_NAME} (workspace_id, object_type)
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_nina_work_objects_client
                ON {_TABLE_NAME} (workspace_id, client_id)
                """
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_nina_work_objects_updated
                ON {_TABLE_NAME} (updated_at)
                """
            )
            conn.commit()
        finally:
            cur.close()

        _SCHEMA_READY = True
        return True
    except Exception as exc:
        raise WorkObjectPersistenceError(
            f"NinaOS Work Object persistence nav pieejams: {exc}"
        ) from exc
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _row_to_work_object(row: Any) -> WorkObject:
    return WorkObject(
        object_id=_clean(row[0]),
        workspace_id=_clean(row[1]),
        object_type=_clean(row[2]),
        title=_clean(row[3]),
        status=_clean(row[4]) or "open",
        assigned_agent_id=_clean(row[5]),
        client_id=_clean(row[6]),
        project_id=_clean(row[7]),
        priority=_clean(row[8]) or "normal",
        due_date=_clean(row[9]),
        linked_files=list(_json_loads(row[10], [])),
        metadata=dict(_json_loads(row[11], {})),
        origin_channel=_clean(row[12]),
        origin_user_id=_clean(row[13]),
        source_key=_clean(row[14]),
        created_at=_clean(row[15]),
        updated_at=_clean(row[16]),
    )


_SELECT_FIELDS = """
    object_id,
    workspace_id,
    object_type,
    title,
    status,
    assigned_agent_id,
    client_id,
    project_id,
    priority,
    due_date,
    linked_files_json,
    metadata_json,
    origin_channel,
    origin_user_id,
    source_key,
    created_at,
    updated_at
"""


def _cache(obj: Optional[WorkObject]) -> Optional[WorkObject]:
    if obj is not None:
        WORK_OBJECT_STORE[obj.object_id] = obj
    return obj


def persistence_backend() -> str:
    return "postgres" if USE_POSTGRES else f"sqlite:{DB_FILE}"


def persistence_health() -> Dict[str, Any]:
    try:
        ensure_work_objects_schema()
        conn = _connect()
        cur = conn.cursor()
        try:
            _execute(cur, f"SELECT COUNT(*) FROM {_TABLE_NAME}")
            count = int((cur.fetchone() or [0])[0] or 0)
        finally:
            cur.close()
            conn.close()
        return {
            "ok": True,
            "backend": persistence_backend(),
            "table": _TABLE_NAME,
            "objects": count,
            "version": WORK_OBJECTS_VERSION,
        }
    except Exception as exc:
        return {
            "ok": False,
            "backend": persistence_backend(),
            "table": _TABLE_NAME,
            "error": str(exc)[:300],
            "version": WORK_OBJECTS_VERSION,
        }


# =========================================================
# Registry helpers
# =========================================================

def get_work_object_type(type_id: str) -> Optional[WorkObjectType]:
    return WORK_OBJECT_TYPES.get(_clean(type_id))


def list_work_object_types() -> List[WorkObjectType]:
    return list(WORK_OBJECT_TYPES.values())


def list_work_object_type_ids() -> List[str]:
    return sorted(WORK_OBJECT_TYPES.keys())


def _validate_object_type(object_type: str) -> WorkObjectType:
    obj_type = get_work_object_type(object_type)
    if not obj_type:
        raise ValueError(f"Unknown work object type: {object_type}")
    return obj_type


def _default_status(object_type: str) -> str:
    obj_type = _validate_object_type(object_type)
    return obj_type.default_statuses[0] if obj_type.default_statuses else "open"


def _validate_status(object_type: str, status: str) -> str:
    value = _clean(status) or _default_status(object_type)
    obj_type = _validate_object_type(object_type)
    if obj_type.default_statuses and value not in obj_type.default_statuses:
        raise ValueError(
            f"Invalid status '{value}' for work object type '{object_type}'. "
            f"Allowed: {', '.join(obj_type.default_statuses)}"
        )
    return value


# =========================================================
# ONE NINA Canonical Work Mapping V2
# =========================================================

def classify_canonical_work_object_type(raw_text="", title="", metadata=None, default_type="task"):
    """One shared semantic mapper for Telegram, Web and future channels."""
    metadata = metadata if isinstance(metadata, dict) else {}
    legacy = metadata.get("legacy_task")
    legacy_text = " " .join(str(v) for v in legacy.values() if v not in (None, "")) if isinstance(legacy, dict) else str(legacy or "")
    text = " ".join([str(raw_text or ""), str(title or ""), str(metadata.get("raw_text") or ""), legacy_text]).lower()
    if any(x in text for x in ("rēķin", "rekin", "invoice", "apmaks")):
        return "invoice"
    if any(x in text for x in ("piedāvājum", "piedavajum", "tāme", "tame", "estimate", "quote", "quotation")):
        return "estimate"
    if any(x in text for x in ("follow-up", "follow up", "followup", "jāpajaut", "japajaut", "atgādin", "atgadin")):
        return "followup_task"
    if any(x in text for x in ("dokuments", "dokumentu", "līgums", "ligums", "pdf", "pielikums", "attachment")):
        return "document_case"
    if any(x in text for x in ("projekts", "projektu", "projekta", "būvobjekts", "buvobjekts")):
        return "project"
    return _clean(default_type) or "task"


def migrate_canonical_work_mapping_v2():
    """Correct old ONE NINA bridge rows in place and preserve object_id/source_key."""
    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    updated = 0
    try:
        _execute(cur, f"SELECT {_SELECT_FIELDS} FROM {_TABLE_NAME} ORDER BY created_at ASC")
        for row in cur.fetchall() or []:
            obj = _row_to_work_object(row)
            meta = obj.metadata if isinstance(obj.metadata, dict) else {}
            if str(meta.get("source") or "") != "telegram_task_engine":
                continue
            mapped = classify_canonical_work_object_type(meta.get("raw_text", ""), obj.title, meta, obj.object_type)
            if mapped == obj.object_type:
                continue
            _validate_object_type(mapped)
            meta = dict(meta)
            meta["canonical_mapping_version"] = "ONE_NINA_CANONICAL_WORK_MAPPING_V2"
            meta["previous_object_type"] = obj.object_type
            meta["mapped_object_type"] = mapped
            _execute(cur, f"UPDATE {_TABLE_NAME} SET object_type=%s, status=%s, metadata_json=%s, updated_at=%s WHERE object_id=%s", (mapped, _default_status(mapped), _json_dumps(meta), _utc_now(), obj.object_id))
            updated += 1
        conn.commit()
        return {"ok": True, "updated": updated}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


# =========================================================
# Canonical Work Object API
# =========================================================

def get_work_object_by_source_key(
    source_key: str,
    workspace_id: str = "demo_small_business",
) -> Optional[WorkObject]:
    source_key = _clean(source_key)
    workspace_id = _clean(workspace_id) or "demo_small_business"
    if not source_key:
        return None

    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"""
            SELECT {_SELECT_FIELDS}
            FROM {_TABLE_NAME}
            WHERE workspace_id = %s AND source_key = %s
            LIMIT 1
            """,
            (workspace_id, source_key),
        )
        row = cur.fetchone()
        return _cache(_row_to_work_object(row)) if row else None
    finally:
        cur.close()
        conn.close()


def get_work_object(object_id: str) -> Optional[WorkObject]:
    object_id = _clean(object_id)
    if not object_id:
        return None

    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"""
            SELECT {_SELECT_FIELDS}
            FROM {_TABLE_NAME}
            WHERE object_id = %s
            LIMIT 1
            """,
            (object_id,),
        )
        row = cur.fetchone()
        return _cache(_row_to_work_object(row)) if row else None
    finally:
        cur.close()
        conn.close()


def create_work_object(
    object_type: str,
    title: str,
    workspace_id: str = "demo_small_business",
    assigned_agent_id: str = "nina_office_manager_smb",
    client_id: str = "",
    project_id: str = "",
    priority: str = "normal",
    due_date: str = "",
    status: Optional[str] = None,
    linked_files: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    origin_channel: str = "",
    origin_user_id: str = "",
    source_key: str = "",
) -> WorkObject:
    """Create one canonical persistent Work Object.

    Backward-compatible with the V1 signature. New fields are optional.
    When source_key is present, an existing object with the same
    (workspace_id, source_key) is returned instead of creating a duplicate.
    """
    object_type = _clean(object_type)
    title = _clean(title)
    workspace_id = _clean(workspace_id) or "demo_small_business"
    source_key = _clean(source_key)

    _validate_object_type(object_type)
    if not title:
        raise ValueError("Work object title is required.")

    if source_key:
        existing = get_work_object_by_source_key(source_key, workspace_id)
        if existing:
            return existing

    status_value = _validate_status(object_type, status or _default_status(object_type))
    now = _utc_now()
    obj = WorkObject(
        object_id=f"wo_{uuid.uuid4().hex}",
        object_type=object_type,
        title=title,
        status=status_value,
        workspace_id=workspace_id,
        assigned_agent_id=_clean(assigned_agent_id),
        client_id=_clean(client_id),
        project_id=_clean(project_id),
        priority=_clean(priority) or "normal",
        due_date=_clean(due_date),
        linked_files=list(linked_files or []),
        metadata=dict(metadata or {}),
        origin_channel=_clean(origin_channel),
        origin_user_id=_clean(origin_user_id),
        source_key=source_key,
        created_at=now,
        updated_at=now,
    )

    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"""
            INSERT INTO {_TABLE_NAME} (
                object_id,
                workspace_id,
                object_type,
                title,
                status,
                assigned_agent_id,
                client_id,
                project_id,
                priority,
                due_date,
                linked_files_json,
                metadata_json,
                origin_channel,
                origin_user_id,
                source_key,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                obj.object_id,
                obj.workspace_id,
                obj.object_type,
                obj.title,
                obj.status,
                obj.assigned_agent_id,
                obj.client_id,
                obj.project_id,
                obj.priority,
                obj.due_date,
                _json_dumps(obj.linked_files),
                _json_dumps(obj.metadata),
                obj.origin_channel,
                obj.origin_user_id,
                obj.source_key or None,
                obj.created_at,
                obj.updated_at,
            ),
        )
        conn.commit()
        return _cache(obj)
    except Exception:
        conn.rollback()
        if source_key:
            existing = get_work_object_by_source_key(source_key, workspace_id)
            if existing:
                return existing
        raise
    finally:
        cur.close()
        conn.close()


def save_or_get_work_object(
    *,
    object_type: str,
    title: str,
    source_key: str,
    workspace_id: str = "demo_small_business",
    assigned_agent_id: str = "nina_office_manager_smb",
    client_id: str = "",
    project_id: str = "",
    priority: str = "normal",
    due_date: str = "",
    status: Optional[str] = None,
    linked_files: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    origin_channel: str = "",
    origin_user_id: str = "",
) -> Tuple[WorkObject, bool]:
    """Idempotent canonical save.

    Returns (object, created).
    The source_key is mandatory because this API is intended for channel bridges.
    """
    source_key = _clean(source_key)
    if not source_key:
        raise ValueError("source_key is required for save_or_get_work_object().")

    existing = get_work_object_by_source_key(source_key, workspace_id)
    if existing:
        return existing, False

    metadata = dict(metadata or {})
    object_type = classify_canonical_work_object_type(
        metadata.get("raw_text", ""), title, metadata, object_type
    )
    metadata["canonical_mapping_version"] = "ONE_NINA_CANONICAL_WORK_MAPPING_V2"

    obj = create_work_object(
        object_type=object_type,
        title=title,
        workspace_id=workspace_id,
        assigned_agent_id=assigned_agent_id,
        client_id=client_id,
        project_id=project_id,
        priority=priority,
        due_date=due_date,
        status=status,
        linked_files=linked_files,
        metadata=metadata,
        origin_channel=origin_channel,
        origin_user_id=origin_user_id,
        source_key=source_key,
    )
    return obj, True


def list_work_objects(
    workspace_id: Optional[str] = None,
    object_type: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 500,
) -> List[WorkObject]:
    ensure_work_objects_schema()
    migrate_canonical_work_mapping_v2()

    where: List[str] = []
    params: List[Any] = []

    if workspace_id:
        where.append("workspace_id = %s")
        params.append(_clean(workspace_id))
    if object_type:
        where.append("object_type = %s")
        params.append(_clean(object_type))
    if status:
        where.append("status = %s")
        params.append(_clean(status))
    if client_id:
        where.append("client_id = %s")
        params.append(_clean(client_id))
    if project_id:
        where.append("project_id = %s")
        params.append(_clean(project_id))

    where_sql = " WHERE " + " AND ".join(where) if where else ""
    safe_limit = max(1, min(int(limit or 500), 5000))

    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"""
            SELECT {_SELECT_FIELDS}
            FROM {_TABLE_NAME}
            {where_sql}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT %s
            """,
            tuple(params + [safe_limit]),
        )
        objects = [_row_to_work_object(row) for row in cur.fetchall()]
        for obj in objects:
            _cache(obj)
        return objects
    finally:
        cur.close()
        conn.close()


def update_work_object(
    object_id: str,
    *,
    title: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    client_id: Optional[str] = None,
    project_id: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    linked_files: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[WorkObject]:
    obj = get_work_object(object_id)
    if not obj:
        return None

    next_title = obj.title if title is None else _clean(title)
    if not next_title:
        raise ValueError("Work object title cannot be empty.")

    next_status = obj.status if status is None else _validate_status(obj.object_type, status)
    next_metadata = obj.metadata if metadata is None else dict(metadata)
    next_files = obj.linked_files if linked_files is None else list(linked_files)
    updated_at = _utc_now()

    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"""
            UPDATE {_TABLE_NAME}
            SET
                title = %s,
                status = %s,
                assigned_agent_id = %s,
                client_id = %s,
                project_id = %s,
                priority = %s,
                due_date = %s,
                linked_files_json = %s,
                metadata_json = %s,
                updated_at = %s
            WHERE object_id = %s
            """,
            (
                next_title,
                next_status,
                obj.assigned_agent_id if assigned_agent_id is None else _clean(assigned_agent_id),
                obj.client_id if client_id is None else _clean(client_id),
                obj.project_id if project_id is None else _clean(project_id),
                obj.priority if priority is None else (_clean(priority) or "normal"),
                obj.due_date if due_date is None else _clean(due_date),
                _json_dumps(next_files),
                _json_dumps(next_metadata),
                updated_at,
                obj.object_id,
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return get_work_object(obj.object_id)


def update_work_object_status(object_id: str, status: str) -> Optional[WorkObject]:
    return update_work_object(object_id, status=status)


def count_work_objects(
    workspace_id: str = "demo_small_business",
    object_type: Optional[str] = None,
    statuses: Optional[List[str]] = None,
) -> int:
    ensure_work_objects_schema()

    where = ["workspace_id = %s"]
    params: List[Any] = [_clean(workspace_id) or "demo_small_business"]

    if object_type:
        where.append("object_type = %s")
        params.append(_clean(object_type))

    if statuses:
        cleaned = [_clean(value) for value in statuses if _clean(value)]
        if cleaned:
            placeholders = ", ".join(["%s"] * len(cleaned))
            where.append(f"status IN ({placeholders})")
            params.extend(cleaned)

    conn = _connect()
    cur = conn.cursor()
    try:
        _execute(
            cur,
            f"SELECT COUNT(*) FROM {_TABLE_NAME} WHERE {' AND '.join(where)}",
            tuple(params),
        )
        return int((cur.fetchone() or [0])[0] or 0)
    finally:
        cur.close()
        conn.close()


def dashboard_counts(workspace_id: str = "demo_small_business") -> Dict[str, int]:
    return {
        "tasks_today": count_work_objects(
            workspace_id=workspace_id,
            object_type="task",
            statuses=["open", "in_progress"],
        ),
        "followups": count_work_objects(
            workspace_id=workspace_id,
            object_type="followup_task",
            statuses=["open", "scheduled"],
        ),
        "invoices_due": count_work_objects(
            workspace_id=workspace_id,
            object_type="invoice",
            statuses=["sent", "overdue"],
        ),
        "estimates_in_progress": count_work_objects(
            workspace_id=workspace_id,
            object_type="estimate",
            statuses=["draft", "in_progress"],
        ),
        "projects_active": count_work_objects(
            workspace_id=workspace_id,
            object_type="project",
            statuses=["open", "active"],
        ),
    }


# =========================================================
# Demo seed — persistent and isolated
# =========================================================

def _demo_objects() -> List[Dict[str, Any]]:
    return [
        {
            "object_type": "client",
            "title": "Demo Client",
            "status": "active",
            "source_key": "demo:client:1",
        },
        {
            "object_type": "task",
            "title": "Prepare today workspace priorities",
            "priority": "high",
            "status": "open",
            "source_key": "demo:task:1",
        },
        {
            "object_type": "followup_task",
            "title": "Follow up with Demo Client about offer",
            "priority": "normal",
            "status": "scheduled",
            "source_key": "demo:followup:1",
        },
        {
            "object_type": "estimate",
            "title": "Demo estimate draft",
            "status": "draft",
            "source_key": "demo:estimate:1",
        },
        {
            "object_type": "invoice",
            "title": "Demo invoice follow-up",
            "status": "sent",
            "source_key": "demo:invoice:1",
        },
        {
            "object_type": "project",
            "title": "Demo active project",
            "status": "active",
            "source_key": "demo:project:1",
        },
        {
            "object_type": "document_case",
            "title": "Demo client document package",
            "status": "open",
            "source_key": "demo:document:1",
        },
    ]


def seed_demo_work_objects() -> Dict[str, Any]:
    created = 0
    for item in _demo_objects():
        metadata = {"source": "demo_seed", "demo": True}
        _obj, was_created = save_or_get_work_object(
            workspace_id="demo_small_business",
            assigned_agent_id="nina_office_manager_smb",
            metadata=metadata,
            origin_channel="demo",
            origin_user_id="__demo__",
            **item,
        )
        if was_created:
            created += 1

    count = len(
        [
            obj
            for obj in list_work_objects(workspace_id="demo_small_business", limit=5000)
            if obj.metadata.get("source") == "demo_seed"
        ]
    )
    return {
        "ok": True,
        "message": "Demo work objects created." if created else "Demo work objects already exist.",
        "created": created,
        "count": count,
    }


def clear_demo_work_objects() -> Dict[str, Any]:
    ensure_work_objects_schema()
    conn = _connect()
    cur = conn.cursor()
    try:
        if USE_POSTGRES:
            _execute(
                cur,
                f"DELETE FROM {_TABLE_NAME} WHERE metadata_json LIKE %s",
                ('%"source": "demo_seed"%',),
            )
        else:
            _execute(
                cur,
                f"DELETE FROM {_TABLE_NAME} WHERE metadata_json LIKE %s",
                ('%"source": "demo_seed"%',),
            )
        deleted = int(cur.rowcount or 0)
        conn.commit()
    finally:
        cur.close()
        conn.close()

    for object_id, obj in list(WORK_OBJECT_STORE.items()):
        if obj.metadata.get("source") == "demo_seed":
            WORK_OBJECT_STORE.pop(object_id, None)

    return {
        "ok": True,
        "message": "Demo work objects cleared.",
        "count": 0,
        "deleted": deleted,
    }


# =========================================================
# Human-readable answers
# =========================================================

def work_objects_status() -> str:
    health = persistence_health()
    if health.get("ok"):
        persistence_line = (
            f"Persistence: OK — {health.get('backend')}\n"
            f"Canonical objects: {health.get('objects')}"
        )
        status_line = "Status: active ✅"
    else:
        persistence_line = f"Persistence: ERROR — {health.get('error', 'unknown error')}"
        status_line = "Status: persistence error ⚠️"

    return (
        "🧱 NinaOS Persistent Work Objects\n\n"
        f"Version: {WORK_OBJECTS_VERSION}\n"
        f"Registered object types: {len(WORK_OBJECT_TYPES)}\n"
        f"{persistence_line}\n\n"
        "Source of truth:\n"
        f"• {_TABLE_NAME}\n"
        "• one source_key = one canonical channel work item\n"
        "• Telegram / Web / future channels share the same object layer\n\n"
        f"{status_line}"
    )


def build_work_object_types_answer() -> str:
    lines = [
        "🧱 NinaOS Work Object Types",
        "",
        f"Version: {WORK_OBJECTS_VERSION}",
        "",
    ]
    for obj_type in list_work_object_types():
        lines.append(f"• {obj_type.type_id}")
        lines.append(f"  Name: {obj_type.name}")
        lines.append(f"  Category: {obj_type.category}")
        lines.append(f"  Risk: {obj_type.risk_level}")
        lines.append("")
    return "\n".join(lines).strip()


def build_work_objects_answer(workspace_id: str = "demo_small_business") -> str:
    objects = list_work_objects(workspace_id=workspace_id)
    lines = [
        "🧱 NinaOS Canonical Work Objects",
        "",
        f"Workspace: {workspace_id}",
        f"Objects: {len(objects)}",
        "",
    ]
    if not objects:
        lines.append("No work objects yet.")
    else:
        for obj in objects:
            lines.append(f"• {obj.object_id}")
            lines.append(f"  Type: {obj.object_type}")
            lines.append(f"  Title: {obj.title}")
            lines.append(f"  Status: {obj.status}")
            lines.append(f"  Priority: {obj.priority}")
            if obj.client_id:
                lines.append(f"  Client: {obj.client_id}")
            if obj.source_key:
                lines.append(f"  Source key: {obj.source_key}")
            lines.append("")
    lines.append(f"Version: {WORK_OBJECTS_VERSION}")
    return "\n".join(lines).strip()


def build_work_object_counts_answer(workspace_id: str = "demo_small_business") -> str:
    counts = dashboard_counts(workspace_id)
    return (
        "📊 NinaOS Work Object Counts\n\n"
        f"Workspace: {workspace_id}\n\n"
        f"Tasks Today: {counts['tasks_today']}\n"
        f"Follow-ups: {counts['followups']}\n"
        f"Invoices Due: {counts['invoices_due']}\n"
        f"Estimates in Progress: {counts['estimates_in_progress']}\n"
        f"Active Projects: {counts['projects_active']}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def build_demo_seed_answer() -> str:
    result = seed_demo_work_objects()
    return (
        "🧪 NinaOS Demo Work Objects\n\n"
        f"{result.get('message')}\n"
        f"Objects: {result.get('count')}\n"
        f"Created now: {result.get('created', 0)}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def build_demo_clear_answer() -> str:
    result = clear_demo_work_objects()
    return (
        "🧹 NinaOS Demo Work Objects\n\n"
        f"{result.get('message')}\n"
        f"Deleted: {result.get('deleted', 0)}\n\n"
        f"Version: {WORK_OBJECTS_VERSION}"
    )


def route_work_objects_command(text: str) -> Optional[str]:
    lower = _clean(text).lower()

    if lower in ["work objects", "objects", "object types"]:
        return build_work_object_types_answer()
    if lower in ["work object list", "objects list", "my objects"]:
        return build_work_objects_answer()
    if lower in ["object counts", "work object counts", "dashboard counts"]:
        return build_work_object_counts_answer()
    if lower in ["seed demo objects", "demo objects", "create demo objects"]:
        return build_demo_seed_answer()
    if lower in ["clear demo objects", "delete demo objects"]:
        return build_demo_clear_answer()
    if lower in ["work objects status", "objects status"]:
        return work_objects_status()

    return None


def work_objects_schema() -> Dict[str, Any]:
    objects = list_work_objects(limit=5000)
    return {
        "version": WORK_OBJECTS_VERSION,
        "persistence": persistence_health(),
        "object_types": {
            type_id: obj_type.__dict__
            for type_id, obj_type in WORK_OBJECT_TYPES.items()
        },
        "stored_objects": {
            obj.object_id: obj.__dict__
            for obj in objects
        },
    }


if __name__ == "__main__":
    print(work_objects_status())
    print()
    print(build_work_object_types_answer())
    print()
    print(build_demo_seed_answer())
    print()
    print(build_work_object_counts_answer())
