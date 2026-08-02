import inspect
import unittest

import web_app


class WebConversationTimelineTests(unittest.TestCase):
    def test_new_nina_reply_is_last_across_timestamp_formats(self):
        items = [
            {"role": "nina", "text": "old reminder", "created_at": "2026-08-02T08:00:00+00:00", "message_id": "reminder-1"},
            {"role": "user", "text": "new question", "created_at": "2026-08-02 09:00:00", "message_id": "conversation:2:0:user"},
            {"role": "nina", "text": "new answer", "created_at": "2026-08-02 09:00:00", "message_id": "conversation:2:1:nina"},
        ]
        result = web_app._canonical_conversation_timeline(items)
        self.assertEqual([item["text"] for item in result], ["old reminder", "new question", "new answer"])

    def test_effective_timestamp_prefers_delivered_then_sent_then_created(self):
        items = [
            {"text": "delivered", "created_at": "2026-08-02T12:00:00Z", "sent_at": "2026-08-02T10:00:00Z", "delivered_at": "2026-08-02T11:00:00Z", "message_id": "c"},
            {"text": "sent", "created_at": "2026-08-02T09:00:00Z", "sent_at": "2026-08-02T10:30:00Z", "message_id": "b"},
        ]
        result = web_app._canonical_conversation_timeline(items)
        self.assertEqual([item["text"] for item in result], ["sent", "delivered"])

    def test_equal_timestamp_has_deterministic_message_id_tie_breaker(self):
        items = [
            {"text": "second", "created_at": "2026-08-02T10:00:00Z", "message_id": "b"},
            {"text": "first", "created_at": "2026-08-02 10:00:00", "message_id": "a"},
        ]
        first = web_app._canonical_conversation_timeline(items)
        second = web_app._canonical_conversation_timeline(reversed(items))
        self.assertEqual([item["message_id"] for item in first], ["a", "b"])
        self.assertEqual([item["message_id"] for item in second], ["a", "b"])

    def test_render_and_poll_share_timeline_and_scroll_to_bottom(self):
        source = inspect.getsource(web_app.nina_chat_body)
        self.assertIn("data-timeline-key", source)
        self.assertIn("order();bottom()", source)
        self.assertIn("if(added){order();bottom();}", source)
        self.assertNotIn("reminder-block", source)


if __name__ == "__main__":
    unittest.main()
