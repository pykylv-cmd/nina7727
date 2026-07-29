"""ONE NINA workspace Ready Worker Catalog V1.

A Worker is a customer-facing composition of existing RolePacks. It does not
own AI state, memory, planning, approval, execution, or background processes.
"""

from __future__ import annotations

import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType

import persistence_backend
from rolepack_system import (
    AUTONOMY_MODES,
    get_rolepack,
    get_workspace_rolepack,
    initialize_rolepack_system,
)


WORKER_CATALOG_VERSION = "1.0"
WORKER_STATUSES = frozenset({"active", "disabled", "archived"})
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VERSION_RE = re.compile(r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*)){0,2}$")


class WorkerCatalogError(RuntimeError):
    pass


class WorkerValidationError(WorkerCatalogError):
    pass


class WorkerNotFoundError(WorkerCatalogError):
    pass


@dataclass(frozen=True)
class Worker:
    worker_id: str
    key: str
    display_name: str
    description: str
    status: str
    version: str
    icon: str
    created_at: str
    updated_at: str
    primary_rolepack: str
    secondary_rolepacks: tuple
    supported_channels: tuple
    supported_capabilities: tuple
    supported_actions: tuple
    default_autonomy_mode: str
    required_permissions: tuple

    @property
    def rolepacks(self):
        return (self.primary_rolepack,) + self.secondary_rolepacks


@dataclass(frozen=True)
class WorkspaceWorker:
    workspace_id: str
    worker_id: str
    worker_version: str
    updated_by: str
    created_at: str
    updated_at: str


