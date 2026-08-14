"""Single orchestration boundary for the ONE NINA Executive Brain."""

from __future__ import annotations

from dataclasses import dataclass

from .brain_events import record_decision
from .decision import Decision
from .executive_brain import classify_message


@dataclass(frozen=True)
class BrainContext:
    workspace_id: str
    channel: str
    conversation_id: str = ""


class Brain:
    """V1 decides only; existing NinaOS modules remain responsible for effects."""

    @staticmethod
    def decide(message: str, context: BrainContext) -> Decision:
        decision = classify_message(message)
        record_decision(decision, {
            "workspace_id": context.workspace_id,
            "channel": context.channel,
            "conversation_id": context.conversation_id,
        })
        return decision
