"""Safe, persistence-free Brain V1 decision observability."""

from __future__ import annotations

import logging
from typing import Mapping

from .decision import Decision

logger = logging.getLogger(__name__)


def record_decision(decision: Decision, context: Mapping[str, str]) -> None:
    """Log only decision flags and opaque routing identifiers, never message text."""
    logger.info(
        "brain_decision workspace=%s channel=%s conversation_present=%s "
        "reply_required=%s remember=%s work=%s reminder=%s follow_up=%s "
        "clarification=%s no_action=%s priority=%s confidence=%.2f reason=%s",
        str(context.get("workspace_id") or "")[:80],
        str(context.get("channel") or "")[:40],
        bool(context.get("conversation_id")),
        decision.reply_required, decision.remember, decision.create_work_object,
        decision.create_reminder, decision.follow_up, decision.needs_clarification,
        decision.no_action, decision.priority, decision.confidence, decision.reason,
    )
