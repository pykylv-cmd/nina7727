"""Universal Work Objects V1 over the existing ONE NINA canonical work table."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend
from agent_assignment import (
    AgentAssignmentNotFoundError,
    get_assignment,
)


TABLE_NAME = "nina_work_objects"
EVENT_TABLE = "nina_work_object_events"
OBJECT_TYPES = frozenset({
    "task", "follow_up", "approval", "reminder", "request", "issue",
    "opportunity", "deliverable",
})
STATUSES = frozenset({
    "draft", "open", "in_progress", "blocked", "waiting", "completed",
    "cancelled", "archived",
})
PRIORITIES = frozenset({"low", "normal", "high", "urgent"})
OWNER_TYPES = frozenset({"tenant", "human"})
SOURCE_TYPES = frozenset({
    "nina", "user", "web", "telegram", "whatsapp", "system", "import",
})
TRANSITIONS = frozenset({
    ("draft", "open"), ("draft", "cancelled"),
    ("open", "in_progress"), ("open", "waiting"), ("open", "blocked"),
    ("open", "completed"), ("open", "cancelled"),
    ("in_progress", "waiting"), ("in_progress", "blocked"),
    ("in_progress", "completed"), ("in_progress", "cancelled"),
    ("waiting", "open"), ("waiting", "in_progress"), ("waiting", "cancelled"),
    ("blocked", "open"), ("blocked", "in_progress"), ("blocked", "cancelled"),
    ("completed", "archived"), ("cancelled", "archived"),
})
MAX_TITLE_CHARS = 300
MAX_DESCRIPTION_BYTES = 16 * 1024
MAX_METADATA_BYTES = 8 * 1024
MAX_METADATA_DEPTH = 4
MAX_LIST_LIMIT = 100
DEFAULT_LIST_LIMIT = 50
MAX_OFFSET = 100_000
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_KEYS = {
    "tenant_id", "workspace_id", "work_object_id", "object_id", "status",
    "owner", "owner_id", "owner_type", "created_by", "assigned_agent_id",
    "assigned_agent_assignment_id", "system_prompt", "constitution",
    "api_key", "access_token", "refresh_token", "token", "password", "secret",
    "credentials", "private_key",
}


class UniversalWorkError(RuntimeError):
    pass


class UniversalWorkValidationError(UniversalWorkError):
    pass


class UniversalWorkNotFoundError(UniversalWorkError):
    pass


class UniversalWorkTransitionError(UniversalWorkError):
    pass


class UniversalWorkConflictError(UniversalWorkError):
    pass


class UniversalWorkPersistenceError(UniversalWorkError):
    pass


@dataclass(frozen=True)
class UniversalWorkObject:
    work_object_id: str
    tenant_id: str
    object_type: str
    title: str
    description: str
    status: str
    priority: str
    owner_type: str
    owner_id: str
    assigned_agent_assignment_id: str
    client_id: str
    project_id: str
    parent_work_object_id: str
    source_type: str
    source_reference: str
    due_at: str
    started_at: str
    completed_at: str
    cancelled_at: str
    archived_at: str
    created_by: str
    created_at: str
    updated_at: str
    metadata: dict

    def as_dict(self):
        return {
            "id": self.work_object_id,
            "object_type": self.object_type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "assigned_agent_assignment_id": self.assigned_agent_assignment_id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "parent_work_object_id": self.parent_work_object_id,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "due_at": self.due_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cancelled_at": self.cancelled_at,
            "archived_at": self.archived_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


def _sql(statement):
    return persistence_backend.sql(statement)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field, *, required=False, maximum=500):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise UniversalWorkValidationError(f"work_{field}_invalid")
    value = value.strip()
    if required and not value:
        raise UniversalWorkValidationError(f"work_{field}_required")
    if len(value) > maximum:
        raise UniversalWorkValidationError(f"work_{field}_too_long")
    return value


def _identifier(value, field, *, required=True):
    value = _text(value, field, required=required, maximum=128)
    if value and not _ID_RE.fullmatch(value):
        raise UniversalWorkValidationError(f"work_{field}_invalid")
    return value


def _enum(value, field, allowed):
    value = _text(value, field, required=True, maximum=64)
    if value not in allowed:
        raise UniversalWorkValidationError(f"work_{field}_invalid")
    return value


def _timestamp(value, field):
    value = _text(value, field, maximum=64)
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UniversalWorkValidationError(f"work_{field}_invalid") from exc
    if parsed.tzinfo is None:
        raise UniversalWorkValidationError(f"work_{field}_timezone_required")
    return parsed.astimezone(timezone.utc).isoformat()


def _validate_tree(value, depth=0, path="metadata"):
    if depth > MAX_METADATA_DEPTH:
        raise UniversalWorkValidationError("work_metadata_too_deep")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise UniversalWorkValidationError("work_metadata_key_invalid")
            normalized = key.casefold().replace("-", "_").replace(" ", "_")
            if normalized in _SENSITIVE_KEYS:
                raise UniversalWorkValidationError(
                    f"work_metadata_field_forbidden:{path}.{key}"
                )
            _validate_tree(child, depth + 1, f"{path}.{key}")
    elif isinstance(value, list):
        if len(value) > 100:
            raise UniversalWorkValidationError("work_metadata_list_too_large")
        for index, child in enumerate(value):
            _validate_tree(child, depth + 1, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise UniversalWorkValidationError("work_metadata_not_json_safe")
    elif isinstance(value, str) and len(value) > 2000:
        raise UniversalWorkValidationError("work_metadata_value_too_long")


def _metadata(value):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise UniversalWorkValidationError("work_metadata_must_be_object")
    _validate_tree(value)
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as exc:
        raise UniversalWorkValidationError(
            "work_metadata_not_json_safe"
        ) from exc
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise UniversalWorkValidationError("work_metadata_too_large")
    return json.loads(encoded), encoded


def _description(value):
    value = _text(value, "description", maximum=MAX_DESCRIPTION_BYTES)
    if len(value.encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise UniversalWorkValidationError("work_description_too_large")
    return value


def _validate_assignment(tenant_id, assignment_id):
    assignment_id = _identifier(
        assignment_id, "assigned_agent_assignment_id", required=False
    )
    if not assignment_id:
        return ""
    try:
        assignment = get_assignment(tenant_id, assignment_id)
    except AgentAssignmentNotFoundError as exc:
        raise UniversalWorkNotFoundError("work_assignment_not_found") from exc
    if assignment.status != "active":
        raise UniversalWorkConflictError("work_assignment_not_active")
    return assignment.assignment_id


_FIELDS = """
object_id,workspace_id,object_type,title,description,status,priority,owner_type,
owner_id,assigned_agent_assignment_id,client_id,project_id,
parent_work_object_id,source_type,source_reference,due_at,started_at,
completed_at,cancelled_at,archived_at,created_by,created_at,updated_at,
metadata_json
"""


def _from_row(row):
    return UniversalWorkObject(
        work_object_id=str(row[0]), tenant_id=str(row[1]),
        object_type=str(row[2]), title=str(row[3]),
        description=str(row[4] or ""), status=str(row[5]),
        priority=str(row[6] or "normal"), owner_type=str(row[7] or "tenant"),
        owner_id=str(row[8] or ""),
        assigned_agent_assignment_id=str(row[9] or ""),
        client_id=str(row[10] or ""), project_id=str(row[11] or ""),
        parent_work_object_id=str(row[12] or ""),
        source_type=str(row[13] or "system"),
        source_reference=str(row[14] or ""), due_at=str(row[15] or ""),
        started_at=str(row[16] or ""), completed_at=str(row[17] or ""),
        cancelled_at=str(row[18] or ""), archived_at=str(row[19] or ""),
        created_by=str(row[20] or "legacy"), created_at=str(row[21]),
        updated_at=str(row[22]), metadata=json.loads(row[23] or "{}"),
    )


def _record_event(
    conn, tenant_id, object_id, event_type, actor,
    from_status="", to_status="", details=None,
):
    _, details_json = _metadata(details or {})
    cur = conn.cursor()
    cur.execute(_sql(f"""
        INSERT INTO {EVENT_TABLE} (
            event_id,workspace_id,object_id,event_type,from_status,to_status,
            actor,details_json,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """), (
        "wev_" + secrets.token_hex(16), tenant_id, object_id, event_type,
        from_status, to_status, actor, details_json, _now(),
    ))
    cur.close()


def get_work_object(tenant_id, work_object_id):
    tenant = _identifier(tenant_id, "tenant_id")
    object_id = _identifier(work_object_id, "id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM {TABLE_NAME}
            WHERE workspace_id=%s AND object_id=%s LIMIT 1
        """), (tenant, object_id))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise UniversalWorkNotFoundError("work_object_not_found")
    return _from_row(row)


