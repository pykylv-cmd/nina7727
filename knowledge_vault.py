"""Canonical workspace Knowledge Vault V1 for the ONE NINA architecture."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend


TABLE_NAME = "nina_knowledge_items"
VERSION_TABLE = "nina_knowledge_versions"
EVENT_TABLE = "nina_knowledge_events"
KNOWLEDGE_TYPES = frozenset({
    "FACT", "INSTRUCTION", "POLICY", "PROCEDURE",
    "PRODUCT", "SERVICE", "FAQ", "NOTE",
})
SOURCE_TYPES = frozenset({"MANUAL", "IMPORTED_TEXT", "SYSTEM"})
STATUSES = frozenset({"ACTIVE", "ARCHIVED"})
CONTENT_FORMATS = frozenset({"plain_text"})
DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100
MAX_CONTENT_BYTES = 64 * 1024
MAX_TAGS = 30
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SECRET = re.compile(
    r"(?:api[_ -]?key|access[_ -]?token|password|passwd|secret|"
    r"connection[_ -]?string)\s*[:=]\s*\S+|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{16,}",
    re.IGNORECASE,
)
_SOURCE_TO_STORAGE = {
    "MANUAL": "note",
    "IMPORTED_TEXT": "document",
    "SYSTEM": "structured_data",
}
_SOURCE_FROM_STORAGE = {
    value: key for key, value in _SOURCE_TO_STORAGE.items()
}


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
    workspace_id: str
    title: str
    content: str
    knowledge_type: str
    status: str
    source_type: str
    source_reference: str
    tags: tuple[str, ...]
    version: int
    content_checksum: str
    created_by: str
    updated_by: str
    created_at: str
    updated_at: str
    archived_at: str

    @property
    def tenant_id(self):
        return self.workspace_id

    @property
    def checksum(self):
        return self.content_checksum

    @property
    def source_name(self):
        return self.source_reference

    @property
    def metadata(self):
        return {"tags": list(self.tags)}

    @property
    def content_format(self):
        return "plain_text"

    @property
    def activated_at(self):
        return self.created_at

    @property
    def parent_version(self):
        return self.version - 1 if self.version > 1 else None

    def as_dict(self, include_content=True):
        result = {
            "id": self.knowledge_id,
            "knowledge_id": self.knowledge_id,
            "title": self.title,
            "knowledge_type": self.knowledge_type,
            "status": self.status,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "tags": list(self.tags),
            "version": self.version,
            "content_checksum": self.content_checksum,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived_at": self.archived_at,
        }
        if include_content:
            result["content"] = self.content
        return result


def _sql(value):
    return persistence_backend.sql(value)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field, *, required=False, maximum=500):
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


def _id(value, field="id"):
    value = _text(value, field, required=True, maximum=128)
    if not _IDENTIFIER.fullmatch(value):
        raise KnowledgeVaultValidationError(f"knowledge_{field}_invalid")
    return value


def _enum(value, field, allowed):
    value = _text(value, field, required=True, maximum=64).upper()
    if value not in allowed:
        raise KnowledgeVaultValidationError(f"knowledge_{field}_invalid")
    return value


def _content(value):
    if not isinstance(value, str):
        raise KnowledgeVaultValidationError("knowledge_content_invalid")
    value = value.strip()
    if not value:
        raise KnowledgeVaultValidationError("knowledge_content_required")
    if len(value.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise KnowledgeVaultValidationError("knowledge_content_too_large")
    if _SECRET.search(value):
        raise KnowledgeVaultValidationError("knowledge_secret_content_forbidden")
    return value


def _tags(value):
    if value is None:
        return ()
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, (list, tuple)) or len(value) > MAX_TAGS:
        raise KnowledgeVaultValidationError("knowledge_tags_invalid")
    result = []
    for item in value:
        tag = _text(item, "tag", required=True, maximum=64).casefold()
        if tag not in result:
            result.append(tag)
    return tuple(result)


def _checksum(title, content, knowledge_type, source_type, source_reference, tags):
    canonical = json.dumps({
        "title": title, "content": content, "knowledge_type": knowledge_type,
        "source_type": source_type, "source_reference": source_reference,
        "tags": list(tags),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_SELECT = """
