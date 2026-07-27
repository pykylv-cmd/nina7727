"""Immutable, version-aware deployable Ready Worker definition catalog."""

from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from types import MappingProxyType


READY_WORKER_DEFINITION_REGISTRY_VERSION = "1.0"
_VERSION_RE = re.compile(r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*)){0,2}$")
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VISIBILITY = frozenset({"public", "private", "internal"})


class ReadyWorkerCatalogError(RuntimeError):
    pass


class ReadyWorkerValidationError(ReadyWorkerCatalogError):
    pass


class DuplicateReadyWorkerError(ReadyWorkerCatalogError):
    pass


class ReadyWorkerNotFoundError(ReadyWorkerCatalogError):
    pass


class ReadyWorkerVersionConflictError(ReadyWorkerCatalogError):
    pass


class ReadyWorkerCatalogNotHealthyError(ReadyWorkerCatalogError):
    pass


def _version_key(version):
    value = str(version or "").strip()
    if not _VERSION_RE.fullmatch(value):
        raise ReadyWorkerValidationError(
            f"ready_worker_version_invalid:{value}"
        )
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (3 - len(parts))


def compare_ready_worker_versions(left, right):
    left_key = _version_key(left)
    right_key = _version_key(right)
    return (left_key > right_key) - (left_key < right_key)


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({
            str(key): _freeze(item) for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, (dict, MappingProxyType)):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_thaw(item) for item in value]
    return value


def _json_safe(value):
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _unique(values, field_name):
    normalized = tuple(
        str(value or "").strip() for value in (values or ())
    )
    if any(not value for value in normalized):
        raise ReadyWorkerValidationError(
            f"ready_worker_{field_name}_blank"
        )
    if len(set(normalized)) != len(normalized):
        raise ReadyWorkerValidationError(
            f"ready_worker_{field_name}_duplicate"
        )
    return normalized


@dataclass(frozen=True)
class RolePackBinding:
    rolepack_id: str
    version: str
    order: int


@dataclass(frozen=True)
class ReadyWorkerDefinition:
    worker_id: str
    name: str
    version: str
    description: str
    category: str
    rolepack_bindings: tuple
    primary_rolepack_id: str
    required_platform_capabilities: tuple
    supported_channels: tuple
    supported_languages: tuple
    default_language: str
    allowed_tools: tuple
    supported_work_object_types: tuple
    provisioning_defaults: object
    operating_safeguards: tuple
    customer_visibility: str
    enabled: bool
    metadata: object


