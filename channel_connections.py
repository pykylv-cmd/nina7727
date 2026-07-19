"""Workspace-scoped channel connection state for NinaOS Web.

This module stores configuration state only. It does not start channel runtimes,
send messages, or resolve secret references.
"""

import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

try:
    import psycopg2
except Exception:
    psycopg2 = None


DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()
DB_FILE = (os.environ.get("NINA_DB_FILE") or "nina_memory.db").strip()
USE_POSTGRES = bool(DATABASE_URL and psycopg2)
_TABLE = "nina_channel_connections"
_SCHEMA_READY = False
ALLOWED_CHANNELS = {"telegram", "whatsapp"}
ALLOWED_STATUSES = {"disconnected", "pending", "connected", "error"}
_WORKSPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")
_SECRET_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
_TELEGRAM_CONNECT_TOKEN_RE = re.compile(r"^ninaos_[A-Za-z0-9_-]{24,48}$")


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sql(statement):
    return statement if USE_POSTGRES else statement.replace("%s", "?")


def _connect():
    return psycopg2.connect(DATABASE_URL) if USE_POSTGRES else sqlite3.connect(DB_FILE)


def _validate_workspace(workspace_id):
    value = str(workspace_id or "").strip()
    if not _WORKSPACE_RE.fullmatch(value):
        raise ValueError("invalid_workspace")
    return value


