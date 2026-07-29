"""Read-only production schema inventory and evidence-based ledger adoption."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

import persistence_backend
from deployment_compatibility import commit_identifier
from managed_migrations import (
    LEDGER_TABLE,
    MIGRATION_LOCK_KEY,
    MIGRATIONS,
    MigrationPreflightError,
    _begin_and_lock,
    _ledger_ddl,
    _ledger_rows,
)


CLASS_EXACT = "EXACTLY SATISFIED"
CLASS_PARTIAL = "PARTIALLY SATISFIED, SAFE TO EXPAND"
CLASS_CONFLICTING = "CONFLICTING"
CLASS_ABSENT = "NOT PRESENT"

TEXT_TYPES = {"text", "varchar", "character varying", "char", "character"}
INTEGER_TYPES = {"integer", "bigint", "smallint"}
TIMESTAMP_TYPES = {
    "timestamp", "timestamp without time zone", "timestamp with time zone",
    "datetime",
}

CONTRACTS = {
    "0001_shared_conversation_state": {
        "conversation_state": {
            "columns": {
                "id": (INTEGER_TYPES, False),
                "user_id": (TEXT_TYPES, True),
                "user_text": (TEXT_TYPES, True),
                "nina_text": (TEXT_TYPES, True),
                "intent": (TEXT_TYPES, True),
                "emotion": (TEXT_TYPES, True),
                "topic": (TEXT_TYPES, True),
                "created_at": (TIMESTAMP_TYPES | TEXT_TYPES, True),
            },
            "primary_key": ("id",),
        },
    },
    "0002_agent_assignment_v1": {
        "nina_agent_assignments": {
            "columns": {
                name: (TEXT_TYPES, nullable)
                for name, nullable in {
                    "assignment_id": False, "tenant_id": False,
                    "ready_worker_definition_id": False,
                    "definition_version": False, "primary_rolepack_id": False,
                    "display_name": False, "status": False,
                    "configuration_json": False, "permissions_json": False,
                    "assigned_by": False, "created_at": False,
                    "updated_at": False, "activated_at": False,
                    "suspended_at": False, "archived_at": False,
                }.items()
            },
            "primary_key": ("assignment_id",),
            "indexes": {
                "idx_nina_agent_assignments_tenant",
                "idx_nina_agent_assignments_definition",
                "idx_nina_agent_assignments_status",
                "idx_nina_agent_assignments_tenant_status",
                "idx_nina_agent_assignments_tenant_definition",
            },
        },
    },
    "0003_knowledge_vault_v1": {
        "nina_knowledge_items": {
            "columns": {
                **{
                    name: (TEXT_TYPES, nullable)
                    for name, nullable in {
                        "knowledge_id": False, "tenant_id": False,
                        "title": False, "source_type": False, "status": False,
                        "content": False, "content_format": False,
                        "source_name": False, "checksum": False,
                        "metadata_json": False, "created_by": False,
                        "created_at": False, "updated_at": False,
                        "activated_at": False, "archived_at": False,
                    }.items()
                },
                "version": (INTEGER_TYPES, False),
                "parent_version": (INTEGER_TYPES, True),
            },
            "primary_key": ("tenant_id", "knowledge_id", "version"),
            "indexes": {
                "idx_nina_knowledge_tenant",
                "idx_nina_knowledge_status",
                "idx_nina_knowledge_tenant_status",
                "idx_nina_knowledge_tenant_item_version",
                "idx_nina_knowledge_tenant_source",
            },
        },
    },
    "0004_universal_work_objects_v1": {
        "nina_work_objects": {
            "columns": {
                **{
                    name: (TEXT_TYPES, nullable)
                    for name, nullable in {
                        "object_id": False, "workspace_id": False,
                        "object_type": False, "title": False, "status": False,
                        "assigned_agent_id": True, "client_id": True,
                        "project_id": True, "priority": True,
                        "due_date": True, "linked_files_json": True,
                        "metadata_json": True, "origin_channel": True,
                        "origin_user_id": True, "created_at": False,
                        "updated_at": False,
                        "source_key": True, "description": False,
                        "owner_type": False, "owner_id": False,
                        "assigned_agent_assignment_id": False,
                        "parent_work_object_id": False, "source_type": False,
                        "source_reference": False, "due_at": False,
                        "started_at": False, "completed_at": False,
                        "cancelled_at": False, "archived_at": False,
                        "created_by": False,
                    }.items()
                },
            },
            "indexes": {
                "idx_nina_work_objects_workspace_source_key",
                "idx_nina_work_objects_workspace_status",
                "idx_nina_work_objects_workspace_type",
                "idx_nina_work_objects_workspace_priority",
                "idx_nina_work_objects_workspace_assignment",
                "idx_nina_work_objects_workspace_due",
                "idx_nina_work_objects_workspace_parent",
            },
        },
        "nina_work_object_events": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "event_id", "workspace_id", "object_id", "event_type",
                    "from_status", "to_status", "actor", "details_json",
                    "created_at",
                )
            },
            "primary_key": ("event_id",),
            "indexes": {"idx_nina_work_events_workspace_object"},
        },
    },
    "0005_approval_layer_v1": {
        "nina_approvals": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "approval_id", "workspace_id", "initiative_id",
                    "reply_id", "work_object_id", "decision", "status",
                    "snoozed_until", "created_at", "updated_at",
                    "decided_at", "decided_by", "decision_reason",
                )
            },
            "primary_key": ("approval_id",),
            "indexes": {"idx_nina_approvals_workspace_status"},
        },
        "nina_approval_events": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "event_id", "approval_id", "workspace_id", "action",
                    "actor", "reason", "created_at",
                )
            },
            "primary_key": ("event_id",),
            "indexes": {"idx_nina_approval_events_workspace"},
        },
    },
    "0006_execution_layer_v1": {
        "nina_executions": {
            "columns": {
                **{
                    name: (TEXT_TYPES, False)
                    for name in (
                        "execution_id", "workspace_id", "approval_id",
                        "initiative_id", "reply_id", "work_object_id",
                        "action_type", "status", "idempotency_key",
                        "result_type", "result_reference", "error_code",
                        "error_summary", "requested_by", "created_at",
                        "started_at", "completed_at", "updated_at",
                    )
                },
                "attempt_count": (INTEGER_TYPES, False),
            },
            "primary_key": ("execution_id",),
            "indexes": {
                "idx_nina_executions_workspace_status",
                "idx_nina_executions_approval",
            },
        },
        "nina_execution_events": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "event_id", "execution_id", "workspace_id",
                    "event_type", "previous_status", "new_status", "actor",
                    "safe_metadata", "created_at",
                )
            },
            "primary_key": ("event_id",),
            "indexes": {"idx_nina_execution_events_workspace"},
        },
    },
    "0007_autonomy_framework_v1": {
        "nina_autonomy_profiles": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "workspace_id", "mode", "updated_by",
                    "created_at", "updated_at",
                )
            },
            "primary_key": ("workspace_id",),
            "indexes": set(),
        },
        "nina_autonomy_events": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "event_id", "workspace_id", "event_type", "old_mode",
                    "new_mode", "actor", "created_at",
                )
            },
            "primary_key": ("event_id",),
            "indexes": {"idx_nina_autonomy_events_workspace"},
        },
    },
    "0008_rolepack_system_v1": {
        "nina_workspace_rolepacks": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "workspace_id", "rolepack_id", "rolepack_version",
                    "updated_by", "created_at", "updated_at",
                )
            },
            "primary_key": ("workspace_id",),
            "indexes": set(),
        },
        "nina_rolepack_events": {
            "columns": {
                name: (TEXT_TYPES, False)
                for name in (
                    "event_id", "workspace_id", "event_type",
                    "old_rolepack", "new_rolepack", "actor", "created_at",
                )
            },
            "primary_key": ("event_id",),
            "indexes": {"idx_nina_rolepack_events_workspace"},
        },
    },
}


def _execute_rows(conn, sql, params=()):
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return cur.fetchall() or []
    finally:
        cur.close()


def _quote_identifier(value):
    return '"' + str(value).replace('"', '""') + '"'


def _safe_default(value):
    if value is None:
        return None
    text = str(value)
    if "nextval(" in text or "CURRENT_TIMESTAMP" in text.upper():
        return text
    if re.search(r"'[^']*'", text):
        return re.sub(r"'[^']*'", "'<literal>'", text)
    return text[:160]


def _sqlite_inventory(conn):
    tables = [
        row[0] for row in _execute_rows(
            conn,
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        )
    ]
    result = {}
    for table in tables:
        columns = {}
        primary = []
        for row in _execute_rows(conn, f"PRAGMA table_info({_quote_identifier(table)})"):
            columns[str(row[1])] = {
                "type": str(row[2] or "").lower(),
                "nullable": not bool(row[3] or row[5]),
                "default": _safe_default(row[4]),
                "identity": bool(row[5] and "int" in str(row[2]).lower()),
            }
            if row[5]:
                primary.append((int(row[5]), str(row[1])))
        indexes = []
        unique_constraints = []
        for index in _execute_rows(
            conn, f"PRAGMA index_list({_quote_identifier(table)})"
        ):
            name = str(index[1])
            cols = [
                str(item[2]) for item in _execute_rows(
                    conn, f"PRAGMA index_info({_quote_identifier(name)})"
                )
            ]
            indexes.append({"name": name, "columns": cols, "unique": bool(index[2])})
            if index[2]:
                unique_constraints.append({"name": name, "columns": cols})
        foreign_keys = [
            {
                "name": f"sqlite_fk_{row[0]}",
                "columns": [str(row[3])],
                "referenced_table": str(row[2]),
                "referenced_columns": [str(row[4])],
            }
            for row in _execute_rows(
                conn, f"PRAGMA foreign_key_list({_quote_identifier(table)})"
            )
        ]
        row_count = int(_execute_rows(
            conn, f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
        )[0][0])
        result[table] = {
            "columns": columns,
            "primary_key": [name for _, name in sorted(primary)],
            "unique_constraints": unique_constraints,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count,
            "sequence": [],
        }
    return {
        "engine": "sqlite",
        "postgresql_version": None,
        "schema": "main",
        "search_path": "main",
        "tables": result,
    }


def _postgres_inventory(conn):
    version = str(_execute_rows(conn, "SHOW server_version")[0][0])
    schema = str(_execute_rows(conn, "SELECT current_schema()")[0][0])
    search_path = str(_execute_rows(conn, "SHOW search_path")[0][0])
    table_names = [
        str(row[0]) for row in _execute_rows(
            conn,
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=current_schema() AND table_type='BASE TABLE' "
            "ORDER BY table_name",
        )
    ]
    result = {}
    for table in table_names:
        column_rows = _execute_rows(
            conn,
            """
            SELECT column_name,data_type,is_nullable,column_default,
                   is_identity,identity_generation
            FROM information_schema.columns
            WHERE table_schema=current_schema() AND table_name=%s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        columns = {
            str(row[0]): {
                "type": str(row[1]).lower(),
                "nullable": str(row[2]).upper() == "YES",
                "default": _safe_default(row[3]),
                "identity": str(row[4]).upper() == "YES",
                "identity_generation": None if row[5] is None else str(row[5]),
            }
            for row in column_rows
        }
        constraint_rows = _execute_rows(
            conn,
            """
            SELECT tc.constraint_name,tc.constraint_type,kcu.column_name,
                   kcu.ordinal_position,ccu.table_name,ccu.column_name
            FROM information_schema.table_constraints tc
            LEFT JOIN information_schema.key_column_usage kcu
              ON tc.constraint_schema=kcu.constraint_schema
             AND tc.constraint_name=kcu.constraint_name
            LEFT JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_schema=ccu.constraint_schema
             AND tc.constraint_name=ccu.constraint_name
            WHERE tc.table_schema=current_schema() AND tc.table_name=%s
            ORDER BY tc.constraint_name,kcu.ordinal_position
            """,
            (table,),
        )
        grouped = {}
        for row in constraint_rows:
            item = grouped.setdefault(
                (str(row[0]), str(row[1])),
                {"columns": [], "referenced_table": row[4],
                 "referenced_columns": []},
            )
            if row[2] is not None:
                item["columns"].append(str(row[2]))
            if row[5] is not None:
                item["referenced_columns"].append(str(row[5]))
        primary = []
        uniques = []
        foreign_keys = []
        for (name, kind), item in grouped.items():
            if kind == "PRIMARY KEY":
                primary = item["columns"]
            elif kind == "UNIQUE":
                uniques.append({"name": name, "columns": item["columns"]})
            elif kind == "FOREIGN KEY":
                foreign_keys.append({
                    "name": name, "columns": item["columns"],
                    "referenced_table": str(item["referenced_table"]),
                    "referenced_columns": item["referenced_columns"],
                })
        indexes = [
            {"name": str(row[0]), "definition": str(row[1])}
            for row in _execute_rows(
                conn,
                "SELECT indexname,indexdef FROM pg_indexes "
                "WHERE schemaname=current_schema() AND tablename=%s "
                "ORDER BY indexname",
                (table,),
            )
        ]
        row_count = int(_execute_rows(
            conn, f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
        )[0][0])
        sequence = []
        for column, detail in columns.items():
            default = detail.get("default") or ""
            if detail.get("identity") or "nextval(" in default:
                maximum = _execute_rows(
                    conn,
                    f"SELECT MAX({_quote_identifier(column)}) "
                    f"FROM {_quote_identifier(table)}",
                )[0][0]
                serial_name = _execute_rows(
                    conn, "SELECT pg_get_serial_sequence(%s,%s)",
                    (table, column),
                )[0][0]
                current = None
                if serial_name:
                    parts = str(serial_name).split(".", 1)
                    qualified = ".".join(_quote_identifier(p) for p in parts)
                    current = _execute_rows(
                        conn, f"SELECT last_value FROM {qualified}"
                    )[0][0]
                sequence.append({
                    "column": column,
                    "max_id": None if maximum is None else int(maximum),
                    "current_value": None if current is None else int(current),
                    "identity": bool(detail.get("identity")),
                    "default_uses_sequence": "nextval(" in default,
                })
        result[table] = {
            "columns": columns,
            "primary_key": primary,
            "unique_constraints": uniques,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count,
            "sequence": sequence,
        }
    return {
        "engine": "postgresql",
        "postgresql_version": version,
        "schema": schema,
        "search_path": search_path,
        "tables": result,
    }


