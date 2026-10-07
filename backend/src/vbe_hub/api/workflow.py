from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from vbe_hub.adapters.persistence.workflow_repository import SqlAlchemyWorkflowRepository
from vbe_hub.application.workflow import (
    ClosureReason,
    DecisionAction,
    ReviewCommand,
    ReviewEvent,
    ReviewTargetType,
    SignalWorkflow,
    TransitionCommand,
    WorkflowOutcome,
    WorkflowService,
    WorkflowState,
)
from vbe_hub.infrastructure.settings import get_settings

router = APIRouter(prefix="/signals", tags=["workflow"])
SafeKey = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._@:-]+$"),
]
ReasonCode = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$"),
]
ShortText = Annotated[str, StringConstraints(max_length=200)]
CorrectionValue = ShortText | int | float | bool | None


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TransitionRequest(StrictRequest):
    operation_key: SafeKey
    expected_version: int = Field(ge=0)
    target_state: WorkflowState
    reason_code: ClosureReason | None = None
    comment: str | None = Field(default=None, max_length=500)


class ReviewRequest(StrictRequest):
    operation_key: SafeKey
    expected_version: int = Field(ge=0)
    target_type: ReviewTargetType
    target_id: UUID
    suggestion_identity_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: DecisionAction
    corrected_value: dict[str, CorrectionValue] | None = Field(default=None, max_length=20)
    reason_code: ReasonCode | None = None
    comment: str | None = Field(default=None, max_length=500)


class WorkflowResponse(BaseModel):
    signal_id: UUID
    state: WorkflowState
    version: int
    state_machine_version: str
    updated_at: datetime


class EventResponse(BaseModel):
    id: UUID
    operation_key: str
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
    previous_value: dict[str, Any]
    new_value: dict[str, Any]
    reason_code: str | None
    comment: str | None


class OutcomeResponse(BaseModel):
    workflow: WorkflowResponse
    event: EventResponse


async def get_workflow_service() -> AsyncIterator[WorkflowService]:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory.begin() as session:
            yield WorkflowService(
                SqlAlchemyWorkflowRepository(session),
                now=lambda: datetime.now(UTC),
            )
    finally:
        await engine.dispose()


def get_review_actor_id() -> str:
    return get_settings().review_actor_id


WorkflowServiceDependency = Annotated[WorkflowService, Depends(get_workflow_service)]
ReviewActorDependency = Annotated[str, Depends(get_review_actor_id)]


@router.get("/{signal_id}/workflow", response_model=WorkflowResponse)
async def get_workflow(
    signal_id: UUID,
    service: WorkflowServiceDependency,
) -> SignalWorkflow:
    return await service.get(signal_id)


@router.get("/{signal_id}/audit-events", response_model=list[EventResponse])
async def get_audit_events(
    signal_id: UUID,
    service: WorkflowServiceDependency,
) -> list[ReviewEvent]:
    return await service.history(signal_id)


@router.post("/{signal_id}/workflow/transitions", response_model=OutcomeResponse)
async def transition_workflow(
    signal_id: UUID,
    request: TransitionRequest,
    service: WorkflowServiceDependency,
    actor_id: ReviewActorDependency,
) -> WorkflowOutcome:
    return await service.transition(
        TransitionCommand(
            signal_id=signal_id,
            operation_key=request.operation_key,
            actor_id=actor_id,
            expected_version=request.expected_version,
            target_state=request.target_state,
            reason_code=request.reason_code,
            comment=request.comment,
        )
    )


@router.post("/{signal_id}/reviews", response_model=OutcomeResponse)
async def review_suggestion(
    signal_id: UUID,
    request: ReviewRequest,
    service: WorkflowServiceDependency,
    actor_id: ReviewActorDependency,
) -> WorkflowOutcome:
    return await service.review(
        ReviewCommand(
            signal_id=signal_id,
            operation_key=request.operation_key,
            actor_id=actor_id,
            expected_version=request.expected_version,
            target_type=request.target_type,
            target_id=request.target_id,
            suggestion_identity_key=request.suggestion_identity_key,
            action=request.action,
            corrected_value=request.corrected_value,
            reason_code=request.reason_code,
            comment=request.comment,
        )
    )
