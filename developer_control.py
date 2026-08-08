"""Persistent control plane for the owner-only read-only Developer capability."""

from __future__ import annotations

import json
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import persistence_backend

AGENT_ID = "ninaos_owner_windows"
ALLOWED_OPERATIONS = frozenset({
    "list_root", "list_directory", "read_text_file", "search_text", "git_status",
    "apply_approved_patch",
})


def _now():
    return datetime.now(timezone.utc)


def _iso(value=None):
    return (value or _now()).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _connect():
    database_url, db_file, use_postgres = persistence_backend.module_settings()
    return persistence_backend.connect(database_url, db_file, use_postgres)


def _sql(statement):
    return persistence_backend.sql(statement)


def ensure_schema():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS nina_developer_agents (
            agent_id TEXT PRIMARY KEY, status TEXT NOT NULL,
            repository_status TEXT NOT NULL, repository_root_label TEXT NOT NULL,
            last_seen_at TEXT NOT NULL, safe_metadata_json TEXT NOT NULL DEFAULT '{}')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS nina_developer_jobs (
            job_id TEXT PRIMARY KEY, operation TEXT NOT NULL,
            arguments_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL,
            result_json TEXT NOT NULL DEFAULT '{}', error_code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, claimed_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS nina_developer_events (
            event_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, job_id TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL, safe_metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nina_developer_jobs_status ON nina_developer_jobs(status,created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nina_developer_events_created ON nina_developer_events(created_at)")
        conn.commit()
        cur.close()
    finally:
        conn.close()


def authorize_agent(header):
    expected = (os.environ.get("NINA_DEVELOPER_AGENT_TOKEN") or "").strip()
    supplied = str(header or "").removeprefix("Bearer ").strip()
    return bool(expected and supplied and secrets.compare_digest(expected, supplied))


def _event(cur, event_type, job_id="", metadata=None):
    cur.execute(_sql("INSERT INTO nina_developer_events (event_id,agent_id,job_id,event_type,safe_metadata_json,created_at) VALUES (%s,%s,%s,%s,%s,%s)"),
                ("devevt_" + uuid.uuid4().hex, AGENT_ID, job_id, event_type,
                 json.dumps(metadata or {}, separators=(",", ":")), _iso()))


def heartbeat(repository_root_label="nina7727"):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("DELETE FROM nina_developer_agents WHERE agent_id=%s"), (AGENT_ID,))
        cur.execute(_sql("INSERT INTO nina_developer_agents (agent_id,status,repository_status,repository_root_label,last_seen_at,safe_metadata_json) VALUES (%s,%s,%s,%s,%s,%s)"),
                    (AGENT_ID, "connected", "connected", str(repository_root_label)[:80], _iso(), "{}"))
        _event(cur, "heartbeat")
        conn.commit(); cur.close()
    finally:
        conn.close()
    return True


def connection_status(now=None):
    ensure_schema()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT status,repository_status,last_seen_at FROM nina_developer_agents WHERE agent_id=%s"), (AGENT_ID,))
        row = cur.fetchone(); cur.close()
    finally:
        conn.close()
    if not row:
        return {"agent": "not_connected", "repository": "not_connected"}
    try:
        seen = datetime.fromisoformat(str(row[2]).replace("Z", "+00:00"))
    except ValueError:
        seen = datetime.min.replace(tzinfo=timezone.utc)
    connected = seen >= (now or _now()) - timedelta(seconds=45)
    return {
        "agent": "connected" if connected and row[0] == "connected" else "not_connected",
        "repository": "connected" if connected and row[1] == "connected" else "not_connected",
    }


def create_job(operation, arguments=None):
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("developer_operation_not_allowed")
    job_id = "devjob_" + uuid.uuid4().hex
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("INSERT INTO nina_developer_jobs (job_id,operation,arguments_json,status,result_json,error_code,created_at,claimed_at,completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"),
                    (job_id, operation, json.dumps(arguments or {}, separators=(",", ":")), "pending", "{}", "", _iso(), "", ""))
        _event(cur, "job_created", job_id, {"operation": operation})
        conn.commit(); cur.close()
    finally:
        conn.close()
    return job_id


def create_approved_patch_job(investigation_id, patch, submitted_hash, affected_files,
                              expected_source_hashes, validation, owner_identity="platform_admin",
                              now=None):
    investigation_id = str(investigation_id or "")
    patch = str(patch or "")
    calculated_hash = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    if not investigation_id.startswith("devinvest_") or not patch:
        raise ValueError("developer_approval_invalid")
    if not secrets.compare_digest(calculated_hash, str(submitted_hash or "")):
        raise ValueError("developer_diff_hash_changed")
    paths = [str(path) for path in (affected_files or [])]
    hashes = {str(path): str(value) for path, value in (expected_source_hashes or {}).items()}
    if not paths or len(paths) != len(set(paths)) or set(paths) != set(hashes):
        raise ValueError("developer_approval_paths_changed")
    if any(len(value) != 64 or any(character not in "0123456789abcdef" for character in value.casefold())
           for value in hashes.values()):
        raise ValueError("developer_source_hash_missing")
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        if persistence_backend.USE_POSTGRES:
            cur.execute(_sql("SELECT agent_id FROM nina_developer_agents WHERE agent_id=%s FOR UPDATE"),
                        (AGENT_ID,))
        else:
            cur.execute("BEGIN IMMEDIATE")
        cur.execute(_sql("SELECT arguments_json FROM nina_developer_jobs WHERE operation=%s"),
                    ("apply_approved_patch",))
        for row in cur.fetchall():
            arguments = json.loads(row[0] or "{}")
            if str(arguments.get("source_investigation_id") or "") == investigation_id:
                conn.rollback(); cur.close()
                raise ValueError("developer_approval_replayed")
        approved_at = now or _now()
        approval_id = "devapproval_" + uuid.uuid4().hex
        job_id = "devjob_" + uuid.uuid4().hex
        arguments = {
            "approval_id": approval_id,
            "source_investigation_id": investigation_id,
            "diff_hash": calculated_hash,
            "patch": patch,
            "affected_files": paths,
            "expected_source_hashes": hashes,
            "validation": validation if isinstance(validation, dict) else {},
            "approved_at": _iso(approved_at),
            "expires_at": _iso(approved_at + timedelta(minutes=10)),
            "owner_identity": str(owner_identity or "platform_admin")[:80],
            "one_time": True,
        }
        cur.execute(_sql("INSERT INTO nina_developer_jobs (job_id,operation,arguments_json,status,result_json,error_code,created_at,claimed_at,completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"),
                    (job_id, "apply_approved_patch", json.dumps(arguments, separators=(",", ":")),
                     "pending", "{}", "", _iso(approved_at), "", ""))
        _event(cur, "approval_created", job_id, {"approval_id": approval_id,
                                                  "diff_hash": calculated_hash,
                                                  "files": paths})
        conn.commit(); cur.close()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
    return {"approval_id": approval_id, "job_id": job_id, "diff_hash": calculated_hash}


def write_access_status():
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT status FROM nina_developer_jobs WHERE operation=%s ORDER BY created_at DESC,job_id DESC LIMIT 1"),
                    ("apply_approved_patch",))
        row = cur.fetchone(); cur.close()
    finally:
        conn.close()
    return "one_time_approved" if row and row[0] in {"pending", "claimed"} else "disabled"


