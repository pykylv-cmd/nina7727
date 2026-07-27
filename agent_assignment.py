"""Tenant-scoped Agent Assignment V1 under the ONE NINA architecture."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType

import persistence_backend
from ready_worker_catalog import (
    ReadyWorkerNotFoundError,
    get_ready_worker,
    initialize_ready_worker_catalog,
)


AGENT_ASSIGNMENT_VERSION = "1.0"
TABLE_NAME = "nina_agent_assignments"
STATUSES = frozenset({"draft", "active", "suspended", "archived"})
TRANSITIONS = MappingProxyType({
    "draft": frozenset({"active", "archived"}),
    "active": frozenset({"suspended", "archived"}),
    "suspended": frozenset({"active", "archived"}),
    "archived": frozenset(),
})
CONFIGURATION_KEYS = frozenset({"language", "timezone", "approval_mode"})
PERMISSION_KEYS = frozenset({
    "allowed_tools",
    "allowed_work_object_types",
    "requires_human_approval",
})
APPROVAL_MODES = frozenset({
    "definition_default",
    "always",
    "required_for_external_actions",
})
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{1,127}$")
_LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
_TIMEZONE_RE = re.compile(r"^[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*$")
_SECRET_TERMS = frozenset({
    "secret", "token", "password", "credential", "api_key", "apikey",
    "private_key", "prompt", "code",
})


class AgentAssignmentError(RuntimeError):
    pass


class AgentAssignmentValidationError(AgentAssignmentError):
    pass


class AgentAssignmentNotFoundError(AgentAssignmentError):
    pass


class AgentAssignmentTransitionError(AgentAssignmentError):
    pass


class AgentAssignmentConflictError(AgentAssignmentError):
    pass


class AgentAssignmentPersistenceError(AgentAssignmentError):
    pass


@dataclass(frozen=True)
class AgentAssignment:
    assignment_id: str
    tenant_id: str
    ready_worker_definition_id: str
    definition_version: str
    primary_rolepack_id: str
    display_name: str
    status: str
    configuration: object
    permissions: object
    assigned_by: str
    created_at: str
    updated_at: str
    activated_at: str
    suspended_at: str
    archived_at: str

    def as_dict(self):
        return {
            "id": self.assignment_id,
            "tenant_id": self.tenant_id,
            "ready_worker_definition_id": self.ready_worker_definition_id,
            "definition_version": self.definition_version,
            "primary_rolepack_id": self.primary_rolepack_id,
            "display_name": self.display_name,
            "status": self.status,
            "configuration": dict(self.configuration),
            "permissions": {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in self.permissions.items()
            },
            "assigned_by": self.assigned_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "activated_at": self.activated_at,
            "suspended_at": self.suspended_at,
            "archived_at": self.archived_at,
        }


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sql(statement):
    return persistence_backend.sql(statement)


def _connect():
    return persistence_backend.connect()


def _identifier(value, field):
    clean = str(value or "").strip()
    if not _ID_RE.fullmatch(clean):
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_invalid"
        )
    return clean


def _text(value, field, maximum=160, required=False):
    clean = str(value or "").strip()
    if required and not clean:
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_required"
        )
    if len(clean) > maximum:
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_too_long"
        )
    return clean


def _json_mapping(value, field):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_must_be_object"
        )
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
    except (TypeError, ValueError) as exc:
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_not_json_safe"
        ) from exc
    if len(encoded.encode("utf-8")) > 8192:
        raise AgentAssignmentValidationError(
            f"agent_assignment_{field}_too_large"
        )
    return dict(value)


def _reject_sensitive(value, path="configuration"):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if any(term in normalized for term in _SECRET_TERMS):
                raise AgentAssignmentValidationError(
                    f"agent_assignment_sensitive_field_forbidden:{path}.{key}"
                )
            _reject_sensitive(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_sensitive(item, f"{path}.{index}")
    elif isinstance(value, str) and len(value) > 512:
        raise AgentAssignmentValidationError(
            f"agent_assignment_text_value_too_long:{path}"
        )


def validate_configuration(value):
    source = _json_mapping(value, "configuration")
    unknown = set(source) - CONFIGURATION_KEYS
    if unknown:
        raise AgentAssignmentValidationError(
            "agent_assignment_configuration_field_forbidden:"
            + sorted(unknown)[0]
        )
    _reject_sensitive(source)
    result = {}
    if "language" in source:
        language = str(source["language"] or "").strip()
        if not _LANGUAGE_RE.fullmatch(language):
            raise AgentAssignmentValidationError(
                "agent_assignment_language_invalid"
            )
        result["language"] = language
    if "timezone" in source:
        timezone_name = str(source["timezone"] or "").strip()
        if (
            not timezone_name
            or len(timezone_name) > 64
            or not _TIMEZONE_RE.fullmatch(timezone_name)
        ):
            raise AgentAssignmentValidationError(
                "agent_assignment_timezone_invalid"
            )
        result["timezone"] = timezone_name
    if "approval_mode" in source:
        mode = str(source["approval_mode"] or "").strip()
        if mode not in APPROVAL_MODES:
            raise AgentAssignmentValidationError(
                "agent_assignment_approval_mode_invalid"
            )
        result["approval_mode"] = mode
    return result


def validate_permissions(value, definition):
    source = _json_mapping(value, "permissions")
    unknown = set(source) - PERMISSION_KEYS
    if unknown:
        raise AgentAssignmentValidationError(
            "agent_assignment_permission_field_forbidden:"
            + sorted(unknown)[0]
        )
    _reject_sensitive(source, "permissions")
    result = {}
    subset_fields = (
        ("allowed_tools", set(definition.allowed_tools)),
        (
            "allowed_work_object_types",
            set(definition.supported_work_object_types),
        ),
    )
    for field, permitted in subset_fields:
        if field not in source:
            continue
        values = source[field]
        if not isinstance(values, (list, tuple)):
            raise AgentAssignmentValidationError(
                f"agent_assignment_{field}_must_be_list"
            )
        normalized = tuple(str(item or "").strip() for item in values)
        if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
            raise AgentAssignmentValidationError(
                f"agent_assignment_{field}_invalid"
            )
        if not set(normalized).issubset(permitted):
            raise AgentAssignmentValidationError(
                f"agent_assignment_{field}_broadens_definition"
            )
        result[field] = normalized
    if "requires_human_approval" in source:
        if source["requires_human_approval"] is not True:
            raise AgentAssignmentValidationError(
                "agent_assignment_human_approval_may_only_be_strengthened"
            )
        result["requires_human_approval"] = True
    return result


def _definition(worker_id, version):
    try:
        definition = get_ready_worker(worker_id, version)
    except ReadyWorkerNotFoundError as exc:
        raise AgentAssignmentValidationError(
            "agent_assignment_ready_worker_not_found"
        ) from exc
    if not definition.enabled:
        raise AgentAssignmentValidationError(
            "agent_assignment_ready_worker_disabled"
        )
    return definition


def _row(row):
    if not row:
        return None
    configuration = json.loads(row[7] or "{}")
    permissions = json.loads(row[8] or "{}")
    for key in ("allowed_tools", "allowed_work_object_types"):
        if key in permissions:
            permissions[key] = tuple(permissions[key])
    return AgentAssignment(
        assignment_id=str(row[0]),
        tenant_id=str(row[1]),
        ready_worker_definition_id=str(row[2]),
        definition_version=str(row[3]),
        primary_rolepack_id=str(row[4]),
        display_name=str(row[5]),
        status=str(row[6]),
        configuration=MappingProxyType(configuration),
        permissions=MappingProxyType(permissions),
        assigned_by=str(row[9] or ""),
        created_at=str(row[10] or ""),
        updated_at=str(row[11] or ""),
        activated_at=str(row[12] or ""),
        suspended_at=str(row[13] or ""),
        archived_at=str(row[14] or ""),
    )


_SELECT = """
assignment_id,tenant_id,ready_worker_definition_id,definition_version,
primary_rolepack_id,display_name,status,configuration_json,permissions_json,
assigned_by,created_at,updated_at,activated_at,suspended_at,archived_at
"""


def create_assignment(
    tenant_id,
    ready_worker_definition_id,
    definition_version=None,
    display_name="",
    configuration=None,
    permissions=None,
    assigned_by="",
):
    tenant = _identifier(tenant_id, "tenant_id")
    worker_id = _identifier(
        ready_worker_definition_id, "ready_worker_definition_id"
    )
    definition = _definition(worker_id, definition_version)
    config = validate_configuration(configuration)
    permission_values = validate_permissions(permissions, definition)
    name = _text(display_name, "display_name") or definition.name
    actor = _text(assigned_by, "assigned_by", maximum=128)
    assignment_id = "asg_" + secrets.token_hex(16)
    now = _now()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(f"""
                INSERT INTO {TABLE_NAME} (
                    assignment_id,tenant_id,ready_worker_definition_id,
                    definition_version,primary_rolepack_id,display_name,status,
                    configuration_json,permissions_json,assigned_by,
                    created_at,updated_at,activated_at,suspended_at,archived_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """),
            (
                assignment_id, tenant, definition.worker_id,
                definition.version, definition.primary_rolepack_id, name,
                "draft",
                json.dumps(config, ensure_ascii=False, separators=(",", ":")),
                json.dumps(
                    {
                        key: list(value) if isinstance(value, tuple) else value
                        for key, value in permission_values.items()
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                actor, now, now, "", "", "",
            ),
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        conn.rollback()
        if isinstance(exc, AgentAssignmentError):
            raise
        raise AgentAssignmentPersistenceError(
            f"agent_assignment_create_failed:{type(exc).__name__}"
        ) from exc
    finally:
        conn.close()
    return get_assignment(tenant, assignment_id)


def get_assignment(tenant_id, assignment_id):
    tenant = _identifier(tenant_id, "tenant_id")
    identifier = _identifier(assignment_id, "id")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(f"SELECT {_SELECT} FROM {TABLE_NAME} "
                 "WHERE tenant_id=%s AND assignment_id=%s"),
            (tenant, identifier),
        )
        result = _row(cur.fetchone())
        cur.close()
    finally:
        conn.close()
    if result is None:
        raise AgentAssignmentNotFoundError("agent_assignment_not_found")
    return result


def list_tenant_assignments(tenant_id, status=None, limit=200):
    tenant = _identifier(tenant_id, "tenant_id")
    clean_status = str(status or "").strip()
    if clean_status and clean_status not in STATUSES:
        raise AgentAssignmentValidationError(
            "agent_assignment_status_invalid"
        )
    try:
        selected_limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError) as exc:
        raise AgentAssignmentValidationError(
            "agent_assignment_limit_invalid"
        ) from exc
    where = "tenant_id=%s"
    params = [tenant]
    if clean_status:
        where += " AND status=%s"
        params.append(clean_status)
    params.append(selected_limit)
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(f"SELECT {_SELECT} FROM {TABLE_NAME} WHERE {where} "
                 "ORDER BY created_at,assignment_id LIMIT %s"),
            tuple(params),
        )
        results = tuple(_row(row) for row in cur.fetchall())
        cur.close()
        return results
    finally:
        conn.close()


def update_assignment(
    tenant_id,
    assignment_id,
    *,
    display_name=None,
    configuration=None,
    permissions=None,
):
    current = get_assignment(tenant_id, assignment_id)
    if current.status == "archived":
        raise AgentAssignmentConflictError(
            "agent_assignment_archived_immutable"
        )
    definition = _definition(
        current.ready_worker_definition_id, current.definition_version
    )
    name = (
        current.display_name
        if display_name is None
        else _text(display_name, "display_name", required=True)
    )
    config = (
        dict(current.configuration)
        if configuration is None
        else validate_configuration(configuration)
    )
    permission_values = (
        dict(current.permissions)
        if permissions is None
        else validate_permissions(permissions, definition)
    )
    now = _now()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(f"""
                UPDATE {TABLE_NAME}
                SET display_name=%s,configuration_json=%s,
                    permissions_json=%s,updated_at=%s
                WHERE tenant_id=%s AND assignment_id=%s AND status<>%s
            """),
            (
                name,
                json.dumps(config, ensure_ascii=False, separators=(",", ":")),
                json.dumps(
                    {
                        key: list(value) if isinstance(value, tuple) else value
                        for key, value in permission_values.items()
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                now, current.tenant_id, current.assignment_id, "archived",
            ),
        )
        if cur.rowcount != 1:
            raise AgentAssignmentConflictError(
                "agent_assignment_update_conflict"
            )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_assignment(current.tenant_id, current.assignment_id)


def transition_assignment(tenant_id, assignment_id, target_status):
    current = get_assignment(tenant_id, assignment_id)
    target = str(target_status or "").strip()
    if target not in STATUSES or target not in TRANSITIONS[current.status]:
        raise AgentAssignmentTransitionError(
            f"agent_assignment_transition_invalid:{current.status}:{target}"
        )
    now = _now()
    timestamps = {
        "activated_at": current.activated_at,
        "suspended_at": current.suspended_at,
        "archived_at": current.archived_at,
    }
    if target == "active":
        timestamps["activated_at"] = now
    elif target == "suspended":
        timestamps["suspended_at"] = now
    elif target == "archived":
        timestamps["archived_at"] = now
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            _sql(f"""
                UPDATE {TABLE_NAME}
                SET status=%s,updated_at=%s,activated_at=%s,
                    suspended_at=%s,archived_at=%s
                WHERE tenant_id=%s AND assignment_id=%s AND status=%s
            """),
            (
                target, now, timestamps["activated_at"],
                timestamps["suspended_at"], timestamps["archived_at"],
                current.tenant_id, current.assignment_id, current.status,
            ),
        )
        if cur.rowcount != 1:
            raise AgentAssignmentConflictError(
                "agent_assignment_transition_conflict"
            )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return get_assignment(current.tenant_id, current.assignment_id)


def activate_assignment(tenant_id, assignment_id):
    return transition_assignment(tenant_id, assignment_id, "active")


def suspend_assignment(tenant_id, assignment_id):
    return transition_assignment(tenant_id, assignment_id, "suspended")


def archive_assignment(tenant_id, assignment_id):
    return transition_assignment(tenant_id, assignment_id, "archived")


def initialize_agent_assignment_service():
    initialize_ready_worker_catalog()
    return True


def persistence_health():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {TABLE_NAME} LIMIT 1")
        cur.fetchone()
        cur.close()
        return {"ok": True, "version": AGENT_ASSIGNMENT_VERSION}
    except Exception as exc:
        return {
            "ok": False,
            "version": AGENT_ASSIGNMENT_VERSION,
            "error": type(exc).__name__,
        }
    finally:
        conn.close()