def create_work_object(
    tenant_id, *, object_type, title, description="", priority="normal",
    owner_type="tenant", owner_id="", assigned_agent_assignment_id="",
    client_id="", project_id="", parent_work_object_id="", source_type="user",
    source_reference="", due_at="", metadata=None,
    created_by="workspace_client",
):
    tenant = _identifier(tenant_id, "tenant_id")
    object_type = _enum(object_type, "object_type", OBJECT_TYPES)
    title = _text(title, "title", required=True, maximum=MAX_TITLE_CHARS)
    description = _description(description)
    priority = _enum(priority, "priority", PRIORITIES)
    owner_type = _enum(owner_type, "owner_type", OWNER_TYPES)
    owner_id = _identifier(owner_id, "owner_id", required=False)
    assignment_id = _validate_assignment(tenant, assigned_agent_assignment_id)
    client_id = _identifier(client_id, "client_id", required=False)
    project_id = _identifier(project_id, "project_id", required=False)
    source_type = _enum(source_type, "source_type", SOURCE_TYPES)
    source_reference = _text(
        source_reference, "source_reference", maximum=500
    )
    due_at = _timestamp(due_at, "due_at")
    _, metadata_json = _metadata(metadata)
    actor = _identifier(created_by, "created_by")
    object_id = "wo_" + secrets.token_hex(16)
    parent_id = ""
    if parent_work_object_id:
        parent_id = get_work_object(
            tenant, parent_work_object_id
        ).work_object_id
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            INSERT INTO {TABLE_NAME} (
                object_id,workspace_id,object_type,title,status,
                assigned_agent_id,client_id,project_id,priority,due_date,
                linked_files_json,metadata_json,origin_channel,origin_user_id,
                source_key,created_at,updated_at,description,owner_type,
                owner_id,assigned_agent_assignment_id,parent_work_object_id,
                source_type,source_reference,due_at,started_at,completed_at,
                cancelled_at,archived_at,created_by
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
        """), (
            object_id, tenant, object_type, title, "draft", "", client_id,
            project_id, priority, due_at, "[]", metadata_json, source_type, "",
            None, now, now, description, owner_type, owner_id, assignment_id,
            parent_id, source_type, source_reference, due_at, "", "", "", "",
            actor,
        ))
        cur.close()
        _record_event(
            conn, tenant, object_id, "created", actor,
            to_status="draft", details={"source_type": source_type},
        )
        conn.commit()
    except UniversalWorkError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise UniversalWorkPersistenceError(
            f"work_create_failed:{type(exc).__name__}"
        ) from exc
    finally:
        conn.close()
    return get_work_object(tenant, object_id)


def _pagination(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIST_LIMIT:
        raise UniversalWorkValidationError("work_limit_invalid")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= MAX_OFFSET:
        raise UniversalWorkValidationError("work_offset_invalid")
    return limit, offset


def list_work_objects(
    tenant_id, *, object_type=None, status=None, priority=None,
    assigned_agent_assignment_id=None, client_id=None, project_id=None,
    query=None, due_before=None, due_after=None,
    limit=DEFAULT_LIST_LIMIT, offset=0,
):
    tenant = _identifier(tenant_id, "tenant_id")
    limit, offset = _pagination(limit, offset)
    where = ["workspace_id=%s"]
    params = [tenant]
    filters = (
        ("object_type", object_type, OBJECT_TYPES),
        ("status", status, STATUSES),
        ("priority", priority, PRIORITIES),
    )
    for column, value, allowed in filters:
        if value is not None:
            where.append(f"{column}=%s")
            params.append(_enum(value, column, allowed))
    for column, value in (
        ("assigned_agent_assignment_id", assigned_agent_assignment_id),
        ("client_id", client_id), ("project_id", project_id),
    ):
        if value is not None:
            where.append(f"{column}=%s")
            params.append(_identifier(value, column))
    if due_before is not None:
        where.append("due_at<>'' AND due_at<=%s")
        params.append(_timestamp(due_before, "due_before"))
    if due_after is not None:
        where.append("due_at<>'' AND due_at>=%s")
        params.append(_timestamp(due_after, "due_after"))
    if query is not None:
        query = _text(query, "query", required=True, maximum=200)
        escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        where.append(
            "(LOWER(title) LIKE %s ESCAPE '\\' OR "
            "LOWER(description) LIKE %s ESCAPE '\\')"
        )
        params.extend([pattern, pattern])
    params.extend([limit, offset])
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM {TABLE_NAME}
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE priority WHEN 'urgent' THEN 4 WHEN 'high' THEN 3
                WHEN 'normal' THEN 2 ELSE 1 END DESC,
                CASE WHEN due_at='' THEN 1 ELSE 0 END,due_at,updated_at DESC
            LIMIT %s OFFSET %s
        """), tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_from_row(row) for row in rows)