knowledge_id,workspace_id,title,content,knowledge_type,status,source_type,
source_reference,tags_json,version,content_checksum,created_by,updated_by,
created_at,updated_at,archived_at
"""


def _item(row):
    return KnowledgeItem(
        str(row[0]), str(row[1]), str(row[2]), str(row[3]),
        str(row[4]).upper(), str(row[5]).upper(),
        _SOURCE_FROM_STORAGE.get(str(row[6]), str(row[6]).upper()),
        str(row[7] or ""), tuple(json.loads(row[8] or "[]")), int(row[9]),
        str(row[10]), str(row[11]), str(row[12]), str(row[13]),
        str(row[14]), str(row[15] or ""),
    )


def _event(cur, workspace_id, knowledge_id, event_type, actor,
           old_version, new_version, metadata=None):
    safe = metadata or {}
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":"))
    if _SECRET.search(encoded):
        encoded = "{}"
    cur.execute(_sql(f"""
        INSERT INTO {EVENT_TABLE} (
            event_id,workspace_id,knowledge_id,event_type,actor,
            old_version,new_version,safe_metadata,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """), (
        "knowledge_event_" + secrets.token_hex(16), workspace_id, knowledge_id,
        event_type, actor, old_version, new_version, encoded, _now(),
    ))


def _version(cur, item):
    cur.execute(_sql(f"""
        INSERT INTO {VERSION_TABLE} (
            version_id,workspace_id,knowledge_id,version,title,content,
            knowledge_type,source_type,source_reference,tags_json,
            content_checksum,created_by,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """), (
        "knowledge_version_" + secrets.token_hex(16), item.workspace_id,
        item.knowledge_id, item.version, item.title, item.content,
        item.knowledge_type, item.source_type, item.source_reference,
        json.dumps(list(item.tags)), item.content_checksum, item.updated_by,
        item.updated_at,
    ))


def create_knowledge_item(
    workspace_id, *, title, content, knowledge_type=None, source_type,
    source_reference="", tags=None, created_by="workspace_client",
    content_format="plain_text", source_name=None, metadata=None,
):
    workspace = _id(workspace_id, "workspace_id")
    title = _text(title, "title", required=True, maximum=300)
    content = _content(content)
    knowledge_type = _enum(
        knowledge_type or "NOTE", "type", KNOWLEDGE_TYPES
    )
    source_type = _enum(source_type, "source_type", SOURCE_TYPES)
    if source_name is not None and not source_reference:
        source_reference = source_name
    source_reference = _text(
        source_reference, "source_reference", maximum=500
    )
    if source_type == "IMPORTED_TEXT" and not source_reference:
        raise KnowledgeVaultValidationError(
            "knowledge_source_reference_required"
        )
    if metadata and tags is None:
        tags = metadata.get("tags") if isinstance(metadata, dict) else None
    tags = _tags(tags)
    actor = _text(created_by, "created_by", required=True, maximum=128)
    knowledge_id = "knowledge_" + secrets.token_hex(16)
    now = _now()
    checksum = _checksum(
        title, content, knowledge_type, source_type, source_reference, tags
    )
    item = KnowledgeItem(
        knowledge_id, workspace, title, content, knowledge_type, "ACTIVE",
        source_type, source_reference, tags, 1, checksum, actor, actor,
        now, now, "",
    )
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            INSERT INTO {TABLE_NAME} (
                knowledge_id,tenant_id,title,source_type,status,content,
                content_format,source_name,version,checksum,metadata_json,
                created_by,created_at,updated_at,activated_at,archived_at,
                parent_version,workspace_id,knowledge_type,source_reference,
                tags_json,content_checksum,updated_by
            ) VALUES (
                %s,%s,%s,%s,'active',%s,'plain_text',%s,1,%s,%s,%s,
                %s,%s,%s,'',NULL,%s,%s,%s,%s,%s,%s
            )
        """), (
            knowledge_id, workspace, title, _SOURCE_TO_STORAGE[source_type], content,
            source_reference, checksum, json.dumps({"tags": list(tags)}),
            actor, now, now, now, workspace, knowledge_type, source_reference,
            json.dumps(list(tags)), checksum, actor,
        ))
        _version(cur, item)
        _event(
            cur, workspace, knowledge_id, "knowledge_created", actor,
            None, 1, {"knowledge_type": knowledge_type, "source_type": source_type},
        )
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(
            f"knowledge_create_failed:{type(exc).__name__}"
        ) from exc
    finally:
        conn.close()
    return item


def get_knowledge_item(workspace_id, knowledge_id, version=None):
    workspace = _id(workspace_id, "workspace_id")
    identifier = _id(knowledge_id)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        if version is None:
            cur.execute(_sql(f"""
                SELECT {_SELECT} FROM {TABLE_NAME}
                WHERE workspace_id=%s AND knowledge_id=%s LIMIT 1
            """), (workspace, identifier))
            row = cur.fetchone()
            cur.close()
            if not row:
                raise KnowledgeVaultNotFoundError("knowledge_item_not_found")
            return _item(row)
        cur.execute(_sql(f"""
            SELECT knowledge_id,workspace_id,title,content,knowledge_type,
                'ACTIVE',source_type,source_reference,tags_json,version,
                content_checksum,created_by,created_by,created_at,created_at,''
            FROM {VERSION_TABLE}
            WHERE workspace_id=%s AND knowledge_id=%s AND version=%s
        """), (workspace, identifier, int(version)))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise KnowledgeVaultNotFoundError("knowledge_item_not_found")
    return _item(row)