def inspect_production_schema(conn=None, require_postgres=True):
    owned = conn is None
    conn = persistence_backend.connect() if owned else conn
    try:
        if require_postgres and (
            not persistence_backend.HOSTED or not persistence_backend.USE_POSTGRES
        ):
            raise MigrationPreflightError(
                "nina_schema_inspection_requires_hosted_postgresql"
            )
        report = (
            _postgres_inventory(conn)
            if persistence_backend.USE_POSTGRES else _sqlite_inventory(conn)
        )
        report["fingerprint"] = schema_fingerprint(report)
        return report
    finally:
        if owned:
            conn.close()


def _structural_inventory(inventory):
    return {
        "engine": inventory["engine"],
        "schema": inventory["schema"],
        "tables": {
            name: {
                key: value for key, value in details.items()
                if key not in {"row_count", "sequence"}
            }
            for name, details in sorted(inventory["tables"].items())
            if name != LEDGER_TABLE
        },
    }


def schema_fingerprint(inventory):
    payload = json.dumps(
        _structural_inventory(inventory),
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _classify_table(actual, expected):
    if actual is None:
        return CLASS_ABSENT, ["table_missing"]
    missing = []
    conflicts = []
    for name, (allowed_types, nullable) in expected.get("columns", {}).items():
        column = actual["columns"].get(name)
        if column is None:
            missing.append(f"column_missing:{name}")
            continue
        if column["type"] not in allowed_types:
            conflicts.append(f"type_conflict:{name}")
        if not nullable and column["nullable"]:
            conflicts.append(f"nullability_conflict:{name}")
    expected_pk = tuple(expected.get("primary_key", ()))
    if expected_pk and tuple(actual.get("primary_key", ())) != expected_pk:
        conflicts.append("primary_key_conflict")
    actual_indexes = {item["name"] for item in actual.get("indexes", [])}
    missing_indexes = sorted(expected.get("indexes", set()) - actual_indexes)
    missing.extend(f"index_missing:{name}" for name in missing_indexes)
    if conflicts:
        return CLASS_CONFLICTING, conflicts
    if missing:
        return CLASS_PARTIAL, missing
    return CLASS_EXACT, []


def classify_migrations(inventory):
    output = {}
    for migration in MIGRATIONS:
        table_results = {}
        classes = []
        for table, expected in CONTRACTS[migration.identifier].items():
            classification, reasons = _classify_table(
                inventory["tables"].get(table), expected
            )
            table_results[table] = {
                "classification": classification,
                "reasons": reasons,
            }
            classes.append(classification)
        if CLASS_CONFLICTING in classes:
            overall = CLASS_CONFLICTING
        elif all(item == CLASS_ABSENT for item in classes):
            overall = CLASS_ABSENT
        elif all(item == CLASS_EXACT for item in classes):
            overall = CLASS_EXACT
        else:
            overall = CLASS_PARTIAL
        output[migration.identifier] = {
            "name": migration.name,
            "classification": overall,
            "tables": table_results,
        }
    return output


def data_safety_checks(conn, inventory):
    checks = []
    tables = inventory["tables"]
    work = tables.get("nina_work_objects")
    if work and {"workspace_id", "source_key"}.issubset(work["columns"]):
        count = int(_execute_rows(
            conn,
            """
            SELECT COUNT(*) FROM (
              SELECT workspace_id,source_key FROM nina_work_objects
              WHERE source_key IS NOT NULL AND source_key <> ''
              GROUP BY workspace_id,source_key HAVING COUNT(*) > 1
            ) duplicates
            """,
        )[0][0])
        checks.append({
            "type": "duplicate_workspace_source_key", "count": count,
            "conflict": count > 0,
        })
    duplicate_contracts = {
        "nina_work_objects": ("object_id",),
        "nina_agent_assignments": ("assignment_id",),
        "nina_knowledge_items": ("tenant_id", "knowledge_id", "version"),
    }
    for table, key_columns in duplicate_contracts.items():
        details = tables.get(table)
        if not details or not set(key_columns).issubset(details["columns"]):
            continue
        columns = ",".join(_quote_identifier(item) for item in key_columns)
        count = int(_execute_rows(
            conn,
            f"SELECT COUNT(*) FROM (SELECT {columns} "
            f"FROM {_quote_identifier(table)} GROUP BY {columns} "
            "HAVING COUNT(*) > 1) duplicate_natural_keys",
        )[0][0])
        checks.append({
            "type": "duplicate_natural_key", "table": table,
            "columns": list(key_columns), "count": count,
            "conflict": count > 0,
        })
    allowed_statuses = {
        "nina_agent_assignments": {
            "draft", "active", "suspended", "archived",
        },
        "nina_knowledge_items": {"draft", "active", "archived"},
    }
    for table, allowed in allowed_statuses.items():
        details = tables.get(table)
        if not details or "status" not in details["columns"]:
            continue
        placeholders = ",".join("?" for _ in allowed)
        sql = (
            f"SELECT COUNT(*) FROM {_quote_identifier(table)} "
            f"WHERE status IS NULL OR status NOT IN ({placeholders})"
        )
        if persistence_backend.USE_POSTGRES:
            sql = sql.replace("?", "%s")
        count = int(_execute_rows(conn, sql, tuple(sorted(allowed)))[0][0])
        checks.append({
            "type": "invalid_status", "table": table, "count": count,
            "conflict": count > 0,
        })
    for identifier, table_contracts in CONTRACTS.items():
        for table, contract in table_contracts.items():
            details = tables.get(table)
            if not details:
                continue
            for column, (_, nullable) in contract["columns"].items():
                actual = details["columns"].get(column)
                if nullable or not actual or not actual["nullable"]:
                    continue
                count = int(_execute_rows(
                    conn,
                    f"SELECT COUNT(*) FROM {_quote_identifier(table)} "
                    f"WHERE {_quote_identifier(column)} IS NULL",
                )[0][0])
                checks.append({
                    "type": "nulls_before_not_null", "migration": identifier,
                    "table": table, "column": column, "count": count,
                    "conflict": count > 0,
                })
    for table, details in tables.items():
        for foreign_key in details.get("foreign_keys", []):
            if len(foreign_key["columns"]) != 1:
                continue
            source = foreign_key["columns"][0]
            target_table = foreign_key["referenced_table"]
            target_columns = foreign_key["referenced_columns"]
            if len(target_columns) != 1 or target_table not in tables:
                continue
            target = target_columns[0]
            sql = (
                f"SELECT COUNT(*) FROM {_quote_identifier(table)} child "
                f"LEFT JOIN {_quote_identifier(target_table)} parent "
                f"ON child.{_quote_identifier(source)}="
                f"parent.{_quote_identifier(target)} "
                f"WHERE child.{_quote_identifier(source)} IS NOT NULL "
                f"AND parent.{_quote_identifier(target)} IS NULL"
            )
            count = int(_execute_rows(conn, sql)[0][0])
            checks.append({
                "type": "orphan_foreign_key", "table": table,
                "constraint": foreign_key["name"], "count": count,
                "conflict": count > 0,
            })
    for table, details in tables.items():
        for sequence in details.get("sequence", []):
            maximum = sequence["max_id"]
            current = sequence.get("current_value")
            conflict = (
                maximum is not None and current is not None and current < maximum
            )
            checks.append({
                "type": "sequence_identity_state", "table": table,
                "column": sequence["column"], "max_id": maximum,
                "current_value": current, "conflict": conflict,
            })
    return checks


def adoption_plan(conn=None, require_postgres=True):
    owned = conn is None
    conn = persistence_backend.connect() if owned else conn
    try:
        inventory = inspect_production_schema(
            conn=conn, require_postgres=require_postgres
        )
        classifications = classify_migrations(inventory)
        checks = data_safety_checks(conn, inventory)
        conflicts = [
            {"scope": identifier, "details": item}
            for identifier, item in classifications.items()
            if item["classification"] == CLASS_CONFLICTING
        ]
        conflicts.extend(
            {"scope": "data_safety", "details": item}
            for item in checks if item.get("conflict")
        )
        adoptable = [
            identifier for identifier, item in classifications.items()
            if item["classification"] == CLASS_EXACT
        ]
        repairs = [
            identifier for identifier, item in classifications.items()
            if item["classification"] in {CLASS_PARTIAL, CLASS_ABSENT}
        ]
        return {
            "ok": not conflicts,
            "mode": "plan",
            "fingerprint": inventory["fingerprint"],
            "inventory": inventory,
            "migrations": classifications,
            "data_safety_checks": checks,
            "conflicts": conflicts,
            "adoptable_migrations": adoptable,
            "requires_expand": repairs,
        }
    finally:
        if owned:
            conn.close()


def adopt_baseline_apply(expected_fingerprint, conn=None, require_postgres=True):
    owned = conn is None
    conn = persistence_backend.connect() if owned else conn
    try:
        initial = adoption_plan(conn=conn, require_postgres=require_postgres)
        if not initial["ok"]:
            raise MigrationPreflightError("nina_schema_adoption_conflict")
        if initial["fingerprint"] != expected_fingerprint:
            raise MigrationPreflightError(
                "nina_schema_adoption_fingerprint_changed"
            )
        _begin_and_lock(conn)
        locked = adoption_plan(conn=conn, require_postgres=require_postgres)
        if not locked["ok"] or locked["fingerprint"] != expected_fingerprint:
            raise MigrationPreflightError(
                "nina_schema_adoption_fingerprint_changed"
            )
        cur = conn.cursor()
        cur.execute(_ledger_ddl())
        cur.close()
        existing = _ledger_rows(conn)
        adopted = []
        for migration in MIGRATIONS:
            if migration.identifier not in locked["adoptable_migrations"]:
                continue
            row = existing.get(migration.identifier)
            if row:
                if row["checksum"] != migration.checksum or not row["success"]:
                    raise MigrationPreflightError(
                        "nina_schema_adoption_existing_ledger_conflict:"
                        + migration.identifier
                    )
                continue
            cur = conn.cursor()
            cur.execute(
                persistence_backend.sql(
                    f"""
                    INSERT INTO {LEDGER_TABLE} (
                      migration_identifier,migration_version,migration_name,
                      migration_checksum,applied_at,application_commit,
                      migration_phase,success_state
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """
                ),
                (
                    migration.identifier, migration.version, migration.name,
                    migration.checksum, datetime.now(timezone.utc).isoformat(),
                    "schema-adoption:" + commit_identifier(),
                    migration.phase, 1,
                ),
            )
            cur.close()
            adopted.append(migration.identifier)
        final_inventory = inspect_production_schema(
            conn=conn, require_postgres=require_postgres
        )
        if final_inventory["fingerprint"] != expected_fingerprint:
            raise MigrationPreflightError(
                "nina_schema_adoption_fingerprint_changed"
            )
        conn.commit()
        return {
            "ok": True, "mode": "apply",
            "fingerprint": expected_fingerprint,
            "adopted_migrations": adopted,
            "business_schema_changed": False,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        if owned:
            conn.close()


def public_report(plan):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": plan["ok"],
        "fingerprint": plan["fingerprint"],
        "inventory": plan["inventory"],
        "migrations": plan["migrations"],
        "data_safety_checks": plan["data_safety_checks"],
        "conflicts": plan["conflicts"],
        "adoptable_migrations": plan["adoptable_migrations"],
        "requires_expand": plan["requires_expand"],
    }


def write_reports(plan, json_path, markdown_path):
    report = public_report(plan)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    lines = [
        "# NinaOS Production Schema Adoption Report", "",
        f"- Result: {'PASS' if plan['ok'] else 'STOP'}",
        f"- Schema fingerprint: `{plan['fingerprint']}`",
        f"- Engine: `{plan['inventory']['engine']}`",
        f"- Schema: `{plan['inventory']['schema']}`", "",
        "## Migration classifications", "",
    ]
    for identifier, item in plan["migrations"].items():
        lines.append(
            f"- `{identifier}`: **{item['classification']}**"
        )
    lines.extend(["", "## Conflicts", ""])
    if plan["conflicts"]:
        for conflict in plan["conflicts"]:
            lines.append(
                f"- `{conflict['scope']}`: "
                f"`{conflict['details'].get('type', 'schema_contract')}`"
            )
    else:
        lines.append("- None.")
    lines.extend([
        "", "## Adoption plan", "",
        "- Ledger adoption candidates: "
        + (", ".join(plan["adoptable_migrations"]) or "none"),
        "- Pending additive EXPAND: "
        + (", ".join(plan["requires_expand"]) or "none"),
        "",
        "This report contains schema metadata and aggregate counts only. "
        "Adoption does not migrate or modify business data.",
    ])
    with open(markdown_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
