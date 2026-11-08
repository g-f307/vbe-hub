from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, select

from vbe_hub.adapters.persistence.individual_workflow_models import (
    IndividualSignalWorkflowModel,
    InvestigationWorkflowModel,
)
from vbe_hub.adapters.persistence.individual_workflow_repository import (
    SqlAlchemyIndividualWorkflowRepository,
)
from vbe_hub.adapters.persistence.investigation_models import (
    IndividualSignalModel,
    InvestigationFileMemberModel,
    InvestigationFileModel,
    SignalRelationSuggestionModel,
)
from vbe_hub.api.individual_signals import Session
from vbe_hub.api.workflow import get_review_actor_id
from vbe_hub.application.individual_workflow import (
    IndividualWorkflowNotFound,
    IndividualWorkflowService,
    SignalsNotInTriage,
    SubjectTransitionCommand,
    SubjectWorkflow,
    SubjectWorkflowEvent,
    SubjectWorkflowOutcome,
    WorkflowSubjectType,
)
from vbe_hub.application.workflow import (
    ClosureReason,
    ConcurrencyConflict,
    InvalidTransition,
    WorkflowState,
    WorkflowValidationError,
)

router = APIRouter(prefix="/v1", tags=["workflow-v2"])
SafeKey = Annotated[
    str,
    StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._@:-]+$"),
]
Actor = Annotated[str, Depends(get_review_actor_id)]


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    operation_key: SafeKey
    expected_version: int = Field(ge=0)
    target_state: WorkflowState
    reason_code: ClosureReason | None = None
    comment: str | None = Field(default=None, max_length=500)


class WorkflowResponse(BaseModel):
    subject_type: WorkflowSubjectType
    subject_id: UUID
    state: WorkflowState
    version: int
    state_machine_version: Literal["workflow-v2"]
    updated_at: datetime


class WorkflowEventResponse(BaseModel):
    id: UUID
    operation_key: str
    subject_type: WorkflowSubjectType
    subject_id: UUID
    sequence: int
    workflow_version: int
    workflow_state: WorkflowState
    state_machine_version: Literal["workflow-v2"]
    actor_id: str
    occurred_at: datetime
    previous_value: dict[str, str]
    new_value: dict[str, str]
    reason_code: str | None
    comment: str | None


class WorkflowOutcomeResponse(BaseModel):
    workflow: WorkflowResponse
    event: WorkflowEventResponse


class UnitStateMetrics(BaseModel):
    total: int
    by_state: dict[str, int]


class InvestigationMetrics(UnitStateMetrics):
    members: int


class WorkflowMetricsResponse(BaseModel):
    contract_version: Literal["workflow-metrics-v2"] = "workflow-metrics-v2"
    signals: UnitStateMetrics
    suggestions: dict[str, int]
    investigations: InvestigationMetrics


def _service(session: Session) -> IndividualWorkflowService:
    return IndividualWorkflowService(
        SqlAlchemyIndividualWorkflowRepository(session), now=lambda: datetime.now(UTC)
    )


def _raise_error(error: Exception) -> None:
    if isinstance(error, IndividualWorkflowNotFound):
        code = (
            "individual_signal_not_found"
            if error.subject_type is WorkflowSubjectType.SIGNAL
            else "investigation_not_found"
        )
        raise HTTPException(status_code=404, detail={"code": code}) from error
    if isinstance(error, ConcurrencyConflict):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "workflow_version_conflict",
                "expected_version": error.expected_version,
                "current_version": error.current_version,
            },
        ) from error
    if isinstance(error, InvalidTransition):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invalid_workflow_transition",
                "current_state": error.current.value,
                "requested_state": error.requested.value,
            },
        ) from error
    if isinstance(error, SignalsNotInTriage):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "investigation_members_not_in_triage",
                "signal_ids": [str(item) for item in error.signal_ids],
            },
        ) from error
    if isinstance(error, WorkflowValidationError):
        raise HTTPException(status_code=422, detail={"code": error.code}) from error
    raise error


async def _get(
    subject_type: WorkflowSubjectType, subject_id: UUID, session: Session
) -> SubjectWorkflow:
    try:
        return await _service(session).get(subject_type, subject_id)
    except Exception as error:
        _raise_error(error)


async def _history(
    subject_type: WorkflowSubjectType, subject_id: UUID, session: Session
) -> list[SubjectWorkflowEvent]:
    try:
        return await _service(session).history(subject_type, subject_id)
    except Exception as error:
        _raise_error(error)


