"""Approval Layer V1: durable human decisions, never execution."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import persistence_backend


DECISIONS = frozenset({"approved", "dismissed", "snoozed"})
STATUSES = frozenset({"pending", "approved", "dismissed", "snoozed"})


class ApprovalError(RuntimeError):
    pass


class ApprovalValidationError(ApprovalError):
    pass


class ApprovalConflictError(ApprovalError):
    pass


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    workspace_id: str
    initiative_id: str
    reply_id: str
    work_object_id: str
    decision: str
    status: str
    snoozed_until: str
    created_at: str
    updated_at: str
    decided_at: str
    decided_by: str
    decision_reason: str


_FIELDS = (
    "approval_id,workspace_id,initiative_id,reply_id,work_object_id,"
    "decision,status,snoozed_until,created_at,updated_at,decided_at,"
    "decided_by,decision_reason"
)


def _sql(value):
    return persistence_backend.sql(value)


def _now(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _text(value, name, maximum=500):
    value = str(value or "").strip()
    if not value or len(value) > maximum:
        raise ApprovalValidationError(f"approval_{name}_invalid")
    return value


def _from_row(row):
    return ApprovalRecord(*[str(value or "") for value in row])


def approval_identity(workspace_id, initiative_id, reply_id):
    key = "|".join((
        _text(workspace_id, "workspace_id", 128),
        _text(initiative_id, "initiative_id", 500),
        _text(reply_id, "reply_id", 600),
    ))
    return "approval_" + hashlib.sha256(key.encode()).hexdigest()[:32]


def _event(conn, record, action, actor="", reason="", now=None):
    cur = conn.cursor()
    cur.execute(_sql("""
        INSERT INTO nina_approval_events (
            event_id,approval_id,workspace_id,action,actor,reason,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
    """), (
        "approval_event_" + secrets.token_hex(16), record.approval_id,
        record.workspace_id, action, str(actor or "")[:128],
        str(reason or "")[:500], _now(now).isoformat(),
    ))
    cur.close()


def get_approval(workspace_id, initiative_id, reply_id):
    workspace_id = _text(workspace_id, "workspace_id", 128)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM nina_approvals
            WHERE workspace_id=%s AND initiative_id=%s AND reply_id=%s
            LIMIT 1
        """), (workspace_id, initiative_id, reply_id))
        row = cur.fetchone()
        cur.close()
        return _from_row(row) if row else None
    finally:
        conn.close()


def get_approval_by_id(workspace_id, approval_id):
    workspace_id = _text(workspace_id, "workspace_id", 128)
    approval_id = _text(approval_id, "approval_id", 128)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM nina_approvals
            WHERE workspace_id=%s AND approval_id=%s
            LIMIT 1
        """), (workspace_id, approval_id))
        row = cur.fetchone()
        cur.close()
        return _from_row(row) if row else None
    finally:
        conn.close()


def ensure_approval(workspace_id, initiative_id, reply_id, work_object_id, now=None):
    approval_id = approval_identity(workspace_id, initiative_id, reply_id)
    current = get_approval(workspace_id, initiative_id, reply_id)
    if current:
        if current.work_object_id != work_object_id:
            raise ApprovalConflictError("approval_identity_work_object_conflict")
        return current
    timestamp = _now(now).isoformat()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            INSERT INTO nina_approvals (
                approval_id,workspace_id,initiative_id,reply_id,work_object_id,
                decision,status,snoozed_until,created_at,updated_at,decided_at,
                decided_by,decision_reason
            ) VALUES (%s,%s,%s,%s,%s,'','pending','',%s,%s,'','','')
            ON CONFLICT (workspace_id,initiative_id,reply_id) DO NOTHING
        """), (
            approval_id, workspace_id, initiative_id, reply_id, work_object_id,
            timestamp, timestamp,
        ))
        created = cur.rowcount == 1
        cur.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    record = get_approval(workspace_id, initiative_id, reply_id)
    if created:
        conn = persistence_backend.connect()
        try:
            _event(conn, record, "created", now=now)
            conn.commit()
        finally:
            conn.close()
    return record


def decide(
    workspace_id, initiative_id, reply_id, decision, *,
    decided_by, decision_reason="", snoozed_until="", now=None,
):
    decision = str(decision or "").strip().lower()
    if decision not in DECISIONS:
        raise ApprovalValidationError("approval_decision_invalid")
    record = get_approval(workspace_id, initiative_id, reply_id)
    if not record:
        raise ApprovalValidationError("approval_not_found")
    current_time = _now(now)
    snooze_value = ""
    if decision == "snoozed":
        try:
            parsed = datetime.fromisoformat(str(snoozed_until).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ApprovalValidationError("approval_snooze_invalid") from exc
        parsed = _now(parsed)
        if parsed <= current_time:
            raise ApprovalValidationError("approval_snooze_must_be_future")
        snooze_value = parsed.isoformat()
    if record.status in {"approved", "dismissed"}:
        if record.status == decision:
            return record
        raise ApprovalConflictError("approval_terminal_conflict")
    if (
        record.status == decision
        and record.snoozed_until == snooze_value
        and record.decided_by == str(decided_by or "")
    ):
        return record
    timestamp = current_time.isoformat()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            UPDATE nina_approvals SET decision=%s,status=%s,snoozed_until=%s,
                updated_at=%s,decided_at=%s,decided_by=%s,decision_reason=%s
            WHERE approval_id=%s AND workspace_id=%s
        """), (
            decision, decision, snooze_value, timestamp, timestamp,
            _text(decided_by, "decided_by", 128),
            str(decision_reason or "")[:500], record.approval_id,
            record.workspace_id,
        ))
        cur.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    updated = get_approval(workspace_id, initiative_id, reply_id)
    conn = persistence_backend.connect()
    try:
        _event(
            conn, updated, decision, actor=updated.decided_by,
            reason=updated.decision_reason, now=current_time,
        )
        conn.commit()
    finally:
        conn.close()
    return updated


def wake_expired(workspace_id, now=None):
    timestamp = _now(now).isoformat()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            UPDATE nina_approvals SET decision='',status='pending',
                snoozed_until='',updated_at=%s
            WHERE workspace_id=%s AND status='snoozed'
                AND snoozed_until<>'' AND snoozed_until<=%s
        """), (timestamp, workspace_id, timestamp))
        count = cur.rowcount
        cur.close()
        conn.commit()
        return count
    finally:
        conn.close()


def list_approvals(workspace_id, statuses=None, limit=100):
    workspace_id = _text(workspace_id, "workspace_id", 128)
    where = ["workspace_id=%s"]
    params = [workspace_id]
    if statuses:
        values = [value for value in statuses if value in STATUSES]
        if not values:
            return ()
        where.append("status IN (" + ",".join(["%s"] * len(values)) + ")")
        params.extend(values)
    params.append(max(1, min(int(limit), 500)))
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_FIELDS} FROM nina_approvals
            WHERE {' AND '.join(where)}
            ORDER BY updated_at DESC,approval_id
            LIMIT %s
        """), tuple(params))
        rows = cur.fetchall() or []
        cur.close()
        return tuple(_from_row(row) for row in rows)
    finally:
        conn.close()


def snooze_one_hour(now=None):
    return (_now(now) + timedelta(hours=1)).isoformat()


def snooze_tomorrow(now=None):
    current = _now(now)
    return (current + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0,
    ).isoformat()
