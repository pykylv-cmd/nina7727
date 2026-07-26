"""Tenant-scoped bridge from Contact Identity to canonical business client IDs."""

from __future__ import annotations

import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone

try:
    import psycopg2
except Exception:
    psycopg2 = None

from contact_identity import get_contact

DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()
DB_FILE = (os.environ.get("NINA_DB_FILE") or "nina_memory.db").strip()
USE_POSTGRES = bool(DATABASE_URL and psycopg2)
MAPPING_TABLE = "nina_contact_client_mappings"
_SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_OPAQUE_ID = re.compile(r"^client_[a-f0-9]{32}$")


def _connect():
    return psycopg2.connect(DATABASE_URL) if USE_POSTGRES else sqlite3.connect(DB_FILE)


def _sql(value):
    return value if USE_POSTGRES else value.replace("%s", "?")


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _workspace(value):
    clean = str(value or "").strip()
    if not _SCOPE.fullmatch(clean):
        raise ValueError("invalid_client_mapping_scope")
    return clean


def ensure_schema():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {MAPPING_TABLE} (
            workspace_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            canonical_client_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            merged_into_client_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, contact_id))""")
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_nina_client_mapping_client "
            f"ON {MAPPING_TABLE} (workspace_id, canonical_client_id)"
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def get_client_mapping(workspace_id, contact_id):
    workspace = _workspace(workspace_id)
    clean_contact = str(contact_id or "").strip()
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""SELECT workspace_id,contact_id,canonical_client_id,status,
            merged_into_client_id,created_at,updated_at FROM {MAPPING_TABLE}
            WHERE workspace_id=%s AND contact_id=%s"""), (workspace, clean_contact))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "workspace_id": str(row[0]), "contact_id": str(row[1]),
        "canonical_client_id": str(row[2]), "status": str(row[3]),
        "merged_into_client_id": str(row[4] or ""),
        "created_at": str(row[5]), "updated_at": str(row[6]),
    }


def get_or_create_client_mapping(workspace_id, contact_id):
    workspace = _workspace(workspace_id)
    clean_contact = str(contact_id or "").strip()
    # Proves the contact belongs to this tenant before any business mapping is made.
    get_contact(clean_contact, workspace)
    existing = get_client_mapping(workspace, clean_contact)
    if existing:
        return existing

    now = _now()
    candidate = "client_" + secrets.token_hex(16)
    conn = _connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(_sql(f"""INSERT INTO {MAPPING_TABLE}
                (workspace_id,contact_id,canonical_client_id,status,merged_into_client_id,created_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)"""),
                (workspace, clean_contact, candidate, "active", "", now, now))
            conn.commit()
        except Exception:
            conn.rollback()
        cur.close()
    finally:
        conn.close()
    mapping = get_client_mapping(workspace, clean_contact)
    if not mapping:
        raise RuntimeError("client_mapping_create_failed")
    return mapping


def list_client_mappings(workspace_id=None, limit=500):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        if workspace_id:
            workspace = _workspace(workspace_id)
            cur.execute(_sql(f"""SELECT workspace_id,contact_id,canonical_client_id,status,
                merged_into_client_id,created_at,updated_at FROM {MAPPING_TABLE}
                WHERE workspace_id=%s ORDER BY updated_at DESC LIMIT %s"""),
                (workspace, min(max(int(limit), 1), 1000)))
        else:
            cur.execute(_sql(f"""SELECT workspace_id,contact_id,canonical_client_id,status,
                merged_into_client_id,created_at,updated_at FROM {MAPPING_TABLE}
                ORDER BY updated_at DESC LIMIT %s"""), (min(max(int(limit), 1), 1000),))
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return [{
        "workspace_id": str(row[0]), "contact_id": str(row[1]),
        "canonical_client_id": str(row[2]), "status": str(row[3]),
        "merged_into_client_id": str(row[4] or ""),
        "created_at": str(row[5]), "updated_at": str(row[6]),
    } for row in rows]


def client_context(workspace_id, canonical_client_id):
    workspace = _workspace(workspace_id)
    client_id = str(canonical_client_id or "").strip()
    if not _OPAQUE_ID.fullmatch(client_id):
        return None
    for mapping in list_client_mappings(workspace, limit=1000):
        effective = mapping["merged_into_client_id"] or mapping["canonical_client_id"]
        if effective != client_id or mapping["status"] != "active":
            continue
        try:
            contact = get_contact(mapping["contact_id"], workspace)
        except ValueError:
            continue
        return {
            "canonical_client_id": client_id,
            "display_name": str(contact.get("preferred_name") or contact.get("display_name") or "").strip(),
            "channels": list(contact.get("channels") or []),
        }
    return None
