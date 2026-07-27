import threading
import unittest
from pathlib import Path
from types import MappingProxyType

from platform_core import PlatformCapabilityRegistry
from rolepack_system import (
    DuplicateRolePackError,
    RolePackRegistry,
    RolePackValidationError,
    RolePackVersionConflictError,
    compare_rolepack_versions,
    initialize_rolepack_system,
)


CAPABILITY_IDS = (
    "persistence_backend",
    "deployment_compatibility",
    "work_objects",
    "contact_identity",
    "message_service",
    "channel_services",
    "rolepack_system",
    "ready_worker_catalog",
)


def platform_registry(capability_ids=CAPABILITY_IDS):
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


def rolepack(identifier="test_role", version="1.0.0", **changes):
    definition = {
        "rolepack_id": identifier,
        "name": "Test Role",
        "version": version,
        "description": "Test definition",
        "category": "test",
        "responsibilities": ("Organize tasks",),
        "required_capabilities": ("message_service", "work_objects"),
        "optional_capabilities": ("contact_identity",),
        "allowed_work_object_types": ("task",),
        "allowed_channels": ("web",),
        "allowed_tools": ("files",),
        "operating_rules": ("Preserve user intent",),
        "default_language": "en",
        "supported_languages": ("en", "lv"),
        "enabled": True,
        "metadata": {"test": True},
    }
    definition.update(changes)
    return definition