def _assert_editable(item):
    if item.status == "archived":
        raise UniversalWorkConflictError("work_archived_immutable")


def update_work_object(
    tenant_id, work_object_id, *, title=None, description=None,
    owner_type=None, owner_id=None, client_id=None, project_id=None,
    due_at=None, metadata=None,
):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    title = current.title if title is None else _text(
        title, "title", required=True, maximum=MAX_TITLE_CHARS
    )
    description = current.description if description is None else _description(
        description
    )
    owner_type = current.owner_type if owner_type is None else _enum(
        owner_type, "owner_type", OWNER_TYPES
    )
    owner_id = current.owner_id if owner_id is None else _identifier(
        owner_id, "owner_id", required=False
    )
    client_id = current.client_id if client_id is None else _identifier(
        client_id, "client_id", required=False
    )
    project_id = current.project_id if project_id is None else _identifier(
        project_id, "project_id", required=False
    )
    due_at = current.due_at if due_at is None else _timestamp(due_at, "due_at")
    selected_metadata = current.metadata if metadata is None else metadata
    _, metadata_json = _metadata(selected_metadata)
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET title=%s,description=%s,owner_type=%s,
                owner_id=%s,client_id=%s,project_id=%s,due_at=%s,due_date=%s,
                metadata_json=%s,updated_at=%s
            WHERE workspace_id=%s AND object_id=%s AND status<>'archived'
        """), (
            title, description, owner_type, owner_id, client_id, project_id,
            due_at, due_at, metadata_json, now, current.tenant_id,
            current.work_object_id,
        ))
        if cur.rowcount != 1:
            raise UniversalWorkConflictError("work_update_conflict")
        cur.close()
        _record_event(
            conn, current.tenant_id, current.work_object_id, "updated",
            "workspace_client",
        )
        conn.commit()
    except UniversalWorkError:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_work_object(current.tenant_id, current.work_object_id)


def transition_work_object(tenant_id, work_object_id, target_status, actor="workspace_client"):
    current = get_work_object(tenant_id, work_object_id)
    target = _enum(target_status, "status", STATUSES)
    if (current.status, target) not in TRANSITIONS:
        raise UniversalWorkTransitionError(
            f"work_transition_invalid:{current.status}:{target}"
        )
    actor = _identifier(actor, "actor")
    now = _now()
    started = now if target == "in_progress" and not current.started_at else current.started_at
    completed = now if target == "completed" else current.completed_at
    cancelled = now if target == "cancelled" else current.cancelled_at
    archived = now if target == "archived" else current.archived_at
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET status=%s,started_at=%s,completed_at=%s,
                cancelled_at=%s,archived_at=%s,updated_at=%s
            WHERE workspace_id=%s AND object_id=%s AND status=%s
        """), (
            target, started, completed, cancelled, archived, now,
            current.tenant_id, current.work_object_id, current.status,
        ))
        if cur.rowcount != 1:
            raise UniversalWorkConflictError("work_transition_conflict")
        cur.close()
        _record_event(
            conn, current.tenant_id, current.work_object_id, "transition",
            actor, current.status, target,
        )
        conn.commit()
    except UniversalWorkError:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_work_object(current.tenant_id, current.work_object_id)


