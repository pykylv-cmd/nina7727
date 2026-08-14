"""Immutable structured decision returned by the ONE NINA Brain."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class Decision:
    reply_required: bool = True
    remember: bool = False
    create_work_object: bool = False
    create_reminder: bool = False
    follow_up: bool = False
    initiative: bool = False
    needs_clarification: bool = False
    no_action: bool = False
    priority: str = "normal"
    confidence: float = 1.0
    reason: str = "general_reply"
    reminder_operation: str = ""

    def __post_init__(self) -> None:
        if self.priority not in {"low", "normal", "high"}:
            raise ValueError("invalid_decision_priority")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("invalid_decision_confidence")
        if self.no_action and any((
            self.remember, self.create_work_object, self.create_reminder,
            self.follow_up, self.initiative, self.needs_clarification,
        )):
            raise ValueError("invalid_no_action_decision")
        if self.create_reminder and not self.create_work_object:
            raise ValueError("reminder_requires_work_object")
        if self.reminder_operation not in {
            "", "CREATE", "LIST", "ASK", "UPDATE", "CANCEL", "CONFIRM_MODIFY",
        }:
            raise ValueError("invalid_reminder_operation")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
