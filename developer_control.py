"""Persistent control plane for the owner-only read-only Developer capability."""

from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import persistence_backend

AGENT_ID = "ninaos_owner_windows"
ALLOWED_OPERATIONS = frozenset({
    "list_root", "list_directory", "read_text_file", "search_text", "git_status",
    "apply_approved_patch", "execute_approved_release",
})
RELEASE_BRANCH = "feature/web-chat-v1"
RELEASE_OPERATIONS = frozenset({"execute_approved_release"})
VERIFIED_LESSON_OUTCOMES = frozenset({
    "successful_patch_tests", "failed_validation_rollback", "production_regression",
    "rejected_quality_review", "owner_rejection", "successful_production_live_proof",
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


def record_verified_lesson(outcome_type, lesson, source_ids, now=None):
    outcome_type = str(outcome_type or "")
    lesson = lesson if isinstance(lesson, dict) else {}
    source_ids = source_ids if isinstance(source_ids, dict) else {}
    if outcome_type not in VERIFIED_LESSON_OUTCOMES:
        raise ValueError("developer_lesson_outcome_unverified")
    required = ("problem_pattern", "root_cause", "attempted_solution", "outcome", "architecture_rule")
    if any(not str(lesson.get(field) or "").strip() for field in required):
        raise ValueError("developer_lesson_evidence_incomplete")
    allowed_sources = ("developer_job_id", "approval_id", "release_id")
    sources = {key: str(source_ids.get(key) or "").strip()[:120] for key in allowed_sources}
    if not any(sources.values()):
        raise ValueError("developer_lesson_source_required")
    affected_modules = sorted({str(value).strip()[:240] for value in (lesson.get("affected_modules") or [])
                               if str(value).strip()})
    tests = sorted({str(value).strip()[:240] for value in (lesson.get("tests_that_caught_it") or [])
                    if str(value).strip()})
    regression_risk = str(lesson.get("regression_risk") or "MEDIUM").upper()
    if regression_risk not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("developer_lesson_risk_invalid")
    if outcome_type == "failed_validation_rollback" and not str(lesson.get("failure_reason") or "").strip():
        raise ValueError("developer_lesson_failure_reason_required")
    if outcome_type in {"successful_patch_tests", "successful_production_live_proof"} \
            and not str(lesson.get("successful_pattern") or "").strip():
        raise ValueError("developer_lesson_success_pattern_required")
    identity_source = json.dumps({"outcome_type": outcome_type, "sources": sources,
                                  "problem_pattern": lesson["problem_pattern"]}, sort_keys=True)
    lesson_id = "devlesson_" + hashlib.sha256(identity_source.encode("utf-8")).hexdigest()[:32]
    metadata = {
        "lesson_id": lesson_id,
        "verification_type": outcome_type,
        "problem_pattern": str(lesson["problem_pattern"]).strip()[:1000],
        "affected_modules": affected_modules,
        "root_cause": str(lesson["root_cause"]).strip()[:3000],
        "attempted_solution": str(lesson["attempted_solution"]).strip()[:3000],
        "outcome": str(lesson["outcome"]).strip()[:1000],
        "failure_reason": str(lesson.get("failure_reason") or "").strip()[:2000],
        "successful_pattern": str(lesson.get("successful_pattern") or "").strip()[:2000],
        "regression_risk": regression_risk,
        "tests_that_caught_it": tests,
        "architecture_rule": str(lesson["architecture_rule"]).strip()[:2000],
        "created_at": _iso(now),
        "source_ids": sources,
    }
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT safe_metadata_json FROM nina_developer_events WHERE agent_id=%s AND event_type=%s"),
                    (AGENT_ID, "developer_lesson_recorded"))
        for row in cur.fetchall():
            existing = json.loads(row[0] or "{}")
            if existing.get("lesson_id") == lesson_id:
                cur.close(); return existing
        _event(cur, "developer_lesson_recorded", sources["developer_job_id"], metadata)
        conn.commit(); cur.close()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
    return metadata


def retrieve_relevant_lessons(problem_pattern, affected_modules=None, limit=5):
    query_tokens = {token for token in re.findall(r"[a-z0-9_]{4,}", str(problem_pattern or "").casefold())}
    requested_modules = {str(value).replace("\\", "/").casefold()
                         for value in (affected_modules or []) if str(value).strip()}
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT safe_metadata_json FROM nina_developer_events WHERE agent_id=%s AND event_type=%s ORDER BY created_at DESC LIMIT %s"),
                    (AGENT_ID, "developer_lesson_recorded", 100))
        rows = cur.fetchall(); cur.close()
    finally:
        conn.close()
    ranked = []
    for row in rows:
        lesson = json.loads(row[0] or "{}")
        text = " ".join((str(lesson.get("problem_pattern") or ""),
                         str(lesson.get("root_cause") or ""),
                         str(lesson.get("architecture_rule") or ""))).casefold()
        lesson_tokens = set(re.findall(r"[a-z0-9_]{4,}", text))
        lesson_modules = {str(value).replace("\\", "/").casefold()
                          for value in (lesson.get("affected_modules") or [])}
        score = len(query_tokens & lesson_tokens) + 10 * len(requested_modules & lesson_modules)
        if score > 0:
            ranked.append((score, str(lesson.get("created_at") or ""), lesson))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:max(1, min(int(limit), 10))]]


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
                              now=None, lesson_context=None):
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
            "lesson_context": lesson_context if isinstance(lesson_context, dict) else {},
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