class ReadyWorkerCatalog:
    """Thread-safe least-privilege RolePack composition registry.

    Channels, languages, tools and Work Object types use intersection
    semantics across bindings. A worker may narrow but never broaden those
    permissions. Required capabilities equal the union of the bound RolePacks'
    mandatory capabilities. Every binding pins an exact version and has a
    unique explicit order.
    """

    def __init__(self, rolepack_registry=None, platform_registry=None):
        self._lock = threading.RLock()
        self._definitions = OrderedDict()
        self._initialized = False
        self._rolepack_registry = rolepack_registry
        self._platform_registry = platform_registry

    @property
    def initialized(self):
        with self._lock:
            return self._initialized

    def _roles(self):
        if self._rolepack_registry is not None:
            return self._rolepack_registry
        from rolepack_system import get_rolepack_registry

        return get_rolepack_registry()

    def _platform(self):
        if self._platform_registry is not None:
            return self._platform_registry
        from platform_core import get_platform_registry

        return get_platform_registry()

    @staticmethod
    def _binding(value):
        if isinstance(value, RolePackBinding):
            source = {
                "rolepack_id": value.rolepack_id,
                "version": value.version,
                "order": value.order,
            }
        elif isinstance(value, dict):
            source = dict(value)
        else:
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_binding_invalid"
            )
        rolepack_id = str(source.get("rolepack_id") or "").strip()
        version = str(source.get("version") or "").strip()
        order = source.get("order")
        if not rolepack_id:
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_binding_id_blank"
            )
        try:
            from rolepack_system import compare_rolepack_versions

            compare_rolepack_versions(version, version)
        except Exception as exc:
            raise ReadyWorkerValidationError(
                f"ready_worker_rolepack_version_invalid:{version}"
            ) from exc
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_binding_order_invalid"
            )
        return RolePackBinding(rolepack_id, version, order)

    @classmethod
    def _normalize(cls, definition=None, **values):
        if isinstance(definition, ReadyWorkerDefinition):
            if values:
                raise TypeError(
                    "ready_worker_and_values_are_mutually_exclusive"
                )
            source = {
                name: getattr(definition, name)
                for name in ReadyWorkerDefinition.__dataclass_fields__
            }
            source["provisioning_defaults"] = _thaw(
                definition.provisioning_defaults
            )
            source["metadata"] = _thaw(definition.metadata)
        elif isinstance(definition, dict):
            source = dict(definition)
            source.update(values)
        elif definition is None:
            source = dict(values)
        else:
            raise TypeError(
                "ready_worker_must_be_mapping_or_definition"
            )

        worker_id = str(source.get("worker_id") or "").strip()
        name = str(source.get("name") or "").strip()
        version = str(source.get("version") or "").strip()
        if not worker_id or not _ID_RE.fullmatch(worker_id):
            raise ReadyWorkerValidationError(
                f"ready_worker_id_invalid:{worker_id}"
            )
        if not name:
            raise ReadyWorkerValidationError("ready_worker_name_blank")
        _version_key(version)

        bindings = tuple(sorted(
            (cls._binding(item)
             for item in (source.get("rolepack_bindings") or ())),
            key=lambda item: (item.order, item.rolepack_id),
        ))
        if not bindings:
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_bindings_required"
            )
        ids = tuple(item.rolepack_id for item in bindings)
        orders = tuple(item.order for item in bindings)
        if len(set(ids)) != len(ids):
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_binding_duplicate"
            )
        if len(set(orders)) != len(orders):
            raise ReadyWorkerValidationError(
                "ready_worker_rolepack_binding_order_duplicate"
            )

        defaults = dict(source.get("provisioning_defaults") or {})
        metadata = dict(source.get("metadata") or {})
        if not _json_safe(defaults):
            raise ReadyWorkerValidationError(
                "ready_worker_provisioning_defaults_not_serializable"
            )
        if not _json_safe(metadata):
            raise ReadyWorkerValidationError(
                "ready_worker_metadata_not_serializable"
            )
        return ReadyWorkerDefinition(
            worker_id=worker_id,
            name=name,
            version=version,
            description=str(source.get("description") or "").strip(),
            category=str(source.get("category") or "").strip(),
            rolepack_bindings=bindings,
            primary_rolepack_id=str(
                source.get("primary_rolepack_id") or ""
            ).strip(),
            required_platform_capabilities=_unique(
                source.get("required_platform_capabilities"),
                "required_platform_capabilities",
            ),
            supported_channels=_unique(
                source.get("supported_channels"), "supported_channels"
            ),
            supported_languages=tuple(
                language.lower()
                for language in _unique(
                    source.get("supported_languages"),
                    "supported_languages",
                )
            ),
            default_language=str(
                source.get("default_language") or ""
            ).strip().lower(),
            allowed_tools=_unique(
                source.get("allowed_tools"), "allowed_tools"
            ),
            supported_work_object_types=_unique(
                source.get("supported_work_object_types"),
                "supported_work_object_types",
            ),
            provisioning_defaults=_freeze(defaults),
            operating_safeguards=_unique(
                source.get("operating_safeguards"),
                "operating_safeguards",
            ),
            customer_visibility=str(
                source.get("customer_visibility") or ""
            ).strip().lower(),
            enabled=bool(source.get("enabled", True)),
            metadata=_freeze(metadata),
        )

    def validate(self, definition):
        candidate = self._normalize(definition)
        binding_ids = {
            item.rolepack_id for item in candidate.rolepack_bindings
        }
        if not candidate.primary_rolepack_id:
            raise ReadyWorkerValidationError(
                "ready_worker_primary_rolepack_missing"
            )
        if candidate.primary_rolepack_id not in binding_ids:
            raise ReadyWorkerValidationError(
                "ready_worker_primary_rolepack_not_bound"
            )
        if candidate.customer_visibility not in _VISIBILITY:
            raise ReadyWorkerValidationError(
                "ready_worker_customer_visibility_invalid"
            )
        if candidate.default_language not in candidate.supported_languages:
            raise ReadyWorkerValidationError(
                "ready_worker_default_language_not_supported"
            )

        bound = []
        for binding in candidate.rolepack_bindings:
            try:
                rolepack = self._roles().lookup(
                    binding.rolepack_id, binding.version
                )
            except Exception as exc:
                raise ReadyWorkerValidationError(
                    "ready_worker_rolepack_missing:"
                    f"{binding.rolepack_id}:{binding.version}"
                ) from exc
            if not rolepack.enabled:
                raise ReadyWorkerValidationError(
                    "ready_worker_rolepack_disabled:"
                    f"{binding.rolepack_id}:{binding.version}"
                )
            bound.append(rolepack)

        primary = next(
            item for item in bound
            if item.rolepack_id == candidate.primary_rolepack_id
        )
        if candidate.category != primary.category:
            raise ReadyWorkerValidationError(
                "ready_worker_category_must_match_primary_rolepack"
            )

        def intersection(attribute):
            return set.intersection(*(
                set(getattr(item, attribute)) for item in bound
            ))

        channels = intersection("allowed_channels")
        languages = intersection("supported_languages")
        tools = intersection("allowed_tools")
        work_types = intersection("allowed_work_object_types")
        for label, values in (
            ("channels", channels),
            ("languages", languages),
            ("work_object_types", work_types),
        ):
            if not values:
                raise ReadyWorkerValidationError(
                    f"ready_worker_rolepack_{label}_conflict"
                )
        for label, requested, permitted in (
            ("channel", candidate.supported_channels, channels),
            ("language", candidate.supported_languages, languages),
            ("tool", candidate.allowed_tools, tools),
            (
                "work_object_type",
                candidate.supported_work_object_types,
                work_types,
            ),
        ):
            broadened = set(requested) - permitted
            if broadened:
                raise ReadyWorkerValidationError(
                    f"ready_worker_{label}_not_permitted:"
                    + ",".join(sorted(broadened))
                )

        capability_union = set()
        for rolepack in bound:
            capability_union.update(rolepack.required_capabilities)
        if set(candidate.required_platform_capabilities) != capability_union:
            raise ReadyWorkerValidationError(
                "ready_worker_required_capability_union_mismatch"
            )
        if candidate.enabled:
            missing = []
            disabled = []
            for capability_id in candidate.required_platform_capabilities:
                try:
                    capability = self._platform().lookup(capability_id)
                except Exception:
                    missing.append(capability_id)
                    continue
                if not capability.enabled:
                    disabled.append(capability_id)
            if missing:
                raise ReadyWorkerValidationError(
                    "ready_worker_required_capability_missing:"
                    + ",".join(sorted(missing))
                )
            if disabled:
                raise ReadyWorkerValidationError(
                    "ready_worker_required_capability_disabled:"
                    + ",".join(sorted(disabled))
                )
        return candidate

    def register(self, definition=None, **values):
        candidate = self.validate(self._normalize(definition, **values))
        key = (candidate.worker_id, candidate.version)
        with self._lock:
            if key in self._definitions:
                raise DuplicateReadyWorkerError(
                    f"ready_worker_duplicate:{candidate.worker_id}:"
                    f"{candidate.version}"
                )
            self._definitions[key] = candidate
            self._initialized = False
            return candidate

    def replace_version(self, definition, expected_version):
        candidate = self.validate(definition)
        expected = str(expected_version or "").strip()
        _version_key(expected)
        if candidate.version != expected:
            raise ReadyWorkerVersionConflictError(
                f"ready_worker_replace_version_mismatch:{expected}:"
                f"{candidate.version}"
            )
        key = (candidate.worker_id, expected)
        with self._lock:
            if key not in self._definitions:
                raise ReadyWorkerNotFoundError(
                    f"ready_worker_not_found:{candidate.worker_id}:{expected}"
                )
            self._definitions[key] = candidate
            self._initialized = False
            return candidate

    def remove(self, worker_id, version):
        selected = self.lookup(worker_id, version)
        with self._lock:
            del self._definitions[(selected.worker_id, selected.version)]
            self._initialized = False
            return selected

    def lookup(self, worker_id, version=None):
        identifier = str(worker_id or "").strip()
        with self._lock:
            if version is not None:
                value = str(version or "").strip()
                _version_key(value)
                item = self._definitions.get((identifier, value))
                if item is None:
                    raise ReadyWorkerNotFoundError(
                        f"ready_worker_not_found:{identifier}:{value}"
                    )
                return item
            candidates = [
                item
                for (item_id, _), item in self._definitions.items()
                if item_id == identifier
            ]
            if not candidates:
                raise ReadyWorkerNotFoundError(
                    f"ready_worker_not_found:{identifier}"
                )
            return max(candidates, key=lambda item: _version_key(item.version))

    def lookup_latest_compatible(self, worker_id, compatible_with):
        target = _version_key(compatible_with)
        identifier = str(worker_id or "").strip()
        with self._lock:
            candidates = [
                item
                for (item_id, _), item in self._definitions.items()
                if item_id == identifier
                and _version_key(item.version)[0] == target[0]
                and _version_key(item.version) <= target
            ]
            if not candidates:
                raise ReadyWorkerNotFoundError(
                    "ready_worker_compatible_version_not_found:"
                    f"{identifier}:{compatible_with}"
                )
            return max(candidates, key=lambda item: _version_key(item.version))

    def list_definitions(
        self, enabled_only=False, customer_visible_only=False
    ):
        with self._lock:
            return tuple(sorted(
                (
                    item for item in self._definitions.values()
                    if (not enabled_only or item.enabled)
                    and (
                        not customer_visible_only
                        or item.customer_visibility == "public"
                    )
                ),
                key=lambda item: (
                    item.worker_id, _version_key(item.version)
                ),
            ))

    def list_enabled(self):
        return self.list_definitions(enabled_only=True)

    def list_customer_visible(self):
        return self.list_definitions(True, True)

    def enable(self, worker_id, version=None):
        return self._set_enabled(worker_id, version, True)

    def disable(self, worker_id, version=None):
        return self._set_enabled(worker_id, version, False)

    def _set_enabled(self, worker_id, version, enabled):
        with self._lock:
            current = self.lookup(worker_id, version)
            candidate = replace(current, enabled=bool(enabled))
            if enabled:
                candidate = self.validate(candidate)
            self._definitions[
                (candidate.worker_id, candidate.version)
            ] = candidate
            self._initialized = False
            return candidate

    def validate_catalog(self):
        with self._lock:
            for definition in self._definitions.values():
                self.validate(definition)
            return True

    def mark_initialized(self):
        with self._lock:
            self.validate_catalog()
            self._initialized = True
            return True

    def immutable_snapshot(self):
        with self._lock:
            return MappingProxyType({
                "version": READY_WORKER_DEFINITION_REGISTRY_VERSION,
                "initialized": self._initialized,
                "definitions": self.list_definitions(),
            })

    def health_status(self):
        with self._lock:
            try:
                self.validate_catalog()
                valid = True
            except ReadyWorkerCatalogError:
                valid = False
            try:
                self.immutable_snapshot()
                snapshot_safe = True
            except Exception:
                snapshot_safe = False
            return MappingProxyType({
                "ready": bool(
                    self._initialized and valid and snapshot_safe
                ),
                "initialized": self._initialized,
                "valid": valid,
                "snapshot_safe": snapshot_safe,
                "definition_count": len(self._definitions),
                "enabled_count": len(self.list_enabled()),
                "version": READY_WORKER_DEFINITION_REGISTRY_VERSION,
            })


