import threading
import unittest
from pathlib import Path
from types import MappingProxyType

from platform_core import PlatformCapabilityRegistry
from ready_worker_catalog import (
    DuplicateReadyWorkerError,
    ReadyWorkerCatalog,
    ReadyWorkerValidationError,
    ReadyWorkerVersionConflictError,
    initialize_ready_worker_catalog,
)
from rolepack_system import RolePackRegistry, initialize_rolepack_system


CAPABILITIES = (
    "persistence_backend",
    "deployment_compatibility",
    "work_objects",
    "contact_identity",
    "message_service",
    "channel_services",
    "rolepack_system",
    "ready_worker_catalog",
    "agent_assignment",
    "knowledge_vault",
    "universal_work_objects",
)


def platform_registry(capability_ids=CAPABILITIES):
    registry = PlatformCapabilityRegistry()
    for index, identifier in enumerate(capability_ids, start=1):
        registry.register({
            "id": identifier,
            "name": identifier,
            "version": "1",
            "description": "",
            "startup_order": index * 10,
            "dependencies": (),
            "healthy": True,
            "enabled": True,
        })
    registry.mark_initialized()
    return registry


def role_definition(identifier="primary_role", version="1.0.0", **changes):
    value = {
        "rolepack_id": identifier,
        "name": identifier,
        "version": version,
        "description": "",
        "category": "operations",
        "responsibilities": ("Coordinate work",),
        "required_capabilities": ("message_service", "work_objects"),
        "optional_capabilities": (),
        "allowed_work_object_types": ("task", "project"),
        "allowed_channels": ("web", "telegram"),
        "allowed_tools": ("files", "calendar"),
        "operating_rules": ("Preserve intent",),
        "default_language": "en",
        "supported_languages": ("en", "lv"),
        "enabled": True,
        "metadata": {},
    }
    value.update(changes)
    return value


def role_registry(extra=()):
    platform = platform_registry()
    registry = RolePackRegistry(
        platform_registry=platform,
        channel_ids={
            "web", "telegram", "whatsapp_personal",
            "whatsapp_company", "email",
        },
        work_object_type_ids={
            "task", "project", "client", "client_request",
            "followup_task", "document_case", "reminder",
            "meeting_note", "estimate", "offer",
        },
    )
    registry.register(role_definition())
    for definition in extra:
        registry.register(definition)
    registry.mark_initialized()
    return registry, platform


def worker(identifier="test_worker", version="1.0.0", **changes):
    value = {
        "worker_id": identifier,
        "name": "Test Worker",
        "version": version,
        "description": "Test deployable definition",
        "category": "operations",
        "rolepack_bindings": ({
            "rolepack_id": "primary_role",
            "version": "1.0.0",
            "order": 10,
        },),
        "primary_rolepack_id": "primary_role",
        "required_platform_capabilities": (
            "message_service", "work_objects",
        ),
        "supported_channels": ("web", "telegram"),
        "supported_languages": ("en", "lv"),
        "default_language": "en",
        "allowed_tools": ("files", "calendar"),
        "supported_work_object_types": ("task", "project"),
        "provisioning_defaults": {
            "memory_policy_id": "one_nina_workspace_memory",
            "approval_mode": "human_review",
        },
        "operating_safeguards": ("Require approval",),
        "customer_visibility": "public",
        "enabled": True,
        "metadata": {"test": True},
    }
    value.update(changes)
    return value