def select_release_services(paths):
    paths = {str(value).replace("\\", "/") for value in (paths or [])}
    if not paths:
        raise ValueError("developer_release_files_required")
    if any(path.startswith("../") or path.startswith("/") or path in {".env", "nina_memory.db"}
           for path in paths):
        raise ValueError("developer_release_file_not_allowed")
    production = {path for path in paths if not path.rsplit("/", 1)[-1].startswith("test_")}
    services = set()
    core_only = {"app.py"}
    shared = {"nina_message_service.py", "persistence_backend.py", "runtime_readiness.py"}
    if production & core_only:
        services.add("core")
    if production & shared:
        services.update({"web", "core"})
    if production - core_only - shared:
        services.add("web")
    if not services:
        services.add("web")
    return sorted(services)


def create_approved_release_job(source_patch_job_id, submitted_hash, branch, target_services,
                                owner_identity="platform_admin", now=None):
    if str(branch or "") != RELEASE_BRANCH:
        raise ValueError("developer_release_branch_not_allowed")
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        if persistence_backend.USE_POSTGRES:
            cur.execute(_sql("SELECT job_id FROM nina_developer_jobs WHERE job_id=%s FOR UPDATE"),
                        (str(source_patch_job_id),))
        else:
            cur.execute("BEGIN IMMEDIATE")
        cur.execute(_sql("SELECT status,result_json,arguments_json FROM nina_developer_jobs WHERE job_id=%s AND operation=%s"),
                    (str(source_patch_job_id), "apply_approved_patch"))
        row = cur.fetchone()
        if not row or row[0] != "completed":
            raise ValueError("developer_release_patch_not_ready")
        result, patch_arguments = json.loads(row[1] or "{}"), json.loads(row[2] or "{}")
        validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
        diff = str(validation.get("git_diff") or "")
        files = [str(value) for value in (result.get("applied_files") or [])]
        if not result.get("write_executed") or not diff or not validation.get("checks"):
            raise ValueError("developer_release_validation_required")
        quality = str((patch_arguments.get("lesson_context") or {}).get("quality_verdict") or "")
        if quality != "APPROVE FOR OWNER REVIEW":
            raise ValueError("developer_release_quality_not_approved")
        content_hash = hashlib.sha256(diff.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(content_hash, str(submitted_hash or "")):
            raise ValueError("developer_release_diff_changed")
        selected = select_release_services(files)
        if sorted({str(value) for value in (target_services or [])}) != selected:
            raise ValueError("developer_release_services_changed")
        cur.execute(_sql("SELECT arguments_json FROM nina_developer_jobs WHERE operation=%s"),
                    ("execute_approved_release",))
        if any(str(json.loads(item[0] or "{}").get("source_patch_job_id") or "") == str(source_patch_job_id)
               for item in cur.fetchall()):
            raise ValueError("developer_release_replayed")
        approved_at = now or _now()
        release_id = "devrelease_" + uuid.uuid4().hex
        job_id = "devjob_" + uuid.uuid4().hex
        arguments = {
            "release_id": release_id, "source_patch_job_id": str(source_patch_job_id),
            "content_hash": content_hash, "affected_files": files,
            "branch": RELEASE_BRANCH, "target_services": selected,
            "commit_message": "Nina Developer approved change",
            "quality_verdict": quality, "risk_level": "LOW",
            "tests": validation.get("checks") or [],
            "expected_deployment_impact": "Railway webhook redeploys only selected affected services.",
            "live_verification": "developer_console_safety",
            "approved_at": _iso(approved_at),
            "expires_at": _iso(approved_at + timedelta(minutes=10)),
            "owner_identity": str(owner_identity or "platform_admin")[:80], "one_time": True,
        }
        cur.execute(_sql("INSERT INTO nina_developer_jobs (job_id,operation,arguments_json,status,result_json,error_code,created_at,claimed_at,completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"),
                    (job_id, "execute_approved_release", json.dumps(arguments, separators=(",", ":")),
                     "pending", "{}", "", _iso(approved_at), "", ""))
        _event(cur, "release_approved", job_id, {
            "release_id": release_id, "content_hash": content_hash, "branch": RELEASE_BRANCH,
            "target_services": selected, "owner_identity": arguments["owner_identity"],
        })
        conn.commit(); cur.close()
        return {"release_id": release_id, "job_id": job_id, "content_hash": content_hash}
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def discard_release_candidate(source_patch_job_id, owner_identity="platform_admin"):
    ensure_schema(); conn = _connect()
    try:
        cur = conn.cursor()
        _event(cur, "release_discarded", str(source_patch_job_id), {
            "owner_identity": str(owner_identity or "platform_admin")[:80]
        })
        conn.commit(); cur.close()
    finally:
        conn.close()


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
    operation, arguments, accepted = "", {}, False
    try:
        cur = conn.cursor()
        cur.execute(_sql("SELECT operation,arguments_json FROM nina_developer_jobs WHERE job_id=%s AND status=%s"),
                    (str(job_id), "claimed"))
        row = cur.fetchone()
        if row:
            operation, arguments = str(row[0]), json.loads(row[1] or "{}")
        cur.execute(_sql("UPDATE nina_developer_jobs SET status=%s,result_json=%s,error_code=%s,completed_at=%s WHERE job_id=%s AND status=%s"),
                    (status, encoded, str(error_code)[:80], _iso(), str(job_id), "claimed"))
        if cur.rowcount != 1:
            conn.rollback(); cur.close(); return False
        _event(cur, "job_" + status, str(job_id), {"error_code": str(error_code)[:80]})
        conn.commit(); cur.close(); accepted = True
    finally:
        conn.close()
    context = arguments.get("lesson_context") if isinstance(arguments.get("lesson_context"), dict) else {}
    if accepted and operation in RELEASE_OPERATIONS:
        conn = _connect()
        try:
            cur = conn.cursor()
            _event(cur, "release_failed" if error_code else "release_verified", str(job_id), {
                "release_id": str(arguments.get("release_id") or ""),
                "failed_stage": str(safe_result.get("failed_stage") or error_code or "")[:80],
                "commit_sha": str(safe_result.get("commit_sha") or "")[:64],
            })
            conn.commit(); cur.close()
        finally:
            conn.close()
    if accepted and operation == "apply_approved_patch" and context:
        sources = {"developer_job_id": str(job_id),
                   "approval_id": str(arguments.get("approval_id") or "")}
        base = {
            "problem_pattern": context.get("problem_pattern"),
            "affected_modules": arguments.get("affected_files") or context.get("affected_modules") or [],
            "root_cause": context.get("root_cause"),
            "attempted_solution": context.get("attempted_solution"),
            "regression_risk": context.get("regression_risk") or "MEDIUM",
            "tests_that_caught_it": context.get("tests_that_caught_it") or [],
            "architecture_rule": context.get("architecture_rule"),
        }
        try:
            if not error_code and safe_result.get("write_executed") and safe_result.get("validation"):
                record_verified_lesson("successful_patch_tests", {
                    **base, "outcome": "Owner-approved patch applied and focused validation passed.",
                    "successful_pattern": context.get("successful_pattern") or context.get("attempted_solution"),
                }, sources)
            elif error_code and ("validation" in str(error_code).casefold()
                                 or "write_failure" in str(error_code).casefold()):
                record_verified_lesson("failed_validation_rollback", {
                    **base, "outcome": "Validation or controlled write failed; repository rollback completed.",
                    "failure_reason": str(error_code),
                }, sources)
        except ValueError:
            pass
    return accepted


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
