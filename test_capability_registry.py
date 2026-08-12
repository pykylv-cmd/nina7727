import unittest

from capability_registry import CapabilityId, CapabilityState, get_capability_registry


class CapabilityRegistryTests(unittest.TestCase):
    def test_registry_is_typed_and_truthful_without_connections(self):
        registry = get_capability_registry({})
        self.assertEqual(registry[CapabilityId.WEB_RESEARCH].state, CapabilityState.AVAILABLE)
        self.assertEqual(registry[CapabilityId.EMAIL_DRAFT].state, CapabilityState.AVAILABLE)
        self.assertEqual(registry[CapabilityId.EMAIL_SEND].state, CapabilityState.REQUIRES_CONNECTION)
        self.assertEqual(registry[CapabilityId.CALENDAR_WRITE].state, CapabilityState.REQUIRES_CONNECTION)
        self.assertEqual(registry[CapabilityId.AUTOMATION_EXECUTION].state, CapabilityState.NOT_IMPLEMENTED)

    def test_connected_external_actions_still_require_approval(self):
        registry = get_capability_registry({"NINA_EMAIL_CONNECTED": "true", "NINA_CALENDAR_CONNECTED": "ready"})
        self.assertEqual(registry[CapabilityId.EMAIL_SEND].state, CapabilityState.AVAILABLE_WITH_APPROVAL)
        self.assertTrue(registry[CapabilityId.EMAIL_SEND].approval_required)
        self.assertEqual(registry[CapabilityId.CALENDAR_WRITE].state, CapabilityState.AVAILABLE_WITH_APPROVAL)

    def test_every_descriptor_has_safe_user_truth(self):
        registry = get_capability_registry({})
        self.assertEqual(set(registry), set(CapabilityId))
        self.assertTrue(all(item.safe_user_description and item.what_nina_can_do for item in registry.values()))


if __name__ == "__main__":
    unittest.main()