def list_knowledge_versions(workspace_id, knowledge_id):
    current = get_knowledge_item(workspace_id, knowledge_id)
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT knowledge_id,workspace_id,title,content,knowledge_type,
                'ACTIVE',source_type,source_reference,tags_json,version,
                content_checksum,created_by,created_by,created_at,created_at,''
            FROM {VERSION_TABLE}
            WHERE workspace_id=%s AND knowledge_id=%s
            ORDER BY version DESC
        """), (current.workspace_id, current.knowledge_id))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_item(row) for row in rows)


def list_tenant_knowledge(
    workspace_id, *, status="ACTIVE", source_type=None, knowledge_type=None,
    tag=None, query=None, limit=DEFAULT_LIST_LIMIT, offset=0,
):
    workspace = _id(workspace_id, "workspace_id")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIST_LIMIT:
        raise KnowledgeVaultValidationError("knowledge_limit_invalid")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise KnowledgeVaultValidationError("knowledge_offset_invalid")
    clauses, params = ["workspace_id=%s"], [workspace]
    if status is not None:
        status = _enum(status, "status", STATUSES)
        clauses.append("status=%s")
        params.append(status.casefold())
    if source_type:
        clauses.append("source_type=%s")
        params.append(_SOURCE_TO_STORAGE[
            _enum(source_type, "source_type", SOURCE_TYPES)
        ])
    if knowledge_type:
        clauses.append("knowledge_type=%s")
        params.append(_enum(knowledge_type, "type", KNOWLEDGE_TYPES))
    if tag:
        selected = _tags([tag])[0]
        clauses.append("LOWER(tags_json) LIKE %s")
        params.append(f'%"{selected}"%')
    if query:
        query = _text(query, "query", required=True, maximum=200).casefold()
        query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append(
            "(LOWER(title) LIKE %s ESCAPE '\\' OR "
            "LOWER(content) LIKE %s ESCAPE '\\')"
        )
        params.extend([f"%{query}%", f"%{query}%"])
    params.extend([limit, offset])
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT {_SELECT} FROM {TABLE_NAME}
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC, knowledge_id ASC LIMIT %s OFFSET %s
        """), tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_item(row) for row in rows)


def update_knowledge_item(
    workspace_id, knowledge_id, *, expected_version=None, title=None,
    content=None, knowledge_type=None, source_type=None,
    source_reference=None, tags=None, updated_by="workspace_client", **_unused,
):
    current = get_knowledge_item(workspace_id, knowledge_id)
    if current.status != "ACTIVE":
        raise KnowledgeVaultConflictError("knowledge_active_update_required")
    if expected_version is not None and int(expected_version) != current.version:
        raise KnowledgeVaultConflictError("knowledge_version_conflict")
    title = current.title if title is None else _text(
        title, "title", required=True, maximum=300
    )
    content = current.content if content is None else _content(content)
    knowledge_type = current.knowledge_type if knowledge_type is None else _enum(
        knowledge_type, "type", KNOWLEDGE_TYPES
    )
    source_type = current.source_type if source_type is None else _enum(
        source_type, "source_type", SOURCE_TYPES
    )
    source_reference = current.source_reference if source_reference is None else _text(
        source_reference, "source_reference", maximum=500
    )
    tags = current.tags if tags is None else _tags(tags)
    actor = _text(updated_by, "updated_by", required=True, maximum=128)
    checksum = _checksum(
        title, content, knowledge_type, source_type, source_reference, tags
    )
    if checksum == current.content_checksum:
        return current
    next_version, now = current.version + 1, _now()
    result = KnowledgeItem(
        current.knowledge_id, current.workspace_id, title, content,
        knowledge_type, "ACTIVE", source_type, source_reference, tags,
        next_version, checksum, current.created_by, actor, current.created_at,
        now, "",
    )
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET title=%s,content=%s,knowledge_type=%s,
                source_type=%s,source_reference=%s,source_name=%s,
                tags_json=%s,metadata_json=%s,version=%s,checksum=%s,
                content_checksum=%s,updated_by=%s,updated_at=%s,parent_version=%s
            WHERE workspace_id=%s AND knowledge_id=%s AND version=%s
                AND status='active'
        """), (
            title, content, knowledge_type, _SOURCE_TO_STORAGE[source_type],
            source_reference, source_reference, json.dumps(list(tags)),
            json.dumps({"tags": list(tags)}), next_version, checksum, checksum,
            actor, now, current.version, current.workspace_id,
            current.knowledge_id, current.version,
        ))
        if cur.rowcount != 1:
            raise KnowledgeVaultConflictError("knowledge_version_conflict")
        _version(cur, result)
        _event(
            cur, current.workspace_id, current.knowledge_id,
            "knowledge_updated", actor, current.version, next_version,
            {"changed": True},
        )
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise KnowledgeVaultPersistenceError(
            f"knowledge_update_failed:{type(exc).__name__}"
        ) from exc
    finally:
        conn.close()
    return result


def update_draft(workspace_id, knowledge_id, **values):
    if "source_name" in values and "source_reference" not in values:
        values["source_reference"] = values.pop("source_name")
    if "metadata" in values and "tags" not in values:
        metadata = values.pop("metadata")
        values["tags"] = metadata.get("tags") if isinstance(metadata, dict) else None
    values.pop("content_format", None)
    return update_knowledge_item(workspace_id, knowledge_id, **values)


def create_knowledge_version(workspace_id, knowledge_id, **values):
    if "created_by" in values:
        values["updated_by"] = values.pop("created_by")
    return update_draft(workspace_id, knowledge_id, **values)


def activate_knowledge_item(workspace_id, knowledge_id):
    item = get_knowledge_item(workspace_id, knowledge_id)
    if item.status != "ACTIVE":
        raise KnowledgeVaultTransitionError("knowledge_transition_invalid")
    return item


def archive_knowledge_item(workspace_id, knowledge_id, actor="workspace_client"):
    current = get_knowledge_item(workspace_id, knowledge_id)
    if current.status != "ACTIVE":
        return current
    now = _now()
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {TABLE_NAME} SET status='archived',archived_at=%s,
                updated_at=%s,updated_by=%s
            WHERE workspace_id=%s AND knowledge_id=%s AND version=%s
                AND status='active'
        """), (
            now, now, actor, current.workspace_id, current.knowledge_id,
            current.version,
        ))
        if cur.rowcount != 1:
            raise KnowledgeVaultConflictError("knowledge_archive_conflict")
        _event(
            cur, current.workspace_id, current.knowledge_id,
            "knowledge_archived", actor, current.version, current.version,
            {"status": "ARCHIVED"},
        )
        conn.commit()
        cur.close()
    except KnowledgeVaultError:
        conn.rollback()
        raise
    finally:
        conn.close()
    return KnowledgeItem(
        current.knowledge_id, current.workspace_id, current.title,
        current.content, current.knowledge_type, "ARCHIVED",
        current.source_type, current.source_reference, current.tags,
        current.version, current.content_checksum, current.created_by, actor,
        current.created_at, now, now,
    )


