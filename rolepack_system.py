"""Authoritative immutable RolePack definitions and runtime registry."""

from __future__ import annotations

import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from types import MappingProxyType


ROLEPACK_SYSTEM_VERSION = "1.0"
_VERSION_RE = re.compile(r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*)){0,2}$")
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

# NinaOS currently has transport-specific identifiers but no single channel
# identifier registry. These constants normalize only channels already used by
# the active runtimes and intentionally remain local to the RolePack boundary.
SUPPORTED_CHANNEL_IDS = frozenset({
    "web",
    "telegram",
    "whatsapp_personal",
    "whatsapp_company",
    "email",
})


class RolePackError(RuntimeError):
    pass


class RolePackValidationError(RolePackError):
    pass


class DuplicateRolePackError(RolePackError):
    pass


class RolePackNotFoundError(RolePackError):
    pass


class RolePackVersionConflictError(RolePackError):
    pass


class RolePackSystemNotHealthyError(RolePackError):
    pass


def _version_key(version):
    value = str(version or "").strip()
    if not _VERSION_RE.fullmatch(value):
        raise RolePackValidationError(f"rolepack_version_invalid:{value}")
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (3 - len(parts))


def compare_rolepack_versions(left, right):
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
    if isinstance(value, MappingProxyType):
        return {
            str(key): _thaw(item) for key, item in value.items()
        }
    if isinstance(value, dict):
        return {
            str(key): _thaw(item) for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_thaw(item) for item in value]
    return value


def _json_compatible(value):
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _normalized_unique(values, field_name):
    normalized = tuple(str(value or "").strip() for value in (values or ()))
    if any(not value for value in normalized):
        raise RolePackValidationError(f"rolepack_{field_name}_blank")
    if len(set(normalized)) != len(normalized):
        raise RolePackValidationError(f"rolepack_{field_name}_duplicate")
    return normalized


@dataclass(frozen=True)
class RolePack:
    rolepack_id: str
    name: str
    version: str
    description: str
    category: str
    responsibilities: tuple
    required_capabilities: tuple
    optional_capabilities: tuple
    allowed_work_object_types: tuple
    allowed_channels: tuple
    allowed_tools: tuple
    operating_rules: tuple
    default_language: str
    supported_languages: tuple
    enabled: bool
    metadata: object


