"""Channel Layer V1: canonical communication records for the one Nina runtime.

This domain service extends the existing channel connection truth and routes
content to the existing Message Service. It does not send provider messages,
run workers, schedule work, or contain AI behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend
from contact_identity import resolve_contact_identity
from universal_work_objects import get_work_object


CONNECTION_TABLE = "nina_channel_connections"
MESSAGE_TABLE = "nina_channel_messages"
EVENT_TABLE = "nina_channel_message_events"
CHANNEL_TYPES = frozenset({"WEB", "TELEGRAM", "WHATSAPP", "EMAIL"})
CONNECTION_STATUSES = frozenset({
    "PENDING", "CONNECTED", "SUSPENDED", "DISCONNECTED",
})
DIRECTIONS = frozenset({"INBOUND", "OUTBOUND"})
MESSAGE_TYPES = frozenset({"TEXT", "SYSTEM", "IMAGE", "AUDIO", "VIDEO", "FILE"})
PROCESSING_STATUSES = frozenset({
    "RECEIVED", "NORMALIZED", "ROUTED", "PROCESSED", "FAILED", "IGNORED",
})
DELIVERY_STATUSES = frozenset({
    "DRAFT", "APPROVAL_REQUIRED", "APPROVED", "QUEUED", "SENT",
    "DELIVERED", "FAILED", "CANCELLED",
})
CAPABILITIES = frozenset({
    "receive_text", "send_text", "receive_media", "send_media",
    "receive_files", "send_files", "read_receipts", "delivery_receipts",
})
_CONNECTION_TRANSITIONS = frozenset({
    ("PENDING", "CONNECTED"), ("PENDING", "DISCONNECTED"),
    ("CONNECTED", "SUSPENDED"), ("CONNECTED", "DISCONNECTED"),
    ("SUSPENDED", "CONNECTED"), ("SUSPENDED", "DISCONNECTED"),
    ("DISCONNECTED", "PENDING"), ("DISCONNECTED", "CONNECTED"),
})
_PROCESSING_TRANSITIONS = frozenset({
    ("RECEIVED", "NORMALIZED"), ("RECEIVED", "FAILED"),
    ("RECEIVED", "IGNORED"), ("NORMALIZED", "ROUTED"),
    ("NORMALIZED", "FAILED"), ("NORMALIZED", "IGNORED"),
    ("ROUTED", "PROCESSED"), ("ROUTED", "FAILED"),
})
_DELIVERY_TRANSITIONS = frozenset({
    ("DRAFT", "APPROVAL_REQUIRED"), ("DRAFT", "APPROVED"),
    ("DRAFT", "CANCELLED"), ("APPROVAL_REQUIRED", "APPROVED"),
    ("APPROVAL_REQUIRED", "CANCELLED"), ("APPROVED", "QUEUED"),
    ("APPROVED", "CANCELLED"), ("QUEUED", "SENT"),
    ("QUEUED", "FAILED"), ("QUEUED", "CANCELLED"),
    ("SENT", "DELIVERED"), ("SENT", "FAILED"),
})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_SENSITIVE = {
    "token", "secret", "password", "api_key", "authorization", "bearer",
    "connection_string", "database_url", "webhook_secret", "exception", "stack",
}


class ChannelLayerError(RuntimeError):
    pass


class ChannelValidationError(ChannelLayerError):
    pass


class ChannelNotFoundError(ChannelLayerError):
    pass


class ChannelConflictError(ChannelLayerError):
    pass


@dataclass(frozen=True)
class ChannelConnection:
    channel_connection_id: str
    workspace_id: str
    channel_type: str
    display_name: str
    external_account_id: str
    status: str
    capabilities: tuple
    configuration_reference: str
    created_by: str
    updated_by: str
    created_at: str
    updated_at: str
    activated_at: str
    suspended_at: str

    def as_dict(self):
        return {
            "channel_connection_id": self.channel_connection_id,
            "channel_type": self.channel_type,
            "display_name": self.display_name,
            "external_account_safe_label": _safe_external_label(
                self.external_account_id
            ),
            "status": self.status,
            "capabilities": list(self.capabilities),
            "configuration_reference": self.configuration_reference,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "activated_at": self.activated_at,
            "suspended_at": self.suspended_at,
        }


@dataclass(frozen=True)
class ChannelMessage:
    message_id: str
    workspace_id: str
    channel_connection_id: str
    channel_type: str
    direction: str
    external_message_id: str
    thread_reference: str
    contact_id: str
    external_sender_id: str
    message_type: str
    text_content: str
    safe_metadata: dict
    received_at: str
    created_at: str
    deduplication_key: str
    related_work_object_id: str
    processing_status: str
    related_inbound_message_id: str
    approval_reference: str
    execution_reference: str
    delivery_status: str
    external_delivery_id: str

    def as_dict(self, include_text=True):
        value = {
            "message_id": self.message_id,
            "channel_connection_id": self.channel_connection_id,
            "channel_type": self.channel_type,
            "direction": self.direction,
            "external_message_id": self.external_message_id,
            "thread_reference": self.thread_reference,
            "contact_id": self.contact_id,
            "message_type": self.message_type,
            "text_content": self.text_content if include_text else "",
            "text_preview": self.text_content[:120],
            "safe_metadata": dict(self.safe_metadata),
            "received_at": self.received_at,
            "created_at": self.created_at,
            "related_work_object_id": self.related_work_object_id,
            "processing_status": self.processing_status,
            "related_inbound_message_id": self.related_inbound_message_id,
            "approval_reference": self.approval_reference,
            "execution_reference": self.execution_reference,
            "delivery_status": self.delivery_status,
            "external_delivery_id": self.external_delivery_id,
        }
        return value


class ChannelAdapter:
    channel_type = ""
    capabilities = ()
    provider_send_supported = False

    def normalize_inbound(self, payload, connection_context):
        if not isinstance(payload, dict):
            raise ChannelValidationError("channel_payload_invalid")
        return dict(payload)

    def prepare_outbound(self, message, connection_context):
        return {
            "channel_type": self.channel_type,
            "recipient": message.contact_id,
            "text_content": message.text_content,
        }

    def parse_delivery_receipt(self, payload):
        return {}

    def health_check(self, connection=None):
        return True


class WebChannelAdapter(ChannelAdapter):
    channel_type = "WEB"
    capabilities = ("receive_text", "send_text")


class InactiveChannelAdapter(ChannelAdapter):
    def health_check(self, connection=None):
        return connection is None or connection.status != "CONNECTED"


ADAPTERS = {
    "WEB": WebChannelAdapter(),
    "TELEGRAM": InactiveChannelAdapter(),
    "WHATSAPP": InactiveChannelAdapter(),
    "EMAIL": InactiveChannelAdapter(),
}
ADAPTERS["TELEGRAM"].channel_type = "TELEGRAM"
ADAPTERS["WHATSAPP"].channel_type = "WHATSAPP"
ADAPTERS["EMAIL"].channel_type = "EMAIL"


def _sql(value):
    return persistence_backend.sql(value)


def _connect():
    return persistence_backend.connect()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field, *, required=False, maximum=1000):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ChannelValidationError(f"channel_{field}_invalid")
    value = value.strip()
    if required and not value:
        raise ChannelValidationError(f"channel_{field}_required")
    if len(value) > maximum:
        raise ChannelValidationError(f"channel_{field}_too_long")
    return value


def _identifier(value, field, *, required=True):
    value = _text(value, field, required=required, maximum=256)
    if value and not _ID.fullmatch(value):
        raise ChannelValidationError(f"channel_{field}_invalid")
    return value


def _enum(value, field, registry):
    value = _text(value, field, required=True, maximum=64).upper()
    if value not in registry:
        raise ChannelValidationError(f"channel_{field}_invalid")
    return value


def _safe_metadata(value):
    if value is None:
        return {}, "{}"
    if not isinstance(value, dict):
        raise ChannelValidationError("channel_safe_metadata_invalid")
    clean = {}
    for key, item in value.items():
        name = str(key).strip().lower()
        if not name or any(part in name for part in _SENSITIVE):
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            clean[name[:64]] = item if not isinstance(item, str) else item[:500]
    encoded = json.dumps(clean, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode()) > 4096:
        raise ChannelValidationError("channel_safe_metadata_too_large")
    return clean, encoded


def _capabilities(values, channel_type):
    if values is None:
        values = ADAPTERS[channel_type].capabilities
    if not isinstance(values, (list, tuple, set)):
        raise ChannelValidationError("channel_capabilities_invalid")
    result = tuple(dict.fromkeys(str(item).strip().lower() for item in values))
    if not set(result).issubset(CAPABILITIES):
        raise ChannelValidationError("channel_capabilities_invalid")
    if not ADAPTERS[channel_type].provider_send_supported and channel_type != "WEB":
        result = tuple(item for item in result if not item.startswith("send_"))
    return result


def _connection_id(workspace_id, channel_type, external_account_id):
    material = f"{workspace_id}\0{channel_type}\0{external_account_id}".encode()
    return "chc_" + hashlib.sha256(material).hexdigest()[:32]


def _safe_external_label(value):
    value = str(value or "")
    if len(value) <= 6:
        return value
    return value[:3] + "..." + value[-3:]


def _connection_from_row(row):
    status = str(row[5]).upper()
    if status == "ERROR":
        status = "DISCONNECTED"
    return ChannelConnection(
        channel_connection_id=str(row[0]), workspace_id=str(row[1]),
        channel_type=str(row[2]).upper(), display_name=str(row[3] or ""),
        external_account_id=str(row[4] or ""), status=status,
        capabilities=tuple(json.loads(row[6] or "[]")),
        configuration_reference=str(row[7] or ""),
        created_by=str(row[8] or "legacy"),
        updated_by=str(row[9] or "legacy"), created_at=str(row[10]),
        updated_at=str(row[11]), activated_at=str(row[12] or ""),
        suspended_at=str(row[13] or ""),
    )


_CONNECTION_FIELDS = (
    "channel_connection_id,workspace_id,channel_type,display_name,"
    "external_account_id,status,capabilities_json,configuration_reference,"
    "created_by,updated_by,created_at,updated_at,activated_at,suspended_at"
)


def get_connection(workspace_id, channel_connection_id):
    workspace = _identifier(workspace_id, "workspace_id")
    connection_id = _identifier(channel_connection_id, "connection_id")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"SELECT {_CONNECTION_FIELDS} FROM {CONNECTION_TABLE} "
            "WHERE workspace_id=%s AND channel_connection_id=%s LIMIT 1"
        ), (workspace, connection_id))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise ChannelNotFoundError("channel_connection_not_found")
    return _connection_from_row(row)


def list_connections(workspace_id, limit=50):
    workspace = _identifier(workspace_id, "workspace_id")
    limit = max(1, min(int(limit), 100))
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"SELECT {_CONNECTION_FIELDS} FROM {CONNECTION_TABLE} "
            "WHERE workspace_id=%s ORDER BY channel_type,updated_at DESC LIMIT %s"
        ), (workspace, limit))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_connection_from_row(row) for row in rows)


def create_connection(
    workspace_id, *, channel_type, display_name, external_account_id="",
    status="DISCONNECTED", capabilities=None, configuration_reference="",
    created_by="workspace_client",
):
    workspace = _identifier(workspace_id, "workspace_id")
    channel_type = _enum(channel_type, "type", CHANNEL_TYPES)
    display_name = _text(
        display_name, "display_name", required=True, maximum=120
    )
    external_account_id = _text(
        external_account_id, "external_account_id", maximum=256
    )
    status = _enum(status, "status", CONNECTION_STATUSES)
    capabilities = _capabilities(capabilities, channel_type)
    configuration_reference = _identifier(
        configuration_reference, "configuration_reference", required=False
    )
    actor = _identifier(created_by, "created_by")
    connection_id = _connection_id(
        workspace, channel_type, external_account_id or display_name
    )
    now = _now()
    activated_at = now if status == "CONNECTED" else ""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            INSERT INTO {CONNECTION_TABLE} (
                workspace_id,channel,status,metadata_json,secret_ref,
                webhook_secret_ref,app_secret_ref,connect_token_hash,
                connect_token_expires_at,connect_token_used_at,created_at,
                updated_at,channel_connection_id,channel_type,display_name,
                external_account_id,capabilities_json,configuration_reference,
                created_by,updated_by,activated_at,suspended_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s
            )
        """), (
            workspace, channel_type.lower(), status.lower(), "{}", "", "", "",
            "", "", "", now, now, connection_id, channel_type, display_name,
            external_account_id, json.dumps(capabilities), configuration_reference,
            actor, actor, activated_at, "",
        ))
        _event(
            conn, workspace, connection_id, "", "channel_connected"
            if status == "CONNECTED" else "channel_updated", actor,
            {"status": status},
        )
        conn.commit()
        cur.close()
    except Exception as exc:
        conn.rollback()
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise ChannelConflictError("channel_identity_already_linked") from exc
        raise
    finally:
        conn.close()
    return get_connection(workspace, connection_id)