class RolePackRegistryTests(unittest.TestCase):
    def make_registry(self, capabilities=CAPABILITY_IDS):
        return RolePackRegistry(
            platform_registry=platform_registry(capabilities),
            channel_ids={"web", "telegram", "whatsapp_company"},
            work_object_type_ids={"task", "client", "estimate"},
        )

    def test_valid_registration_and_exact_lookup(self):
        registry = self.make_registry()
        registered = registry.register(rolepack())
        self.assertEqual(registry.lookup("test_role", "1.0.0"), registered)

    def test_duplicate_identity_version_is_rejected(self):
        registry = self.make_registry()
        registry.register(rolepack())
        with self.assertRaises(DuplicateRolePackError):
            registry.register(rolepack())

    def test_invalid_version_is_rejected(self):
        registry = self.make_registry()
        with self.assertRaises(RolePackValidationError):
            registry.register(rolepack(version="v1-latest"))

    def test_latest_version_lookup_is_deterministic(self):
        registry = self.make_registry()
        registry.register(rolepack(version="1.2.0"))
        registry.register(rolepack(version="1.10.0"))
        self.assertEqual(registry.lookup("test_role").version, "1.10.0")
        self.assertLess(compare_rolepack_versions("1.2.0", "1.10.0"), 0)

    def test_latest_compatible_version_respects_major_and_ceiling(self):
        registry = self.make_registry()
        registry.register(rolepack(version="1.2.0"))
        registry.register(rolepack(version="1.10.0"))
        registry.register(rolepack(version="2.0.0"))
        selected = registry.lookup_latest_compatible(
            "test_role", "1.5.0"
        )
        self.assertEqual(selected.version, "1.2.0")

    def test_explicit_replacement_requires_matching_version(self):
        registry = self.make_registry()
        registry.register(rolepack())
        replacement = rolepack(name="Updated")
        self.assertEqual(
            registry.replace_version(replacement, "1.0.0").name,
            "Updated",
        )
        with self.assertRaises(RolePackVersionConflictError):
            registry.replace_version(rolepack(version="2.0.0"), "1.0.0")

    def test_enable_disable_and_enabled_listing(self):
        registry = self.make_registry()
        registry.register(rolepack())
        registry.disable("test_role")
        self.assertEqual(registry.list_enabled(), ())
        registry.enable("test_role")
        self.assertEqual(len(registry.list_enabled()), 1)

    def test_snapshot_is_deeply_immutable(self):
        registry = self.make_registry()
        registry.register(rolepack(metadata={"nested": {"value": 1}}))
        registry.mark_initialized()
        snapshot = registry.immutable_snapshot()
        self.assertIsInstance(snapshot, MappingProxyType)
        with self.assertRaises(TypeError):
            snapshot["version"] = "changed"
        with self.assertRaises(TypeError):
            snapshot["rolepacks"][0].metadata["nested"]["value"] = 2

    def test_required_optional_overlap_is_rejected(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError, "rolepack_capability_overlap"
        ):
            registry.register(rolepack(
                optional_capabilities=("message_service",)
            ))

    def test_missing_required_platform_capability_is_rejected(self):
        registry = self.make_registry(capabilities=("work_objects",))
        with self.assertRaisesRegex(
            RolePackValidationError, "rolepack_required_capability_missing"
        ):
            registry.register(rolepack())

    def test_invalid_channel_is_rejected(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError, "rolepack_channel_unsupported"
        ):
            registry.register(rolepack(allowed_channels=("carrier_pigeon",)))

    def test_invalid_work_object_type_is_rejected(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError,
            "rolepack_work_object_type_unsupported",
        ):
            registry.register(rolepack(
                allowed_work_object_types=("unknown_work",)
            ))

    def test_default_language_must_be_supported(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError,
            "rolepack_default_language_not_supported",
        ):
            registry.register(rolepack(
                default_language="ru",
                supported_languages=("en", "lv"),
            ))

    def test_duplicate_responsibilities_are_rejected(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError, "rolepack_responsibilities_duplicate"
        ):
            registry.register(rolepack(
                responsibilities=("Organize tasks", "Organize tasks")
            ))

    def test_invalid_metadata_is_rejected(self):
        registry = self.make_registry()
        with self.assertRaisesRegex(
            RolePackValidationError, "rolepack_metadata_not_serializable"
        ):
            registry.register(rolepack(metadata={"bad": object()}))

    def test_empty_initialized_registry_is_ready(self):
        registry = self.make_registry()
        initialize_rolepack_system(
            registry=registry,
            include_builtins=False,
        )
        self.assertTrue(registry.health_status()["ready"])
        self.assertEqual(registry.list_rolepacks(), ())

    def test_builtin_baseline_initializes_and_validates(self):
        registry = RolePackRegistry(
            platform_registry=platform_registry(),
        )
        initialize_rolepack_system(registry=registry)
        self.assertEqual(
            {item.rolepack_id for item in registry.list_enabled()},
            {
                "executive_assistant",
                "customer_support",
                "sales_assistant",
            },
        )
        self.assertTrue(registry.health_status()["ready"])

    def test_platform_core_registers_rolepack_capability(self):
        from platform_core import initialize_platform_runtime

        checks = {
            identifier: (lambda: True)
            for identifier in CAPABILITY_IDS
        }
        registry = initialize_platform_runtime(checks)
        capability = registry.lookup("rolepack_system")
        self.assertEqual(
            capability.dependencies,
            ("work_objects", "channel_services"),
        )
        self.assertTrue(capability.healthy)

    def test_web_and_telegram_readiness_include_rolepack_system(self):
        root = Path(__file__).resolve().parent
        web_source = (root / "web_app.py").read_text(encoding="utf-8")
        app_source = (root / "app.py").read_text(encoding="utf-8")
        self.assertIn(
            'WEB_RUNTIME_READINESS.register('
            '"rolepack_system", initialize_rolepack_system)',
            web_source,
        )
        self.assertIn(
            'APP_RUNTIME_READINESS.register('
            '"rolepack_system", initialize_rolepack_system)',
            app_source,
        )

    def test_concurrent_registration_is_safe(self):
        registry = self.make_registry()
        errors = []

        def register(index):
            try:
                registry.register(rolepack(
                    identifier=f"role_{index}",
                    version="1.0.0",
                ))
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
        self.assertEqual(len(registry.list_rolepacks()), 30)


if __name__ == "__main__":
    unittest.main()
