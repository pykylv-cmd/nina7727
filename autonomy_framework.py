"""Autonomy Framework V1: tenant-scoped policy decisions for ONE NINA."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend


MODES = frozenset({"MANUAL", "SUGGEST", "SEMI_AUTO", "AUTO"})
DECISIONS = frozenset({"ALLOW", "DENY", "REQUIRE_APPROVAL", "UNSUPPORTED"})
LOW_RISK_ACTIONS = frozenset({"REMIND", "NO_ACTION"})
KNOWN_ACTIONS = frozenset({
    "REMIND", "NO_ACTION", "FOLLOW_UP", "CHECK_IN", "ASK_FOR_UPDATE",
})


class AutonomyError(RuntimeError):
    pass


class AutonomyValidationError(AutonomyError):
    pass


@dataclass(frozen=True)
class AutonomyProfile:
    workspace_id: str
    mode: str
    updated_by: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AutonomyDecision:
    decision: str
    workspace_id: str
    mode: str
    action: str
    reason: str


def _sql(value):
    return persistence_backend.sql(value)


def _now(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _text(value, name, maximum=128):
    value = str(value or "").strip()
    if not value or len(value) > maximum:
        raise AutonomyValidationError(f"autonomy_{name}_invalid")
    return value


def _profile(row):
    return AutonomyProfile(*[str(value or "") for value in row]) if row else None


def get_profile(workspace_id, *, create=True, actor="system"):
    workspace_id = _text(workspace_id, "workspace_id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT workspace_id,mode,updated_by,created_at,updated_at
            FROM nina_autonomy_profiles WHERE workspace_id=%s
        """), (workspace_id,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if row or not create:
        return _profile(row)
    return set_mode(workspace_id, "MANUAL", updated_by=actor)


def set_mode(workspace_id, mode, *, updated_by, now=None):
    workspace_id = _text(workspace_id, "workspace_id")
    mode = _text(mode, "mode", 32).upper()
    updated_by = _text(updated_by, "updated_by")
    if mode not in MODES:
        raise AutonomyValidationError("autonomy_mode_invalid")
    timestamp = _now(now)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT workspace_id,mode,updated_by,created_at,updated_at
            FROM nina_autonomy_profiles WHERE workspace_id=%s
        """), (workspace_id,))
        row = cur.fetchone()
        previous = _profile(row)
        if previous and previous.mode == mode:
            cur.close()
            return previous
        if previous:
            cur.execute(_sql("""
                UPDATE nina_autonomy_profiles
                SET mode=%s,updated_by=%s,updated_at=%s
                WHERE workspace_id=%s
            """), (mode, updated_by, timestamp, workspace_id))
            old_mode = previous.mode
        else:
            cur.execute(_sql("""
                INSERT INTO nina_autonomy_profiles (
                    workspace_id,mode,updated_by,created_at,updated_at
                ) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (workspace_id) DO NOTHING
            """), (workspace_id, mode, updated_by, timestamp, timestamp))
            if cur.rowcount != 1:
                conn.rollback()
                return set_mode(
                    workspace_id, mode, updated_by=updated_by, now=now,
                )
            old_mode = ""
        cur.execute(_sql("""
            INSERT INTO nina_autonomy_events (
                event_id,workspace_id,event_type,old_mode,new_mode,
                actor,created_at
            ) VALUES (%s,%s,'mode_changed',%s,%s,%s,%s)
        """), (
            "autonomy_event_" + secrets.token_hex(16), workspace_id,
            old_mode, mode, updated_by, timestamp,
        ))
        cur.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_profile(workspace_id, create=False)


def list_events(workspace_id, limit=100):
    workspace_id = _text(workspace_id, "workspace_id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("""
            SELECT event_id,workspace_id,event_type,old_mode,new_mode,
                actor,created_at
            FROM nina_autonomy_events
            WHERE workspace_id=%s
            ORDER BY created_at DESC,event_id
            LIMIT %s
        """), (workspace_id, max(1, min(int(limit), 500))))
        rows = cur.fetchall() or []
        cur.close()
        return tuple(tuple(str(value or "") for value in row) for row in rows)
    finally:
        conn.close()


class AutonomyFramework:
    @staticmethod
    def evaluate(workspace_id, approval, reply, action):
        workspace_id = _text(workspace_id, "workspace_id")
        action = _text(action, "action", 64).upper()
        if action not in KNOWN_ACTIONS:
            return AutonomyDecision(
                "UNSUPPORTED", workspace_id,
                get_profile(workspace_id).mode, action, "unknown_action",
            )
        approval_workspace = str(
            getattr(approval, "workspace_id", "") or ""
        ).strip()
        reply_workspace = str(
            getattr(reply, "workspace_id", "") or ""
        ).strip()
        if (
            (approval_workspace and approval_workspace != workspace_id)
            or (reply_workspace and reply_workspace != workspace_id)
        ):
            return AutonomyDecision(
                "DENY", workspace_id,
                get_profile(workspace_id).mode, action,
                "workspace_mismatch",
            )
        profile = get_profile(workspace_id)
        approved = (
            str(getattr(approval, "status", "") or "").lower() == "approved"
            and str(getattr(approval, "decision", "") or "").lower()
            == "approved"
        )
        if approved:
            return AutonomyDecision(
                "ALLOW", workspace_id, profile.mode, action,
                "human_approval_confirmed",
            )
        if profile.mode in {"MANUAL", "SUGGEST"}:
            decision = "REQUIRE_APPROVAL"
        elif action in LOW_RISK_ACTIONS:
            decision = "ALLOW"
        else:
            decision = "REQUIRE_APPROVAL"
        return AutonomyDecision(
            decision, workspace_id, profile.mode, action,
            "policy_" + decision.lower(),
        )
