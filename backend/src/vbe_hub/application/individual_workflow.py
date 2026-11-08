from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid5

from vbe_hub.application.workflow import (
    ClosureReason,
    ConcurrencyConflict,
    InvalidTransition,
    WorkflowState,
    WorkflowValidationError,
)

_EVENT_NAMESPACE = UUID("ce39219e-a7d8-4d13-a9ef-6a15f109477d")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._@:-]+$")


class WorkflowSubjectType(StrEnum):
    SIGNAL = "signal"
    INVESTIGATION = "investigation"


class IndividualWorkflowNotFound(Exception):
    def __init__(self, subject_type: WorkflowSubjectType, subject_id: UUID) -> None:
        self.subject_type = subject_type
        self.subject_id = subject_id
        super().__init__(f"{subject_type.value} workflow was not found")


class SignalsNotInTriage(Exception):
    def __init__(self, signal_ids: list[UUID]) -> None:
        self.signal_ids = signal_ids
        super().__init__("all active investigation members must be in triage")


@dataclass(frozen=True, slots=True)
class SubjectWorkflow:
    subject_type: WorkflowSubjectType
    subject_id: UUID
    state: WorkflowState
    version: int
    state_machine_version: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SubjectWorkflowEvent:
    id: UUID
    operation_key: str
    operation_fingerprint: str
    subject_type: WorkflowSubjectType
    subject_id: UUID
    sequence: int
    workflow_version: int
    workflow_state: WorkflowState
    state_machine_version: str
    actor_id: str
    occurred_at: datetime
    previous_value: dict[str, str]
    new_value: dict[str, str]
    reason_code: str | None
    comment: str | None


@dataclass(frozen=True, slots=True)
class SubjectTransitionCommand:
    subject_type: WorkflowSubjectType
    subject_id: UUID
    operation_key: str
    actor_id: str
    expected_version: int
    target_state: WorkflowState
    reason_code: ClosureReason | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class SubjectWorkflowOutcome:
    workflow: SubjectWorkflow
    event: SubjectWorkflowEvent


class IndividualWorkflowRepository(Protocol):
    async def get(
        self, subject_type: WorkflowSubjectType, subject_id: UUID
    ) -> SubjectWorkflow | None: ...

    async def subject_exists(self, subject_type: WorkflowSubjectType, subject_id: UUID) -> bool: ...

    async def members_not_in_triage(self, investigation_file_id: UUID) -> list[UUID]: ...

    async def get_event(self, operation_key: str) -> SubjectWorkflowEvent | None: ...

    async def append(
        self,
        event: SubjectWorkflowEvent,
        *,
        expected_version: int,
        initial: bool,
    ) -> SubjectWorkflow: ...

    async def list_events(
        self, subject_type: WorkflowSubjectType, subject_id: UUID
    ) -> list[SubjectWorkflowEvent]: ...


_SIGNAL_TRANSITIONS = {
    WorkflowState.DETECTED: frozenset({WorkflowState.TRIAGE}),
    WorkflowState.TRIAGE: frozenset({WorkflowState.CLOSED}),
    WorkflowState.CLOSED: frozenset(),
}
_INVESTIGATION_TRANSITIONS = {
    WorkflowState.VERIFICATION: frozenset({WorkflowState.RISK_ASSESSMENT, WorkflowState.CLOSED}),
    WorkflowState.RISK_ASSESSMENT: frozenset({WorkflowState.VERIFICATION, WorkflowState.CLOSED}),
    WorkflowState.CLOSED: frozenset(),
}


