"""Tenant-scoped Knowledge Vault V1 under the ONE NINA architecture."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend


TABLE_NAME = "nina_knowledge_items"
SOURCE_TYPES = frozenset({"text", "note", "document", "url_reference", "structured_data"})
CONTENT_FORMATS = frozenset({"plain_text", "markdown", "json"})
STATUSES = frozenset({"draft", "active", "archived"})
MAX_CONTENT_BYTES = 64 * 1024
MAX_METADATA_BYTES = 8 * 1024
MAX_METADATA_DEPTH = 4
MAX_LIST_LIMIT = 100
DEFAULT_LIST_LIMIT = 50
MAX_OFFSET = 100_000
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_KEYS = {
    "api_key", "apikey", "access_token", "refresh_token", "token", "password",
    "passwd", "credential", "credentials", "secret", "private_key",
    "system_prompt", "prompt_override",
}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|password|passwd|secret)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
)
_ACTIVE_CONTENT_PATTERN = re.compile(
    r"<\s*[A-Za-z][^>]*>|javascript\s*:", re.IGNORECASE
)


class KnowledgeVaultError(RuntimeError):
    pass


class KnowledgeVaultValidationError(KnowledgeVaultError):
    pass


class KnowledgeVaultNotFoundError(KnowledgeVaultError):
    pass


class KnowledgeVaultTransitionError(KnowledgeVaultError):
    pass


class KnowledgeVaultConflictError(KnowledgeVaultError):
    pass


class KnowledgeVaultPersistenceError(KnowledgeVaultError):
    pass


@dataclass(frozen=True)
class KnowledgeItem:
    knowledge_id: str
    tenant_id: str
    title: str
    source_type: str
    status: str
    content: str
    content_format: str
    source_name: str
    version: int
    checksum: str
    metadata: dict
    created_by: str
    created_at: str
    updated_at: str
    activated_at: str
    archived_at: str
    parent_version: int | None

    def as_dict(self, include_content=True):
        value = {
            "id": self.knowledge_id,
            "title": self.title,
            "source_type": self.source_type,
            "status": self.status,
            "content_format": self.content_format,
            "source_name": self.source_name,
            "version": self.version,
            "checksum": self.checksum,
            "metadata": dict(self.metadata),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "activated_at": self.activated_at,
            "archived_at": self.archived_at,
            "parent_version": self.parent_version,
        }
        if include_content:
            value["content"] = self.content
        return value


def _sql(statement):
    return persistence_backend.sql(statement)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field, *, required=False, maximum=512):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise KnowledgeVaultValidationError(f"knowledge_{field}_invalid")
    value = value.strip()
    if required and not value:
        raise KnowledgeVaultValidationError(f"knowledge_{field}_required")
    if len(value) > maximum:
        raise KnowledgeVaultValidationError(f"knowledge_{field}_too_long")
    return value


def _identifier(value, field):
    value = _text(value, field, required=True, maximum=128)
    if not _IDENTIFIER_RE.fullmatch(value):
        raise KnowledgeVaultValidationError(f"knowledge_{field}_invalid")
    return value


def _enum(value, field, allowed):
    value = _text(value, field, required=True, maximum=64)
    if value not in allowed:
        raise KnowledgeVaultValidationError(f"knowledge_{field}_invalid")
    return value


def _validate_tree(value, depth=0, path="metadata"):
    if depth > MAX_METADATA_DEPTH:
        raise KnowledgeVaultValidationError("knowledge_metadata_too_deep")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise KnowledgeVaultValidationError("knowledge_metadata_key_invalid")
            normalized = key.casefold().replace("-", "_").replace(" ", "_")
            if normalized in _SENSITIVE_KEYS:
                raise KnowledgeVaultValidationError(
                    f"knowledge_sensitive_field_forbidden:{path}.{key}"
                )
            _validate_tree(child, depth + 1, f"{path}.{key}")
    elif isinstance(value, list):
        if len(value) > 100:
            raise KnowledgeVaultValidationError("knowledge_metadata_list_too_large")
        for index, child in enumerate(value):
            _validate_tree(child, depth + 1, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise KnowledgeVaultValidationError("knowledge_metadata_not_json_safe")
    elif isinstance(value, str) and len(value) > 2000:
        raise KnowledgeVaultValidationError("knowledge_metadata_value_too_long")


def _validated_metadata(value):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise KnowledgeVaultValidationError("knowledge_metadata_must_be_object")
    _validate_tree(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise KnowledgeVaultValidationError("knowledge_metadata_not_json_safe") from exc
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise KnowledgeVaultValidationError("knowledge_metadata_too_large")
    return json.loads(encoded), encoded


def _validated_content(value, content_format):
    if not isinstance(value, str):
        raise KnowledgeVaultValidationError("knowledge_content_invalid")
    content = value.strip()
    if not content:
        raise KnowledgeVaultValidationError("knowledge_content_required")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise KnowledgeVaultValidationError("knowledge_content_too_large")
    if _ACTIVE_CONTENT_PATTERN.search(content):
        raise KnowledgeVaultValidationError("knowledge_active_content_forbidden")
    if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
        raise KnowledgeVaultValidationError("knowledge_secret_content_forbidden")
    if content_format == "json":
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError) as exc:
            raise KnowledgeVaultValidationError("knowledge_json_content_invalid") from exc
        _validate_tree(parsed, path="content")
        content = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return content


def _checksum(content, content_format):
    return hashlib.sha256(f"{content_format}\n{content}".encode("utf-8")).hexdigest()


_SELECT_COLUMNS = """
knowledge_id,tenant_id,title,source_type,status,content,content_format,
source_name,version,checksum,metadata_json,created_by,created_at,updated_at,
activated_at,archived_at,parent_version
"""


def _from_row(row):
    return KnowledgeItem(
        str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]),
        str(row[5]), str(row[6]), str(row[7]), int(row[8]), str(row[9]),
        json.loads(row[10] or "{}"), str(row[11]), str(row[12]), str(row[13]),
        str(row[14] or ""), str(row[15] or ""),
        None if row[16] is None else int(row[16]),
    )


def create_knowledge_item(
    tenant_id, *, title, source_type, content, content_format,
    source_name="", metadata=None, created_by="workspace_client",
):
    tenant = _identifier(tenant_id, "tenant_id")
    title = _text(title, "title", required=True, maximum=300)
    source_type = _enum(source_type, "source_type", SOURCE_TYPES)
    content_format = _enum(content_format, "content_format", CONTENT_FORMATS)
    content = _validated_content(content, content_format)
    source_name = _text(source_name, "source_name", maximum=500)
    _, metadata_json = _validated_metadata(metadata)
    actor = _text(created_by, "created_by", required=True, maximum=128)
    knowledge_id = "kno_" + secrets.token_hex(16)
    now = _now()
    checksum = _checksum(content, content_format)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            INSERT INTO {TABLE_NAME} (
                knowledge_id,tenant_id,title,source_type,status,content,
                content_format,source_name,version,checksum,metadata_json,
                created_by,created_at,updated_at,activated_at,archived_at,
                parent_version
            ) VALUES (%s,%s,%s,%s,'draft',%s,%s,%s,1,%s,%s,%s,%s,%s,'','',%s)
        """), (
            knowledge_id, tenant, title, source_type, content, content_format,
            source_name, checksum, metadata_json, actor, now, now, None,
        ))
        conn.commit()
        cur.close()
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(
            f"knowledge_create_failed:{type(exc).__name__}"
        ) from exc
    finally:
        conn.close()
    return get_knowledge_item(tenant, knowledge_id)