def claim_job():
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        try:
            query = "SELECT job_id,operation,arguments_json FROM nina_developer_jobs WHERE status=%s ORDER BY created_at,job_id LIMIT 1"
            if persistence_backend.USE_POSTGRES:
                query += " FOR UPDATE SKIP LOCKED"
            cur.execute(_sql(query), ("pending",))
            row = cur.fetchone()
            if not row:
                conn.commit(); cur.close(); return None
            cur.execute(_sql("UPDATE nina_developer_jobs SET status=%s,claimed_at=%s WHERE job_id=%s AND status=%s"),
                        ("claimed", _iso(), row[0], "pending"))
            if cur.rowcount != 1:
                conn.rollback(); cur.close(); return None
            _event(cur, "job_claimed", row[0], {"operation": row[1]})
            conn.commit(); cur.close()
            return {"job_id": row[0], "operation": row[1], "arguments": json.loads(row[2] or "{}")}
        except Exception:
            conn.rollback(); raise
    finally:
        conn.close()


def complete_job(job_id, result=None, error_code=""):
    safe_result = result if isinstance(result, dict) else {}
    encoded = json.dumps(safe_result, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 256 * 1024:
        encoded, error_code = "{}", "result_too_large"
    status = "failed" if error_code else "completed"
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("UPDATE nina_developer_jobs SET status=%s,result_json=%s,error_code=%s,completed_at=%s WHERE job_id=%s AND status=%s"),
                    (status, encoded, str(error_code)[:80], _iso(), str(job_id), "claimed"))
        if cur.rowcount != 1:
            conn.rollback(); cur.close(); return False
        _event(cur, "job_" + status, str(job_id), {"error_code": str(error_code)[:80]})
        conn.commit(); cur.close(); return True
    finally:
        conn.close()


def list_jobs(limit=10):
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT job_id,operation,status,result_json,error_code,created_at,arguments_json FROM nina_developer_jobs ORDER BY created_at DESC,job_id DESC LIMIT %s"), (max(1, min(int(limit), 25)),))
        rows = cur.fetchall(); cur.close()
    finally:
        conn.close()
    return [{"job_id": r[0], "operation": r[1], "status": r[2],
             "result": json.loads(r[3] or "{}"), "error_code": r[4], "created_at": r[5],
             "arguments": json.loads(r[6] or "{}")} for r in rows]