def _validate_channel(channel):
    value = str(channel or "").strip().lower()
    if value not in ALLOWED_CHANNELS:
        raise ValueError("invalid_channel")
    return value


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return True
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                workspace_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{{}}',
                secret_ref TEXT NOT NULL DEFAULT '',
                connect_token_hash TEXT NOT NULL DEFAULT '',
                connect_token_expires_at TEXT NOT NULL DEFAULT '',
                connect_token_used_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (workspace_id, channel)
            )
            """
        )
        conn.commit()
        cur.close()
        _SCHEMA_READY = True
        return True
    finally:
        conn.close()


def get_connection(workspace_id, channel):
    workspace_id = _validate_workspace(workspace_id)
    channel = _validate_channel(channel)
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT status, metadata_json, secret_ref, connect_token_expires_at, connect_token_used_at, created_at, updated_at FROM {_TABLE} WHERE workspace_id=%s AND channel=%s"), (workspace_id, channel))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        return {"workspace_id": workspace_id, "channel": channel, "status": "disconnected", "metadata": {}, "secret_configured": False}
    try:
        metadata = json.loads(row[1] or "{}")
    except Exception:
        metadata = {}
    return {
        "workspace_id": workspace_id, "channel": channel, "status": row[0],
        "metadata": metadata if isinstance(metadata, dict) else {},
        "secret_configured": bool(row[2]), "token_expires_at": row[3] or "",
        "token_used_at": row[4] or "", "created_at": row[5], "updated_at": row[6],
    }


def _upsert(workspace_id, channel, status, metadata=None, secret_ref="", token_hash="", token_expires_at="", token_used_at=""):
    workspace_id = _validate_workspace(workspace_id)
    channel = _validate_channel(channel)
    if status not in ALLOWED_STATUSES:
        raise ValueError("invalid_status")
    ensure_schema()
    now = _iso(_now())
    payload = json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":"))
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT created_at FROM {_TABLE} WHERE workspace_id=%s AND channel=%s"), (workspace_id, channel))
        existing = cur.fetchone()
        if existing:
            cur.execute(_sql(f"UPDATE {_TABLE} SET status=%s, metadata_json=%s, secret_ref=%s, connect_token_hash=%s, connect_token_expires_at=%s, connect_token_used_at=%s, updated_at=%s WHERE workspace_id=%s AND channel=%s"), (status, payload, secret_ref, token_hash, token_expires_at, token_used_at, now, workspace_id, channel))
        else:
            cur.execute(_sql(f"INSERT INTO {_TABLE} (workspace_id, channel, status, metadata_json, secret_ref, connect_token_hash, connect_token_expires_at, connect_token_used_at, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"), (workspace_id, channel, status, payload, secret_ref, token_hash, token_expires_at, token_used_at, now, now))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return get_connection(workspace_id, channel)


def create_telegram_token(workspace_id, bot_username="", ttl_seconds=600):
    workspace_id = _validate_workspace(workspace_id)
    if get_connection(workspace_id, "telegram")["status"] == "connected":
        raise ValueError("telegram_already_connected")
    username = str(bot_username or "").strip().lstrip("@")
    if username and not re.fullmatch(r"[A-Za-z0-9_]{5,64}", username):
        raise ValueError("invalid_bot_username")
    ttl_seconds = max(60, min(int(ttl_seconds), 3600))
    token = "ninaos_" + secrets.token_urlsafe(24)
    expires = _iso(_now() + timedelta(seconds=ttl_seconds))
    _upsert(workspace_id, "telegram", "pending", {"bot_username": username}, token_hash=hashlib.sha256(token.encode()).hexdigest(), token_expires_at=expires)
    return {"token": token, "expires_at": expires, "bot_username": username, "deep_link": f"https://t.me/{username}?start={token}" if username else ""}


def is_telegram_connection_token(token):
    """Recognize only NinaOS workspace-link payloads, never referral payloads."""
    return bool(_TELEGRAM_CONNECT_TOKEN_RE.fullmatch(str(token or "").strip()))


def consume_telegram_token(
    token,
    telegram_user_id="",
    telegram_username="",
    telegram_chat_id="",
    telegram_display_name="",
    expected_workspace_id=None,
    now=None,
):
    raw = str(token or "").strip()
    if not is_telegram_connection_token(raw):
        return None
    ensure_schema()
    digest = hashlib.sha256(raw.encode()).hexdigest()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT workspace_id, status, metadata_json, connect_token_expires_at, connect_token_used_at FROM {_TABLE} WHERE channel=%s AND connect_token_hash=%s"), ("telegram", digest))
        row = cur.fetchone()
        if not row or row[4] or row[1] != "pending":
            cur.close()
            return None
        if expected_workspace_id is not None and row[0] != _validate_workspace(expected_workspace_id):
            cur.close()
            return None
        current = now or _now()
        expires = datetime.fromisoformat(str(row[3]).replace("Z", "+00:00"))
        if expires <= current:
            cur.close()
            return None
        user_id = str(telegram_user_id or "").strip()[:64]
        chat_id = str(telegram_chat_id or "").strip()[:64]
        if not user_id or not chat_id:
            cur.close()
            return None
        cur.execute(_sql(f"SELECT workspace_id, metadata_json FROM {_TABLE} WHERE channel=%s AND status=%s"), ("telegram", "connected"))
        for linked_workspace, linked_json in cur.fetchall():
            try:
                linked = json.loads(linked_json or "{}")
            except Exception:
                linked = {}
            same_identity = str(linked.get("telegram_user_id") or "") == user_id or str(linked.get("telegram_chat_id") or "") == chat_id
            if same_identity and linked_workspace != row[0]:
                cur.close()
                return None
        metadata = json.loads(row[2] or "{}")
        used = _iso(current)
        metadata.update({
            "telegram_chat_id": chat_id,
            "telegram_user_id": user_id,
            "telegram_username": str(telegram_username or "").strip().lstrip("@")[:64],
            "telegram_display_name": str(telegram_display_name or "").strip()[:160],
            "linked_at": used,
        })
        cur.execute(_sql(f"UPDATE {_TABLE} SET status=%s, metadata_json=%s, connect_token_used_at=%s, updated_at=%s WHERE workspace_id=%s AND channel=%s AND connect_token_hash=%s AND connect_token_used_at=%s"), ("connected", json.dumps(metadata, ensure_ascii=False, separators=(",", ":")), used, used, row[0], "telegram", digest, ""))
        conn.commit()
        changed = cur.rowcount == 1
        cur.close()
        return get_connection(row[0], "telegram") if changed else None
    finally:
        conn.close()


def configure_whatsapp(workspace_id, phone_number_id, business_account_id, secret_ref):
    phone_number_id = str(phone_number_id or "").strip()
    business_account_id = str(business_account_id or "").strip()
    secret_ref = str(secret_ref or "").strip()
    if not _ID_RE.fullmatch(phone_number_id) or not _ID_RE.fullmatch(business_account_id):
        raise ValueError("invalid_whatsapp_id")
    if not _SECRET_REF_RE.fullmatch(secret_ref):
        raise ValueError("invalid_secret_reference")
    metadata = {"phone_number_id": phone_number_id, "business_account_id": business_account_id, "webhook_verified": False}
    return _upsert(workspace_id, "whatsapp", "pending", metadata, secret_ref=secret_ref)


def set_connection_for_test(workspace_id, channel, status, metadata=None, secret_ref=""):
    return _upsert(workspace_id, channel, status, metadata, secret_ref)


def disconnect(workspace_id, channel):
    return _upsert(workspace_id, channel, "disconnected", {})
