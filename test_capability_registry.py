import unittest

from capability_registry import CapabilityId, CapabilityState, get_capability_registry


class CapabilityRegistryTests(unittest.TestCase):
    def test_registry_is_typed_and_truthful_without_connections(self):
        registry = get_capability_registry({})
        self.assertEqual(registry[CapabilityId.WEB_RESEARCH].state, CapabilityState.AVAILABLE)
        self.assertEqual(registry[CapabilityId.EMAIL_DRAFT].state, CapabilityState.AVAILABLE)
        self.assertEqual(registry[CapabilityId.EMAIL_SEND].state, CapabilityState.NOT_IMPLEMENTED)
        self.assertEqual(registry[CapabilityId.CALENDAR_WRITE].state, CapabilityState.NOT_IMPLEMENTED)
        self.assertEqual(registry[CapabilityId.AUTOMATION_EXECUTION].state, CapabilityState.NOT_IMPLEMENTED)

    def test_environment_flags_cannot_invent_external_connectors(self):
        registry = get_capability_registry({"NINA_EMAIL_CONNECTED": "true", "NINA_CALENDAR_CONNECTED": "ready"})
        self.assertEqual(registry[CapabilityId.EMAIL_READ].state, CapabilityState.NOT_IMPLEMENTED)
        self.assertEqual(registry[CapabilityId.EMAIL_SEND].state, CapabilityState.NOT_IMPLEMENTED)
        self.assertTrue(registry[CapabilityId.EMAIL_SEND].approval_required)
        self.assertEqual(registry[CapabilityId.CALENDAR_READ].state, CapabilityState.NOT_IMPLEMENTED)
        self.assertEqual(registry[CapabilityId.CALENDAR_WRITE].state, CapabilityState.NOT_IMPLEMENTED)

    def test_media_without_provider_is_degraded(self):
        registry = get_capability_registry({})
        self.assertEqual(registry[CapabilityId.IMAGE_UNDERSTANDING].state, CapabilityState.DEGRADED)
        self.assertEqual(registry[CapabilityId.AUDIO_UNDERSTANDING].state, CapabilityState.DEGRADED)
        self.assertEqual(registry[CapabilityId.VIDEO_UNDERSTANDING].state, CapabilityState.DEGRADED)

    def test_descriptions_do_not_overclaim_contacts_or_documents(self):
        registry = get_capability_registry({})
        self.assertIn("canonical contact identity", registry[CapabilityId.CONTACTS].what_nina_can_do)
        self.assertIn("document text", registry[CapabilityId.DOCUMENT_GENERATION].what_nina_can_do)

    def test_every_descriptor_has_safe_user_truth(self):
        registry = get_capability_registry({})
        self.assertEqual(set(registry), set(CapabilityId))
        self.assertTrue(all(item.safe_user_description and item.what_nina_can_do for item in registry.values()))


if __name__ == "__main__":
    unittest.main()
