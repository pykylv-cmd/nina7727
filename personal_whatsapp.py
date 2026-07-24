"""Secure, channel-neutral persistence and bridge client for Personal WhatsApp."""

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from channel_connections import (
    DATABASE_URL, DB_FILE, USE_POSTGRES, _sql, claim_channel_message,
    decrypt_channel_credential, disconnect, encrypt_channel_credential,
    get_connection, set_connection_for_test,
)

try:
    import psycopg2
except Exception:
    psycopg2 = None

CHANNEL = "whatsapp_personal"
AUTH_TABLE = "nina_personal_whatsapp_auth"
PAIR_TABLE = "nina_personal_whatsapp_pairing"


def _connect():
    return psycopg2.connect(DATABASE_URL) if USE_POSTGRES else sqlite3.connect(DB_FILE)


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_personal_whatsapp_schema():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {AUTH_TABLE} (
            workspace_id TEXT NOT NULL, auth_key TEXT NOT NULL,
            encrypted_value TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, auth_key))""")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {PAIR_TABLE} (
            workspace_id TEXT PRIMARY KEY, session_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL)""")
        conn.commit()
        cur.close()
    finally:
        conn.close()


def create_pairing_session(workspace_id, ttl_seconds=180):
    ttl = max(60, min(int(ttl_seconds), 300))
    raw = "pwa_" + secrets.token_urlsafe(32)
    now = _now()
    ensure_personal_whatsapp_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        cur.execute(_sql(f"INSERT INTO {PAIR_TABLE} (workspace_id,session_hash,expires_at,created_at) VALUES (%s,%s,%s,%s)"),
                    (workspace_id, hashlib.sha256(raw.encode()).hexdigest(), _iso(now + timedelta(seconds=ttl)), _iso(now)))
        conn.commit(); cur.close()
    finally:
        conn.close()
    set_connection_for_test(workspace_id, CHANNEL, "pending", {"mode": "self_chat", "pairing_expires_at": _iso(now + timedelta(seconds=ttl))})
    return {"session_token": raw, "expires_at": _iso(now + timedelta(seconds=ttl))}


def validate_pairing_session(workspace_id, token, consume=False, now=None):
    digest = hashlib.sha256(str(token or "").encode()).hexdigest()
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT session_hash,expires_at FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        row = cur.fetchone()
        valid = bool(row and secrets.compare_digest(row[0], digest) and datetime.fromisoformat(row[1].replace("Z", "+00:00")) > (now or _now()))
        if valid and consume:
            cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s AND session_hash=%s"), (workspace_id, digest)); conn.commit()
        cur.close(); return valid
    finally:
        conn.close()


def pairing_is_active(workspace_id, now=None):
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur=conn.cursor(); cur.execute(_sql(f"SELECT expires_at FROM {PAIR_TABLE} WHERE workspace_id=%s"),(workspace_id,)); row=cur.fetchone(); cur.close()
        return bool(row and datetime.fromisoformat(row[0].replace("Z", "+00:00")) > (now or _now()))
    finally: conn.close()


def store_auth_record(workspace_id, auth_key, value):
    key = str(auth_key or "")[:180]
    if not key or value is None: raise ValueError("invalid_auth_record")
    encrypted = encrypt_channel_credential(json.dumps(value, separators=(",", ":")))
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s AND auth_key=%s"), (workspace_id, key))
        cur.execute(_sql(f"INSERT INTO {AUTH_TABLE} (workspace_id,auth_key,encrypted_value,updated_at) VALUES (%s,%s,%s,%s)"), (workspace_id, key, encrypted, _iso(_now())))
        conn.commit(); cur.close()
    finally: conn.close()


def delete_auth_record(workspace_id, auth_key):
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s AND auth_key=%s"), (workspace_id, str(auth_key or "")[:180])); conn.commit(); cur.close()
    finally: conn.close()


def load_auth_records(workspace_id):
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"SELECT auth_key,encrypted_value FROM {AUTH_TABLE} WHERE workspace_id=%s"), (workspace_id,)); rows = cur.fetchall(); cur.close()
    finally: conn.close()
    result = {}
    for key, encrypted in rows:
        raw = decrypt_channel_credential(encrypted)
        if raw:
            try: result[key] = json.loads(raw)
            except Exception: pass
    return result


def mark_connected(workspace_id, session_token, identity):
    if not validate_pairing_session(workspace_id, session_token, consume=True): return None
    safe = {k: str((identity or {}).get(k) or "")[:160] for k in ("jid", "display_name", "masked_identity")}
    safe.update({"mode": "self_chat", "linked_at": _iso(_now())})
    return set_connection_for_test(workspace_id, CHANNEL, "connected", safe)


def disconnect_personal(workspace_id):
    ensure_personal_whatsapp_schema(); conn = _connect()
    try:
        cur = conn.cursor(); cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s"), (workspace_id,)); cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,)); conn.commit(); cur.close()
    finally: conn.close()
    return disconnect(workspace_id, CHANNEL)


def list_connected_workspaces():
    from channel_connections import ensure_schema
    ensure_schema(); conn = _connect()
    try:
        cur=conn.cursor(); cur.execute(_sql("SELECT workspace_id FROM nina_channel_connections WHERE channel=%s AND status=%s"),(CHANNEL,"connected")); rows=[str(row[0]) for row in cur.fetchall()]; cur.close(); return rows
    finally: conn.close()


def bridge_request(path, payload=None, method="POST", timeout=10):
    base = (os.environ.get("PERSONAL_WHATSAPP_BRIDGE_URL") or "").strip().rstrip("/")
    token = (os.environ.get("NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN") or "").strip()
    if not base or not token: raise RuntimeError("personal_whatsapp_bridge_unavailable")
    body = json.dumps(payload or {}).encode() if payload is not None else None
    req = Request(base + path, data=body, method=method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response: return json.loads(response.read().decode() or "{}")
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError("personal_whatsapp_bridge_unavailable") from exc


def authorize_bridge(header):
    expected = (os.environ.get("NINA_PERSONAL_WHATSAPP_BRIDGE_TOKEN") or "").strip()
    supplied = str(header or "").removeprefix("Bearer ").strip()
    return bool(expected and supplied and secrets.compare_digest(expected, supplied))


def accept_inbound(workspace_id, message_id, chat_jid, text, is_group=False):
    connection = get_connection(workspace_id, CHANNEL)
    own_jid = str((connection.get("metadata") or {}).get("jid") or "")
    if connection["status"] != "connected" or is_group or not own_jid or chat_jid != own_jid: return False
    return bool(str(text or "").strip()) and claim_channel_message(workspace_id, CHANNEL, message_id)