class ReadyWorkerCatalogTests(unittest.TestCase):
    def make_catalog(self, extra_roles=(), capabilities=CAPABILITIES):
        roles, _ = role_registry(extra_roles)
        platform = platform_registry(capabilities)
        return ReadyWorkerCatalog(roles, platform), roles, platform

    def test_valid_registration_and_exact_lookup(self):
        catalog, _, _ = self.make_catalog()
        registered = catalog.register(worker())
        self.assertEqual(catalog.lookup("test_worker", "1.0.0"), registered)

    def test_duplicate_identity_version_is_rejected(self):
        catalog, _, _ = self.make_catalog()
        catalog.register(worker())
        with self.assertRaises(DuplicateReadyWorkerError):
            catalog.register(worker())

    def test_invalid_worker_version_is_rejected(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError, "ready_worker_version_invalid"
        ):
            catalog.register(worker(version="latest"))

    def test_exact_latest_and_latest_compatible_lookup(self):
        catalog, _, _ = self.make_catalog()
        for version in ("1.2.0", "1.10.0", "2.0.0"):
            catalog.register(worker(version=version))
        self.assertEqual(
            catalog.lookup("test_worker", "1.2.0").version, "1.2.0"
        )
        self.assertEqual(catalog.lookup("test_worker").version, "2.0.0")
        self.assertEqual(
            catalog.lookup_latest_compatible(
                "test_worker", "1.5.0"
            ).version,
            "1.2.0",
        )

    def test_explicit_replacement_requires_exact_version(self):
        catalog, _, _ = self.make_catalog()
        catalog.register(worker())
        self.assertEqual(
            catalog.replace_version(
                worker(name="Updated"), "1.0.0"
            ).name,
            "Updated",
        )
        with self.assertRaises(ReadyWorkerVersionConflictError):
            catalog.replace_version(worker(version="2.0.0"), "1.0.0")

    def test_enable_disable_and_removal(self):
        catalog, _, _ = self.make_catalog()
        catalog.register(worker())
        catalog.disable("test_worker", "1.0.0")
        self.assertEqual(catalog.list_enabled(), ())
        catalog.enable("test_worker", "1.0.0")
        removed = catalog.remove("test_worker", "1.0.0")
        self.assertEqual(removed.worker_id, "test_worker")
        self.assertEqual(catalog.list_definitions(), ())

    def test_snapshot_and_provisioning_defaults_are_immutable(self):
        catalog, _, _ = self.make_catalog()
        catalog.register(worker(provisioning_defaults={
            "nested": {"approval": True}
        }))
        catalog.mark_initialized()
        snapshot = catalog.immutable_snapshot()
        self.assertIsInstance(snapshot, MappingProxyType)
        with self.assertRaises(TypeError):
            snapshot["version"] = "changed"
        with self.assertRaises(TypeError):
            snapshot["definitions"][0].provisioning_defaults[
                "nested"
            ]["approval"] = False

    def test_non_json_provisioning_defaults_are_rejected(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "provisioning_defaults_not_serializable",
        ):
            catalog.register(worker(
                provisioning_defaults={"bad": object()}
            ))

    def test_missing_and_disabled_rolepacks_are_rejected(self):
        catalog, roles, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError, "ready_worker_rolepack_missing"
        ):
            catalog.register(worker(rolepack_bindings=({
                "rolepack_id": "absent",
                "version": "1.0.0",
                "order": 10,
            },), primary_rolepack_id="absent"))
        roles.disable("primary_role", "1.0.0")
        with self.assertRaisesRegex(
            ReadyWorkerValidationError, "ready_worker_rolepack_disabled"
        ):
            catalog.register(worker())

    def test_rolepack_pin_must_be_exact_and_valid(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_rolepack_version_invalid",
        ):
            catalog.register(worker(rolepack_bindings=({
                "rolepack_id": "primary_role",
                "version": "*",
                "order": 10,
            },)))

    def test_duplicate_binding_is_rejected(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_rolepack_binding_duplicate",
        ):
            catalog.register(worker(rolepack_bindings=(
                {
                    "rolepack_id": "primary_role",
                    "version": "1.0.0", "order": 10,
                },
                {
                    "rolepack_id": "primary_role",
                    "version": "1.0.0", "order": 20,
                },
            )))

    def test_missing_or_unbound_primary_rolepack_is_rejected(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_primary_rolepack_missing",
        ):
            catalog.register(worker(primary_rolepack_id=""))
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_primary_rolepack_not_bound",
        ):
            catalog.register(worker(primary_rolepack_id="other"))

    def test_channel_tool_and_work_type_broadening_is_rejected(self):
        catalog, _, _ = self.make_catalog()
        cases = (
            ("supported_channels", ("web", "email"), "channel"),
            ("allowed_tools", ("files", "payments"), "tool"),
            (
                "supported_work_object_types",
                ("task", "invoice"),
                "work_object_type",
            ),
        )
        for field, value, error in cases:
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    ReadyWorkerValidationError,
                    f"ready_worker_{error}_not_permitted",
                ):
                    catalog.register(worker(**{field: value}))

    def test_multi_role_intersection_and_capability_union(self):
        secondary = role_definition(
            "secondary_role",
            allowed_channels=("web",),
            allowed_tools=("files",),
            allowed_work_object_types=("task",),
            supported_languages=("en",),
            default_language="en",
            required_capabilities=(
                "message_service", "contact_identity",
            ),
        )
        catalog, _, _ = self.make_catalog((secondary,))
        definition = worker(
            rolepack_bindings=(
                {
                    "rolepack_id": "secondary_role",
                    "version": "1.0.0", "order": 20,
                },
                {
                    "rolepack_id": "primary_role",
                    "version": "1.0.0", "order": 10,
                },
            ),
            supported_channels=("web",),
            allowed_tools=("files",),
            supported_work_object_types=("task",),
            supported_languages=("en",),
            required_platform_capabilities=(
                "message_service", "work_objects", "contact_identity",
            ),
        )
        registered = catalog.register(definition)
        self.assertEqual(
            tuple(binding.rolepack_id
                  for binding in registered.rolepack_bindings),
            ("primary_role", "secondary_role"),
        )

    def test_multi_role_language_conflict_is_rejected(self):
        secondary = role_definition(
            "secondary_role",
            supported_languages=("ru",),
            default_language="ru",
        )
        catalog, _, _ = self.make_catalog((secondary,))
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_rolepack_languages_conflict",
        ):
            catalog.register(worker(
                rolepack_bindings=(
                    {
                        "rolepack_id": "primary_role",
                        "version": "1.0.0", "order": 10,
                    },
                    {
                        "rolepack_id": "secondary_role",
                        "version": "1.0.0", "order": 20,
                    },
                )
            ))

    def test_capability_union_must_be_exact(self):
        catalog, _, _ = self.make_catalog()
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_required_capability_union_mismatch",
        ):
            catalog.register(worker(
                required_platform_capabilities=("message_service",)
            ))

    def test_missing_platform_capability_is_rejected(self):
        catalog, _, _ = self.make_catalog(
            capabilities=("work_objects",)
        )
        with self.assertRaisesRegex(
            ReadyWorkerValidationError,
            "ready_worker_required_capability_missing",
        ):
            catalog.register(worker())

    def test_empty_catalog_can_be_ready(self):
        catalog, roles, platform = self.make_catalog()
        initialize_ready_worker_catalog(
            catalog=catalog,
            rolepack_registry=roles,
            platform_registry=platform,
            include_builtins=False,
        )
        self.assertTrue(catalog.health_status()["ready"])
        self.assertEqual(catalog.list_definitions(), ())

    def test_builtin_workers_initialize_and_validate(self):
        platform = platform_registry()
        roles = RolePackRegistry(platform_registry=platform)
        initialize_rolepack_system(
            registry=roles, platform_registry=platform
        )
        catalog = ReadyWorkerCatalog(roles, platform)
        initialize_ready_worker_catalog(
            catalog=catalog,
            rolepack_registry=roles,
            platform_registry=platform,
        )
        self.assertEqual(
            {item.worker_id for item in catalog.list_customer_visible()},
            {
                "nina_executive_assistant",
                "nina_customer_support",
                "nina_sales_assistant",
            },
        )
        self.assertTrue(catalog.health_status()["ready"])

    def test_platform_core_and_runtime_readiness_integration(self):
        from platform_core import initialize_platform_runtime

        checks = {
            identifier: (lambda: True) for identifier in CAPABILITIES
        }
        registry = initialize_platform_runtime(checks)
        capability = registry.lookup("ready_worker_catalog")
        self.assertEqual(capability.dependencies, ("rolepack_system",))
        root = Path(__file__).resolve().parent
        self.assertIn(
            '"ready_worker_catalog", initialize_ready_worker_catalog',
            (root / "web_app.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            '"ready_worker_catalog", initialize_ready_worker_catalog',
            (root / "app.py").read_text(encoding="utf-8"),
        )

    def test_concurrent_registration_is_safe(self):
        catalog, _, _ = self.make_catalog()
        errors = []

        def register(index):
            try:
                catalog.register(worker(identifier=f"worker_{index}"))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register, args=(index,))
            for index in range(30)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(catalog.list_definitions()), 30)


if __name__ == "__main__":
    unittest.main()
