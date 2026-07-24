"""Encrypted persistence and bridge boundary for NinaOS Company WhatsApp."""

import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from channel_connections import (
    DATABASE_URL, DB_FILE, USE_POSTGRES, _sql, claim_channel_message,
    decrypt_channel_credential, disconnect, encrypt_channel_credential,
    get_connection, set_connection_for_test,
)

try:
    import psycopg2
except Exception:
    psycopg2 = None

CHANNEL = "whatsapp_company"
AUTH_TABLE = "nina_company_whatsapp_auth"
PAIR_TABLE = "nina_company_whatsapp_pairing"
_JID = re.compile(r"^([0-9]{6,20})(?::[0-9]+)?@(?:s\.whatsapp\.net|lid)$")


def configured_workspace():
    value = (os.environ.get("NINA_COMPANY_WHATSAPP_WORKSPACE") or "ninaos_company").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}", value):
        raise ValueError("invalid_company_workspace")
    return value


def configured_number():
    value = (os.environ.get("NINA_COMPANY_WHATSAPP_NUMBER") or "").replace(" ", "").strip()
    if value and not re.fullmatch(r"\+[1-9][0-9]{6,14}", value):
        raise ValueError("invalid_company_number")
    return value


def _connect():
    return psycopg2.connect(DATABASE_URL) if USE_POSTGRES else sqlite3.connect(DB_FILE)


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_schema():
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


def create_pairing_session(workspace_id=None, ttl_seconds=300):
    workspace_id = workspace_id or configured_workspace()
    ttl = max(60, min(int(ttl_seconds), 600))
    raw = "cwa_" + secrets.token_urlsafe(32)
    now = _now()
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        cur.execute(_sql(f"INSERT INTO {PAIR_TABLE} (workspace_id,session_hash,expires_at,created_at) VALUES (%s,%s,%s,%s)"),
                    (workspace_id, hashlib.sha256(raw.encode()).hexdigest(), _iso(now + timedelta(seconds=ttl)), _iso(now)))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    set_connection_for_test(workspace_id, CHANNEL, "pending", {"mode": "company_external", "pairing_expires_at": _iso(now + timedelta(seconds=ttl))})
    return {"session_token": raw, "expires_at": _iso(now + timedelta(seconds=ttl))}


def validate_pairing_session(workspace_id, token, consume=False, now=None):
    digest = hashlib.sha256(str(token or "").encode()).hexdigest()
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT session_hash,expires_at FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        row = cur.fetchone()
        valid = bool(row and secrets.compare_digest(row[0], digest) and datetime.fromisoformat(row[1].replace("Z", "+00:00")) > (now or _now()))
        if valid and consume:
            cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s AND session_hash=%s"), (workspace_id, digest))
            conn.commit()
        cur.close()
        return valid
    finally:
        conn.close()


def pairing_is_active(workspace_id=None, now=None):
    workspace_id = workspace_id or configured_workspace()
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT expires_at FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        row = cur.fetchone()
        cur.close()
        return bool(row and datetime.fromisoformat(row[0].replace("Z", "+00:00")) > (now or _now()))
    finally:
        conn.close()


def store_auth_record(workspace_id, auth_key, value):
    key = str(auth_key or "")[:180]
    if not key or value is None:
        raise ValueError("invalid_auth_record")
    encrypted = encrypt_channel_credential(json.dumps(value, separators=(",", ":")))
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s AND auth_key=%s"), (workspace_id, key))
        cur.execute(_sql(f"INSERT INTO {AUTH_TABLE} (workspace_id,auth_key,encrypted_value,updated_at) VALUES (%s,%s,%s,%s)"),
                    (workspace_id, key, encrypted, _iso(_now())))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def delete_auth_record(workspace_id, auth_key):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s AND auth_key=%s"), (workspace_id, str(auth_key or "")[:180]))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def load_auth_records(workspace_id):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT auth_key,encrypted_value FROM {AUTH_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    result = {}
    for key, encrypted in rows:
        raw = decrypt_channel_credential(encrypted)
        if raw:
            try:
                result[key] = json.loads(raw)
            except Exception:
                pass
    return result


def mark_connected(workspace_id, session_token, identity):
    if workspace_id != configured_workspace() or not validate_pairing_session(workspace_id, session_token, consume=True):
        return None
    safe = {
        "mode": "company_external",
        "masked_identity": str((identity or {}).get("masked_identity") or "")[:40],
        "linked_at": _iso(_now()),
    }
    return set_connection_for_test(workspace_id, CHANNEL, "connected", safe)


def sender_digits(sender_jid):
    match = _JID.fullmatch(str(sender_jid or "").strip())
    return match.group(1) if match else ""


def accept_inbound(workspace_id, message_id, sender_jid, text):
    if workspace_id != configured_workspace() or get_connection(workspace_id, CHANNEL)["status"] != "connected":
        return False
    if not sender_digits(sender_jid) or not str(text or "").strip():
        return False
    return claim_channel_message(workspace_id, CHANNEL, message_id)


def disconnect_company(workspace_id=None):
    workspace_id = workspace_id or configured_workspace()
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"DELETE FROM {AUTH_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        cur.execute(_sql(f"DELETE FROM {PAIR_TABLE} WHERE workspace_id=%s"), (workspace_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return disconnect(workspace_id, CHANNEL)


def list_connected_workspaces():
    workspace_id = configured_workspace()
    return [workspace_id] if get_connection(workspace_id, CHANNEL)["status"] == "connected" else []
