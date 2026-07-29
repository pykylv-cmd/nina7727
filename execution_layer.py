"""Execution Layer V1: explicit, approved, allowlisted ONE NINA actions."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import persistence_backend
from approval_layer import get_approval_by_id
from autonomy_framework import AutonomyFramework
from initiative_engine import initiative_queue
from reply_builder import ReplyBuilder
from rolepack_system import action_for_workspace, executable_action_types
from work_objects import create_work_object, get_work_object


ALLOWLIST = executable_action_types()
STATUSES = frozenset({
    "pending", "processing", "succeeded", "failed", "unsupported", "cancelled",
})


class ExecutionError(RuntimeError):
    pass


class ExecutionValidationError(ExecutionError):
    pass


class ExecutionConflictError(ExecutionError):
    pass


@dataclass(frozen=True)
class ExecutionRecord:
    execution_id: str
    workspace_id: str
    approval_id: str
    initiative_id: str
    reply_id: str
    work_object_id: str
    action_type: str
    status: str
    idempotency_key: str
    result_type: str
    result_reference: str
    error_code: str
    error_summary: str
    attempt_count: int
    requested_by: str
    created_at: str
    started_at: str
    completed_at: str
    updated_at: str


_FIELDS = (
    "execution_id,workspace_id,approval_id,initiative_id,reply_id,"
    "work_object_id,action_type,status,idempotency_key,result_type,"
    "result_reference,error_code,error_summary,attempt_count,requested_by,"
    "created_at,started_at,completed_at,updated_at"
)


def _sql(value):
    return persistence_backend.sql(value)


def _now(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _text(value, name, maximum=600):
    value = str(value or "").strip()
    if not value or len(value) > maximum:
        raise ExecutionValidationError(f"execution_{name}_invalid")
    return value


def _record(row):
    if not row:
        return None
    values = [str(value or "") for value in row]
    values[13] = int(row[13] or 0)
    return ExecutionRecord(*values)


def execution_identity(workspace_id, approval_id, action_type):
    raw = "|".join((workspace_id, approval_id, action_type))
    return "execution_" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def _default_idempotency(workspace_id, approval_id, action_type):
    return execution_identity(workspace_id, approval_id, action_type)


def get_execution(workspace_id, approval_id, action_type=None):
    workspace_id = _text(workspace_id, "workspace_id", 128)
    approval_id = _text(approval_id, "approval_id", 128)
    where = "workspace_id=%s AND approval_id=%s"
    params = [workspace_id, approval_id]
    if action_type:
        where += " AND action_type=%s"
        params.append(str(action_type).strip().upper())
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM nina_executions
            WHERE {where}
            ORDER BY created_at DESC LIMIT 1
        """), tuple(params))
        row = cur.fetchone()
        cur.close()
        return _record(row)
    finally:
        conn.close()


def _get_on_conn(conn, workspace_id, approval_id, action_type):
    cur = conn.cursor()
    cur.execute(_sql(f"""
        SELECT {_FIELDS} FROM nina_executions
        WHERE workspace_id=%s AND approval_id=%s AND action_type=%s
        LIMIT 1
    """), (workspace_id, approval_id, action_type))
    row = cur.fetchone()
    cur.close()
    return _record(row)