def ensure_web_connection(workspace_id, actor="system"):
    workspace = _identifier(workspace_id, "workspace_id")
    connection_id = _connection_id(workspace, "WEB", f"web:{workspace}")
    try:
        return get_connection(workspace, connection_id)
    except ChannelNotFoundError:
        try:
            return create_connection(
                workspace, channel_type="WEB", display_name="Web",
                external_account_id=f"web:{workspace}", status="CONNECTED",
                capabilities=("receive_text", "send_text"),
                configuration_reference="internal:web", created_by=actor,
            )
        except ChannelConflictError:
            return get_connection(workspace, connection_id)


def update_connection(
    workspace_id, channel_connection_id, *, display_name=None,
    target_status=None, updated_by="workspace_client",
):
    current = get_connection(workspace_id, channel_connection_id)
    display_name = current.display_name if display_name is None else _text(
        display_name, "display_name", required=True, maximum=120
    )
    status = current.status
    event_type = "channel_updated"
    if target_status is not None:
        target = _enum(target_status, "status", CONNECTION_STATUSES)
        if target != status and (status, target) not in _CONNECTION_TRANSITIONS:
            raise ChannelConflictError("channel_status_transition_invalid")
        status = target
        event_type = {
            "CONNECTED": "channel_connected",
            "SUSPENDED": "channel_suspended",
            "DISCONNECTED": "channel_disconnected",
        }.get(status, "channel_updated")
    actor = _identifier(updated_by, "updated_by")
    now = _now()
    activated_at = now if status == "CONNECTED" and current.status != status else current.activated_at
    suspended_at = now if status == "SUSPENDED" else current.suspended_at
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {CONNECTION_TABLE} SET display_name=%s,status=%s,
                updated_by=%s,updated_at=%s,activated_at=%s,suspended_at=%s
            WHERE workspace_id=%s AND channel_connection_id=%s
        """), (
            display_name, status.lower(), actor, now, activated_at,
            suspended_at, current.workspace_id, current.channel_connection_id,
        ))
        _event(
            conn, current.workspace_id, current.channel_connection_id, "",
            event_type, actor, {"status": status},
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return get_connection(current.workspace_id, current.channel_connection_id)


def _deduplication_key(
    workspace_id, connection_id, external_message_id, thread_reference,
    external_sender_id, text_content, received_at,
):
    external = str(external_message_id or "").strip()
    if external:
        identity = "external:" + external
    else:
        identity = "\0".join((
            "fallback", str(thread_reference or ""), str(external_sender_id or ""),
            str(text_content or ""), str(received_at or ""),
        ))
    material = f"{workspace_id}\0{connection_id}\0{identity}".encode()
    return hashlib.sha256(material).hexdigest()


def _validate_work_object(workspace_id, work_object_id):
    value = _identifier(
        work_object_id, "related_work_object_id", required=False
    )
    if value:
        get_work_object(workspace_id, value)
    return value


def _message_from_row(row):
    return ChannelMessage(
        message_id=str(row[0]), workspace_id=str(row[1]),
        channel_connection_id=str(row[2]), channel_type=str(row[3]),
        direction=str(row[4]), external_message_id=str(row[5] or ""),
        thread_reference=str(row[6] or ""), contact_id=str(row[7] or ""),
        external_sender_id=str(row[8] or ""), message_type=str(row[9]),
        text_content=str(row[10] or ""),
        safe_metadata=json.loads(row[11] or "{}"),
        received_at=str(row[12] or ""), created_at=str(row[13]),
        deduplication_key=str(row[14]),
        related_work_object_id=str(row[15] or ""),
        processing_status=str(row[16]),
        related_inbound_message_id=str(row[17] or ""),
        approval_reference=str(row[18] or ""),
        execution_reference=str(row[19] or ""),
        delivery_status=str(row[20] or ""),
        external_delivery_id=str(row[21] or ""),
    )


_MESSAGE_FIELDS = (
    "message_id,workspace_id,channel_connection_id,channel_type,direction,"
    "external_message_id,thread_reference,contact_id,external_sender_id,"
    "message_type,text_content,safe_metadata_json,received_at,created_at,"
    "deduplication_key,related_work_object_id,processing_status,"
    "related_inbound_message_id,approval_reference,execution_reference,"
    "delivery_status,external_delivery_id"
)


def get_message(workspace_id, message_id):
    workspace = _identifier(workspace_id, "workspace_id")
    message_id = _identifier(message_id, "message_id")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"SELECT {_MESSAGE_FIELDS} FROM {MESSAGE_TABLE} "
            "WHERE workspace_id=%s AND message_id=%s LIMIT 1"
        ), (workspace, message_id))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    if not row:
        raise ChannelNotFoundError("channel_message_not_found")
    return _message_from_row(row)


def list_messages(workspace_id, limit=50):
    workspace = _identifier(workspace_id, "workspace_id")
    limit = max(1, min(int(limit), 100))
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"SELECT {_MESSAGE_FIELDS} FROM {MESSAGE_TABLE} "
            "WHERE workspace_id=%s ORDER BY created_at DESC LIMIT %s"
        ), (workspace, limit))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple(_message_from_row(row) for row in rows)


def get_outbound_for_work_object(workspace_id, work_object_id, contact_id):
    """Return an existing recipient-bound outbound for idempotent delivery."""
    workspace = _identifier(workspace_id, "workspace_id")
    work_object = _identifier(work_object_id, "related_work_object_id")
    contact = _identifier(contact_id, "contact_id")
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"SELECT {_MESSAGE_FIELDS} FROM {MESSAGE_TABLE} "
            "WHERE workspace_id=%s AND related_work_object_id=%s "
            "AND contact_id=%s AND direction=%s ORDER BY created_at LIMIT 1"
        ), (workspace, work_object, contact, "OUTBOUND"))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    return _message_from_row(row) if row else None


def ingest_inbound(
    workspace_id, channel_connection_id, *, external_message_id="",
    thread_reference="", external_sender_id="", message_type="TEXT",
    text_content="", safe_metadata=None, received_at="",
    related_work_object_id="", actor="channel_adapter",
):
    connection = get_connection(workspace_id, channel_connection_id)
    if connection.status != "CONNECTED":
        raise ChannelConflictError("channel_connection_not_connected")
    message_type = _enum(message_type, "message_type", MESSAGE_TYPES)
    if message_type not in {"TEXT", "SYSTEM"}:
        raise ChannelValidationError("channel_message_type_not_supported")
    text_content = _text(
        text_content, "text_content", required=message_type == "TEXT",
        maximum=16000,
    )
    external_message_id = _text(
        external_message_id, "external_message_id", maximum=256
    )
    thread_reference = _text(
        thread_reference, "thread_reference", maximum=256
    )
    external_sender_id = _text(
        external_sender_id, "external_sender_id", maximum=512
    )
    received_at = _text(
        received_at or _now(), "received_at", required=True, maximum=80
    )
    related_work_object_id = _validate_work_object(
        connection.workspace_id, related_work_object_id
    )
    metadata, metadata_json = _safe_metadata(safe_metadata)
    identity = external_sender_id or f"anonymous:{thread_reference or connection.channel_connection_id}"
    contact = resolve_contact_identity(
        connection.workspace_id, connection.channel_type.lower(), identity,
        {"relationship_type": "contact"},
    )
    key = _deduplication_key(
        connection.workspace_id, connection.channel_connection_id,
        external_message_id, thread_reference, identity, text_content,
        received_at,
    )
    message_id = "chm_" + secrets.token_hex(16)
    now = _now()
    conn = _connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(_sql(f"""
                INSERT INTO {MESSAGE_TABLE} (
                    message_id,workspace_id,channel_connection_id,channel_type,
                    direction,external_message_id,thread_reference,contact_id,
                    external_sender_id,message_type,text_content,safe_metadata_json,
                    received_at,created_at,deduplication_key,
                    related_work_object_id,processing_status,
                    related_inbound_message_id,approval_reference,
                    execution_reference,delivery_status,external_delivery_id
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                )
            """), (
                message_id, connection.workspace_id,
                connection.channel_connection_id, connection.channel_type,
                "INBOUND", external_message_id, thread_reference,
                contact["contact_id"], identity, message_type, text_content,
                metadata_json, received_at, now, key, related_work_object_id,
                "NORMALIZED", "", "", "", "", "",
            ))
            _event(
                conn, connection.workspace_id,
                connection.channel_connection_id, message_id,
                "inbound_received", actor,
                {"message_type": message_type},
            )
            conn.commit()
            cur.close()
            return get_message(connection.workspace_id, message_id), False
        except Exception as exc:
            conn.rollback()
            cur = conn.cursor()
            cur.execute(_sql(
                f"SELECT message_id FROM {MESSAGE_TABLE} "
                "WHERE workspace_id=%s AND channel_connection_id=%s "
                "AND deduplication_key=%s AND direction='INBOUND' LIMIT 1"
            ), (
                connection.workspace_id, connection.channel_connection_id, key,
            ))
            row = cur.fetchone()
            cur.close()
            if not row:
                raise exc
            duplicate = get_message(connection.workspace_id, row[0])
            audit_conn = _connect()
            try:
                _event(
                    audit_conn, connection.workspace_id,
                    connection.channel_connection_id, duplicate.message_id,
                    "inbound_deduplicated", actor, {},
                )
                audit_conn.commit()
            finally:
                audit_conn.close()
            return duplicate, True
    finally:
        conn.close()


def create_outbound(
    workspace_id, channel_connection_id, *, contact_id, text_content,
    related_inbound_message_id="", related_work_object_id="",
    approval_reference="", execution_reference="", status="DRAFT",
    safe_metadata=None, created_by="workspace_client",
):
    connection = get_connection(workspace_id, channel_connection_id)
    status = _enum(status, "delivery_status", DELIVERY_STATUSES)
    if status not in {"DRAFT", "APPROVAL_REQUIRED", "APPROVED"}:
        raise ChannelConflictError("channel_outbound_initial_status_invalid")
    contact_id = _identifier(contact_id, "contact_id")
    text_content = _text(
        text_content, "text_content", required=True, maximum=16000
    )
    related_inbound_message_id = _identifier(
        related_inbound_message_id, "related_inbound_message_id",
        required=False,
    )
    if related_inbound_message_id:
        inbound = get_message(
            connection.workspace_id, related_inbound_message_id
        )
        if inbound.direction != "INBOUND":
            raise ChannelConflictError("channel_related_inbound_invalid")
    related_work_object_id = _validate_work_object(
        connection.workspace_id, related_work_object_id
    )
    approval_reference = _identifier(
        approval_reference, "approval_reference", required=False
    )
    execution_reference = _identifier(
        execution_reference, "execution_reference", required=False
    )
    _, metadata_json = _safe_metadata(safe_metadata)
    actor = _identifier(created_by, "created_by")
    message_id = "chm_" + secrets.token_hex(16)
    now = _now()
    key = hashlib.sha256(
        f"{connection.workspace_id}\0{message_id}".encode()
    ).hexdigest()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            INSERT INTO {MESSAGE_TABLE} (
                message_id,workspace_id,channel_connection_id,channel_type,
                direction,external_message_id,thread_reference,contact_id,
                external_sender_id,message_type,text_content,safe_metadata_json,
                received_at,created_at,deduplication_key,
                related_work_object_id,processing_status,
                related_inbound_message_id,approval_reference,
                execution_reference,delivery_status,external_delivery_id
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s
            )
        """), (
            message_id, connection.workspace_id,
            connection.channel_connection_id, connection.channel_type,
            "OUTBOUND", "", "", contact_id, "", "TEXT", text_content,
            metadata_json, "", now, key, related_work_object_id, "PROCESSED",
            related_inbound_message_id, approval_reference,
            execution_reference, status, "",
        ))
        _event(
            conn, connection.workspace_id, connection.channel_connection_id,
            message_id, "outbound_created", actor,
            {"delivery_status": status},
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return get_message(connection.workspace_id, message_id)


def transition_delivery(
    workspace_id, message_id, target_status, *, actor="channel_adapter",
    provider_confirmed=False, delivery_receipt=False, external_delivery_id="",
    safe_metadata=None,
):
    current = get_message(workspace_id, message_id)
    if current.direction != "OUTBOUND":
        raise ChannelConflictError("channel_delivery_direction_invalid")
    target = _enum(target_status, "delivery_status", DELIVERY_STATUSES)
    if (current.delivery_status, target) not in _DELIVERY_TRANSITIONS:
        raise ChannelConflictError("channel_delivery_transition_invalid")
    if target == "SENT" and not provider_confirmed:
        raise ChannelConflictError("channel_sent_confirmation_required")
    if target == "DELIVERED" and not delivery_receipt:
        raise ChannelConflictError("channel_delivery_receipt_required")
    external_delivery_id = _text(
        external_delivery_id, "external_delivery_id", maximum=256
    )
    actor = _identifier(actor, "actor")
    _, safe_json = _safe_metadata(safe_metadata)
    now = _now()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            UPDATE {MESSAGE_TABLE} SET delivery_status=%s,
                external_delivery_id=%s
            WHERE workspace_id=%s AND message_id=%s
                AND delivery_status=%s
        """), (
            target, external_delivery_id or current.external_delivery_id,
            current.workspace_id, current.message_id, current.delivery_status,
        ))
        if cur.rowcount != 1:
            raise ChannelConflictError("channel_delivery_transition_conflict")
        event_type = {
            "APPROVED": "outbound_approved", "QUEUED": "outbound_queued",
            "SENT": "outbound_sent", "DELIVERED": "outbound_delivered",
            "FAILED": "outbound_failed", "CANCELLED": "outbound_cancelled",
        }.get(target, "outbound_created")
        _event(
            conn, current.workspace_id, current.channel_connection_id,
            current.message_id, event_type, actor, json.loads(safe_json),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return get_message(current.workspace_id, current.message_id)


def transition_processing(
    workspace_id, message_id, target_status, *, actor="channel_router",
    safe_metadata=None,
):
    current = get_message(workspace_id, message_id)
    target = _enum(target_status, "processing_status", PROCESSING_STATUSES)
    if (current.processing_status, target) not in _PROCESSING_TRANSITIONS:
        raise ChannelConflictError("channel_processing_transition_invalid")
    actor = _identifier(actor, "actor")
    metadata, _ = _safe_metadata(safe_metadata)
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(
            f"UPDATE {MESSAGE_TABLE} SET processing_status=%s "
            "WHERE workspace_id=%s AND message_id=%s "
            "AND processing_status=%s"
        ), (
            target, current.workspace_id, current.message_id,
            current.processing_status,
        ))
        if cur.rowcount != 1:
            raise ChannelConflictError("channel_processing_transition_conflict")
        event_type = {
            "ROUTED": "inbound_routed", "FAILED": "inbound_failed",
        }.get(target, "inbound_received")
        _event(
            conn, current.workspace_id, current.channel_connection_id,
            current.message_id, event_type, actor, metadata,
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return get_message(current.workspace_id, current.message_id)


def _event(
    conn, workspace_id, channel_connection_id, message_id, event_type,
    actor, metadata,
):
    _, metadata_json = _safe_metadata(metadata)
    cur = conn.cursor()
    cur.execute(_sql(f"""
        INSERT INTO {EVENT_TABLE} (
            event_id,workspace_id,channel_connection_id,message_id,event_type,
            actor,safe_metadata_json,created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """), (
        "che_" + secrets.token_hex(16), workspace_id,
        channel_connection_id, message_id, event_type,
        str(actor or "system")[:128], metadata_json, _now(),
    ))
    cur.close()


def list_events(workspace_id, limit=100):
    workspace = _identifier(workspace_id, "workspace_id")
    limit = max(1, min(int(limit), 200))
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_sql(f"""
            SELECT event_id,channel_connection_id,message_id,event_type,actor,
                   safe_metadata_json,created_at
            FROM {EVENT_TABLE} WHERE workspace_id=%s
            ORDER BY created_at DESC LIMIT %s
        """), (workspace, limit))
        rows = cur.fetchall() or []
        cur.close()
    finally:
        conn.close()
    return tuple({
        "event_id": str(row[0]), "channel_connection_id": str(row[1] or ""),
        "message_id": str(row[2] or ""), "event_type": str(row[3]),
        "actor": str(row[4]), "safe_metadata": json.loads(row[5] or "{}"),
        "created_at": str(row[6]),
    } for row in rows)


def initialize_channel_layer(require_schema=None):
    persistence_backend.assert_backend_ready()
    strict = (
        persistence_backend.HOSTED
        if require_schema is None else bool(require_schema)
    )
    if (
        CHANNEL_TYPES != {"WEB", "TELEGRAM", "WHATSAPP", "EMAIL"}
        or not {"CONNECTED", "SUSPENDED", "DISCONNECTED"}.issubset(
            CONNECTION_STATUSES
        )
        or DIRECTIONS != {"INBOUND", "OUTBOUND"}
        or set(ADAPTERS) != set(CHANNEL_TYPES)
    ):
        return not strict
    required = {
        CONNECTION_TABLE: {
            "channel_connection_id", "workspace_id", "channel_type",
            "display_name", "external_account_id", "status",
            "capabilities_json", "configuration_reference",
        },
        MESSAGE_TABLE: {
            "message_id", "workspace_id", "channel_connection_id",
            "channel_type", "direction", "external_message_id",
            "deduplication_key", "processing_status", "delivery_status",
        },
        EVENT_TABLE: {
            "event_id", "workspace_id", "channel_connection_id",
            "message_id", "event_type", "safe_metadata_json",
        },
    }
    conn = _connect()
    try:
        cur = conn.cursor()
        for table, expected in required.items():
            if persistence_backend.USE_POSTGRES:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name=%s",
                    (table,),
                )
                columns = {str(row[0]) for row in cur.fetchall()}
            else:
                cur.execute(f"PRAGMA table_info({table})")
                columns = {str(row[1]) for row in cur.fetchall()}
            if not expected.issubset(columns):
                cur.close()
                return not strict
        cur.execute(_sql(
            f"SELECT message_id FROM {MESSAGE_TABLE} "
            "WHERE workspace_id=%s LIMIT 1"
        ), ("readiness_probe",))
        cur.fetchall()
        cur.close()
        return bool(ADAPTERS["WEB"].health_check())
    except Exception:
        return not strict
    finally:
        conn.close()