def list_knowledge_events(workspace_id, knowledge_id=None, limit=100):
    workspace = _id(workspace_id, "workspace_id")
    clauses, params = ["workspace_id=%s"], [workspace]
    if knowledge_id:
        clauses.append("knowledge_id=%s")
        params.append(_id(knowledge_id))
    params.append(min(max(int(limit), 1), 200))
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT event_id,workspace_id,knowledge_id,event_type,actor,
                old_version,new_version,safe_metadata,created_at
            FROM {EVENT_TABLE} WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC,event_id DESC LIMIT %s
        """), tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(rows)


def initialize_knowledge_vault(require_schema=None):
    # Hosted runtimes are always fail-closed. Local legacy test/runtime imports
    # remain compatible until their explicit managed-migration fixture runs.
    strict = persistence_backend.HOSTED if require_schema is None else bool(
        require_schema
    )
    if KNOWLEDGE_TYPES != frozenset({
        "FACT", "INSTRUCTION", "POLICY", "PROCEDURE",
        "PRODUCT", "SERVICE", "FAQ", "NOTE",
    }) or STATUSES != frozenset({"ACTIVE", "ARCHIVED"}):
        return False
    conn = persistence_backend.connect()
    try:
        cur = conn.cursor()
        required = {TABLE_NAME, VERSION_TABLE, EVENT_TABLE}
        if persistence_backend.USE_POSTGRES:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=current_schema()"
            )
            tables = {str(row[0]) for row in cur.fetchall()}
        else:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {str(row[0]) for row in cur.fetchall()}
        if not required.issubset(tables):
            return False if strict else True
        columns = set()
        if persistence_backend.USE_POSTGRES:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() "
                "AND table_name='nina_knowledge_items'"
            )
            columns = {str(row[0]) for row in cur.fetchall()}
        else:
            cur.execute("PRAGMA table_info(nina_knowledge_items)")
            columns = {str(row[1]) for row in cur.fetchall()}
        cur.execute(_sql(
            "SELECT COUNT(*) FROM nina_knowledge_items WHERE workspace_id=%s"
        ), ("readiness_probe",))
        cur.fetchone()
        cur.close()
        result = {
            "ok": {
                "workspace_id", "knowledge_type", "source_reference",
                "tags_json", "content_checksum", "updated_by",
            }.issubset(columns)
        }
        return result if strict else True
    except Exception:
        return False
    finally:
        conn.close()


def persistence_health():
    return initialize_knowledge_vault()