def list_executions(workspace_id, limit=100):
    workspace_id = _text(workspace_id, "workspace_id", 128)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM nina_executions
            WHERE workspace_id=%s ORDER BY updated_at DESC,execution_id
            LIMIT %s
        """), (workspace_id, max(1, min(int(limit), 500))))
        rows = cur.fetchall() or []
        cur.close()
        return tuple(_record(row) for row in rows)
    finally:
        conn.close()


def _event(conn, execution, event_type, previous_status, new_status, actor, metadata=None, now=None):
    safe = {
        key: str(value or "")[:160]
        for key, value in dict(metadata or {}).items()
        if key in {"action_type", "result_type", "result_reference", "error_code"}
    }
    cur = conn.cursor()
    cur.execute(_sql("""
        INSERT INTO nina_execution_events (
            event_id,execution_id,workspace_id,event_type,previous_status,
            new_status,actor,safe_metadata,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """), (
        "execution_event_" + secrets.token_hex(16), execution.execution_id,
        execution.workspace_id, event_type, previous_status, new_status,
        str(actor or "")[:128], json.dumps(safe, sort_keys=True),
        _now(now).isoformat(),
    ))
    cur.close()


def _canonical_context(workspace_id, approval_id):
    approval = get_approval_by_id(workspace_id, approval_id)
    if not approval:
        raise ExecutionValidationError("approval_not_found")
    if approval.status != "approved" or approval.decision != "approved":
        raise ExecutionValidationError("approval_not_approved")
    source = get_work_object(approval.work_object_id)
    if not source or source.workspace_id != workspace_id:
        raise ExecutionValidationError("execution_stale_work_object")
    initiative = next((
        item for item in initiative_queue(workspace_id, limit=100)
        if item.initiative_id == approval.initiative_id
    ), None)
    if not initiative or initiative.work_object_id != source.object_id:
        raise ExecutionValidationError("execution_stale_initiative")
    try:
        reply = ReplyBuilder.build(initiative)
    except (TypeError, ValueError) as exc:
        raise ExecutionValidationError("execution_stale_reply") from exc
    if (
        reply.reply_id != approval.reply_id
        or reply.initiative_id != approval.initiative_id
        or reply.work_object_id != source.object_id
        or reply.workspace_id != workspace_id
    ):
        raise ExecutionValidationError("execution_stale_reply")
    return approval, initiative, reply, source


def _reminder_time(source, now=None):
    current = _now(now)
    raw = str(source.due_date or "").strip()
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("Europe/Riga"))
            parsed = parsed.astimezone(timezone.utc)
            if parsed > current:
                return parsed.isoformat()
        except (TypeError, ValueError):
            pass
    local = current.astimezone(ZoneInfo("Europe/Riga"))
    target = (local + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0,
    )
    return target.astimezone(timezone.utc).isoformat()


def _create_reminder(execution, source, now=None):
    planned_at = _reminder_time(source, now)
    return create_work_object(
        object_type="reminder",
        title=f"Atgādinājums: {source.title}",
        workspace_id=execution.workspace_id,
        assigned_agent_id=source.assigned_agent_id,
        client_id=source.client_id,
        project_id=source.project_id,
        priority=source.priority,
        due_date=planned_at,
        status="active",
        metadata={
            "source": "execution_layer_v1",
            "source_work_object_id": source.object_id,
            "execution_id": execution.execution_id,
            "planned_at": planned_at,
            "reminder_at": planned_at,
            "delivery_status": "scheduled",
            "attempt_count": 0,
            "unread": False,
            "delivery_history": [],
        },
        origin_channel=source.origin_channel,
        origin_user_id=source.origin_user_id,
        source_key=f"execution-reminder:{execution.execution_id}",
    )


def _claim(approval, action_type, requested_by, idempotency_key, now=None):
    timestamp = _now(now).isoformat()
    execution_id = execution_identity(
        approval.workspace_id, approval.approval_id, action_type,
    )
    key = str(idempotency_key or "").strip() or _default_idempotency(
        approval.workspace_id, approval.approval_id, action_type,
    )
    conn = persistence_backend.connect()
    created = False
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            INSERT INTO nina_executions (
                execution_id,workspace_id,approval_id,initiative_id,reply_id,
                work_object_id,action_type,status,idempotency_key,result_type,
                result_reference,error_code,error_summary,attempt_count,
                requested_by,created_at,started_at,completed_at,updated_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,'processing',%s,'','','','',1,
                %s,%s,%s,'',%s
            )
            ON CONFLICT (workspace_id,approval_id,action_type) DO NOTHING
        """), (
            execution_id, approval.workspace_id, approval.approval_id,
            approval.initiative_id, approval.reply_id, approval.work_object_id,
            action_type, key, requested_by, timestamp, timestamp, timestamp,
        ))
        created = cur.rowcount == 1
        cur.close()
        if created:
            current = _get_on_conn(
                conn, approval.workspace_id, approval.approval_id, action_type,
            )
            created_time = _now(now)
            _event(
                conn, current, "execution_created", "", "pending",
                requested_by, {"action_type": action_type}, created_time,
            )
            _event(
                conn, current, "execution_started", "pending", "processing",
                requested_by, {"action_type": action_type},
                created_time + timedelta(microseconds=1),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_execution(
        approval.workspace_id, approval.approval_id, action_type,
    ), created


def _finish(execution, status, actor, *, result_type="", result_reference="", error_code="", error_summary="", now=None):
    timestamp = _now(now).isoformat()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            UPDATE nina_executions SET status=%s,result_type=%s,
                result_reference=%s,error_code=%s,error_summary=%s,
                completed_at=%s,updated_at=%s
            WHERE execution_id=%s AND workspace_id=%s AND status='processing'
        """), (
            status, str(result_type)[:64], str(result_reference)[:500],
            str(error_code)[:128], str(error_summary)[:500], timestamp,
            timestamp, execution.execution_id, execution.workspace_id,
        ))
        changed = cur.rowcount == 1
        cur.close()
        updated = _get_on_conn(
            conn, execution.workspace_id, execution.approval_id,
            execution.action_type,
        )
        if changed:
            event_type = {
                "succeeded": "execution_succeeded",
                "failed": "execution_failed",
                "unsupported": "execution_unsupported",
            }[status]
            _event(
                conn, updated, event_type, "processing", status, actor,
                {
                    "action_type": updated.action_type,
                    "result_type": result_type,
                    "result_reference": result_reference,
                    "error_code": error_code,
                },
                now,
            )
        conn.commit()
        return updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class ExecutionLayer:
    @staticmethod
    def execute_approved(
        workspace_id, approval_id, requested_by, idempotency_key=None, now=None,
    ):
        workspace_id = _text(workspace_id, "workspace_id", 128)
        approval_id = _text(approval_id, "approval_id", 128)
        requested_by = _text(requested_by, "requested_by", 128)
        approval = get_approval_by_id(workspace_id, approval_id)
        if not approval:
            raise ExecutionValidationError("approval_not_found")
        if approval.status != "approved" or approval.decision != "approved":
            raise ExecutionValidationError("approval_not_approved")
        existing = get_execution(workspace_id, approval_id)
        if existing and existing.status in {
            "processing", "succeeded", "unsupported",
        }:
            return existing
        approval, _initiative, reply, source = _canonical_context(
            workspace_id, approval_id,
        )
        action_type = str(reply.suggested_action or "").strip().upper()
        if not action_type:
            raise ExecutionValidationError("execution_action_missing")
        policy = AutonomyFramework.evaluate(
            workspace_id, approval, reply, action_type,
        )
        if policy.decision != "ALLOW":
            raise ExecutionValidationError(
                "execution_autonomy_" + policy.decision.lower()
            )
        action_definition, rolepack = action_for_workspace(
            workspace_id, action_type,
        )
        if not action_definition or not rolepack:
            raise ExecutionValidationError("execution_rolepack_action_denied")
        execution, created = _claim(
            approval, action_type, requested_by, idempotency_key, now,
        )
        if not created:
            return execution
        if (
            action_definition.status != "active"
            or not action_definition.executor
        ):
            return _finish(
                execution, "unsupported", requested_by,
                error_code="unsupported_action",
                error_summary="Action is not supported in Execution Layer V1.",
                now=now,
            )
        if action_type == "NO_ACTION":
            return _finish(
                execution, "succeeded", requested_by,
                result_type="no_action", result_reference=execution.execution_id,
                now=now,
            )
        try:
            reminder = _create_reminder(execution, source, now)
        except Exception as exc:
            return _finish(
                execution, "failed", requested_by,
                error_code="reminder_creation_failed",
                error_summary=f"Reminder creation failed: {type(exc).__name__}",
                now=now,
            )
        return _finish(
            execution, "succeeded", requested_by,
            result_type="reminder", result_reference=reminder.object_id,
            now=now,
        )


def execute_approved(*args, **kwargs):
    return ExecutionLayer.execute_approved(*args, **kwargs)