class IndividualWorkflowService:
    def __init__(self, repository: IndividualWorkflowRepository, *, now) -> None:
        self._repository = repository
        self._now = now

    async def get(self, subject_type: WorkflowSubjectType, subject_id: UUID) -> SubjectWorkflow:
        workflow = await self._repository.get(subject_type, subject_id)
        if workflow is None:
            raise IndividualWorkflowNotFound(subject_type, subject_id)
        return workflow

    async def history(
        self, subject_type: WorkflowSubjectType, subject_id: UUID
    ) -> list[SubjectWorkflowEvent]:
        if not await self._repository.subject_exists(subject_type, subject_id):
            raise IndividualWorkflowNotFound(subject_type, subject_id)
        return await self._repository.list_events(subject_type, subject_id)

    async def transition(self, command: SubjectTransitionCommand) -> SubjectWorkflowOutcome:
        _validate(command)
        fingerprint = _fingerprint(command)
        replay = await self._repository.get_event(command.operation_key)
        if replay is not None:
            if (
                replay.subject_type != command.subject_type
                or replay.subject_id != command.subject_id
                or replay.operation_fingerprint != fingerprint
            ):
                raise WorkflowValidationError(
                    "operation_key_conflict",
                    "operation key was already used with different content",
                )
            return SubjectWorkflowOutcome(
                SubjectWorkflow(
                    replay.subject_type,
                    replay.subject_id,
                    replay.workflow_state,
                    replay.workflow_version,
                    replay.state_machine_version,
                    replay.occurred_at,
                ),
                replay,
            )

        current = await self._repository.get(command.subject_type, command.subject_id)
        initial = current is None and command.subject_type is WorkflowSubjectType.INVESTIGATION
        if current is None:
            if not await self._repository.subject_exists(command.subject_type, command.subject_id):
                raise IndividualWorkflowNotFound(command.subject_type, command.subject_id)
            if not initial or command.expected_version != 0:
                raise ConcurrencyConflict(command.expected_version, 0)
            if command.target_state is not WorkflowState.VERIFICATION:
                raise InvalidTransition(WorkflowState.TRIAGE, command.target_state)
            invalid_members = await self._repository.members_not_in_triage(command.subject_id)
            if invalid_members:
                raise SignalsNotInTriage(invalid_members)
            previous_state = WorkflowState.TRIAGE
            next_version = 1
        else:
            if current.version != command.expected_version:
                raise ConcurrencyConflict(command.expected_version, current.version)
            allowed = (
                _SIGNAL_TRANSITIONS
                if command.subject_type is WorkflowSubjectType.SIGNAL
                else _INVESTIGATION_TRANSITIONS
            )
            if command.target_state not in allowed[current.state]:
                raise InvalidTransition(current.state, command.target_state)
            previous_state = current.state
            next_version = current.version + 1
        if command.target_state is WorkflowState.CLOSED and command.reason_code is None:
            raise WorkflowValidationError(
                "closure_reason_required", "closure requires a structured reason"
            )
        occurred_at = self._now()
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise WorkflowValidationError("invalid_clock", "workflow clock must include timezone")
        event = SubjectWorkflowEvent(
            id=uuid5(_EVENT_NAMESPACE, command.operation_key),
            operation_key=command.operation_key,
            operation_fingerprint=fingerprint,
            subject_type=command.subject_type,
            subject_id=command.subject_id,
            sequence=next_version,
            workflow_version=next_version,
            workflow_state=command.target_state,
            state_machine_version="workflow-v2",
            actor_id=command.actor_id,
            occurred_at=occurred_at,
            previous_value={"state": previous_state.value},
            new_value={"state": command.target_state.value},
            reason_code=command.reason_code.value if command.reason_code else None,
            comment=command.comment.strip() if command.comment else None,
        )
        workflow = await self._repository.append(
            event, expected_version=command.expected_version, initial=initial
        )
        return SubjectWorkflowOutcome(workflow, event)


def _validate(command: SubjectTransitionCommand) -> None:
    if not 1 <= len(command.operation_key) <= 128 or not _SAFE_IDENTIFIER.fullmatch(
        command.operation_key
    ):
        raise WorkflowValidationError("invalid_operation_key", "invalid operation key")
    if not 1 <= len(command.actor_id) <= 100 or not _SAFE_IDENTIFIER.fullmatch(command.actor_id):
        raise WorkflowValidationError("invalid_actor_id", "invalid actor id")
    if command.expected_version < 0:
        raise WorkflowValidationError("invalid_expected_version", "version cannot be negative")
    if command.comment is not None and len(command.comment.strip()) > 500:
        raise WorkflowValidationError("comment_too_long", "comment exceeds 500 characters")


def _fingerprint(command: SubjectTransitionCommand) -> str:
    payload = json.dumps(
        {
            "subject_type": command.subject_type.value,
            "subject_id": str(command.subject_id),
            "actor_id": command.actor_id,
            "expected_version": command.expected_version,
            "target_state": command.target_state.value,
            "reason_code": command.reason_code.value if command.reason_code else None,
            "comment": command.comment.strip() if command.comment else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