def get_knowledge_item(tenant_id, knowledge_id, version=None):
    tenant = _identifier(tenant_id, "tenant_id")
    identifier = _identifier(knowledge_id, "id")
    params = [tenant, identifier]
    version_sql = ""
    if version is not None:
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise KnowledgeVaultValidationError("knowledge_version_invalid")
        version_sql = " AND version=%s"
        params.append(version)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME}
            WHERE tenant_id=%s AND knowledge_id=%s{version_sql}
            ORDER BY version DESC LIMIT 1
        """), tuple(params))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise KnowledgeVaultNotFoundError("knowledge_item_not_found")
    return _from_row(row)


def list_knowledge_versions(tenant_id, knowledge_id):
    tenant = _identifier(tenant_id, "tenant_id")
    identifier = _identifier(knowledge_id, "id")
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME}
            WHERE tenant_id=%s AND knowledge_id=%s ORDER BY version DESC
        """), (tenant, identifier))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    if not rows:
        raise KnowledgeVaultNotFoundError("knowledge_item_not_found")
    return tuple(_from_row(row) for row in rows)


def _pagination(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIST_LIMIT:
        raise KnowledgeVaultValidationError("knowledge_limit_invalid")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= MAX_OFFSET:
        raise KnowledgeVaultValidationError("knowledge_offset_invalid")
    return limit, offset


def list_tenant_knowledge(
    tenant_id, *, status=None, source_type=None, query=None,
    limit=DEFAULT_LIST_LIMIT, offset=0,
):
    tenant = _identifier(tenant_id, "tenant_id")
    limit, offset = _pagination(limit, offset)
    clauses = [
        "tenant_id=%s",
        "version=(SELECT MAX(v.version) FROM nina_knowledge_items v "
        "WHERE v.tenant_id=nina_knowledge_items.tenant_id "
        "AND v.knowledge_id=nina_knowledge_items.knowledge_id)",
    ]
    params = [tenant]
    if status is not None:
        clauses.append("status=%s")
        params.append(_enum(status, "status", STATUSES))
    if source_type is not None:
        clauses.append("source_type=%s")
        params.append(_enum(source_type, "source_type", SOURCE_TYPES))
    if query is not None:
        query = _text(query, "query", required=True, maximum=200)
        escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append(
            "(LOWER(title) LIKE %s ESCAPE '\\' OR LOWER(source_name) LIKE %s ESCAPE '\\' "
            "OR LOWER(content) LIKE %s ESCAPE '\\' OR LOWER(metadata_json) LIKE %s ESCAPE '\\')"
        )
        pattern = f"%{escaped}%"
        params.extend([pattern] * 4)
    params.extend([limit, offset])
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_SELECT_COLUMNS} FROM {TABLE_NAME}
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC,knowledge_id LIMIT %s OFFSET %s
        """), tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_from_row(row) for row in rows)


def update_draft(
    tenant_id, knowledge_id, *, title=None, source_type=None, content=None,
    content_format=None, source_name=None, metadata=None,
):
    current = get_knowledge_item(tenant_id, knowledge_id)
    if current.status != "draft":
        raise KnowledgeVaultConflictError("knowledge_draft_update_required")
    title = current.title if title is None else _text(title, "title", required=True, maximum=300)
    source_type = current.source_type if source_type is None else _enum(source_type, "source_type", SOURCE_TYPES)
    selected_format = current.content_format if content_format is None else _enum(content_format, "content_format", CONTENT_FORMATS)
    selected_content = _validated_content(current.content if content is None else content, selected_format)
    source_name = current.source_name if source_name is None else _text(source_name, "source_name", maximum=500)
    _, metadata_json = _validated_metadata(current.metadata if metadata is None else metadata)
    checksum = _checksum(selected_content, selected_format)
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME}
            SET title=%s,source_type=%s,content=%s,content_format=%s,
                source_name=%s,metadata_json=%s,checksum=%s,updated_at=%s
            WHERE tenant_id=%s AND knowledge_id=%s AND version=%s AND status='draft'
        """), (
            title, source_type, selected_content, selected_format, source_name,
            metadata_json, checksum, now, current.tenant_id,
            current.knowledge_id, current.version,
        ))
        if cur.rowcount != 1:
            raise KnowledgeVaultConflictError("knowledge_update_conflict")
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(f"knowledge_update_failed:{type(exc).__name__}") from exc
    finally:
        conn.close()
    return get_knowledge_item(current.tenant_id, current.knowledge_id)


