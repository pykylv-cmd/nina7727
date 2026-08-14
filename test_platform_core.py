import threading
import unittest
from types import MappingProxyType

from platform_core import (
    CapabilityDependencyCycleError,
    CapabilityDependencyError,
    CapabilityStartupOrderError,
    DuplicateCapabilityError,
    PlatformCapabilityRegistry,
    PlatformNotHealthyError,
    get_platform_registry,
    initialize_platform_runtime,
)
from runtime_readiness import RuntimeReadiness


def capability(identifier, order, dependencies=(), **values):
    return {
        "id": identifier,
        "name": values.get("name", identifier.title()),
        "version": values.get("version", "1"),
        "description": values.get("description", ""),
        "startup_order": order,
        "dependencies": dependencies,
        "healthy": values.get("healthy", True),
        "enabled": values.get("enabled", True),
        "metadata": values.get("metadata", {"required": True}),
    }


class PlatformCapabilityRegistryTests(unittest.TestCase):
    def test_registration_lookup_list_and_unregister(self):
        registry = PlatformCapabilityRegistry()
        registered = registry.register(capability("persistence", 10))
        self.assertEqual(registry.lookup("persistence"), registered)
        self.assertEqual(registry.list_capabilities(), (registered,))
        self.assertEqual(registry.unregister("persistence"), registered)
        self.assertEqual(registry.list_capabilities(), ())

    def test_duplicate_registration_is_rejected(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("persistence", 10))
        with self.assertRaises(DuplicateCapabilityError):
            registry.register(capability("persistence", 20))

    def test_missing_dependency_is_reported(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("message", 20, ("persistence",)))
        with self.assertRaises(CapabilityDependencyError):
            registry.validate()

    def test_dependency_cycle_is_rejected(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("a", 10, ("b",)))
        with self.assertRaises(CapabilityDependencyCycleError):
            registry.register(capability("b", 20, ("a",)))

    def test_startup_order_must_follow_dependencies(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("persistence", 20))
        with self.assertRaises(CapabilityStartupOrderError):
            registry.register(capability("message", 10, ("persistence",)))

    def test_enable_disable_and_health(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("persistence", 10))
        registry.mark_initialized()
        self.assertTrue(registry.health_status()["ready"])
        registry.disable("persistence")
        self.assertFalse(registry.health_status()["ready"])
        registry.enable("persistence")
        registry.set_healthy("persistence", False)
        self.assertFalse(registry.health_status()["ready"])

    def test_snapshot_is_deeply_immutable(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability(
            "persistence", 10, metadata={"required": True, "nested": {"a": 1}}
        ))
        registry.mark_initialized()
        snapshot = registry.immutable_snapshot()
        self.assertIsInstance(snapshot, MappingProxyType)
        with self.assertRaises(TypeError):
            snapshot["version"] = "changed"
        with self.assertRaises(TypeError):
            snapshot["capabilities"][0].metadata["nested"]["a"] = 2

    def test_readiness_integration_requires_healthy_platform(self):
        registry = PlatformCapabilityRegistry()
        registry.register(capability("persistence", 10, healthy=False))
        registry.mark_initialized()
        readiness = RuntimeReadiness("platform-test")
        readiness.register(
            "platform_core",
            lambda: registry.health_status()["ready"],
        )
        readiness.begin_startup()
        with self.assertRaises(RuntimeError):
            readiness.run_checks()
        self.assertFalse(readiness.ready)
        registry.set_healthy("persistence", True)
        readiness.begin_startup()
        readiness.run_checks()
        readiness.complete_startup()
        self.assertTrue(readiness.ready)

    def test_concurrent_registration_is_safe(self):
        registry = PlatformCapabilityRegistry()
        errors = []

        def register(index):
            try:
                registry.register(capability(f"capability-{index}", index + 1))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register, args=(index,))
            for index in range(40)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(registry.list_capabilities()), 40)

    def test_runtime_initialization_registers_required_capabilities(self):
        checks = {
            identifier: (lambda: True)
            for identifier in (
                "persistence_backend",
                "message_service",
                "contact_identity",
                "channel_services",
                "deployment_compatibility",
                "work_objects",
                "rolepack_system",
                "ready_worker_catalog",
                "agent_assignment",
                "knowledge_vault",
                "universal_work_objects",
            )
        }
        registry = initialize_platform_runtime(checks)
        self.assertIs(registry, get_platform_registry())
        self.assertTrue(registry.health_status()["ready"])
        self.assertEqual(
            set(registry.startup_order()),
            set(checks),
        )

    def test_runtime_initialization_rejects_unhealthy_required_capability(self):
        checks = {
            identifier: (lambda: True)
            for identifier in (
                "persistence_backend",
                "message_service",
                "contact_identity",
                "channel_services",
                "deployment_compatibility",
                "work_objects",
                "rolepack_system",
                "ready_worker_catalog",
                "agent_assignment",
                "knowledge_vault",
                "universal_work_objects",
            )
        }
        checks["message_service"] = lambda: False
        with self.assertRaises(PlatformNotHealthyError):
            initialize_platform_runtime(checks)

    def test_web_readiness_registers_platform_core(self):
        import web_app

        self.assertIn("platform_core", web_app.WEB_RUNTIME_READINESS._checks)


if __name__ == "__main__":
    unittest.main()