def _builtins():
    defaults = {
        "display_name_template": "{worker_name}",
        "timezone_policy": "workspace_default",
        "memory_policy_id": "one_nina_workspace_memory",
        "channel_activation_defaults": {"mode": "manual"},
        "escalation_policy_id": "human_review",
        "approval_mode": "required_for_external_actions",
        "work_queue_policy": "workspace_canonical_queue",
    }
    common = {
        "version": "1.0.0",
        "supported_languages": ("lv", "en", "ru"),
        "default_language": "lv",
        "customer_visibility": "public",
        "enabled": True,
        "metadata": {"built_in": True},
    }
    return (
        {
            **common,
            "worker_id": "nina_executive_assistant",
            "name": "Nina Executive Assistant",
            "description": "Ready support for priorities and projects.",
            "category": "operations",
            "rolepack_bindings": ({
                "rolepack_id": "executive_assistant",
                "version": "1.0.0", "order": 10,
            },),
            "primary_rolepack_id": "executive_assistant",
            "required_platform_capabilities": (
                "message_service", "work_objects", "contact_identity",
            ),
            "supported_channels": (
                "web", "telegram", "whatsapp_personal",
            ),
            "allowed_tools": ("calendar", "files"),
            "supported_work_object_types": (
                "task", "reminder", "followup_task", "project",
                "meeting_note",
            ),
            "provisioning_defaults": defaults,
            "operating_safeguards": (
                "Require approval before consequential external actions",
                "Preserve canonical work truth",
            ),
        },
        {
            **common,
            "worker_id": "nina_customer_support",
            "name": "Nina Customer Support",
            "description": "Ready support for customer requests.",
            "category": "support",
            "rolepack_bindings": ({
                "rolepack_id": "customer_support",
                "version": "1.0.0", "order": 10,
            },),
            "primary_rolepack_id": "customer_support",
            "required_platform_capabilities": (
                "message_service", "work_objects", "contact_identity",
                "channel_services",
            ),
            "supported_channels": (
                "web", "telegram", "whatsapp_company", "email",
            ),
            "allowed_tools": ("files",),
            "supported_work_object_types": (
                "client", "client_request", "followup_task",
                "document_case", "task",
            ),
            "provisioning_defaults": defaults,
            "operating_safeguards": (
                "Never invent customer or case facts",
                "Keep sender and workspace context isolated",
            ),
        },
        {
            **common,
            "worker_id": "nina_sales_assistant",
            "name": "Nina Sales Assistant",
            "description": "Ready ethical sales and follow-up support.",
            "category": "sales",
            "rolepack_bindings": ({
                "rolepack_id": "sales_assistant",
                "version": "1.0.0", "order": 10,
            },),
            "primary_rolepack_id": "sales_assistant",
            "required_platform_capabilities": (
                "message_service", "work_objects", "contact_identity",
            ),
            "supported_channels": (
                "web", "telegram", "whatsapp_company", "email",
            ),
            "allowed_tools": ("files",),
            "supported_work_object_types": (
                "client", "estimate", "offer", "followup_task",
                "project", "task",
            ),
            "provisioning_defaults": defaults,
            "operating_safeguards": (
                "Use truthful non-manipulative communication",
                "Require approval before sending commercial terms",
            ),
        },
    )


