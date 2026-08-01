"""Optional Web Push delivery capability for the existing ONE NINA Web channel."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone

import persistence_backend
from channel_connections import decrypt_channel_credential, encrypt_channel_credential


SUBSCRIPTION_TABLE = "nina_web_push_subscriptions"
DELIVERY_TABLE = "nina_web_push_deliveries"
EVENT_TABLE = "nina_web_push_events"
STATUSES = frozenset({"ACTIVE", "DISABLED", "EXPIRED", "INVALID"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")


class WebPushError(RuntimeError):
    pass


class WebPushValidationError(WebPushError):
    pass


class WebPushConflictError(WebPushError):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sql(value):
    return persistence_backend.sql(value)


def _identifier(value, name):
    clean = str(value or "").strip()
    if not _ID.fullmatch(clean):
        raise WebPushValidationError(f"{name}_invalid")
    return clean


def _event(conn, workspace_id, subscription_id, event_type, safe_metadata=None):
    cur = conn.cursor()
    cur.execute(_sql(f"""
        INSERT INTO {EVENT_TABLE}
        (event_id,workspace_id,subscription_id,event_type,safe_metadata_json,created_at)
        VALUES (%s,%s,%s,%s,%s,%s)
    """), (
        "wpe_" + secrets.token_hex(16), workspace_id, subscription_id,
        event_type, json.dumps(safe_metadata or {}, sort_keys=True), _now(),
    ))
    cur.close()


def _validate_subscription(payload):
    if not isinstance(payload, dict):
        raise WebPushValidationError("subscription_invalid")
    endpoint = str(payload.get("endpoint") or "").strip()
    keys = payload.get("keys") if isinstance(payload.get("keys"), dict) else {}
    p256dh = str(keys.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or "").strip()
    if not endpoint.startswith("https://") or len(endpoint) > 2048:
        raise WebPushValidationError("subscription_endpoint_invalid")
    if not (20 <= len(p256dh) <= 512 and 8 <= len(auth) <= 256):
        raise WebPushValidationError("subscription_keys_invalid")
    canonical = {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}
    return canonical, hashlib.sha256(endpoint.encode()).hexdigest()


def register_subscription(workspace_id, contact_id, payload, user_agent_safe=""):
    workspace = _identifier(workspace_id, "workspace_id")
    contact = _identifier(contact_id, "contact_id")
    canonical, endpoint_hash = _validate_subscription(payload)
    encrypted = encrypt_channel_credential(json.dumps(canonical, separators=(",", ":")))
    user_agent = str(user_agent_safe or "").replace("\r", " ").replace("\n", " ")[:240]
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT subscription_id,workspace_id,contact_id FROM {SUBSCRIPTION_TABLE}
            WHERE endpoint_hash=%s LIMIT 1
        """), (endpoint_hash,))
        existing = cur.fetchone()
        if existing and (str(existing[1]) != workspace or str(existing[2]) != contact):
            raise WebPushConflictError("subscription_owner_conflict")
        if existing:
            subscription_id = str(existing[0])
            cur.execute(_sql(f"""
                UPDATE {SUBSCRIPTION_TABLE} SET encrypted_subscription_json=%s,
                    user_agent_safe=%s,status='ACTIVE',updated_at=%s,failure_code=''
                WHERE subscription_id=%s AND workspace_id=%s AND contact_id=%s
            """), (encrypted, user_agent, now, subscription_id, workspace, contact))
            event_type = "subscription_updated"
        else:
            subscription_id = "wps_" + secrets.token_hex(16)
            cur.execute(_sql(f"""
                INSERT INTO {SUBSCRIPTION_TABLE}
                (subscription_id,workspace_id,contact_id,endpoint_hash,
                 encrypted_subscription_json,user_agent_safe,status,created_at,updated_at,
                 last_success_at,last_failure_at,failure_code)
                VALUES (%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s,'','','')
            """), (
                subscription_id, workspace, contact, endpoint_hash, encrypted,
                user_agent, now, now,
            ))
            event_type = "subscription_created"
        _event(conn, workspace, subscription_id, event_type)
        conn.commit()
        cur.close()
        return {"subscription_id": subscription_id, "status": "ACTIVE"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def unsubscribe(workspace_id, contact_id, endpoint):
    workspace = _identifier(workspace_id, "workspace_id")
    contact = _identifier(contact_id, "contact_id")
    clean_endpoint = str(endpoint or "").strip()
    if not clean_endpoint.startswith("https://"):
        raise WebPushValidationError("subscription_endpoint_invalid")
    endpoint_hash = hashlib.sha256(clean_endpoint.encode()).hexdigest()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {SUBSCRIPTION_TABLE} SET status='DISABLED',updated_at=%s
            WHERE workspace_id=%s AND contact_id=%s AND endpoint_hash=%s
        """), (_now(), workspace, contact, endpoint_hash))
        changed = cur.rowcount
        if changed:
            cur.execute(_sql(f"SELECT subscription_id FROM {SUBSCRIPTION_TABLE} WHERE endpoint_hash=%s"), (endpoint_hash,))
            row = cur.fetchone()
            _event(conn, workspace, str(row[0]), "subscription_disabled")
        conn.commit()
        cur.close()
        return bool(changed)
    finally:
        conn.close()


def list_active_subscriptions(workspace_id, contact_id):
    workspace = _identifier(workspace_id, "workspace_id")
    contact = _identifier(contact_id, "contact_id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT subscription_id,encrypted_subscription_json FROM {SUBSCRIPTION_TABLE}
            WHERE workspace_id=%s AND contact_id=%s AND status='ACTIVE'
            ORDER BY created_at
        """), (workspace, contact))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple((str(row[0]), str(row[1])) for row in rows)


