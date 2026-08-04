"""Managed, durable NinaOS schema migrations for pre-deploy execution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import persistence_backend
from deployment_compatibility import commit_identifier


LEDGER_TABLE = "nina_schema_migrations"
MIGRATION_LOCK_KEY = 7727002401
PHASE_EXPAND = "EXPAND"
PHASE_CONTRACT = "CONTRACT"
BASELINE_ID = "0000_current_shared_schema_baseline"
BASELINE_VERSION = 0
BASELINE_NAME = "Verified current NinaOS shared schema"

EXPECTED_CURRENT_SHARED_TABLES = {
    "conversation_state",
    "nina_channel_connections",
    "nina_channel_message_receipts",
    "nina_contacts",
    "nina_contact_channel_identities",
    "nina_contact_link_claims",
    "nina_contact_client_mappings",
    "nina_company_whatsapp_auth",
    "nina_company_whatsapp_pairing",
    "nina_personal_whatsapp_auth",
    "nina_personal_whatsapp_pairing",
    "nina_work_objects",
}


class MigrationError(RuntimeError):
    pass


class AmbiguousSchemaError(MigrationError):
    pass


class MigrationChecksumError(MigrationError):
    pass


class IncompleteMigrationError(MigrationError):
    pass


class ContractMigrationForbidden(MigrationError):
    pass


class MigrationPreflightError(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    identifier: str
    version: int
    name: str
    phase: str
    operation: object
    checksum_source: str

    @property
    def checksum(self):
        return hashlib.sha256(self.checksum_source.encode("utf-8")).hexdigest()


def _create_conversation_state(conn):
    cur = conn.cursor()
    id_column = (
        "BIGSERIAL PRIMARY KEY"
        if persistence_backend.USE_POSTGRES
        else "INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS conversation_state (
            id {id_column},
            user_id TEXT,
            user_text TEXT,
            nina_text TEXT DEFAULT '',
            intent TEXT DEFAULT '',
            emotion TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.close()


def _create_agent_assignments(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_agent_assignments (
            assignment_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            ready_worker_definition_id TEXT NOT NULL,
            definition_version TEXT NOT NULL,
            primary_rolepack_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('draft','active','suspended','archived')
            ),
            configuration_json TEXT NOT NULL DEFAULT '{}',
            permissions_json TEXT NOT NULL DEFAULT '{}',
            assigned_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            activated_at TEXT NOT NULL DEFAULT '',
            suspended_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_tenant
        ON nina_agent_assignments (tenant_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_definition
        ON nina_agent_assignments (ready_worker_definition_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_status
        ON nina_agent_assignments (status)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_tenant_status
        ON nina_agent_assignments (tenant_id, status)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_tenant_definition
        ON nina_agent_assignments (
            tenant_id, ready_worker_definition_id, definition_version
        )
    """)
    cur.close()