class RolePackRegistry:
    """Thread-safe, version-aware RolePack definition registry."""

    def __init__(
        self,
        platform_registry=None,
        channel_ids=None,
        work_object_type_ids=None,
    ):
        self._lock = threading.RLock()
        self._rolepacks = OrderedDict()
        self._initialized = False
        self._platform_registry = platform_registry
        self._channel_ids = frozenset(channel_ids or SUPPORTED_CHANNEL_IDS)
        self._work_object_type_ids = (
            frozenset(work_object_type_ids)
            if work_object_type_ids is not None
            else None
        )

    @property
    def initialized(self):
        with self._lock:
            return self._initialized

    def _canonical_work_object_ids(self):
        if self._work_object_type_ids is not None:
            return self._work_object_type_ids
        from work_objects import list_work_object_type_ids

        return frozenset(list_work_object_type_ids())

    def _active_platform_registry(self):
        if self._platform_registry is not None:
            return self._platform_registry
        from platform_core import get_platform_registry

        return get_platform_registry()

    @staticmethod
    def _normalize(rolepack=None, **values):
        if isinstance(rolepack, RolePack):
            if values:
                raise TypeError("rolepack_and_values_are_mutually_exclusive")
            source = {
                name: getattr(rolepack, name)
                for name in RolePack.__dataclass_fields__
            }
            source["metadata"] = _thaw(rolepack.metadata)
        elif isinstance(rolepack, dict):
            source = dict(rolepack)
            source.update(values)
        elif rolepack is None:
            source = dict(values)
        else:
            raise TypeError("rolepack_must_be_mapping_or_rolepack")

        rolepack_id = str(source.get("rolepack_id") or "").strip()
        name = str(source.get("name") or "").strip()
        if not rolepack_id or not _ID_RE.fullmatch(rolepack_id):
            raise RolePackValidationError(
                f"rolepack_id_invalid:{rolepack_id}"
            )
        if not name:
            raise RolePackValidationError("rolepack_name_blank")
        version = str(source.get("version") or "").strip()
        _version_key(version)
        metadata = dict(source.get("metadata") or {})
        if not _json_compatible(metadata):
            raise RolePackValidationError("rolepack_metadata_not_serializable")

        normalized = RolePack(
            rolepack_id=rolepack_id,
            name=name,
            version=version,
            description=str(source.get("description") or "").strip(),
            category=str(source.get("category") or "").strip(),
            responsibilities=_normalized_unique(
                source.get("responsibilities"), "responsibilities"
            ),
            required_capabilities=_normalized_unique(
                source.get("required_capabilities"),
                "required_capabilities",
            ),
            optional_capabilities=_normalized_unique(
                source.get("optional_capabilities"),
                "optional_capabilities",
            ),
            allowed_work_object_types=_normalized_unique(
                source.get("allowed_work_object_types"),
                "allowed_work_object_types",
            ),
            allowed_channels=_normalized_unique(
                source.get("allowed_channels"), "allowed_channels"
            ),
            allowed_tools=_normalized_unique(
                source.get("allowed_tools"), "allowed_tools"
            ),
            operating_rules=_normalized_unique(
                source.get("operating_rules"), "operating_rules"
            ),
            default_language=str(
                source.get("default_language") or ""
            ).strip().lower(),
            supported_languages=tuple(
                language.lower()
                for language in _normalized_unique(
                    source.get("supported_languages"),
                    "supported_languages",
                )
            ),
            enabled=bool(source.get("enabled", True)),
            metadata=_freeze(metadata),
        )
        return normalized

    def validate(self, rolepack):
        candidate = self._normalize(rolepack)
        overlap = (
            set(candidate.required_capabilities)
            & set(candidate.optional_capabilities)
        )
        if overlap:
            raise RolePackValidationError(
                "rolepack_capability_overlap:" + ",".join(sorted(overlap))
            )
        unsupported_channels = (
            set(candidate.allowed_channels) - self._channel_ids
        )
        if unsupported_channels:
            raise RolePackValidationError(
                "rolepack_channel_unsupported:"
                + ",".join(sorted(unsupported_channels))
            )
        unsupported_types = (
            set(candidate.allowed_work_object_types)
            - self._canonical_work_object_ids()
        )
        if unsupported_types:
            raise RolePackValidationError(
                "rolepack_work_object_type_unsupported:"
                + ",".join(sorted(unsupported_types))
            )
        if (
            not candidate.default_language
            or candidate.default_language
            not in candidate.supported_languages
        ):
            raise RolePackValidationError(
                "rolepack_default_language_not_supported"
            )
        if candidate.enabled:
            platform_registry = self._active_platform_registry()
            missing = []
            disabled = []
            for capability_id in candidate.required_capabilities:
                try:
                    capability = platform_registry.lookup(capability_id)
                except Exception:
                    missing.append(capability_id)
                    continue
                if not capability.enabled:
                    disabled.append(capability_id)
            if missing:
                raise RolePackValidationError(
                    "rolepack_required_capability_missing:"
                    + ",".join(sorted(missing))
                )
            if disabled:
                raise RolePackValidationError(
                    "rolepack_required_capability_disabled:"
                    + ",".join(sorted(disabled))
                )
        return candidate

    def register(self, rolepack=None, **values):
        candidate = self.validate(self._normalize(rolepack, **values))
        key = (candidate.rolepack_id, candidate.version)
        with self._lock:
            if key in self._rolepacks:
                raise DuplicateRolePackError(
                    f"rolepack_duplicate:{candidate.rolepack_id}:"
                    f"{candidate.version}"
                )
            self._rolepacks[key] = candidate
            self._initialized = False
            return candidate

    def replace_version(self, rolepack, expected_version):
        candidate = self.validate(rolepack)
        expected = str(expected_version or "").strip()
        _version_key(expected)
        if candidate.version != expected:
            raise RolePackVersionConflictError(
                f"rolepack_replace_version_mismatch:{expected}:"
                f"{candidate.version}"
            )
        key = (candidate.rolepack_id, expected)
        with self._lock:
            if key not in self._rolepacks:
                raise RolePackNotFoundError(
                    f"rolepack_not_found:{candidate.rolepack_id}:{expected}"
                )
            self._rolepacks[key] = candidate
            self._initialized = False
            return candidate

    def remove(self, rolepack_id, version=None):
        with self._lock:
            selected = self.lookup(rolepack_id, version)
            del self._rolepacks[(selected.rolepack_id, selected.version)]
            self._initialized = False
            return selected

    def lookup(self, rolepack_id, version=None):
        identifier = str(rolepack_id or "").strip()
        with self._lock:
            if version is not None:
                normalized_version = str(version or "").strip()
                _version_key(normalized_version)
                item = self._rolepacks.get((identifier, normalized_version))
                if item is None:
                    raise RolePackNotFoundError(
                        f"rolepack_not_found:{identifier}:{normalized_version}"
                    )
                return item
            candidates = [
                item for (item_id, _), item in self._rolepacks.items()
                if item_id == identifier
            ]
            if not candidates:
                raise RolePackNotFoundError(
                    f"rolepack_not_found:{identifier}"
                )
            return max(candidates, key=lambda item: _version_key(item.version))

    def lookup_latest_compatible(self, rolepack_id, compatible_with):
        target = _version_key(compatible_with)
        identifier = str(rolepack_id or "").strip()
        with self._lock:
            candidates = [
                item
                for (item_id, _), item in self._rolepacks.items()
                if item_id == identifier
                and _version_key(item.version)[0] == target[0]
                and _version_key(item.version) <= target
            ]
            if not candidates:
                raise RolePackNotFoundError(
                    "rolepack_compatible_version_not_found:"
                    f"{identifier}:{compatible_with}"
                )
            return max(candidates, key=lambda item: _version_key(item.version))

    def list_rolepacks(self, enabled_only=False):
        with self._lock:
            values = (
                item for item in self._rolepacks.values()
                if not enabled_only or item.enabled
            )
            return tuple(sorted(
                values,
                key=lambda item: (
                    item.rolepack_id,
                    _version_key(item.version),
                ),
            ))

    def list_enabled(self):
        return self.list_rolepacks(enabled_only=True)

    def enable(self, rolepack_id, version=None):
        return self._set_enabled(rolepack_id, version, True)

    def disable(self, rolepack_id, version=None):
        return self._set_enabled(rolepack_id, version, False)

    def _set_enabled(self, rolepack_id, version, enabled):
        with self._lock:
            current = self.lookup(rolepack_id, version)
            candidate = replace(current, enabled=bool(enabled))
            if enabled:
                candidate = self.validate(candidate)
            self._rolepacks[
                (candidate.rolepack_id, candidate.version)
            ] = candidate
            self._initialized = False
            return candidate

    def validate_registry(self):
        with self._lock:
            for rolepack in self._rolepacks.values():
                self.validate(rolepack)
            return True

    def mark_initialized(self):
        with self._lock:
            self.validate_registry()
            self._initialized = True
            return True

    def health_status(self):
        with self._lock:
            try:
                self.validate_registry()
                valid = True
            except RolePackError:
                valid = False
            snapshot_safe = True
            try:
                self.immutable_snapshot()
            except Exception:
                snapshot_safe = False
            return MappingProxyType({
                "ready": bool(self._initialized and valid and snapshot_safe),
                "initialized": self._initialized,
                "valid": valid,
                "snapshot_safe": snapshot_safe,
                "rolepack_count": len(self._rolepacks),
                "enabled_count": len(self.list_enabled()),
                "version": ROLEPACK_SYSTEM_VERSION,
            })

    def immutable_snapshot(self):
        with self._lock:
            return MappingProxyType({
                "version": ROLEPACK_SYSTEM_VERSION,
                "initialized": self._initialized,
                "rolepacks": self.list_rolepacks(),
            })