def set_priority(tenant_id, work_object_id, priority):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    priority = _enum(priority, "priority", PRIORITIES)
    return _set_scalar(
        current, "priority", priority, "priority_changed",
        {"priority": priority},
    )


def assign_work_object(tenant_id, work_object_id, assignment_id):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    assignment_id = _validate_assignment(current.tenant_id, assignment_id)
    return _set_scalar(
        current, "assigned_agent_assignment_id", assignment_id, "assigned",
        {"assignment_id": assignment_id},
    )


def unassign_work_object(tenant_id, work_object_id):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    return _set_scalar(
        current, "assigned_agent_assignment_id", "", "unassigned", {}
    )


def _set_scalar(current, column, value, event_type, details):
    allowed = {"priority", "assigned_agent_assignment_id", "parent_work_object_id"}
    if column not in allowed:
        raise UniversalWorkValidationError("work_internal_column_invalid")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET {column}=%s,updated_at=%s
            WHERE workspace_id=%s AND object_id=%s AND status<>'archived'
        """), (value, _now(), current.tenant_id, current.work_object_id))
        if cur.rowcount != 1:
            raise UniversalWorkConflictError("work_update_conflict")
        cur.close()
        _record_event(
            conn, current.tenant_id, current.work_object_id, event_type,
            "workspace_client", details=details,
        )
        conn.commit()
    except UniversalWorkError:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_work_object(current.tenant_id, current.work_object_id)


def attach_parent(tenant_id, work_object_id, parent_work_object_id):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    parent = get_work_object(tenant_id, parent_work_object_id)
    if current.work_object_id == parent.work_object_id:
        raise UniversalWorkValidationError("work_parent_self_forbidden")
    ancestor = parent
    seen = {current.work_object_id}
    for _ in range(100):
        if ancestor.work_object_id in seen:
            raise UniversalWorkValidationError("work_parent_cycle_forbidden")
        seen.add(ancestor.work_object_id)
        if not ancestor.parent_work_object_id:
            break
        ancestor = get_work_object(tenant_id, ancestor.parent_work_object_id)
    else:
        raise UniversalWorkValidationError("work_parent_depth_exceeded")
    return _set_scalar(
        current, "parent_work_object_id", parent.work_object_id,
        "parent_attached", {"parent_id": parent.work_object_id},
    )


def detach_parent(tenant_id, work_object_id):
    current = get_work_object(tenant_id, work_object_id)
    _assert_editable(current)
    return _set_scalar(
        current, "parent_work_object_id", "", "parent_detached", {}
    )


def list_children(tenant_id, work_object_id):
    parent = get_work_object(tenant_id, work_object_id)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM {TABLE_NAME}
            WHERE workspace_id=%s AND parent_work_object_id=%s
            ORDER BY created_at,object_id
        """), (parent.tenant_id, parent.work_object_id))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_from_row(row) for row in rows)