def _transition(tenant_id, knowledge_id, target):
    current = get_knowledge_item(tenant_id, knowledge_id)
    if (current.status, target) not in {
        ("draft", "active"), ("draft", "archived"), ("active", "archived"),
    }:
        raise KnowledgeVaultTransitionError(
            f"knowledge_transition_invalid:{current.status}:{target}"
        )
    now = _now()
    activated = now if target == "active" else current.activated_at
    archived = now if target == "archived" else current.archived_at
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME}
            SET status=%s,updated_at=%s,activated_at=%s,archived_at=%s
            WHERE tenant_id=%s AND knowledge_id=%s AND version=%s AND status=%s
        """), (
            target, now, activated, archived, current.tenant_id,
            current.knowledge_id, current.version, current.status,
        ))
        if cur.rowcount != 1:
            raise KnowledgeVaultConflictError("knowledge_transition_conflict")
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(f"knowledge_transition_failed:{type(exc).__name__}") from exc
    finally:
        conn.close()
    return get_knowledge_item(current.tenant_id, current.knowledge_id)


def activate_knowledge_item(tenant_id, knowledge_id):
    return _transition(tenant_id, knowledge_id, "active")


def archive_knowledge_item(tenant_id, knowledge_id):
    return _transition(tenant_id, knowledge_id, "archived")


def create_knowledge_version(
    tenant_id, knowledge_id, *, content, content_format=None, title=None,
    source_type=None, source_name=None, metadata=None,
    created_by="workspace_client",
):
    current = get_knowledge_item(tenant_id, knowledge_id)
    if current.status != "active":
        raise KnowledgeVaultConflictError("knowledge_active_version_required")
    title = current.title if title is None else _text(title, "title", required=True, maximum=300)
    source_type = current.source_type if source_type is None else _enum(source_type, "source_type", SOURCE_TYPES)
    selected_format = current.content_format if content_format is None else _enum(content_format, "content_format", CONTENT_FORMATS)
    selected_content = _validated_content(content, selected_format)
    source_name = current.source_name if source_name is None else _text(source_name, "source_name", maximum=500)
    _, metadata_json = _validated_metadata(current.metadata if metadata is None else metadata)
    actor = _text(created_by, "created_by", required=True, maximum=128)
    checksum = _checksum(selected_content, selected_format)
    if checksum == current.checksum:
        raise KnowledgeVaultConflictError("knowledge_content_unchanged")
    next_version = current.version + 1
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET status='archived',updated_at=%s,archived_at=%s
            WHERE tenant_id=%s AND knowledge_id=%s AND version=%s AND status='active'
        """), (now, now, current.tenant_id, current.knowledge_id, current.version))
        if cur.rowcount != 1:
            raise KnowledgeVaultConflictError("knowledge_version_conflict")
        cur.execute(_sql(f"""
            INSERT INTO {TABLE_NAME} (
                knowledge_id,tenant_id,title,source_type,status,content,
                content_format,source_name,version,checksum,metadata_json,
                created_by,created_at,updated_at,activated_at,archived_at,parent_version
            ) VALUES (%s,%s,%s,%s,'active',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'',%s)
        """), (
            current.knowledge_id, current.tenant_id, title, source_type,
            selected_content, selected_format, source_name, next_version,
            checksum, metadata_json, actor, now, now, now, current.version,
        ))
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(f"knowledge_version_failed:{type(exc).__name__}") from exc
    finally:
        conn.close()
    return get_knowledge_item(current.tenant_id, current.knowledge_id)


def initialize_knowledge_vault():
    persistence_backend.assert_backend_ready()
    return True


def persistence_health():
    return initialize_knowledge_vault()
