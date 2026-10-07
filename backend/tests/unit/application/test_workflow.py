from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.application.workflow import (
    ClosureReason,
    ConcurrencyConflict,
    DecisionAction,
    InvalidTransition,
    ReviewCommand,
    ReviewEvent,
    ReviewTargetType,
    SignalWorkflow,
    TransitionCommand,
    WorkflowRepository,
    WorkflowService,
    WorkflowState,
    WorkflowValidationError,
)

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


def uid(value: int) -> UUID:
    return UUID(int=value)


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.workflow = SignalWorkflow(
            signal_id=uid(1),
            state=WorkflowState.DETECTED,
            version=0,
            state_machine_version="workflow-v1",
            updated_at=NOW,
        )
        self.events: list[ReviewEvent] = []
        self.target_exists = True

    async def get_or_create(self, signal_id: UUID) -> SignalWorkflow:
        assert signal_id == self.workflow.signal_id
        return self.workflow

    async def get_event_by_operation(self, operation_key: str) -> ReviewEvent | None:
        return next(
            (item for item in self.events if item.operation_key == operation_key),
            None,
        )

    async def get_latest_decision(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
    ) -> ReviewEvent | None:
        matches = [
            item
            for item in self.events
            if item.signal_id == signal_id
            and item.target_type is target_type
            and item.target_id == target_id
        ]
        return matches[-1] if matches else None

    async def review_target_exists(
        self,
        signal_id: UUID,
        target_type: ReviewTargetType,
        target_id: UUID,
        suggestion_identity_key: str,
    ) -> bool:
        return self.target_exists

    async def append(
        self,
        *,
        event: ReviewEvent,
        expected_version: int,
        next_state: WorkflowState,
    ) -> SignalWorkflow:
        if self.workflow.version != expected_version:
            raise ConcurrencyConflict(expected_version, self.workflow.version)
        self.events.append(event)
        self.workflow = SignalWorkflow(
            signal_id=self.workflow.signal_id,
            state=next_state,
            version=expected_version + 1,
            state_machine_version=self.workflow.state_machine_version,
            updated_at=event.occurred_at,
        )
        return self.workflow

    async def list_events(self, signal_id: UUID) -> list[ReviewEvent]:
        return [item for item in self.events if item.signal_id == signal_id]


def service(repository: InMemoryWorkflowRepository) -> WorkflowService:
    return WorkflowService(repository, now=lambda: NOW)


@pytest.mark.asyncio
async def test_accepts_grouping_then_advances_from_detected_to_triage() -> None:
    repository = InMemoryWorkflowRepository()
    workflow = service(repository)

    accepted = await workflow.review(
        ReviewCommand(
            signal_id=uid(1),
            operation_key="accept-grouping-1",
            actor_id="analyst-001",
            expected_version=0,
            target_type=ReviewTargetType.GROUPING,
            target_id=uid(1),
            suggestion_identity_key="a" * 64,
            action=DecisionAction.ACCEPT,
        )
    )
    transitioned = await workflow.transition(
        TransitionCommand(
            signal_id=uid(1),
            operation_key="move-triage-1",
            actor_id="analyst-001",
            expected_version=1,
            target_state=WorkflowState.TRIAGE,
        )
    )

    assert accepted.workflow.state is WorkflowState.DETECTED
    assert transitioned.workflow.state is WorkflowState.TRIAGE
    assert transitioned.workflow.version == 2
    assert [item.action for item in repository.events] == ["accept", "transition"]
    assert repository.events[0].new_value["suggestion_identity_key"] == "a" * 64


@pytest.mark.asyncio
async def test_invalid_transition_preserves_state_and_audit_history() -> None:
    repository = InMemoryWorkflowRepository()

    with pytest.raises(InvalidTransition) as error:
        await service(repository).transition(
            TransitionCommand(
                signal_id=uid(1),
                operation_key="skip-to-risk",
                actor_id="analyst-001",
                expected_version=0,
                target_state=WorkflowState.RISK_ASSESSMENT,
            )
        )

    assert error.value.code == "invalid_workflow_transition"
    assert repository.workflow.state is WorkflowState.DETECTED
    assert repository.events == []


@pytest.mark.asyncio
async def test_closing_requires_a_structured_reason() -> None:
    repository = InMemoryWorkflowRepository()
    repository.workflow = SignalWorkflow(
        signal_id=uid(1),
        state=WorkflowState.TRIAGE,
        version=3,
        state_machine_version="workflow-v1",
        updated_at=NOW,
    )

    with pytest.raises(WorkflowValidationError) as error:
        await service(repository).transition(
            TransitionCommand(
                signal_id=uid(1),
                operation_key="close-without-reason",
                actor_id="analyst-001",
                expected_version=3,
                target_state=WorkflowState.CLOSED,
            )
        )

    assert error.value.code == "closure_reason_required"
    assert repository.events == []


@pytest.mark.asyncio
async def test_closure_preserves_reason_comment_actor_and_before_after_values() -> None:
    repository = InMemoryWorkflowRepository()
    repository.workflow = SignalWorkflow(
        signal_id=uid(1),
        state=WorkflowState.VERIFICATION,
        version=2,
        state_machine_version="workflow-v1",
        updated_at=NOW,
    )

    outcome = await service(repository).transition(
        TransitionCommand(
            signal_id=uid(1),
            operation_key="close-verified-1",
            actor_id="analyst-002",
            expected_version=2,
            target_state=WorkflowState.CLOSED,
            reason_code=ClosureReason.INSUFFICIENT_EVIDENCE,
            comment="Fontes sintéticas insuficientes para continuar.",
        )
    )

    event = outcome.event
    assert event.actor_id == "analyst-002"
    assert event.previous_value == {"state": "verification"}
    assert event.new_value == {"state": "closed"}
    assert event.reason_code == "insufficient_evidence"
    assert outcome.workflow.version == 3