def configuration_status():
    public_key = (os.environ.get("NINA_WEB_PUSH_VAPID_PUBLIC_KEY") or "").strip()
    private_key = (os.environ.get("NINA_WEB_PUSH_VAPID_PRIVATE_KEY") or "").strip()
    subject = (os.environ.get("NINA_WEB_PUSH_VAPID_SUBJECT") or "").strip()
    configured = bool(public_key or private_key or subject)
    valid = bool(public_key and private_key and (subject.startswith("mailto:") or subject.startswith("https://")))
    return {"configured": configured, "available": valid, "public_key": public_key if valid else ""}


def schema_ready():
    conn = None
    try:
        conn = persistence_backend.connect()
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {SUBSCRIPTION_TABLE} LIMIT 1")
        cur.fetchone()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


def readiness_status(service_worker_present=True, adapter_present=True):
    config = configuration_status()
    return {
        "configured": config["configured"],
        "available": bool(config["available"] and schema_ready() and service_worker_present and adapter_present),
        "schema": schema_ready(),
        "service_worker": bool(service_worker_present),
        "adapter": bool(adapter_present),
        "public_key": bool(config["public_key"]),
        "sender": bool(config["available"]),
    }


def _send_push(subscription, payload):
    from pywebpush import webpush
    private_key = (os.environ.get("NINA_WEB_PUSH_VAPID_PRIVATE_KEY") or "").strip().replace("\\n", "\n")
    subject = (os.environ.get("NINA_WEB_PUSH_VAPID_SUBJECT") or "").strip()
    webpush(
        subscription_info=subscription,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        vapid_private_key=private_key,
        vapid_claims={"sub": subject},
        ttl=300,
    )


def deliver_reminder_push(reminder, sender=None):
    """Best-effort additive push; canonical Web reminder success remains independent."""
    config = configuration_status()
    if not config["available"]:
        return []
    workspace = _identifier(reminder.workspace_id, "workspace_id")
    contact = _identifier(reminder.origin_user_id, "contact_id")
    payload = {
        "title": "Nina reminder",
        "body": reminder.title.removeprefix("Atgādinājums: ").strip()[:180],
        "url": "/nina",
        "tag": f"nina-reminder-{reminder.object_id}",
    }
    results = []
    for subscription_id, encrypted in list_active_subscriptions(workspace, contact):
        delivery_id = "wpd_" + secrets.token_hex(16)
        idempotency_key = hashlib.sha256(
            f"{workspace}\0{reminder.object_id}\0{subscription_id}".encode()
        ).hexdigest()
        conn = persistence_backend.connect()
        try:
            cur = conn.cursor()
            try:
                cur.execute(_sql(f"""
                    INSERT INTO {DELIVERY_TABLE}
                    (delivery_id,workspace_id,contact_id,subscription_id,reminder_id,
                     idempotency_key,status,failure_code,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,'PENDING','',%s,%s)
                """), (
                    delivery_id, workspace, contact, subscription_id,
                    reminder.object_id, idempotency_key, _now(), _now(),
                ))
                conn.commit()
            except Exception:
                conn.rollback()
                cur.execute(_sql(f"SELECT status FROM {DELIVERY_TABLE} WHERE idempotency_key=%s"), (idempotency_key,))
                existing = cur.fetchone()
                if not existing:
                    cur.close()
                    raise
                cur.close()
                results.append({"subscription_id": subscription_id, "status": str(existing[0])})
                continue
            raw = decrypt_channel_credential(encrypted)
            subscription = json.loads(raw) if raw else {}
            try:
                (sender or _send_push)(subscription, payload)
                status, failure_code, subscription_status = "DELIVERED", "", "ACTIVE"
                success_at, failure_at = _now(), ""
            except Exception as exc:
                response = getattr(exc, "response", None)
                status_code = int(getattr(response, "status_code", 0) or 0)
                invalid = status_code in {404, 410}
                status, failure_code = "FAILED", "endpoint_invalid" if invalid else f"sender_{type(exc).__name__.lower()}"
                subscription_status = "EXPIRED" if status_code == 410 else "INVALID" if invalid else "ACTIVE"
                success_at, failure_at = "", _now()
            cur.execute(_sql(f"UPDATE {DELIVERY_TABLE} SET status=%s,failure_code=%s,updated_at=%s WHERE delivery_id=%s"), (status, failure_code, _now(), delivery_id))
            cur.execute(_sql(f"""
                UPDATE {SUBSCRIPTION_TABLE} SET status=%s,last_success_at=CASE WHEN %s<>'' THEN %s ELSE last_success_at END,
                    last_failure_at=CASE WHEN %s<>'' THEN %s ELSE last_failure_at END,failure_code=%s,updated_at=%s
                WHERE subscription_id=%s AND workspace_id=%s AND contact_id=%s
            """), (
                subscription_status, success_at, success_at, failure_at, failure_at,
                failure_code, _now(), subscription_id, workspace, contact,
            ))
            _event(conn, workspace, subscription_id, "push_delivered" if status == "DELIVERED" else "push_failed", {"reminder_id": reminder.object_id, "failure_code": failure_code})
            conn.commit()
            cur.close()
            results.append({"subscription_id": subscription_id, "status": status})
        finally:
            conn.close()
    return results
