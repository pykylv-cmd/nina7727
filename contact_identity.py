"""Tenant-scoped Contact Identity V1 for every NinaOS channel."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timezone

import persistence_backend
DATABASE_URL, DB_FILE, USE_POSTGRES = persistence_backend.module_settings()
CONTACT_TABLE = "nina_contacts"
IDENTITY_TABLE = "nina_contact_channel_identities"
LINK_TABLE = "nina_contact_link_claims"
ALLOWED_CHANNELS = {"company_whatsapp", "telegram", "web", "email", "personal_whatsapp", "whatsapp", "ninaos_number"}
_SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _connect():
    return persistence_backend.connect(DATABASE_URL, DB_FILE, USE_POSTGRES)


def _sql(value):
    return value if USE_POSTGRES else value.replace("%s", "?")


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret():
    value = (
        os.environ.get("NINA_CONTACT_IDENTITY_KEY")
        or os.environ.get("NINAOS_NUMBER_IDENTITY_KEY")
        or os.environ.get("NINA_CHANNEL_CREDENTIAL_KEY")
        or ""
    ).strip()
    if len(value) < 32:
        raise RuntimeError("contact_identity_key_missing")
    return value.encode()


def ensure_schema():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {CONTACT_TABLE} (
            contact_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '', preferred_name TEXT NOT NULL DEFAULT '',
            relationship_type TEXT NOT NULL DEFAULT 'contact', language TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '', notes_json TEXT NOT NULL DEFAULT '{{}}',
            source_metadata_json TEXT NOT NULL DEFAULT '{{}}', name_quality INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)""")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {IDENTITY_TABLE} (
            workspace_id TEXT NOT NULL, channel TEXT NOT NULL,
            external_identity_hash TEXT NOT NULL, contact_id TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0, source_metadata_json TEXT NOT NULL DEFAULT '{{}}',
            created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, channel, external_identity_hash))""")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {LINK_TABLE} (
            claim_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
            source_contact_id TEXT NOT NULL, target_contact_id TEXT NOT NULL,
            verification_method TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, verified_at TEXT NOT NULL DEFAULT '')""")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_nina_contacts_workspace ON {CONTACT_TABLE} (workspace_id, last_seen_at)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_nina_contact_identity_contact ON {IDENTITY_TABLE} (contact_id)")
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _scope(workspace_id, channel):
    workspace = str(workspace_id or "").strip()
    clean_channel = str(channel or "").strip().lower()
    if not _SCOPE.fullmatch(workspace) or clean_channel not in ALLOWED_CHANNELS:
        raise ValueError("invalid_contact_scope")
    return workspace, clean_channel


def _external_hash(workspace_id, channel, external_identity):
    external = str(external_identity or "").strip()
    if not external or len(external) > 512:
        raise ValueError("invalid_external_identity")
    material = f"{workspace_id}\0{channel}\0{external}".encode()
    return hmac.new(_secret(), material, hashlib.sha256).hexdigest()


def _safe_profile(metadata):
    value = metadata if isinstance(metadata, dict) else {}
    quality = max(0, min(int(value.get("display_name_quality") or 0), 100))
    return {
        "display_name": str(value.get("display_name") or "")[:120].strip(),
        "preferred_name": str(value.get("preferred_name") or "")[:120].strip(),
        "preferred_name_verified": bool(value.get("preferred_name_verified")),
        "relationship_type": str(value.get("relationship_type") or "contact")[:40].strip() or "contact",
        "language": str(value.get("language") or "")[:12].lower().strip(),
        "language_verified": bool(value.get("language_verified")),
        "timezone": str(value.get("timezone") or "")[:64].strip(),
        "display_name_quality": quality,
    }