def _utc(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _text(value, field, maximum=128):
    value = str(value or "").strip()
    if not value or len(value) > maximum:
        raise WorkerValidationError(f"worker_{field}_invalid")
    return value


def _sql(value):
    return persistence_backend.sql(value)


def _compose(
    worker_id,
    display_name,
    description,
    icon,
    primary_rolepack,
    secondary_rolepacks=(),
    default_autonomy_mode="MANUAL",
):
    initialize_rolepack_system()
    rolepack_ids = (primary_rolepack,) + tuple(secondary_rolepacks)
    if len(set(rolepack_ids)) != len(rolepack_ids):
        raise WorkerValidationError(
            f"worker_rolepack_duplicate:{worker_id}"
        )
    rolepacks = tuple(get_rolepack(rolepack_id) for rolepack_id in rolepack_ids)
    if any(
        not rolepack.enabled or rolepack.status != "active"
        for rolepack in rolepacks
    ):
        raise WorkerValidationError(
            f"worker_rolepack_not_active:{worker_id}"
        )
    if default_autonomy_mode not in AUTONOMY_MODES:
        raise WorkerValidationError(
            f"worker_autonomy_mode_invalid:{worker_id}"
        )

    def union(attribute):
        return tuple(sorted({
            value
            for rolepack in rolepacks
            for value in getattr(rolepack, attribute)
        }))

    timestamp = "2026-07-29T00:00:00+00:00"
    return Worker(
        worker_id=worker_id,
        key=worker_id,
        display_name=display_name,
        description=description,
        status="active",
        version="1.0.0",
        icon=icon,
        created_at=timestamp,
        updated_at=timestamp,
        primary_rolepack=primary_rolepack,
        secondary_rolepacks=tuple(secondary_rolepacks),
        supported_channels=union("supported_channels"),
        supported_capabilities=union("capabilities"),
        supported_actions=union("allowed_actions"),
        default_autonomy_mode=default_autonomy_mode,
        required_permissions=union("required_permissions"),
    )


def _builtins():
    return (
        _compose(
            "office_manager", "Office Manager",
            "Organizes daily operations, priorities, documents and replies.",
            "briefcase", "office_manager",
        ),
        _compose(
            "sales_assistant", "Sales Assistant",
            "Supports ethical sales work, offers and client follow-up.",
            "chart", "sales_assistant",
        ),
        _compose(
            "client_manager", "Client Manager",
            "Maintains client context, relationships and follow-up work.",
            "people", "client_manager",
        ),
        _compose(
            "personal_assistant", "Personal Assistant",
            "Organizes personal tasks, calendar and reminders.",
            "spark", "personal_assistant",
        ),
        _compose(
            "general_nina", "General Nina",
            "One Nina configured across office, sales, client and personal work.",
            "nina", "office_manager",
            ("sales_assistant", "client_manager", "personal_assistant"),
        ),
    )


def _validate(worker):
    if not _ID_RE.fullmatch(worker.worker_id):
        raise WorkerValidationError(
            f"worker_id_invalid:{worker.worker_id}"
        )
    if worker.key != worker.worker_id:
        raise WorkerValidationError("worker_key_must_match_id")
    if worker.status not in WORKER_STATUSES:
        raise WorkerValidationError("worker_status_invalid")
    if not _VERSION_RE.fullmatch(worker.version):
        raise WorkerValidationError("worker_version_invalid")
    if not worker.display_name or not worker.description or not worker.icon:
        raise WorkerValidationError("worker_identity_incomplete")
    return worker


_WORKERS = None
_WORKER_LOCK = threading.RLock()


def _workers():
    global _WORKERS
    with _WORKER_LOCK:
        if _WORKERS is None:
            definitions = _builtins()
            _WORKERS = MappingProxyType({
                worker.worker_id: _validate(worker)
                for worker in definitions
            })
        return _WORKERS


def list_workers(active_only=True):
    workers = _workers()
    return tuple(
        workers[key] for key in sorted(workers)
        if not active_only or workers[key].status == "active"
    )


def get_worker(worker_id):
    worker_id = str(worker_id or "").strip()
    worker = _workers().get(worker_id)
    if worker is None:
        raise WorkerNotFoundError(f"worker_not_found:{worker_id}")
    return worker


def _workspace_record(row):
    return WorkspaceWorker(
        *[str(value or "") for value in row]
    ) if row else None


def _worker_for_rolepack(rolepack_id):
    return {
        "office_manager": "office_manager",
        "sales_assistant": "sales_assistant",
        "client_manager": "client_manager",
        "personal_assistant": "personal_assistant",
    }.get(str(rolepack_id or ""), "office_manager")


def get_workspace_worker(workspace_id, *, create=True, actor="system"):
    workspace_id = _text(workspace_id, "workspace_id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT workspace_id,worker_id,worker_version,updated_by,
                created_at,updated_at
            FROM nina_workspace_workers WHERE workspace_id=%s
        """), (workspace_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if row or not create:
        return _workspace_record(row)
    rolepack = get_workspace_rolepack(workspace_id, actor=actor)
    return set_workspace_worker(
        workspace_id, _worker_for_rolepack(rolepack.rolepack_id),
        updated_by=actor,
    )


def set_workspace_worker(
    workspace_id, worker_id, *, updated_by, now=None,
):
    """Select one Worker and its primary RolePack in one transaction."""
    workspace_id = _text(workspace_id, "workspace_id")
    worker_id = _text(worker_id, "id", 64)
    updated_by = _text(updated_by, "updated_by")
    worker = get_worker(worker_id)
    if worker.status != "active":
        raise WorkerValidationError("worker_not_active")
    primary = get_rolepack(worker.primary_rolepack)
    timestamp = _utc(now)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT workspace_id,worker_id,worker_version,updated_by,
                created_at,updated_at
            FROM nina_workspace_workers WHERE workspace_id=%s
        """), (workspace_id,))
        previous = _workspace_record(cur.fetchone())
        if (
            previous
            and previous.worker_id == worker.worker_id
            and previous.worker_version == worker.version
        ):
            cur.close()
            return previous

        if previous:
            cur.execute(_sql("""
                UPDATE nina_workspace_workers
                SET worker_id=%s,worker_version=%s,updated_by=%s,
                    updated_at=%s WHERE workspace_id=%s
            """), (
                worker.worker_id, worker.version, updated_by, timestamp,
                workspace_id,
            ))
            old_worker = previous.worker_id
        else:
            cur.execute(_sql("""
                INSERT INTO nina_workspace_workers (
                    workspace_id,worker_id,worker_version,updated_by,
                    created_at,updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s)
            """), (
                workspace_id, worker.worker_id, worker.version, updated_by,
                timestamp, timestamp,
            ))
            old_worker = ""

        cur.execute(_sql("""
            SELECT rolepack_id,rolepack_version
            FROM nina_workspace_rolepacks WHERE workspace_id=%s
        """), (workspace_id,))
        rolepack_row = cur.fetchone()
        old_rolepack = str(rolepack_row[0] or "") if rolepack_row else ""
        rolepack_changed = (
            not rolepack_row
            or old_rolepack != primary.rolepack_id
            or str(rolepack_row[1] or "") != primary.version
        )
        if rolepack_row:
            cur.execute(_sql("""
                UPDATE nina_workspace_rolepacks
                SET rolepack_id=%s,rolepack_version=%s,updated_by=%s,
                    updated_at=%s WHERE workspace_id=%s
            """), (
                primary.rolepack_id, primary.version, updated_by,
                timestamp, workspace_id,
            ))
        else:
            cur.execute(_sql("""
                INSERT INTO nina_workspace_rolepacks (
                    workspace_id,rolepack_id,rolepack_version,updated_by,
                    created_at,updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s)
            """), (
                workspace_id, primary.rolepack_id, primary.version,
                updated_by, timestamp, timestamp,
            ))
        if rolepack_changed:
            cur.execute(_sql("""
                INSERT INTO nina_rolepack_events (
                    event_id,workspace_id,event_type,old_rolepack,
                    new_rolepack,actor,created_at
                ) VALUES (%s,%s,'rolepack_changed',%s,%s,%s,%s)
            """), (
                "rolepack_event_" + secrets.token_hex(16), workspace_id,
                old_rolepack, primary.rolepack_id, updated_by, timestamp,
            ))
        cur.execute(_sql("""
            INSERT INTO nina_worker_events (
                event_id,workspace_id,event_type,old_worker,new_worker,
                actor,created_at
            ) VALUES (%s,%s,'worker_changed',%s,%s,%s,%s)
        """), (
            "worker_event_" + secrets.token_hex(16), workspace_id,
            old_worker, worker.worker_id, updated_by, timestamp,
        ))
        cur.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_workspace_worker(workspace_id, create=False)


def list_workspace_worker_events(workspace_id, limit=100):
    workspace_id = _text(workspace_id, "workspace_id")
    limit = max(1, min(int(limit), 500))
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT event_id,workspace_id,event_type,old_worker,new_worker,
                actor,created_at
            FROM nina_worker_events WHERE workspace_id=%s
            ORDER BY created_at DESC,event_id LIMIT %s
        """), (workspace_id, limit))
        rows = cur.fetchall() or []
        cur.close()
        return tuple(
            tuple(str(value or "") for value in row) for row in rows
        )
    finally:
        conn.close()


def active_worker(workspace_id):
    selected = get_workspace_worker(workspace_id)
    return get_worker(selected.worker_id)