def list_work_events(tenant_id, work_object_id):
    item = get_work_object(tenant_id, work_object_id)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT event_id,event_type,from_status,to_status,actor,
                   details_json,created_at
            FROM {EVENT_TABLE}
            WHERE workspace_id=%s AND object_id=%s ORDER BY created_at,event_id
        """), (item.tenant_id, item.work_object_id))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple({
        "event_id": str(row[0]), "event_type": str(row[1]),
        "from_status": str(row[2]), "to_status": str(row[3]),
        "actor": str(row[4]), "details": json.loads(row[5] or "{}"),
        "created_at": str(row[6]),
    } for row in rows)


def planner_projection(tenant_id, limit=20):
    return list_work_objects(
        tenant_id,
        limit=limit,
        offset=0,
    )


def complete_work_object(tenant_id, work_object_id):
    return transition_work_object(tenant_id, work_object_id, "completed")


def cancel_work_object(tenant_id, work_object_id):
    return transition_work_object(tenant_id, work_object_id, "cancelled")


def archive_work_object(tenant_id, work_object_id):
    return transition_work_object(tenant_id, work_object_id, "archived")


def initialize_universal_work_objects():
    persistence_backend.assert_backend_ready()
    return True


def persistence_health():
    return initialize_universal_work_objects()
