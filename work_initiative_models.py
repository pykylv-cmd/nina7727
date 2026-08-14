"""Typed, channel-neutral models for ONE NINA work initiative decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class StableModel:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkExecutionDisposition(str, Enum):
    EXECUTABLE_NOW = "executable_now"
    PREPARATION_ONLY = "preparation_only"
    REQUIRES_APPROVAL = "requires_approval"
    REQUIRES_CAPABILITY = "requires_capability"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class WorkExecutionResult(StableModel):
    disposition: WorkExecutionDisposition
    state: str
    work_title: str
    summary: str = ""
    evidence_references: tuple[str, ...] = ()
    failure_reason: str = ""
    external_action_executed: bool = False
    attempt_id: str = ""


@dataclass(frozen=True)
class UserGoal(StableModel):
    original_text: str
    objective: str
    scope: str = ""
    business_context: str = ""
    urgency: str = "normal"
    constraints: tuple[str, ...] = ()
    known_context: tuple[str, ...] = ()
    missing_context: tuple[str, ...] = ()


@dataclass(frozen=True)
class InitiativeDecision(StableModel):
    should_act: bool
    reason: str
    confidence: float
    actionable_now: bool
    requires_owner_input: bool = False
    requires_connection: bool = False
    requires_approval: bool = False


@dataclass(frozen=True)
class ProposedWork(StableModel):
    title: str
    objective: str
    work_type: str
    why_it_matters: str
    capability_ids: tuple[str, ...]
    required_inputs: tuple[str, ...] = ()
    approval_required: bool = False
    reversible: bool = True
    priority: str = "normal"
    expected_output: str = ""


@dataclass(frozen=True)
class NextBestWork(StableModel):
    work: ProposedWork
    why_now: str
    can_start_now: bool
    owner_question_if_blocked: str = ""


@dataclass(frozen=True)
class CapabilityAnswer(StableModel):
    available_now: tuple[str, ...] = ()
    available_after_connection: tuple[str, ...] = ()
    not_yet_available: tuple[str, ...] = ()
    suggested_first_use: str = ""


@dataclass(frozen=True)
class WorkInitiativeResult(StableModel):
    goal: UserGoal
    decision: InitiativeDecision
    proposed_work: tuple[ProposedWork, ...] = ()
    next_best_work: NextBestWork | None = None
    capability_answer: CapabilityAnswer | None = None
    response_kind: str = "initiative"
    project_candidate: bool = False
    use_business_thinking: bool = False
    use_research: bool = False
    context_update: dict[str, str] | None = None