@pytest.mark.asyncio
async def test_correcting_priority_does_not_mutate_the_automatic_suggestion() -> None:
    repository = InMemoryWorkflowRepository()

    outcome = await service(repository).review(
        ReviewCommand(
            signal_id=uid(1),
            operation_key="correct-priority-1",
            actor_id="analyst-001",
            expected_version=0,
            target_type=ReviewTargetType.PRIORITY,
            target_id=uid(20),
            suggestion_identity_key="b" * 64,
            action=DecisionAction.CORRECT,
            corrected_value={"triage_band": "attention"},
            reason_code="local_context",
        )
    )

    assert outcome.event.previous_value == {}
    assert outcome.event.new_value == {
        "decision": "correct",
        "suggestion_identity_key": "b" * 64,
        "corrected_value": {"triage_band": "attention"},
    }
    assert outcome.event.target_id == uid(20)


@pytest.mark.asyncio
async def test_stale_expected_version_raises_explicit_conflict_without_event() -> None:
    repository = InMemoryWorkflowRepository()
    repository.workflow = SignalWorkflow(
        signal_id=uid(1),
        state=WorkflowState.TRIAGE,
        version=4,
        state_machine_version="workflow-v1",
        updated_at=NOW,
    )

    with pytest.raises(ConcurrencyConflict) as error:
        await service(repository).transition(
            TransitionCommand(
                signal_id=uid(1),
                operation_key="stale-transition",
                actor_id="analyst-001",
                expected_version=3,
                target_state=WorkflowState.VERIFICATION,
            )
        )

    assert error.value.code == "workflow_version_conflict"
    assert error.value.current_version == 4
    assert repository.events == []


@pytest.mark.asyncio
async def test_repeated_operation_key_returns_original_event_without_duplication() -> None:
    repository = InMemoryWorkflowRepository()
    command = TransitionCommand(
        signal_id=uid(1),
        operation_key="idempotent-triage-1",
        actor_id="analyst-001",
        expected_version=0,
        target_state=WorkflowState.TRIAGE,
    )

    first = await service(repository).transition(command)
    repeated = await service(repository).transition(command)

    assert repeated.event.id == first.event.id
    assert repeated.workflow == first.workflow
    assert len(repository.events) == 1


@pytest.mark.asyncio
async def test_reused_operation_key_with_different_payload_is_rejected() -> None:
    repository = InMemoryWorkflowRepository()
    workflow = service(repository)
    await workflow.transition(
        TransitionCommand(
            signal_id=uid(1),
            operation_key="same-operation-key",
            actor_id="analyst-001",
            expected_version=0,
            target_state=WorkflowState.TRIAGE,
        )
    )

    with pytest.raises(WorkflowValidationError) as error:
        await workflow.transition(
            TransitionCommand(
                signal_id=uid(1),
                operation_key="same-operation-key",
                actor_id="analyst-001",
                expected_version=0,
                target_state=WorkflowState.RISK_ASSESSMENT,
            )
        )

    assert error.value.code == "operation_key_conflict"
    assert len(repository.events) == 1


@pytest.mark.asyncio
async def test_new_automatic_suggestion_keeps_previous_human_decision() -> None:
    repository = InMemoryWorkflowRepository()
    workflow = service(repository)

    first = await workflow.review(
        ReviewCommand(
            signal_id=uid(1),
            operation_key="review-priority-v1",
            actor_id="analyst-001",
            expected_version=0,
            target_type=ReviewTargetType.PRIORITY,
            target_id=uid(20),
            suggestion_identity_key="1" * 64,
            action=DecisionAction.ACCEPT,
        )
    )
    second = await workflow.review(
        ReviewCommand(
            signal_id=uid(1),
            operation_key="review-priority-v2",
            actor_id="analyst-001",
            expected_version=1,
            target_type=ReviewTargetType.PRIORITY,
            target_id=uid(21),
            suggestion_identity_key="2" * 64,
            action=DecisionAction.REJECT,
            reason_code="new_evidence",
        )
    )

    assert first.event.id != second.event.id
    assert [item.new_value["suggestion_identity_key"] for item in repository.events] == [
        "1" * 64,
        "2" * 64,
    ]


@pytest.mark.asyncio
async def test_review_rejects_target_that_does_not_belong_to_signal() -> None:
    repository = InMemoryWorkflowRepository()
    repository.target_exists = False

    with pytest.raises(WorkflowValidationError) as error:
        await service(repository).review(
            ReviewCommand(
                signal_id=uid(1),
                operation_key="foreign-priority",
                actor_id="analyst-001",
                expected_version=0,
                target_type=ReviewTargetType.PRIORITY,
                target_id=uid(99),
                suggestion_identity_key="f" * 64,
                action=DecisionAction.ACCEPT,
            )
        )

    assert error.value.code == "review_target_not_found"
    assert repository.events == []


@pytest.mark.asyncio
async def test_review_rejects_nested_or_oversized_correction_values() -> None:
    repository = InMemoryWorkflowRepository()

    with pytest.raises(WorkflowValidationError) as error:
        await service(repository).review(
            ReviewCommand(
                signal_id=uid(1),
                operation_key="unsafe-correction",
                actor_id="analyst-001",
                expected_version=0,
                target_type=ReviewTargetType.PRIORITY,
                target_id=uid(20),
                suggestion_identity_key="b" * 64,
                action=DecisionAction.CORRECT,
                corrected_value={"nested": {"unbounded": "value"}},
                reason_code="local_context",
            )
        )

    assert error.value.code == "invalid_corrected_value"
    assert repository.events == []
