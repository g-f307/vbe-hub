from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid5

_EVENT_NAMESPACE = UUID("2504e25f-6e67-4b5e-8884-947e922d745f")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._@:-]+$")


class WorkflowState(StrEnum):
    DETECTED = "detected"
    TRIAGE = "triage"
    VERIFICATION = "verification"
    RISK_ASSESSMENT = "risk_assessment"
    CLOSED = "closed"


class ReviewTargetType(StrEnum):
    RELATION = "relation"
    MEMBERSHIP = "membership"
    GROUPING = "grouping"
    PRIORITY = "priority"


class DecisionAction(StrEnum):
    ACCEPT = "accept"
    CORRECT = "correct"
    REJECT = "reject"


class ClosureReason(StrEnum):
    DUPLICATE = "duplicate"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_PUBLIC_HEALTH_EVENT = "not_public_health_event"
    RESOLVED = "resolved"
    OTHER = "other"


class WorkflowError(Exception):
    code = "workflow_error"


class WorkflowValidationError(WorkflowError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class WorkflowNotFound(WorkflowError):
    code = "workflow_signal_not_found"

    def __init__(self, signal_id: UUID) -> None:
        self.signal_id = signal_id
        super().__init__("signal was not found")


class InvalidTransition(WorkflowError):
    code = "invalid_workflow_transition"

    def __init__(self, current: WorkflowState, requested: WorkflowState) -> None:
        self.current = current
        self.requested = requested
        super().__init__(f"transition from {current.value} to {requested.value} is not allowed")


class ConcurrencyConflict(WorkflowError):
    code = "workflow_version_conflict"

    def __init__(self, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"expected workflow version {expected_version}, current version is {current_version}"
        )


@dataclass(frozen=True, slots=True)
class SignalWorkflow:
    signal_id: UUID
    state: WorkflowState
    version: int
    state_machine_version: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewEvent:
    id: UUID
    operation_key: str
    operation_fingerprint: str
    signal_id: UUID
    sequence: int
    workflow_version: int
    workflow_state: WorkflowState
    state_machine_version: str
    actor_id: str
    occurred_at: datetime
    action: str
    target_type: ReviewTargetType | None
    target_id: UUID
    previous_value: Mapping[str, Any]
    new_value: Mapping[str, Any]
    reason_code: str | None
    comment: str | None


@dataclass(frozen=True, slots=True)
class TransitionCommand:
    signal_id: UUID
    operation_key: str
    actor_id: str
    expected_version: int
    target_state: WorkflowState
    reason_code: ClosureReason | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewCommand:
    signal_id: UUID
    operation_key: str
    actor_id: str
    expected_version: int
    target_type: ReviewTargetType
    target_id: UUID
    suggestion_identity_key: str
    action: DecisionAction
    corrected_value: Mapping[str, Any] | None = None
    reason_code: str | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowOutcome:
    workflow: SignalWorkflow
    event: ReviewEvent


class WorkflowRepository(Protocol):
    async def get_or_create(self, signal_id: UUID) -> SignalWorkflow: ...

    async def get_event_by_operation(self, operation_key: str) -> ReviewEvent | None: ...

    async def get_latest_decision(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
    ) -> ReviewEvent | None: ...

    async def review_target_exists(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
        suggestion_identity_key: str,
    ) -> bool: ...

    async def append(
        self,
        *,
        event: ReviewEvent,
        expected_version: int,
        next_state: WorkflowState,
    ) -> SignalWorkflow: ...

    async def list_events(self, signal_id: UUID) -> list[ReviewEvent]: ...


_ALLOWED_TRANSITIONS: Mapping[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.DETECTED: frozenset({WorkflowState.TRIAGE}),
    WorkflowState.TRIAGE: frozenset({WorkflowState.VERIFICATION, WorkflowState.CLOSED}),
    WorkflowState.VERIFICATION: frozenset(
        {WorkflowState.TRIAGE, WorkflowState.RISK_ASSESSMENT, WorkflowState.CLOSED}
    ),
    WorkflowState.RISK_ASSESSMENT: frozenset(
        {WorkflowState.VERIFICATION, WorkflowState.CLOSED}
    ),
    WorkflowState.CLOSED: frozenset(),
}


class WorkflowService:
    def __init__(self, repository: WorkflowRepository, *, now) -> None:
        self._repository = repository
        self._now = now

    async def get(self, signal_id: UUID) -> SignalWorkflow:
        return await self._repository.get_or_create(signal_id)

    async def history(self, signal_id: UUID) -> list[ReviewEvent]:
        await self._repository.get_or_create(signal_id)
        return await self._repository.list_events(signal_id)

    async def transition(self, command: TransitionCommand) -> WorkflowOutcome:
        _validate_common(
            command.operation_key,
            command.actor_id,
            command.expected_version,
            command.comment,
        )
        operation_fingerprint = _operation_fingerprint(
            {
                "kind": "transition",
                "signal_id": str(command.signal_id),
                "actor_id": command.actor_id,
                "expected_version": command.expected_version,
                "target_state": command.target_state.value,
                "reason_code": command.reason_code.value if command.reason_code else None,
                "comment": _normalized_comment(command.comment),
            }
        )
        if existing := await self._repository.get_event_by_operation(command.operation_key):
            self._require_same_operation(existing, command.signal_id, operation_fingerprint)
            return self._replayed(existing)
        workflow = await self._repository.get_or_create(command.signal_id)
        self._require_version(workflow, command.expected_version)
        if command.target_state not in _ALLOWED_TRANSITIONS[workflow.state]:
            raise InvalidTransition(workflow.state, command.target_state)
        if command.target_state is WorkflowState.CLOSED and command.reason_code is None:
            raise WorkflowValidationError(
                "closure_reason_required", "closing a signal requires a structured reason"
            )
        event = self._event(
            workflow=workflow,
            operation_key=command.operation_key,
            operation_fingerprint=operation_fingerprint,
            actor_id=command.actor_id,
            action="transition",
            target_type=None,
            target_id=command.signal_id,
            previous_value={"state": workflow.state.value},
            new_value={"state": command.target_state.value},
            reason_code=command.reason_code.value if command.reason_code else None,
            comment=command.comment,
            next_state=command.target_state,
        )
        updated = await self._repository.append(
            event=event,
            expected_version=workflow.version,
            next_state=command.target_state,
        )
        return WorkflowOutcome(updated, event)

    async def review(self, command: ReviewCommand) -> WorkflowOutcome:
        _validate_common(
            command.operation_key,
            command.actor_id,
            command.expected_version,
            command.comment,
        )
        if not re.fullmatch(r"[0-9a-f]{64}", command.suggestion_identity_key):
            raise WorkflowValidationError(
                "invalid_suggestion_identity", "suggestion identity must be a SHA-256 hex value"
            )
        if command.action is DecisionAction.CORRECT and command.corrected_value is None:
            raise WorkflowValidationError(
                "corrected_value_required", "a correction requires a corrected value"
            )
        if command.corrected_value is not None:
            _validate_corrected_value(command.corrected_value)
        if command.action in {DecisionAction.CORRECT, DecisionAction.REJECT}:
            _validate_reason(command.reason_code)
        operation_fingerprint = _operation_fingerprint(
            {
                "kind": "review",
                "signal_id": str(command.signal_id),
                "actor_id": command.actor_id,
                "expected_version": command.expected_version,
                "target_type": command.target_type.value,
                "target_id": str(command.target_id),
                "suggestion_identity_key": command.suggestion_identity_key,
                "action": command.action.value,
                "corrected_value": dict(command.corrected_value or {}),
                "reason_code": command.reason_code,
                "comment": _normalized_comment(command.comment),
            }
        )
        if existing := await self._repository.get_event_by_operation(command.operation_key):
            self._require_same_operation(existing, command.signal_id, operation_fingerprint)
            return self._replayed(existing)
        workflow = await self._repository.get_or_create(command.signal_id)
        self._require_version(workflow, command.expected_version)
        if not await self._repository.review_target_exists(
            command.signal_id,
            command.target_type,
            command.target_id,
            command.suggestion_identity_key,
        ):
            raise WorkflowValidationError(
                "review_target_not_found",
                "review target does not belong to the signal or suggestion version",
            )
        previous = await self._repository.get_latest_decision(
            command.signal_id,
            command.target_type,
            command.target_id,
        )
        new_value: dict[str, Any] = {
            "decision": command.action.value,
            "suggestion_identity_key": command.suggestion_identity_key,
        }
        if command.corrected_value is not None:
            new_value["corrected_value"] = dict(command.corrected_value)
        event = self._event(
            workflow=workflow,
            operation_key=command.operation_key,
            operation_fingerprint=operation_fingerprint,
            actor_id=command.actor_id,
            action=command.action.value,
            target_type=command.target_type,
            target_id=command.target_id,
            previous_value=previous.new_value if previous else {},
            new_value=new_value,
            reason_code=command.reason_code,
            comment=command.comment,
            next_state=workflow.state,
        )
        updated = await self._repository.append(
            event=event,
            expected_version=workflow.version,
            next_state=workflow.state,
        )
        return WorkflowOutcome(updated, event)

    def _event(
        self,
        *,
        workflow: SignalWorkflow,
        operation_key: str,
        operation_fingerprint: str,
        actor_id: str,
        action: str,
        target_type: ReviewTargetType | None,
        target_id: UUID,
        previous_value: Mapping[str, Any],
        new_value: Mapping[str, Any],
        reason_code: str | None,
        comment: str | None,
        next_state: WorkflowState,
    ) -> ReviewEvent:
        occurred_at = self._now()
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise WorkflowValidationError("invalid_clock", "workflow clock must include timezone")
        return ReviewEvent(
            id=uuid5(_EVENT_NAMESPACE, operation_key),
            operation_key=operation_key,
            operation_fingerprint=operation_fingerprint,
            signal_id=workflow.signal_id,
            sequence=workflow.version + 1,
            workflow_version=workflow.version + 1,
            workflow_state=next_state,
            state_machine_version=workflow.state_machine_version,
            actor_id=actor_id,
            occurred_at=occurred_at,
            action=action,
            target_type=target_type,
            target_id=target_id,
            previous_value=dict(previous_value),
            new_value=dict(new_value),
            reason_code=reason_code,
            comment=_normalized_comment(comment),
        )

    @staticmethod
    def _require_version(workflow: SignalWorkflow, expected: int) -> None:
        if workflow.version != expected:
            raise ConcurrencyConflict(expected, workflow.version)

    @staticmethod
    def _require_same_operation(
        event: ReviewEvent,
        signal_id: UUID,
        operation_fingerprint: str,
    ) -> None:
        if (
            event.signal_id != signal_id
            or event.operation_fingerprint != operation_fingerprint
        ):
            raise WorkflowValidationError(
                "operation_key_conflict",
                "operation key was already used with different content",
            )

    @staticmethod
    def _replayed(event: ReviewEvent) -> WorkflowOutcome:
        return WorkflowOutcome(
            workflow=SignalWorkflow(
                signal_id=event.signal_id,
                state=event.workflow_state,
                version=event.workflow_version,
                state_machine_version=event.state_machine_version,
                updated_at=event.occurred_at,
            ),
            event=event,
        )


def _validate_common(
    operation_key: str,
    actor_id: str,
    expected_version: int,
    comment: str | None,
) -> None:
    if not 1 <= len(operation_key) <= 128 or not _SAFE_IDENTIFIER.fullmatch(operation_key):
        raise WorkflowValidationError(
            "invalid_operation_key", "operation key has invalid format"
        )
    if not 1 <= len(actor_id) <= 100 or not _SAFE_IDENTIFIER.fullmatch(actor_id):
        raise WorkflowValidationError("invalid_actor_id", "actor id has invalid format")
    if expected_version < 0:
        raise WorkflowValidationError(
            "invalid_expected_version", "expected version must be non-negative"
        )
    if comment is not None and len(comment.strip()) > 500:
        raise WorkflowValidationError("comment_too_long", "comment exceeds 500 characters")


def _validate_reason(reason_code: str | None) -> None:
    if (
        reason_code is None
        or not 1 <= len(reason_code) <= 64
        or not re.fullmatch(r"[a-z0-9_]+", reason_code)
    ):
        raise WorkflowValidationError(
            "reason_code_required", "correction or rejection requires a structured reason"
        )


def _validate_corrected_value(value: Mapping[str, Any]) -> None:
    if not 1 <= len(value) <= 20:
        raise WorkflowValidationError(
            "invalid_corrected_value", "corrected value must contain between one and 20 fields"
        )
    for key, item in value.items():
        valid_key = isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key)
        valid_scalar = item is None or isinstance(item, str | int | float | bool)
        valid_string = not isinstance(item, str) or len(item) <= 200
        valid_number = not isinstance(item, float) or math.isfinite(item)
        if not (valid_key and valid_scalar and valid_string and valid_number):
            raise WorkflowValidationError(
                "invalid_corrected_value",
                "corrected values require bounded snake_case keys and scalar values",
            )


def _normalized_comment(comment: str | None) -> str | None:
    return comment.strip() if comment and comment.strip() else None


def _operation_fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