async def _transition(
    subject_type: WorkflowSubjectType,
    subject_id: UUID,
    request: TransitionRequest,
    session: Session,
    actor: str,
) -> SubjectWorkflowOutcome:
    try:
        return await _service(session).transition(
            SubjectTransitionCommand(
                subject_type=subject_type,
                subject_id=subject_id,
                operation_key=request.operation_key,
                actor_id=actor,
                expected_version=request.expected_version,
                target_state=request.target_state,
                reason_code=request.reason_code,
                comment=request.comment,
            )
        )
    except Exception as error:
        _raise_error(error)


@router.get("/signals/{signal_id}/workflow", response_model=WorkflowResponse)
async def get_signal_workflow(signal_id: UUID, session: Session) -> SubjectWorkflow:
    return await _get(WorkflowSubjectType.SIGNAL, signal_id, session)


@router.get("/signals/{signal_id}/audit-events", response_model=list[WorkflowEventResponse])
async def get_signal_audit_events(signal_id: UUID, session: Session) -> list[SubjectWorkflowEvent]:
    return await _history(WorkflowSubjectType.SIGNAL, signal_id, session)


@router.post("/signals/{signal_id}/workflow/transitions", response_model=WorkflowOutcomeResponse)
async def transition_signal_workflow(
    signal_id: UUID, request: TransitionRequest, session: Session, actor: Actor
) -> SubjectWorkflowOutcome:
    return await _transition(WorkflowSubjectType.SIGNAL, signal_id, request, session, actor)


@router.get("/investigations/{file_id}/workflow", response_model=WorkflowResponse)
async def get_investigation_workflow(file_id: UUID, session: Session) -> SubjectWorkflow:
    return await _get(WorkflowSubjectType.INVESTIGATION, file_id, session)


@router.get("/investigations/{file_id}/audit-events", response_model=list[WorkflowEventResponse])
async def get_investigation_audit_events(
    file_id: UUID, session: Session
) -> list[SubjectWorkflowEvent]:
    return await _history(WorkflowSubjectType.INVESTIGATION, file_id, session)


@router.post(
    "/investigations/{file_id}/workflow/transitions",
    response_model=WorkflowOutcomeResponse,
)
async def transition_investigation_workflow(
    file_id: UUID, request: TransitionRequest, session: Session, actor: Actor
) -> SubjectWorkflowOutcome:
    return await _transition(WorkflowSubjectType.INVESTIGATION, file_id, request, session, actor)


@router.get("/metrics/summary", response_model=WorkflowMetricsResponse)
async def workflow_metrics(session: Session) -> WorkflowMetricsResponse:
    signal_states = dict(
        (
            await session.execute(
                select(IndividualSignalWorkflowModel.state, func.count())
                .group_by(IndividualSignalWorkflowModel.state)
                .order_by(IndividualSignalWorkflowModel.state)
            )
        ).all()
    )
    suggestion_states = dict(
        (
            await session.execute(
                select(SignalRelationSuggestionModel.status, func.count())
                .group_by(SignalRelationSuggestionModel.status)
                .order_by(SignalRelationSuggestionModel.status)
            )
        ).all()
    )
    investigation_states = dict(
        (
            await session.execute(
                select(InvestigationWorkflowModel.state, func.count())
                .group_by(InvestigationWorkflowModel.state)
                .order_by(InvestigationWorkflowModel.state)
            )
        ).all()
    )
    signal_total = int(
        await session.scalar(select(func.count()).select_from(IndividualSignalModel)) or 0
    )
    investigation_total = int(
        await session.scalar(select(func.count()).select_from(InvestigationFileModel)) or 0
    )
    member_total = int(
        await session.scalar(
            select(func.count())
            .select_from(InvestigationFileMemberModel)
            .where(InvestigationFileMemberModel.removed_at.is_(None))
        )
        or 0
    )
    return WorkflowMetricsResponse(
        signals=UnitStateMetrics(
            total=signal_total,
            by_state={
                state: int(signal_states.get(state, 0))
                for state in ("detected", "triage", "closed")
            },
        ),
        suggestions={
            state: int(suggestion_states.get(state, 0)) for state in ("pending", "ready", "failed")
        },
        investigations=InvestigationMetrics(
            total=investigation_total,
            members=member_total,
            by_state={
                state: int(investigation_states.get(state, 0))
                for state in ("verification", "risk_assessment", "closed")
            },
        ),
    )