def _create_knowledge_vault(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_knowledge_items (
            knowledge_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK (
                source_type IN (
                    'text','note','document','url_reference','structured_data'
                )
            ),
            status TEXT NOT NULL CHECK (
                status IN ('draft','active','archived')
            ),
            content TEXT NOT NULL,
            content_format TEXT NOT NULL CHECK (
                content_format IN ('plain_text','markdown','json')
            ),
            source_name TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL CHECK (version >= 1),
            checksum TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            activated_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL DEFAULT '',
            parent_version INTEGER,
            PRIMARY KEY (tenant_id, knowledge_id, version),
            CHECK (parent_version IS NULL OR parent_version < version)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_tenant
        ON nina_knowledge_items (tenant_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_status
        ON nina_knowledge_items (status)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_tenant_status
        ON nina_knowledge_items (tenant_id, status)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_tenant_item_version
        ON nina_knowledge_items (tenant_id, knowledge_id, version DESC)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_tenant_source
        ON nina_knowledge_items (tenant_id, source_type)
    """)
    cur.close()


def _create_universal_work_objects(conn):
    """Adopt and expand the existing nina_work_objects canonical truth."""
    cur = conn.cursor()
    id_column = (
        "BIGSERIAL PRIMARY KEY"
        if persistence_backend.USE_POSTGRES
        else "INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS nina_work_objects (
            id {id_column},
            object_id TEXT NOT NULL UNIQUE,
            workspace_id TEXT NOT NULL,
            object_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned_agent_id TEXT DEFAULT '',
            client_id TEXT DEFAULT '',
            project_id TEXT DEFAULT '',
            priority TEXT DEFAULT 'normal',
            due_date TEXT DEFAULT '',
            linked_files_json TEXT DEFAULT '[]',
            metadata_json TEXT DEFAULT '{{}}',
            origin_channel TEXT DEFAULT '',
            origin_user_id TEXT DEFAULT '',
            source_key TEXT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    columns = set(_column_contract(conn, "nina_work_objects"))
    _assert_compatible_columns(
        "nina_work_objects",
        _column_contract(conn, "nina_work_objects"),
        _WORK_OBJECT_BASE_CONTRACT,
        allow_missing=True,
    )
    additions = {
        "object_id": "TEXT NOT NULL DEFAULT ''",
        "workspace_id": "TEXT NOT NULL DEFAULT ''",
        "object_type": "TEXT NOT NULL DEFAULT 'task'",
        "title": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'draft'",
        "assigned_agent_id": "TEXT NOT NULL DEFAULT ''",
        "client_id": "TEXT NOT NULL DEFAULT ''",
        "project_id": "TEXT NOT NULL DEFAULT ''",
        "priority": "TEXT NOT NULL DEFAULT 'normal'",
        "due_date": "TEXT NOT NULL DEFAULT ''",
        "linked_files_json": "TEXT NOT NULL DEFAULT '[]'",
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
        "origin_channel": "TEXT NOT NULL DEFAULT ''",
        "origin_user_id": "TEXT NOT NULL DEFAULT ''",
        "source_key": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "description": "TEXT NOT NULL DEFAULT ''",
        "owner_type": "TEXT NOT NULL DEFAULT 'tenant'",
        "owner_id": "TEXT NOT NULL DEFAULT ''",
        "assigned_agent_assignment_id": "TEXT NOT NULL DEFAULT ''",
        "parent_work_object_id": "TEXT NOT NULL DEFAULT ''",
        "source_type": "TEXT NOT NULL DEFAULT 'system'",
        "source_reference": "TEXT NOT NULL DEFAULT ''",
        "due_at": "TEXT NOT NULL DEFAULT ''",
        "started_at": "TEXT NOT NULL DEFAULT ''",
        "completed_at": "TEXT NOT NULL DEFAULT ''",
        "cancelled_at": "TEXT NOT NULL DEFAULT ''",
        "archived_at": "TEXT NOT NULL DEFAULT ''",
        "created_by": "TEXT NOT NULL DEFAULT 'legacy'",
    }
    for name, definition in additions.items():
        if name not in columns:
            cur.execute(
                f"ALTER TABLE nina_work_objects ADD COLUMN {name} {definition}"
            )
    _assert_compatible_columns(
        "nina_work_objects",
        _column_contract(conn, "nina_work_objects"),
        _WORK_OBJECT_BASE_CONTRACT,
    )
    duplicate_count = _duplicate_source_key_count(conn)
    if duplicate_count:
        raise MigrationPreflightError(
            "nina_work_objects_duplicate_workspace_source_key:"
            f"count={duplicate_count}"
        )
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_work_object_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_status TEXT NOT NULL DEFAULT '',
            to_status TEXT NOT NULL DEFAULT '',
            actor TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    statements = (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_source_key "
        "ON nina_work_objects (workspace_id, source_key)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_status "
        "ON nina_work_objects (workspace_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_type "
        "ON nina_work_objects (workspace_id, object_type)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_priority "
        "ON nina_work_objects (workspace_id, priority)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_assignment "
        "ON nina_work_objects (workspace_id, assigned_agent_assignment_id)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_due "
        "ON nina_work_objects (workspace_id, due_at)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_parent "
        "ON nina_work_objects (workspace_id, parent_work_object_id)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_events_workspace_object "
        "ON nina_work_object_events (workspace_id, object_id, created_at)",
    )
    for statement in statements:
        cur.execute(statement)
    cur.close()


def _expand_universal_work_objects_workspace_v1(conn):
    """Add the Constitution V6 workspace contract to the canonical table."""
    cur = conn.cursor()
    columns = set(_column_contract(conn, "nina_work_objects"))
    additions = {
        "owner_assignment_id": "TEXT NOT NULL DEFAULT ''",
        "worker_instance_id": "TEXT NOT NULL DEFAULT ''",
        "knowledge_refs_json": "TEXT NOT NULL DEFAULT '[]'",
        "source_channel": "TEXT NOT NULL DEFAULT ''",
        "updated_by": "TEXT NOT NULL DEFAULT 'legacy'",
        "closed_at": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            cur.execute(
                f"ALTER TABLE nina_work_objects ADD COLUMN {name} {definition}"
            )
    statements = (
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_owner "
        "ON nina_work_objects (workspace_id, owner_assignment_id)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_created "
        "ON nina_work_objects (workspace_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_nina_work_objects_workspace_worker "
        "ON nina_work_objects (workspace_id, worker_instance_id)",
    )
    for statement in statements:
        cur.execute(statement)
    cur.close()


def _create_channel_layer_v1(conn):
    """Add canonical channel identities and messages to existing channel truth."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_channel_connections (
            workspace_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'disconnected',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            secret_ref TEXT NOT NULL DEFAULT '',
            webhook_secret_ref TEXT NOT NULL DEFAULT '',
            app_secret_ref TEXT NOT NULL DEFAULT '',
            connect_token_hash TEXT NOT NULL DEFAULT '',
            connect_token_expires_at TEXT NOT NULL DEFAULT '',
            connect_token_used_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (workspace_id, channel)
        )
    """)
    columns = set(_column_contract(conn, "nina_channel_connections"))
    additions = {
        "workspace_id": "TEXT NOT NULL DEFAULT ''",
        "channel": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'disconnected'",
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
        "secret_ref": "TEXT NOT NULL DEFAULT ''",
        "webhook_secret_ref": "TEXT NOT NULL DEFAULT ''",
        "app_secret_ref": "TEXT NOT NULL DEFAULT ''",
        "connect_token_hash": "TEXT NOT NULL DEFAULT ''",
        "connect_token_expires_at": "TEXT NOT NULL DEFAULT ''",
        "connect_token_used_at": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "channel_connection_id": "TEXT NOT NULL DEFAULT ''",
        "channel_type": "TEXT NOT NULL DEFAULT ''",
        "display_name": "TEXT NOT NULL DEFAULT ''",
        "external_account_id": "TEXT NOT NULL DEFAULT ''",
        "capabilities_json": "TEXT NOT NULL DEFAULT '[]'",
        "configuration_reference": "TEXT NOT NULL DEFAULT ''",
        "created_by": "TEXT NOT NULL DEFAULT 'legacy'",
        "updated_by": "TEXT NOT NULL DEFAULT 'legacy'",
        "activated_at": "TEXT NOT NULL DEFAULT ''",
        "suspended_at": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            cur.execute(
                f"ALTER TABLE nina_channel_connections "
                f"ADD COLUMN {name} {definition}"
            )
    cur.execute(
        "SELECT workspace_id,channel,channel_connection_id "
        "FROM nina_channel_connections"
    )
    for workspace_id, channel, existing_id in cur.fetchall():
        if existing_id:
            continue
        channel_value = str(channel or "").lower()
        channel_type = (
            "WHATSAPP" if "whatsapp" in channel_value
            else channel_value.upper()
        )
        material = (
            f"{workspace_id}\0{channel_type}\0legacy:{channel_value}"
        ).encode()
        connection_id = "chc_" + hashlib.sha256(material).hexdigest()[:32]
        capabilities = (
            '["receive_text","send_text"]'
            if channel_type == "WEB" else '["receive_text"]'
        )
        cur.execute(_sql("""
            UPDATE nina_channel_connections
            SET channel_connection_id=%s,channel_type=%s,display_name=%s,
                capabilities_json=%s,configuration_reference=%s,
                created_by=%s,updated_by=%s
            WHERE workspace_id=%s AND channel=%s
        """), (
            connection_id, channel_type, channel_type.title(), capabilities,
            f"legacy:{channel_value}", "legacy", "legacy",
            workspace_id, channel,
        ))
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_channel_connection_id
        ON nina_channel_connections (channel_connection_id)
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_channel_external_identity
        ON nina_channel_connections (channel_type, external_account_id)
        WHERE external_account_id <> ''
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_channel_workspace_status
        ON nina_channel_connections (workspace_id, status)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_channel_messages (
            message_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            channel_connection_id TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (
                direction IN ('INBOUND','OUTBOUND')
            ),
            external_message_id TEXT NOT NULL DEFAULT '',
            thread_reference TEXT NOT NULL DEFAULT '',
            contact_id TEXT NOT NULL,
            external_sender_id TEXT NOT NULL DEFAULT '',
            message_type TEXT NOT NULL CHECK (
                message_type IN ('TEXT','SYSTEM','IMAGE','AUDIO','VIDEO','FILE')
            ),
            text_content TEXT NOT NULL DEFAULT '',
            safe_metadata_json TEXT NOT NULL DEFAULT '{}',
            received_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            deduplication_key TEXT NOT NULL,
            related_work_object_id TEXT NOT NULL DEFAULT '',
            processing_status TEXT NOT NULL CHECK (
                processing_status IN (
                    'RECEIVED','NORMALIZED','ROUTED','PROCESSED',
                    'FAILED','IGNORED'
                )
            ),
            related_inbound_message_id TEXT NOT NULL DEFAULT '',
            approval_reference TEXT NOT NULL DEFAULT '',
            execution_reference TEXT NOT NULL DEFAULT '',
            delivery_status TEXT NOT NULL DEFAULT '',
            external_delivery_id TEXT NOT NULL DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_channel_inbound_dedup
        ON nina_channel_messages (
            workspace_id,channel_connection_id,deduplication_key
        ) WHERE direction='INBOUND'
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_channel_messages_workspace_created
        ON nina_channel_messages (workspace_id, created_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_channel_messages_workspace_contact
        ON nina_channel_messages (workspace_id, contact_id, created_at)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_channel_message_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            channel_connection_id TEXT NOT NULL DEFAULT '',
            message_id TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            safe_metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_channel_events_workspace_created
        ON nina_channel_message_events (workspace_id, created_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_channel_events_message
        ON nina_channel_message_events (workspace_id, message_id, created_at)
    """)
    cur.close()


def _create_approval_layer(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_approvals (
            approval_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            initiative_id TEXT NOT NULL,
            reply_id TEXT NOT NULL,
            work_object_id TEXT NOT NULL,
            decision TEXT NOT NULL DEFAULT '' CHECK (
                decision IN ('','approved','dismissed','snoozed')
            ),
            status TEXT NOT NULL CHECK (
                status IN ('pending','approved','dismissed','snoozed')
            ),
            snoozed_until TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            decided_at TEXT NOT NULL DEFAULT '',
            decided_by TEXT NOT NULL DEFAULT '',
            decision_reason TEXT NOT NULL DEFAULT '',
            UNIQUE (workspace_id, initiative_id, reply_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_approval_events (
            event_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK (
                action IN ('created','approved','dismissed','snoozed','woken')
            ),
            actor TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_approvals_workspace_status
        ON nina_approvals (workspace_id, status, updated_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_approval_events_workspace
        ON nina_approval_events (workspace_id, created_at)
    """)
    cur.close()


def _create_execution_layer(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_executions (
            execution_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            approval_id TEXT NOT NULL,
            initiative_id TEXT NOT NULL,
            reply_id TEXT NOT NULL,
            work_object_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'pending','processing','succeeded','failed',
                    'unsupported','cancelled'
                )
            ),
            idempotency_key TEXT NOT NULL,
            result_type TEXT NOT NULL DEFAULT '',
            result_reference TEXT NOT NULL DEFAULT '',
            error_code TEXT NOT NULL DEFAULT '',
            error_summary TEXT NOT NULL DEFAULT '',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            requested_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT '',
            completed_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE (workspace_id, approval_id, action_type),
            UNIQUE (workspace_id, idempotency_key)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_execution_events (
            event_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'execution_created','execution_started',
                    'execution_succeeded','execution_failed',
                    'execution_unsupported'
                )
            ),
            previous_status TEXT NOT NULL DEFAULT '',
            new_status TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT '',
            safe_metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_executions_workspace_status
        ON nina_executions (workspace_id, status, updated_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_executions_approval
        ON nina_executions (workspace_id, approval_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_execution_events_workspace
        ON nina_execution_events (workspace_id, execution_id, created_at)
    """)
    cur.close()


def _create_autonomy_framework(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_autonomy_profiles (
            workspace_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL CHECK (
                mode IN ('MANUAL','SUGGEST','SEMI_AUTO','AUTO')
            ),
            updated_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_autonomy_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type='mode_changed'),
            old_mode TEXT NOT NULL DEFAULT '',
            new_mode TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_autonomy_events_workspace
        ON nina_autonomy_events (workspace_id, created_at)
    """)
    cur.close()


def _create_workspace_rolepacks(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_workspace_rolepacks (
            workspace_id TEXT PRIMARY KEY,
            rolepack_id TEXT NOT NULL,
            rolepack_version TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_rolepack_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type='rolepack_changed'
            ),
            old_rolepack TEXT NOT NULL DEFAULT '',
            new_rolepack TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_rolepack_events_workspace
        ON nina_rolepack_events (workspace_id, created_at)
    """)
    cur.close()


def _create_workspace_workers(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_workspace_workers (
            workspace_id TEXT PRIMARY KEY,
            worker_id TEXT NOT NULL,
            worker_version TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_worker_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type='worker_changed'
            ),
            old_worker TEXT NOT NULL DEFAULT '',
            new_worker TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_worker_events_workspace
        ON nina_worker_events (workspace_id, created_at)
    """)
    cur.close()


def _create_agent_assignment_workspace_v1(conn):
    """Expand the existing assignment store into the workspace instance model."""
    cur = conn.cursor()
    columns = (
        ("worker_instance_id", "TEXT"),
        ("workspace_id", "TEXT"),
        ("worker_key", "TEXT"),
        ("worker_version", "TEXT"),
        ("rolepack_version", "TEXT"),
        ("language", "TEXT NOT NULL DEFAULT 'en'"),
        ("timezone", "TEXT NOT NULL DEFAULT 'UTC'"),
        ("permissions_profile", "TEXT NOT NULL DEFAULT 'standard'"),
    )
    if persistence_backend.USE_POSTGRES:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema=current_schema()
                AND table_name='nina_agent_assignments'
        """)
        existing_columns = {str(row[0]) for row in cur.fetchall()}
    else:
        cur.execute("PRAGMA table_info(nina_agent_assignments)")
        existing_columns = {str(row[1]) for row in cur.fetchall()}
    for name, definition in columns:
        if name not in existing_columns:
            cur.execute(
                f"ALTER TABLE nina_agent_assignments "
                f"ADD COLUMN {name} {definition}"
            )
    cur.execute("""
        UPDATE nina_agent_assignments SET
            worker_instance_id=COALESCE(
                worker_instance_id, 'worker_instance_' || assignment_id
            ),
            workspace_id=COALESCE(workspace_id, tenant_id),
            worker_key=COALESCE(
                worker_key, ready_worker_definition_id
            ),
            worker_version=COALESCE(
                worker_version, definition_version
            ),
            rolepack_version=COALESCE(rolepack_version, '1.0.0')
        WHERE worker_instance_id IS NULL OR workspace_id IS NULL
            OR worker_key IS NULL OR worker_version IS NULL
            OR rolepack_version IS NULL
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            uq_nina_agent_assignments_active_workspace
        ON nina_agent_assignments (workspace_id)
        WHERE status='active'
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
            uq_nina_agent_assignments_worker_instance
        ON nina_agent_assignments (worker_instance_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignments_workspace
        ON nina_agent_assignments (workspace_id, updated_at)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_agent_assignment_events (
            event_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            worker_instance_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'assignment_created','assignment_updated',
                    'assignment_activated','assignment_suspended',
                    'assignment_archived'
                )
            ),
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_agent_assignment_events_workspace
        ON nina_agent_assignment_events (workspace_id, created_at)
    """)
    cur.close()


def _create_knowledge_vault_workspace_v1(conn):
    """Add the canonical workspace Vault, immutable versions and safe audit."""
    cur = conn.cursor()
    existing = set(_column_contract(conn, "nina_knowledge_items"))
    additions = (
        ("workspace_id", "TEXT"),
        ("knowledge_type", "TEXT"),
        ("source_reference", "TEXT NOT NULL DEFAULT ''"),
        ("tags_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("content_checksum", "TEXT"),
        ("updated_by", "TEXT NOT NULL DEFAULT ''"),
    )
    for name, definition in additions:
        if name not in existing:
            cur.execute(
                f"ALTER TABLE nina_knowledge_items "
                f"ADD COLUMN {name} {definition}"
            )
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_workspace_status
        ON nina_knowledge_items (workspace_id, status, updated_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_workspace_type
        ON nina_knowledge_items (workspace_id, knowledge_type)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_knowledge_versions (
            version_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            knowledge_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK (version >= 1),
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            knowledge_type TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_reference TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            content_checksum TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (workspace_id, knowledge_id, version)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_versions_workspace
        ON nina_knowledge_versions (workspace_id, knowledge_id, version)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nina_knowledge_events (
            event_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            knowledge_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (
                event_type IN (
                    'knowledge_created','knowledge_updated',
                    'knowledge_archived','knowledge_restored'
                )
            ),
            actor TEXT NOT NULL,
            old_version INTEGER,
            new_version INTEGER,
            safe_metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_nina_knowledge_events_workspace
        ON nina_knowledge_events (workspace_id, created_at)
    """)
    cur.close()


def _create_billing_v1(conn):
    cur = conn.cursor()
    statements = (
        """CREATE TABLE IF NOT EXISTS nina_billing_plans (plan_id TEXT PRIMARY KEY,code TEXT NOT NULL UNIQUE,display_name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,version INTEGER NOT NULL,is_public INTEGER NOT NULL DEFAULT 0,sort_order INTEGER NOT NULL DEFAULT 0,price_minor INTEGER NOT NULL DEFAULT 0,currency TEXT NOT NULL DEFAULT 'EUR',billing_period TEXT NOT NULL DEFAULT 'month',metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_billing_plan_entitlements (entitlement_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,entitlement_key TEXT NOT NULL,entitlement_type TEXT NOT NULL DEFAULT 'boolean',limit_value TEXT NOT NULL DEFAULT '',boolean_value INTEGER NOT NULL DEFAULT 0,text_value TEXT NOT NULL DEFAULT '',value_json TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(plan_id,entitlement_key))""",
        """CREATE TABLE IF NOT EXISTS nina_workspace_subscriptions (subscription_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,plan_id TEXT NOT NULL,status TEXT NOT NULL,billing_interval TEXT NOT NULL DEFAULT 'month',current_period_start TEXT NOT NULL DEFAULT '',current_period_end TEXT NOT NULL DEFAULT '',trial_start TEXT NOT NULL DEFAULT '',trial_end TEXT NOT NULL DEFAULT '',cancel_at_period_end INTEGER NOT NULL DEFAULT 0,cancelled_at TEXT NOT NULL DEFAULT '',provider TEXT NOT NULL DEFAULT 'manual',provider_customer_id TEXT NOT NULL DEFAULT '',provider_subscription_id TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,started_at TEXT NOT NULL,ends_at TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_workspace_entitlement_overrides (override_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,entitlement_key TEXT NOT NULL,entitlement_type TEXT NOT NULL DEFAULT 'boolean',limit_value TEXT NOT NULL DEFAULT '',boolean_value INTEGER NOT NULL DEFAULT 0,text_value TEXT NOT NULL DEFAULT '',value_json TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,reason TEXT NOT NULL DEFAULT '',starts_at TEXT NOT NULL DEFAULT '',expires_at TEXT NOT NULL DEFAULT '',created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_billing_usage_counters (counter_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,metric TEXT NOT NULL,period_start TEXT NOT NULL,period_end TEXT NOT NULL,quantity INTEGER NOT NULL DEFAULT 0,unit TEXT NOT NULL DEFAULT 'count',metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(workspace_id,metric,period_start,period_end))""",
        """CREATE TABLE IF NOT EXISTS nina_billing_usage_events (usage_event_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,metric TEXT NOT NULL,quantity INTEGER NOT NULL,unit TEXT NOT NULL DEFAULT 'count',source_type TEXT NOT NULL,source_id TEXT NOT NULL,idempotency_key TEXT NOT NULL,occurred_at TEXT NOT NULL,safe_metadata TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,UNIQUE(workspace_id,metric,idempotency_key))""",
        """CREATE TABLE IF NOT EXISTS nina_billing_events (event_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,event_type TEXT NOT NULL,actor TEXT NOT NULL,actor_type TEXT NOT NULL DEFAULT 'system',old_state_json TEXT NOT NULL DEFAULT '{}',new_state_json TEXT NOT NULL DEFAULT '{}',safe_metadata TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_billing_customers (mapping_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,provider TEXT NOT NULL,provider_customer_id TEXT NOT NULL,status TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(workspace_id,provider),UNIQUE(provider,provider_customer_id))""",
        """CREATE TABLE IF NOT EXISTS nina_billing_invoices (invoice_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,subscription_id TEXT NOT NULL DEFAULT '',provider TEXT NOT NULL,provider_invoice_id TEXT NOT NULL,provider_payment_id TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,subtotal_minor INTEGER NOT NULL DEFAULT 0,tax_minor INTEGER NOT NULL DEFAULT 0,amount_minor INTEGER NOT NULL,currency TEXT NOT NULL,issued_at TEXT NOT NULL,due_at TEXT NOT NULL DEFAULT '',paid_at TEXT NOT NULL DEFAULT '',invoice_url TEXT NOT NULL DEFAULT '',safe_metadata TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL DEFAULT '',UNIQUE(provider,provider_invoice_id))""",
        "CREATE INDEX IF NOT EXISTS idx_nina_billing_subscriptions_workspace ON nina_workspace_subscriptions(workspace_id,status)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_nina_billing_single_active_subscription ON nina_workspace_subscriptions(workspace_id) WHERE status='active'",
        "CREATE INDEX IF NOT EXISTS idx_nina_billing_overrides_workspace ON nina_workspace_entitlement_overrides(workspace_id,entitlement_key,active)",
        "CREATE INDEX IF NOT EXISTS idx_nina_billing_usage_workspace ON nina_billing_usage_events(workspace_id,metric,occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_nina_billing_events_workspace ON nina_billing_events(workspace_id,created_at)",
    )
    for statement in statements: cur.execute(statement)
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("INSERT INTO nina_billing_plans (plan_id,code,display_name,description,status,version,is_public,price_minor,currency,billing_period,created_at,updated_at) SELECT 'plan_legacy','legacy','Grandfathered','Compatibility plan for existing workspaces','active',1,0,0,'EUR','month',?,? WHERE NOT EXISTS (SELECT 1 FROM nina_billing_plans WHERE plan_id='plan_legacy')" if not persistence_backend.USE_POSTGRES else "INSERT INTO nina_billing_plans (plan_id,code,display_name,description,status,version,is_public,price_minor,currency,billing_period,created_at,updated_at) VALUES ('plan_legacy','legacy','Grandfathered','Compatibility plan for existing workspaces','active',1,0,0,'EUR','month',%s,%s) ON CONFLICT (plan_id) DO NOTHING", (now, now))
    for key, value in (("core.access", "true"), ("limit.work_objects", '"unlimited"'), ("limit.knowledge_items", '"unlimited"'), ("limit.workers", '"unlimited"'), ("limit.channels", '"unlimited"')):
        eid = "legacy_" + key.replace(".", "_")
        query = "INSERT INTO nina_billing_plan_entitlements (entitlement_id,plan_id,entitlement_key,value_json,created_at,updated_at) SELECT ?, 'plan_legacy', ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM nina_billing_plan_entitlements WHERE plan_id='plan_legacy' AND entitlement_key=?)" if not persistence_backend.USE_POSTGRES else "INSERT INTO nina_billing_plan_entitlements (entitlement_id,plan_id,entitlement_key,value_json,created_at,updated_at) VALUES (%s,'plan_legacy',%s,%s,%s,%s) ON CONFLICT (plan_id,entitlement_key) DO NOTHING"
        params = (eid,key,value,now,now,key) if not persistence_backend.USE_POSTGRES else (eid,key,value,now,now)
        cur.execute(query, params)
    cur.close()


def _create_web_push_notifications_v1(conn):
    cur = conn.cursor()
    statements = (
        """CREATE TABLE IF NOT EXISTS nina_web_push_subscriptions (subscription_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,endpoint_hash TEXT NOT NULL UNIQUE,encrypted_subscription_json TEXT NOT NULL,user_agent_safe TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,last_success_at TEXT NOT NULL DEFAULT '',last_failure_at TEXT NOT NULL DEFAULT '',failure_code TEXT NOT NULL DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS nina_web_push_deliveries (delivery_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,subscription_id TEXT NOT NULL,reminder_id TEXT NOT NULL,idempotency_key TEXT NOT NULL UNIQUE,status TEXT NOT NULL,failure_code TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_web_push_events (event_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,subscription_id TEXT NOT NULL,event_type TEXT NOT NULL,safe_metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_nina_web_push_subscription_owner ON nina_web_push_subscriptions(workspace_id,contact_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_nina_web_push_delivery_owner ON nina_web_push_deliveries(workspace_id,contact_id,reminder_id)",
        "CREATE INDEX IF NOT EXISTS idx_nina_web_push_events_workspace ON nina_web_push_events(workspace_id,created_at)",
    )
    for statement in statements:
        cur.execute(statement)
    cur.close()


def _create_vision_document_intelligence_v1(conn):
    cur = conn.cursor()
    statements = (
        """CREATE TABLE IF NOT EXISTS nina_files (file_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,conversation_id TEXT NOT NULL DEFAULT '',source_channel TEXT NOT NULL,original_filename TEXT NOT NULL,safe_filename TEXT NOT NULL,media_type TEXT NOT NULL,mime_type TEXT NOT NULL,size_bytes INTEGER NOT NULL,checksum_sha256 TEXT NOT NULL,storage_reference TEXT NOT NULL,status TEXT NOT NULL,processing_status TEXT NOT NULL,extraction_version TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,processed_at TEXT NOT NULL DEFAULT '',failure_code TEXT NOT NULL DEFAULT '',safe_metadata_json TEXT NOT NULL DEFAULT '{}',UNIQUE(workspace_id,contact_id,checksum_sha256))""",
        """CREATE TABLE IF NOT EXISTS nina_file_extractions (file_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,extraction_version TEXT NOT NULL,content_json TEXT NOT NULL,created_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_file_events (event_id TEXT PRIMARY KEY,file_id TEXT NOT NULL,workspace_id TEXT NOT NULL,event_type TEXT NOT NULL,actor TEXT NOT NULL,safe_metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL)""",
        "CREATE INDEX IF NOT EXISTS idx_nina_files_owner ON nina_files(workspace_id,contact_id,conversation_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_nina_files_status ON nina_files(workspace_id,status,processing_status)",
        "CREATE INDEX IF NOT EXISTS idx_nina_file_events_owner ON nina_file_events(workspace_id,file_id,created_at)",
    )
    for statement in statements: cur.execute(statement)
    cur.close()


def _create_web_research_v1(conn):
    cur = conn.cursor()
    statements = (
        """CREATE TABLE IF NOT EXISTS nina_web_research_sessions (session_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,conversation_id TEXT NOT NULL,intent_json TEXT NOT NULL,results_json TEXT NOT NULL,comparison_json TEXT NOT NULL,source_url TEXT NOT NULL,source_access TEXT NOT NULL,error_code TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS nina_saved_searches (search_id TEXT PRIMARY KEY,workspace_id TEXT NOT NULL,contact_id TEXT NOT NULL,name TEXT NOT NULL,search_type TEXT NOT NULL,query_json TEXT NOT NULL,target_domains TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(workspace_id,contact_id,query_json))""",
        "CREATE INDEX IF NOT EXISTS idx_nina_research_session_owner ON nina_web_research_sessions(workspace_id,contact_id,conversation_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_nina_saved_search_owner ON nina_saved_searches(workspace_id,contact_id,status,created_at)",
    )
    for statement in statements: cur.execute(statement)
    cur.close()


MIGRATIONS = (
    Migration(
        identifier="0001_shared_conversation_state",
        version=1,
        name="Create shared conversation state",
        phase=PHASE_EXPAND,
        operation=_create_conversation_state,
        checksum_source=(
            "0001|EXPAND|conversation_state|"
            "id,user_id,user_text,nina_text,intent,emotion,topic,created_at"
        ),
    ),
    Migration(
        identifier="0002_agent_assignment_v1",
        version=2,
        name="Create tenant-scoped Agent Assignment V1",
        phase=PHASE_EXPAND,
        operation=_create_agent_assignments,
        checksum_source=(
            "0002|EXPAND|nina_agent_assignments|"
            "assignment_id,tenant_id,ready_worker_definition_id,"
            "definition_version,primary_rolepack_id,display_name,status,"
            "configuration_json,permissions_json,assigned_by,created_at,"
            "updated_at,activated_at,suspended_at,archived_at|"
            "indexes:tenant,definition,status,tenant_status,tenant_definition"
        ),
    ),
    Migration(
        identifier="0003_knowledge_vault_v1",
        version=3,
        name="Create tenant-scoped Knowledge Vault V1",
        phase=PHASE_EXPAND,
        operation=_create_knowledge_vault,
        checksum_source=(
            "0003|EXPAND|nina_knowledge_items|"
            "knowledge_id,tenant_id,title,source_type,status,content,"
            "content_format,source_name,version,checksum,metadata_json,"
            "created_by,created_at,updated_at,activated_at,archived_at,"
            "parent_version|pk:tenant_knowledge_version|"
            "checks:source_type,status,content_format,version,parent_version|"
            "indexes:tenant,status,tenant_status,tenant_item_version,tenant_source"
        ),
    ),
    Migration(
        identifier="0004_universal_work_objects_v1",
        version=4,
        name="Expand canonical nina_work_objects for Universal Work Objects V1",
        phase=PHASE_EXPAND,
        operation=_create_universal_work_objects,
        checksum_source=(
            "0004-safety-v2|EXPAND|nina_work_objects+nina_work_object_events|"
            "adopt-existing-table|description,owner_type,owner_id,"
            "assigned_agent_assignment_id,parent_work_object_id,source_type,"
            "source_reference,due_at,started_at,completed_at,cancelled_at,"
            "archived_at,created_by|audit-events|"
            "indexes:tenant_status,tenant_type,tenant_priority,"
            "tenant_assignment,tenant_due,tenant_parent,event_object"
        ),
    ),
    Migration(
        identifier="0005_approval_layer_v1",
        version=5,
        name="Create tenant-scoped Approval Layer V1",
        phase=PHASE_EXPAND,
        operation=_create_approval_layer,
        checksum_source=(
            "0005|EXPAND|nina_approvals+nina_approval_events|"
            "decision-only-no-draft-copy|unique:workspace_initiative_reply|"
            "decisions:approved,dismissed,snoozed|"
            "statuses:pending,approved,dismissed,snoozed|audit-events"
        ),
    ),
    Migration(
        identifier="0006_execution_layer_v1",
        version=6,
        name="Create tenant-scoped Execution Layer V1",
        phase=PHASE_EXPAND,
        operation=_create_execution_layer,
        checksum_source=(
            "0006|EXPAND|nina_executions+nina_execution_events|"
            "allowlist:REMIND,NO_ACTION|"
            "unique:workspace_approval_action,workspace_idempotency|"
            "statuses:pending,processing,succeeded,failed,unsupported,cancelled|"
            "audit-events"
        ),
    ),
    Migration(
        identifier="0007_autonomy_framework_v1",
        version=7,
        name="Create tenant-scoped Autonomy Framework V1",
        phase=PHASE_EXPAND,
        operation=_create_autonomy_framework,
        checksum_source=(
            "0007|EXPAND|nina_autonomy_profiles+nina_autonomy_events|"
            "modes:MANUAL,SUGGEST,SEMI_AUTO,AUTO|"
            "decisions:ALLOW,DENY,REQUIRE_APPROVAL,UNSUPPORTED|"
            "one-profile-per-workspace|audit:mode_changed"
        ),
    ),
    Migration(
        identifier="0008_rolepack_system_v1",
        version=8,
        name="Create tenant-scoped RolePack selection V1",
        phase=PHASE_EXPAND,
        operation=_create_workspace_rolepacks,
        checksum_source=(
            "0008|EXPAND|nina_workspace_rolepacks+nina_rolepack_events|"
            "single-active-primary-rolepack-per-workspace|"
            "action-registry:REMIND,NO_ACTION,FOLLOW_UP,CHECK_IN,"
            "ASK_FOR_UPDATE|audit:rolepack_changed"
        ),
    ),
    Migration(
        identifier="0009_ready_worker_catalog_v1",
        version=9,
        name="Create tenant-scoped Ready Worker Catalog V1",
        phase=PHASE_EXPAND,
        operation=_create_workspace_workers,
        checksum_source=(
            "0009|EXPAND|nina_workspace_workers+nina_worker_events|"
            "single-active-worker-per-workspace|"
            "worker-composes-rolepacks|audit:worker_changed"
        ),
    ),
    Migration(
        identifier="0010_agent_assignment_v1",
        version=10,
        name="Expand Agent Assignment into stable workspace Worker instances",
        phase=PHASE_EXPAND,
        operation=_create_agent_assignment_workspace_v1,
        checksum_source=(
            "0010|EXPAND|nina_agent_assignments+"
            "nina_agent_assignment_events|"
            "stable-worker-instance|single-active-per-workspace|"
            "statuses:provisioning,active,suspended,archived|"
            "audit:create,update,activate,suspend,archive"
        ),
    ),
    Migration(
        identifier="0011_knowledge_vault_v1",
        version=11,
        name="Expand Knowledge Vault into canonical workspace knowledge",
        phase=PHASE_EXPAND,
        operation=_create_knowledge_vault_workspace_v1,
        checksum_source=(
            "0011|EXPAND|nina_knowledge_items+"
            "nina_knowledge_versions+nina_knowledge_events|"
            "workspace-canonical|types:FACT,INSTRUCTION,POLICY,PROCEDURE,"
            "PRODUCT,SERVICE,FAQ,NOTE|statuses:ACTIVE,ARCHIVED|"
            "provenance:MANUAL,IMPORTED_TEXT,SYSTEM|"
            "immutable-versions|safe-audit|deterministic-search"
        ),
    ),
    Migration(
        identifier="0012_universal_work_objects_v1",
        version=12,
        name="Complete the canonical workspace Universal Work Object contract",
        phase=PHASE_EXPAND,
        operation=_expand_universal_work_objects_workspace_v1,
        checksum_source=(
            "0012|EXPAND|canonical-nina_work_objects|"
            "owner_assignment_id,worker_instance_id,knowledge_refs_json,"
            "source_channel,updated_by,closed_at|"
            "indexes:workspace_owner,workspace_created,workspace_worker|"
            "no-copy,no-new-table,additive-only"
        ),
    ),
    Migration(
        identifier="0013_channel_layer_v1",
        version=13,
        name="Add canonical ONE NINA Channel Layer connections and messages",
        phase=PHASE_EXPAND,
        operation=_create_channel_layer_v1,
        checksum_source=(
            "0013|EXPAND|existing:nina_channel_connections|"
            "add:stable-connection-identity,registry,capabilities,safe-config-ref|"
            "new:nina_channel_messages+nina_channel_message_events|"
            "dedup:workspace,connection,key|contact+work+approval+execution-refs|"
            "no-secrets,no-provider-send,additive-only"
        ),
    ),
    Migration(
        identifier="0014_billing_v1", version=14,
        name="Create canonical tenant-scoped Billing V1",
        phase=PHASE_EXPAND, operation=_create_billing_v1,
        checksum_source=("0014|EXPAND|billing-plans+entitlements+subscriptions+"
            "overrides+usage-counters+usage-events+billing-events+customers+"
            "invoices|legacy-grandfathered|provider-independent|tenant-scoped"),
    ),
    Migration(
        identifier="0015_web_push_notifications_v1", version=15,
        name="Add optional Web Push subscriptions and delivery audit",
        phase=PHASE_EXPAND, operation=_create_web_push_notifications_v1,
        checksum_source=("0015|EXPAND|web-push-subscriptions+deliveries+events|"
            "encrypted-subscription|workspace-contact-scope|"
            "reminder-subscription-idempotency|optional-capability"),
    ),
    Migration(
        identifier="0016_vision_document_intelligence_v1", version=16,
        name="Add canonical workspace file identity and extracted content",
        phase=PHASE_EXPAND, operation=_create_vision_document_intelligence_v1,
        checksum_source=("0016|EXPAND|nina_files+nina_file_extractions+nina_file_events|"
            "workspace-contact-scope|checksum-idempotence|safe-storage-reference|"
            "unified-extracted-content|audit-events|additive-only"),
    ),
    Migration(
        identifier="0017_web_research_market_search_v1", version=17,
        name="Add controlled ONE NINA Web Research sessions and saved searches",
        phase=PHASE_EXPAND, operation=_create_web_research_v1,
        checksum_source=("0017|EXPAND|nina_web_research_sessions+nina_saved_searches|"
            "workspace-contact-conversation-scope|explicit-save|query-deduplication|"
            "public-source-provenance|additive-only"),
    ),
)


_TEXT_TYPES = {
    "text", "character varying", "character", "varchar", "char",
}
_WORK_OBJECT_BASE_CONTRACT = {
    "object_id": (_TEXT_TYPES, False),
    "workspace_id": (_TEXT_TYPES, False),
    "object_type": (_TEXT_TYPES, False),
    "title": (_TEXT_TYPES, False),
    "status": (_TEXT_TYPES, False),
    "source_key": (_TEXT_TYPES, True),
}
_WORK_OBJECT_V1_CONTRACT = {
    "description": (_TEXT_TYPES, False),
    "owner_type": (_TEXT_TYPES, False),
    "owner_id": (_TEXT_TYPES, False),
    "assigned_agent_assignment_id": (_TEXT_TYPES, False),
    "parent_work_object_id": (_TEXT_TYPES, False),
    "source_type": (_TEXT_TYPES, False),
    "source_reference": (_TEXT_TYPES, False),
    "due_at": (_TEXT_TYPES, False),
    "started_at": (_TEXT_TYPES, False),
    "completed_at": (_TEXT_TYPES, False),
    "cancelled_at": (_TEXT_TYPES, False),
    "archived_at": (_TEXT_TYPES, False),
    "created_by": (_TEXT_TYPES, False),
}
_WORK_OBJECT_WORKSPACE_V1_CONTRACT = {
    "owner_assignment_id": (_TEXT_TYPES, False),
    "worker_instance_id": (_TEXT_TYPES, False),
    "knowledge_refs_json": (_TEXT_TYPES, False),
    "source_channel": (_TEXT_TYPES, False),
    "updated_by": (_TEXT_TYPES, False),
    "closed_at": (_TEXT_TYPES, False),
}
_WORK_EVENT_CONTRACT = {
    name: (_TEXT_TYPES, False)
    for name in (
        "event_id", "workspace_id", "object_id", "event_type",
        "from_status", "to_status", "actor", "details_json", "created_at",
    )
}


def _column_contract(conn, table_name):
    cur = conn.cursor()
    try:
        if persistence_backend.USE_POSTGRES:
            cur.execute(
                """
                SELECT column_name,data_type,is_nullable
                FROM information_schema.columns
                WHERE table_schema=current_schema() AND table_name=%s
                """,
                (table_name,),
            )
            return {
                str(row[0]): {
                    "type": str(row[1]).lower(),
                    "nullable": str(row[2]).upper() == "YES",
                }
                for row in (cur.fetchall() or [])
            }
        cur.execute(f"PRAGMA table_info({table_name})")
        return {
            str(row[1]): {
                "type": str(row[2] or "").lower(),
                "nullable": not bool(row[3] or row[5]),
            }
            for row in (cur.fetchall() or [])
        }
    finally:
        cur.close()


def _assert_compatible_columns(
    table_name, actual, expected, *, allow_missing=False
):
    for name, (allowed_types, nullable) in expected.items():
        column = actual.get(name)
        if column is None:
            if allow_missing:
                continue
            raise MigrationPreflightError(
                f"nina_migration_schema_column_missing:{table_name}:{name}"
            )
        if column["type"] not in allowed_types:
            raise MigrationPreflightError(
                f"nina_migration_schema_type_conflict:{table_name}:{name}"
            )
        if not nullable and column["nullable"]:
            raise MigrationPreflightError(
                f"nina_migration_schema_nullability_conflict:{table_name}:{name}"
            )


def _duplicate_source_key_count(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT workspace_id,source_key
                FROM nina_work_objects
                WHERE source_key IS NOT NULL AND source_key <> ''
                GROUP BY workspace_id,source_key
                HAVING COUNT(*) > 1
            ) duplicate_keys
        """)
        return int((cur.fetchone() or [0])[0] or 0)
    finally:
        cur.close()


def preflight_release(require_postgres=True):
    """Read-only release gate; never creates, alters, indexes, or writes."""
    if require_postgres and (
        not persistence_backend.HOSTED or not persistence_backend.USE_POSTGRES
    ):
        raise MigrationPreflightError(
            "nina_migration_preflight_requires_hosted_postgresql"
        )
    conn = persistence_backend.connect()
    try:
        tables = _table_names(conn)
        required_tables = {LEDGER_TABLE, "nina_work_objects"}
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            raise MigrationPreflightError(
                "nina_migration_preflight_table_missing:"
                + ",".join(missing_tables)
            )
        ledger = _ledger_rows(conn)
        pending = []
        for migration in MIGRATIONS:
            row = ledger.get(migration.identifier)
            if row is None:
                pending.append(migration.identifier)
                continue
            if not row["success"]:
                raise MigrationPreflightError(
                    "nina_migration_preflight_prior_incomplete:"
                    + migration.identifier
                )
            if row["checksum"] != migration.checksum:
                raise MigrationPreflightError(
                    "nina_migration_preflight_prior_checksum:"
                    + migration.identifier
                )
        if MIGRATIONS[0].identifier in pending:
            raise MigrationPreflightError(
                "nina_migration_preflight_foundation_missing:"
                + MIGRATIONS[0].identifier
            )
        work_columns = _column_contract(conn, "nina_work_objects")
        _assert_compatible_columns(
            "nina_work_objects", work_columns, _WORK_OBJECT_BASE_CONTRACT
        )
        present_v1 = set(work_columns).intersection(_WORK_OBJECT_V1_CONTRACT)
        if present_v1 and present_v1 != set(_WORK_OBJECT_V1_CONTRACT):
            raise MigrationPreflightError(
                "nina_migration_preflight_partial_0004_columns"
            )
        if present_v1:
            _assert_compatible_columns(
                "nina_work_objects", work_columns, _WORK_OBJECT_V1_CONTRACT
            )
        duplicate_count = _duplicate_source_key_count(conn)
        if duplicate_count:
            raise MigrationPreflightError(
                "nina_work_objects_duplicate_workspace_source_key:"
                f"count={duplicate_count}"
            )
        if "nina_work_object_events" in tables:
            _assert_compatible_columns(
                "nina_work_object_events",
                _column_contract(conn, "nina_work_object_events"),
                _WORK_EVENT_CONTRACT,
            )
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM nina_work_objects")
            row_count = int((cur.fetchone() or [0])[0] or 0)
        finally:
            cur.close()
        conn.rollback()
        return {
            "ok": True,
            "backend": persistence_backend.backend_name(),
            "ledger_entries": len(ledger),
            "work_object_rows": row_count,
            "duplicate_source_keys": duplicate_count,
            "events_table": "present" if "nina_work_object_events" in tables
            else "absent",
            "pending_migrations": pending,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ledger_ddl():
    return f"""
        CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
            migration_identifier TEXT PRIMARY KEY,
            migration_version INTEGER NOT NULL,
            migration_name TEXT NOT NULL,
            migration_checksum TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            application_commit TEXT NOT NULL,
            migration_phase TEXT NOT NULL,
            success_state INTEGER NOT NULL
        )
    """


def _sql(statement):
    return persistence_backend.sql(statement)


def _begin_and_lock(conn):
    cur = conn.cursor()
    if persistence_backend.USE_POSTGRES:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))
    else:
        cur.execute("BEGIN IMMEDIATE")
    cur.close()


def _table_names(conn):
    cur = conn.cursor()
    if persistence_backend.USE_POSTGRES:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=current_schema()"
        )
    else:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    names = {str(row[0]) for row in (cur.fetchall() or [])}
    cur.close()
    return names


def _ledger_rows(conn):
    cur = conn.cursor()
    cur.execute(
        f"SELECT migration_identifier,migration_version,migration_name,"
        f"migration_checksum,applied_at,application_commit,migration_phase,"
        f"success_state FROM {LEDGER_TABLE} ORDER BY migration_version,migration_identifier"
    )
    rows = cur.fetchall() or []
    cur.close()
    return {
        str(row[0]): {
            "identifier": str(row[0]),
            "version": int(row[1]),
            "name": str(row[2]),
            "checksum": str(row[3]),
            "applied_at": str(row[4]),
            "application_commit": str(row[5]),
            "phase": str(row[6]),
            "success": bool(row[7]),
        }
        for row in rows
    }


def _record_success(conn, migration):
    cur = conn.cursor()
    cur.execute(
        _sql(f"""
            INSERT INTO {LEDGER_TABLE} (
                migration_identifier,migration_version,migration_name,
                migration_checksum,applied_at,application_commit,
                migration_phase,success_state
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """),
        (
            migration.identifier,
            migration.version,
            migration.name,
            migration.checksum,
            datetime.now(timezone.utc).isoformat(),
            commit_identifier(),
            migration.phase,
            1,
        ),
    )
    cur.close()


def _record_baseline(conn):
    baseline = Migration(
        BASELINE_ID,
        BASELINE_VERSION,
        BASELINE_NAME,
        PHASE_EXPAND,
        lambda _conn: None,
        "NinaOS current shared schema baseline V1",
    )
    _record_success(conn, baseline)


def _validate_or_adopt(conn):
    rows = _ledger_rows(conn)
    if rows:
        return "existing-ledger"
    tables = _table_names(conn) - {LEDGER_TABLE}
    if not tables:
        return "empty-database"
    present = EXPECTED_CURRENT_SHARED_TABLES.intersection(tables)
    missing = EXPECTED_CURRENT_SHARED_TABLES - tables
    if present and missing:
        raise AmbiguousSchemaError(
            "nina_migration_ambiguous_existing_schema:"
            f"present={len(present)}:missing={len(missing)}"
        )
    if not EXPECTED_CURRENT_SHARED_TABLES.issubset(tables):
        raise AmbiguousSchemaError(
            "nina_migration_unrecognized_existing_schema"
        )
    _record_baseline(conn)
    return "verified-baseline"


def _ordered(migrations):
    ordered = tuple(sorted(migrations, key=lambda item: (item.version, item.identifier)))
    identities = [item.identifier for item in ordered]
    versions = [item.version for item in ordered]
    if len(set(identities)) != len(identities) or len(set(versions)) != len(versions):
        raise MigrationError("nina_migration_registry_not_unique")
    return ordered


def run_migrations(phase=PHASE_EXPAND, allow_contract=False, migrations=None):
    phase = str(phase or "").upper()
    if phase not in {PHASE_EXPAND, PHASE_CONTRACT}:
        raise MigrationError("nina_migration_phase_invalid")
    if phase == PHASE_CONTRACT and not allow_contract:
        raise ContractMigrationForbidden("nina_contract_migration_requires_explicit_approval")

    registry = _ordered(MIGRATIONS if migrations is None else migrations)
    conn = persistence_backend.connect()
    applied = []
    skipped = []
    adoption = ""
    try:
        _begin_and_lock(conn)
        cur = conn.cursor()
        cur.execute(_ledger_ddl())
        cur.close()
        adoption = _validate_or_adopt(conn)
        existing = _ledger_rows(conn)
        for migration in registry:
            if migration.phase != phase:
                continue
            prior = existing.get(migration.identifier)
            if prior:
                if prior["checksum"] != migration.checksum:
                    raise MigrationChecksumError(
                        f"nina_migration_checksum_mismatch:{migration.identifier}"
                    )
                if not prior["success"]:
                    raise MigrationError(
                        f"nina_migration_prior_failure:{migration.identifier}"
                    )
                skipped.append(migration.identifier)
                continue
            migration.operation(conn)
            _record_success(conn, migration)
            applied.append(migration.identifier)
        conn.commit()
        return {
            "ok": True,
            "phase": phase,
            "adoption": adoption,
            "applied": applied,
            "skipped": skipped,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migration_status(migrations=None):
    registry = _ordered(MIGRATIONS if migrations is None else migrations)
    conn = persistence_backend.connect()
    try:
        required = [
            migration for migration in registry if migration.phase == PHASE_EXPAND
        ]
        if LEDGER_TABLE not in _table_names(conn):
            return {
                "ok": False,
                "ledger_present": False,
                "required_version": max((item.version for item in required), default=0),
                "applied_version": 0,
                "missing": [item.identifier for item in required],
                "checksum_mismatch": [],
            }
        rows = _ledger_rows(conn)
        missing = []
        mismatched = []
        for migration in required:
            row = rows.get(migration.identifier)
            if not row or not row["success"]:
                missing.append(migration.identifier)
            elif row["checksum"] != migration.checksum:
                mismatched.append(migration.identifier)
        return {
            "ok": not missing and not mismatched,
            "ledger_present": True,
            "required_version": max((item.version for item in required), default=0),
            "applied_version": max(
                (row["version"] for row in rows.values() if row["success"]),
                default=0,
            ),
            "missing": missing,
            "checksum_mismatch": mismatched,
        }
    finally:
        conn.close()


def assert_required_migrations_complete():
    status = migration_status()
    if not status["ok"]:
        raise IncompleteMigrationError(
            "nina_required_expand_migrations_incomplete:"
            f"missing={','.join(status['missing'])}:"
            f"checksum_mismatch={','.join(status['checksum_mismatch'])}"
        )
    return True