def resolve_contact_identity(workspace_id, channel, external_identity, profile_metadata=None):
    workspace, clean_channel = _scope(workspace_id, channel)
    digest = _external_hash(workspace, clean_channel, external_identity)
    profile = _safe_profile(profile_metadata)
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""SELECT contact_id FROM {IDENTITY_TABLE}
            WHERE workspace_id=%s AND channel=%s AND external_identity_hash=%s"""),
            (workspace, clean_channel, digest))
        row = cur.fetchone()
        now = _now()
        if row:
            contact_id = str(row[0])
        else:
            contact_id = "contact_" + secrets.token_hex(16)
            cur.execute(_sql(f"""INSERT INTO {CONTACT_TABLE}
                (contact_id,workspace_id,display_name,preferred_name,relationship_type,language,timezone,
                 notes_json,source_metadata_json,name_quality,status,created_at,updated_at,last_seen_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""),
                (contact_id, workspace, profile["display_name"],
                 profile["preferred_name"] if profile["preferred_name_verified"] else "",
                 profile["relationship_type"], profile["language"] if profile["language_verified"] else "",
                 profile["timezone"], "{}", json.dumps({"first_channel": clean_channel}),
                 profile["display_name_quality"], "active", now, now, now))
            try:
                cur.execute(_sql(f"""INSERT INTO {IDENTITY_TABLE}
                    (workspace_id,channel,external_identity_hash,contact_id,verified,source_metadata_json,created_at,last_seen_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""),
                    (workspace, clean_channel, digest, contact_id, 0,
                     json.dumps({"channel": clean_channel}), now, now))
            except Exception:
                conn.rollback()
                cur = conn.cursor()
                cur.execute(_sql(f"""SELECT contact_id FROM {IDENTITY_TABLE}
                    WHERE workspace_id=%s AND channel=%s AND external_identity_hash=%s"""),
                    (workspace, clean_channel, digest))
                row = cur.fetchone()
                if not row:
                    raise
                contact_id = str(row[0])
        cur.execute(_sql(f"SELECT display_name,name_quality,preferred_name FROM {CONTACT_TABLE} WHERE contact_id=%s AND workspace_id=%s"),
                    (contact_id, workspace))
        current = cur.fetchone() or ("", 0, "")
        display_name = profile["display_name"] if profile["display_name"] and profile["display_name_quality"] >= int(current[1] or 0) else str(current[0] or "")
        preferred_name = profile["preferred_name"] if profile["preferred_name_verified"] else str(current[2] or "")
        cur.execute(_sql(f"""UPDATE {CONTACT_TABLE} SET display_name=%s, preferred_name=%s,
            relationship_type=%s, language=CASE WHEN %s<>'' THEN %s ELSE language END,
            timezone=CASE WHEN %s<>'' THEN %s ELSE timezone END, name_quality=%s,
            updated_at=%s,last_seen_at=%s WHERE contact_id=%s AND workspace_id=%s"""),
            (display_name, preferred_name, profile["relationship_type"],
             profile["language"] if profile["language_verified"] else "", profile["language"],
             profile["timezone"], profile["timezone"],
             max(int(current[1] or 0), profile["display_name_quality"]), now, now, contact_id, workspace))
        cur.execute(_sql(f"""UPDATE {IDENTITY_TABLE} SET last_seen_at=%s
            WHERE workspace_id=%s AND channel=%s AND external_identity_hash=%s"""),
            (now, workspace, clean_channel, digest))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    result = get_contact(contact_id, workspace)
    result.update({"channel": clean_channel, "conversation_id": f"contact:{contact_id}:{clean_channel}"})
    return result


def get_contact(contact_id, workspace_id):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""SELECT contact_id,workspace_id,display_name,preferred_name,relationship_type,
            language,timezone,notes_json,source_metadata_json,status,created_at,updated_at,last_seen_at
            FROM {CONTACT_TABLE} WHERE contact_id=%s AND workspace_id=%s"""), (str(contact_id), str(workspace_id)))
        row = cur.fetchone()
        if not row:
            raise ValueError("contact_not_found")
        cur.execute(_sql(f"SELECT channel FROM {IDENTITY_TABLE} WHERE contact_id=%s AND workspace_id=%s ORDER BY channel"),
                    (str(contact_id), str(workspace_id)))
        channels = [str(item[0]) for item in cur.fetchall()]
        cur.close()
    finally:
        conn.close()
    return {
        "contact_id": row[0], "workspace_id": row[1], "display_name": row[2],
        "preferred_name": row[3], "relationship_type": row[4], "language": row[5],
        "timezone": row[6], "notes": json.loads(row[7] or "{}"),
        "source_metadata": json.loads(row[8] or "{}"), "status": row[9],
        "created_at": row[10], "updated_at": row[11], "last_seen_at": row[12],
        "channels": channels,
    }


def compact_contact_context(contact):
    value = contact if isinstance(contact, dict) else {}
    lines = []
    name = str(value.get("preferred_name") or value.get("display_name") or "").strip()
    if name:
        lines.append(f"Contact: {name}")
    if value.get("language"):
        lines.append(f"Preferred language: {value['language']}")
    if value.get("relationship_type") and value.get("relationship_type") != "contact":
        lines.append(f"Relationship: {value['relationship_type']}")
    channels = list(value.get("channels") or [])
    if channels:
        lines.append(f"Current channel: {channels[-1]}")
    return "\n".join(lines)[:500]


def list_contacts(workspace_id=None, limit=200):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        if workspace_id:
            cur.execute(_sql(f"SELECT contact_id,workspace_id FROM {CONTACT_TABLE} WHERE workspace_id=%s ORDER BY last_seen_at DESC LIMIT %s"),
                        (workspace_id, min(int(limit), 500)))
        else:
            cur.execute(_sql(f"SELECT contact_id,workspace_id FROM {CONTACT_TABLE} ORDER BY last_seen_at DESC LIMIT %s"),
                        (min(int(limit), 500),))
        keys = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return [get_contact(row[0], row[1]) for row in keys]


def create_contact_link_claim(workspace_id, source_contact_id, target_contact_id, verification_method):
    workspace, _ = _scope(workspace_id, "web")
    if source_contact_id == target_contact_id:
        raise ValueError("same_contact")
    get_contact(source_contact_id, workspace)
    get_contact(target_contact_id, workspace)
    method = str(verification_method or "").strip()
    if method not in {"one_time_code", "admin_verified", "signed_channel_challenge"}:
        raise ValueError("invalid_verification_method")
    claim = "claim_" + secrets.token_hex(16)
    now = _now()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""INSERT INTO {LINK_TABLE}
            (claim_id,workspace_id,source_contact_id,target_contact_id,verification_method,status,created_at,verified_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""),
            (claim, workspace, source_contact_id, target_contact_id, method, "pending", now, ""))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return {"claim_id": claim, "status": "pending"}


def verify_contact_link_claim(workspace_id, claim_id, verification_succeeded=False):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"SELECT status FROM {LINK_TABLE} WHERE claim_id=%s AND workspace_id=%s"),
                    (claim_id, workspace_id))
        row = cur.fetchone()
        if not row or row[0] != "pending" or not verification_succeeded:
            cur.close()
            return False
        cur.execute(_sql(f"UPDATE {LINK_TABLE} SET status=%s,verified_at=%s WHERE claim_id=%s AND workspace_id=%s"),
                    ("verified", _now(), claim_id, workspace_id))
        conn.commit()
        cur.close()
        return True
    finally:
        conn.close()