_CATALOG = ReadyWorkerCatalog()
_INITIALIZATION_LOCK = threading.RLock()


def initialize_ready_worker_catalog(
    catalog=None,
    rolepack_registry=None,
    platform_registry=None,
    include_builtins=True,
):
    target = catalog or get_ready_worker_catalog()
    if rolepack_registry is not None:
        target._rolepack_registry = rolepack_registry
    if platform_registry is not None:
        target._platform_registry = platform_registry
    with _INITIALIZATION_LOCK:
        if include_builtins:
            existing = {
                (item.worker_id, item.version)
                for item in target.list_definitions()
            }
            for definition in _builtins():
                key = (definition["worker_id"], definition["version"])
                if key not in existing:
                    target.register(definition)
        target.mark_initialized()
        if not target.health_status()["ready"]:
            raise ReadyWorkerCatalogNotHealthyError(
                "nina_ready_worker_catalog_not_ready"
            )
        return target


def get_ready_worker_catalog():
    return _CATALOG


def get_ready_worker(worker_id, version=None):
    return get_ready_worker_catalog().lookup(worker_id, version)


def list_ready_workers(
    enabled_only=True, customer_visible_only=True
):
    return get_ready_worker_catalog().list_definitions(
        enabled_only=enabled_only,
        customer_visible_only=customer_visible_only,
    )