def _baseline_rolepacks():
    common = {
        "version": "1.0.0",
        "default_language": "lv",
        "supported_languages": ("lv", "en", "ru"),
        "enabled": True,
        "metadata": {"built_in": True},
    }
    return (
        {
            **common,
            "rolepack_id": "executive_assistant",
            "name": "Executive Assistant",
            "description": "Coordinates priorities, follow-ups and projects.",
            "category": "operations",
            "responsibilities": (
                "Organize tasks and priorities",
                "Track follow-ups and project commitments",
                "Prepare clear work summaries",
            ),
            "required_capabilities": (
                "message_service", "work_objects", "contact_identity",
            ),
            "optional_capabilities": ("channel_services",),
            "allowed_work_object_types": (
                "task", "reminder", "followup_task", "project",
                "meeting_note",
            ),
            "allowed_channels": ("web", "telegram", "whatsapp_personal"),
            "allowed_tools": ("calendar", "files"),
            "operating_rules": (
                "Preserve user intent and canonical work truth",
                "Request approval before consequential external actions",
            ),
        },
        {
            **common,
            "rolepack_id": "customer_support",
            "name": "Customer Support",
            "description": "Handles customer requests and service follow-up.",
            "category": "support",
            "responsibilities": (
                "Understand and organize customer requests",
                "Maintain accurate customer context",
                "Escalate unresolved or sensitive cases",
            ),
            "required_capabilities": (
                "message_service", "work_objects", "contact_identity",
                "channel_services",
            ),
            "optional_capabilities": (),
            "allowed_work_object_types": (
                "client", "client_request", "followup_task",
                "document_case", "task",
            ),
            "allowed_channels": (
                "web", "telegram", "whatsapp_company", "email",
            ),
            "allowed_tools": ("files",),
            "operating_rules": (
                "Never invent customer or case facts",
                "Keep sender and workspace context isolated",
            ),
        },
        {
            **common,
            "rolepack_id": "sales_assistant",
            "name": "Sales Assistant",
            "description": "Supports ethical sales work and offer follow-up.",
            "category": "sales",
            "responsibilities": (
                "Organize leads and client follow-ups",
                "Prepare estimate and offer work",
                "Track agreed next actions",
            ),
            "required_capabilities": (
                "message_service", "work_objects", "contact_identity",
            ),
            "optional_capabilities": ("channel_services",),
            "allowed_work_object_types": (
                "client", "estimate", "offer", "followup_task",
                "project", "task",
            ),
            "allowed_channels": (
                "web", "telegram", "whatsapp_company", "email",
            ),
            "allowed_tools": ("files",),
            "operating_rules": (
                "Use truthful non-manipulative communication",
                "Require human approval before sending commercial terms",
            ),
        },
    )


_ROLEPACK_REGISTRY = RolePackRegistry()
_INITIALIZATION_LOCK = threading.RLock()


def initialize_rolepack_system(
    registry=None,
    platform_registry=None,
    include_builtins=True,
):
    target = registry or get_rolepack_registry()
    if platform_registry is not None:
        target._platform_registry = platform_registry
    with _INITIALIZATION_LOCK:
        if include_builtins:
            existing = {
                (item.rolepack_id, item.version)
                for item in target.list_rolepacks()
            }
            for definition in _baseline_rolepacks():
                key = (definition["rolepack_id"], definition["version"])
                if key not in existing:
                    target.register(definition)
        target.mark_initialized()
        if not target.health_status()["ready"]:
            raise RolePackSystemNotHealthyError(
                "nina_rolepack_system_not_ready"
            )
        return target


def get_rolepack_registry():
    return _ROLEPACK_REGISTRY


def get_rolepack(rolepack_id, version=None):
    return get_rolepack_registry().lookup(rolepack_id, version)


def list_rolepacks(enabled_only=True):
    return get_rolepack_registry().list_rolepacks(enabled_only=enabled_only)
