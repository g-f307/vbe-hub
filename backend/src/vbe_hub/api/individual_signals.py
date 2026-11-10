from __future__ import annotations

import base64
import binascii
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vbe_hub.adapters.persistence.individual_workflow_models import (
    IndividualSignalWorkflowModel,
    InvestigationWorkflowModel,
)
from vbe_hub.adapters.persistence.investigation_models import (
    IndividualSignalModel,
    InvestigationFileMemberModel,
    InvestigationFileModel,
    InvestigationMembershipEventModel,
    SignalRelationSuggestionModel,
)
from vbe_hub.adapters.persistence.investigation_repository import (
    SqlAlchemyInvestigationRepository,
)
from vbe_hub.adapters.persistence.models import (
    NormalizedRecordModel,
    ProvenanceModel,
    RawRecordModel,
    TechnicalSheetExtractionModel,
)
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.api.workflow import get_review_actor_id
from vbe_hub.application.investigations.projection import compose_technical_sheet
from vbe_hub.domain.investigations import (
    HeadInvestigationMemberError,
    InvestigationConcurrencyConflict,
    InvestigationMemberNotFound,
    InvestigationOperationConflict,
    LastInvestigationMemberError,
)
from vbe_hub.infrastructure.settings import get_settings

router = APIRouter(prefix="/v1", tags=["individual-signals-v1"])
SignalState = Literal["detected", "triage", "verification", "risk_assessment", "closed"]
SuggestionState = Literal["pending", "ready", "failed"]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceSummary(BaseModel):
    kind: Literal["media", "community"]
    name: str
    published_at: datetime
    title: str | None
    excerpt: str


class SignalCard(BaseModel):
    id: UUID
    state: SignalState
    created_at: datetime
    source: SourceSummary
    active_investigation_id: UUID | None


class SignalPage(BaseModel):
    items: list[SignalCard]
    next_cursor: str | None


class ProvenanceResponse(BaseModel):
    adapter_name: str
    adapter_version: str
    generator_name: str | None
    generator_version: str | None
    seed: int | None
    scenario_id: str | None
    collected_at: datetime


class SourceDetail(SourceSummary):
    external_id: str | None
    body: str
    source_url: str | None
    language: str


class SignalDetail(BaseModel):
    id: UUID
    state: SignalState
    contract_version: str
    created_at: datetime
    source: SourceDetail
    provenance: ProvenanceResponse
    technical_sheet: dict[str, Any] | None
    active_investigation_id: UUID | None


class RelatedItem(BaseModel):
    suggestion_id: UUID
    status: SuggestionState
    updated_at: datetime
    error_code: str | None
    relation: str | None
    confidence: float | None
    justification: str | None
    candidate: SignalCard


class RelatedPage(BaseModel):
    items: list[RelatedItem]
    next_cursor: str | None


class CreateInvestigationRequest(StrictRequest):
    signal_id: UUID
    operation_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class ChangeMemberRequest(StrictRequest):
    operation_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    expected_version: int = Field(ge=1)


class RemoveMemberRequest(ChangeMemberRequest):
    reason_code: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class TransferMemberRequest(StrictRequest):
    operation_key: str = Field(min_length=1, max_length=115, pattern=r"^[A-Za-z0-9._:-]+$")
    destination_file_id: UUID
    source_expected_version: int = Field(ge=1)
    destination_expected_version: int = Field(ge=1)
    reason_code: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class InvestigationEventResponse(BaseModel):
    sequence: int
    action: Literal["add", "remove", "reject"]
    signal_id: UUID
    actor_id: str
    occurred_at: datetime
    reason_code: str | None


class InvestigationMemberResponse(BaseModel):
    added_at: datetime
    added_by: str
    signal: SignalDetail


class InvestigationDetailResponse(BaseModel):
    id: UUID
    head_signal_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    members: list[InvestigationMemberResponse]
    events: list[InvestigationEventResponse]
    technical_sheet: dict[str, Any]
    technical_sheet_provenance: dict[str, list[str]]
    technical_sheet_conflicts: list[dict[str, Any]]


class InvestigationTransferResponse(BaseModel):
    source: InvestigationDetailResponse
    destination: InvestigationDetailResponse


async def get_individual_signal_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session, session.begin():
            yield session
    finally:
        await engine.dispose()


Session = Annotated[AsyncSession, Depends(get_individual_signal_session)]
Actor = Annotated[str, Depends(get_review_actor_id)]


def _encode_cursor(timestamp: datetime, row_id: UUID) -> str:
    value = f"{timestamp.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        padded = value + "=" * (-len(value) % 4)
        timestamp, row_id = base64.urlsafe_b64decode(padded).decode().split("|", 1)
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed, UUID(row_id)
    except (binascii.Error, ValueError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_cursor"},
        ) from error


def _card(signal, raw, file_id: UUID | None, workflow_state: str) -> SignalCard:
    return SignalCard(
        id=signal.id,
        state=workflow_state,
        created_at=signal.created_at,
        source=SourceSummary(
            kind=raw.source_kind,
            name=raw.source_name,
            published_at=raw.published_at,
            title=raw.title,
            excerpt=raw.body[:500],
        ),
        active_investigation_id=file_id,
    )


def _base_signal_query():
    return (
        select(
            IndividualSignalModel,
            RawRecordModel,
            ProvenanceModel,
            InvestigationFileMemberModel.investigation_file_id,
            func.coalesce(
                InvestigationWorkflowModel.state,
                IndividualSignalWorkflowModel.state,
            ).label("workflow_state"),
        )
        .join(
            NormalizedRecordModel,
            NormalizedRecordModel.id == IndividualSignalModel.normalized_record_id,
        )
        .join(RawRecordModel, RawRecordModel.id == NormalizedRecordModel.raw_record_id)
        .join(ProvenanceModel, ProvenanceModel.raw_record_id == RawRecordModel.id)
        .join(
            IndividualSignalWorkflowModel,
            IndividualSignalWorkflowModel.signal_id == IndividualSignalModel.id,
        )
        .outerjoin(
            InvestigationFileMemberModel,
            and_(
                InvestigationFileMemberModel.signal_id == IndividualSignalModel.id,
                InvestigationFileMemberModel.removed_at.is_(None),
            ),
        )
        .outerjoin(
            InvestigationFileModel,
            InvestigationFileModel.id
            == InvestigationFileMemberModel.investigation_file_id,
        )
        .outerjoin(
            InvestigationWorkflowModel,
            InvestigationWorkflowModel.investigation_file_id
            == InvestigationFileMemberModel.investigation_file_id,
        )
    )


@router.get("/signals", response_model=SignalPage)
async def list_individual_signals(
    session: Session,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=200),
    state: SignalState | None = None,
    source_kind: Literal["media", "community"] | None = None,
) -> SignalPage:
    query = _base_signal_query().where(
        or_(
            InvestigationFileMemberModel.investigation_file_id.is_(None),
            InvestigationFileModel.head_signal_id == IndividualSignalModel.id,
        )
    )
    if cursor:
        created_at, signal_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                IndividualSignalModel.created_at < created_at,
                and_(
                    IndividualSignalModel.created_at == created_at,
                    IndividualSignalModel.id < signal_id,
                ),
            )
        )
    if source_kind:
        query = query.where(RawRecordModel.source_kind == source_kind)
    if state is not None:
        query = query.where(
            func.coalesce(
                InvestigationWorkflowModel.state,
                IndividualSignalWorkflowModel.state,
            )
            == state
        )
    rows = (
        await session.execute(
            query.order_by(
                IndividualSignalModel.created_at.desc(), IndividualSignalModel.id.desc()
            ).limit(limit + 1)
        )
    ).all()
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last_signal = page[-1][0]
        next_cursor = _encode_cursor(last_signal.created_at, last_signal.id)
    return SignalPage(
        items=[
            _card(signal, raw, file_id, workflow_state)
            for signal, raw, _provenance, file_id, workflow_state in page
        ],
        next_cursor=next_cursor,
    )


async def _signal_details(
    session: AsyncSession, signal_ids: list[UUID]
) -> dict[UUID, SignalDetail]:
    if not signal_ids:
        return {}
    rows = (
        await session.execute(_base_signal_query().where(IndividualSignalModel.id.in_(signal_ids)))
    ).all()
    normalized_ids = [row[0].normalized_record_id for row in rows]
    extraction_rows = (
        await session.execute(
            select(
                TechnicalSheetExtractionModel.normalized_record_id,
                TechnicalSheetExtractionModel.technical_sheet,
            )
            .where(
                TechnicalSheetExtractionModel.normalized_record_id.in_(normalized_ids),
                TechnicalSheetExtractionModel.state == "succeeded",
            )
            .distinct(TechnicalSheetExtractionModel.normalized_record_id)
            .order_by(
                TechnicalSheetExtractionModel.normalized_record_id,
                TechnicalSheetExtractionModel.created_at.desc(),
            )
        )
    ).all()
    sheets = dict(extraction_rows)
    details: dict[UUID, SignalDetail] = {}
    for signal, raw, provenance, file_id, workflow_state in rows:
        details[signal.id] = SignalDetail(
            id=signal.id,
            state=workflow_state,
            contract_version=signal.contract_version,
            created_at=signal.created_at,
            source=SourceDetail(
                kind=raw.source_kind,
                name=raw.source_name,
                external_id=raw.external_id,
                published_at=raw.published_at,
                title=raw.title,
                body=raw.body,
                source_url=raw.source_url,
                language=raw.language,
                excerpt=raw.body[:500],
            ),
            provenance=ProvenanceResponse.model_validate(provenance, from_attributes=True),
            technical_sheet=sheets.get(signal.normalized_record_id),
            active_investigation_id=file_id,
        )
    return details


async def _signal_detail(session: AsyncSession, signal_id: UUID) -> SignalDetail:
    detail = (await _signal_details(session, [signal_id])).get(signal_id)
    if detail is None:
        raise HTTPException(status_code=404, detail={"code": "individual_signal_not_found"})
    return detail


@router.get("/signals/{signal_id}", response_model=SignalDetail)
async def get_individual_signal(signal_id: UUID, session: Session) -> SignalDetail:
    return await _signal_detail(session, signal_id)


@router.get("/signals/{signal_id}/related", response_model=RelatedPage)
async def list_related_signals(
    signal_id: UUID,
    session: Session,
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=200),
    suggestion_status: SuggestionState | None = None,
) -> RelatedPage:
    if await session.get(IndividualSignalModel, signal_id) is None:
        raise HTTPException(status_code=404, detail={"code": "individual_signal_not_found"})
    candidate = IndividualSignalModel.__table__.alias("candidate_signal")
    candidate_id = or_(
        and_(
            SignalRelationSuggestionModel.left_signal_id == signal_id,
            candidate.c.id == SignalRelationSuggestionModel.right_signal_id,
        ),
        and_(
            SignalRelationSuggestionModel.right_signal_id == signal_id,
            candidate.c.id == SignalRelationSuggestionModel.left_signal_id,
        ),
    )
    query = (
        select(SignalRelationSuggestionModel, RelationAssessmentModel, candidate.c.id)
        .join(candidate, candidate_id)
        .outerjoin(
            RelationAssessmentModel,
            RelationAssessmentModel.id == SignalRelationSuggestionModel.relation_assessment_id,
        )
        .where(
            or_(
                SignalRelationSuggestionModel.left_signal_id == signal_id,
                SignalRelationSuggestionModel.right_signal_id == signal_id,
            ),
            ~select(InvestigationFileMemberModel.id)
            .where(
                InvestigationFileMemberModel.signal_id == candidate.c.id,
                InvestigationFileMemberModel.removed_at.is_(None),
            )
            .exists(),
        )
    )
    if suggestion_status:
        query = query.where(SignalRelationSuggestionModel.status == suggestion_status)
    if cursor:
        updated_at, suggestion_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                SignalRelationSuggestionModel.updated_at < updated_at,
                and_(
                    SignalRelationSuggestionModel.updated_at == updated_at,
                    SignalRelationSuggestionModel.id < suggestion_id,
                ),
            )
        )
    rows = (
        await session.execute(
            query.order_by(
                SignalRelationSuggestionModel.updated_at.desc(),
                SignalRelationSuggestionModel.id.desc(),
            ).limit(limit + 1)
        )
    ).all()
    candidate_details = await _signal_details(session, [row[2] for row in rows[:limit]])
    items: list[RelatedItem] = []
    for suggestion, assessment, candidate_signal_id in rows[:limit]:
        detail = candidate_details[candidate_signal_id]
        items.append(
            RelatedItem(
                suggestion_id=suggestion.id,
                status=suggestion.status,
                updated_at=suggestion.updated_at,
                error_code=suggestion.error_code,
                relation=None if assessment is None else assessment.relation,
                confidence=None if assessment is None else assessment.confidence,
                justification=None if assessment is None else assessment.justification,
                candidate=SignalCard(
                    id=detail.id,
                    state=detail.state,
                    created_at=detail.created_at,
                    source=detail.source,
                    active_investigation_id=detail.active_investigation_id,
                ),
            )
        )
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1][0]
        next_cursor = _encode_cursor(last.updated_at, last.id)
    return RelatedPage(items=items, next_cursor=next_cursor)


async def _investigation_detail(
    session: AsyncSession, file_id: UUID
) -> InvestigationDetailResponse:
    file = await session.get(InvestigationFileModel, file_id)
    if file is None:
        raise HTTPException(status_code=404, detail={"code": "investigation_not_found"})
    members = list(
        (
            await session.scalars(
                select(InvestigationFileMemberModel)
                .where(
                    InvestigationFileMemberModel.investigation_file_id == file_id,
                    InvestigationFileMemberModel.removed_at.is_(None),
                )
                .order_by(InvestigationFileMemberModel.added_at, InvestigationFileMemberModel.id)
            )
        ).all()
    )
    events = list(
        (
            await session.scalars(
                select(InvestigationMembershipEventModel)
                .where(InvestigationMembershipEventModel.investigation_file_id == file_id)
                .order_by(InvestigationMembershipEventModel.sequence)
            )
        ).all()
    )
    signal_details = await _signal_details(session, [member.signal_id for member in members])
    head = signal_details[file.head_signal_id]
    projection = compose_technical_sheet(
        file.head_signal_id,
        head.technical_sheet,
        [
            (member.signal_id, signal_details[member.signal_id].technical_sheet)
            for member in members
            if member.signal_id != file.head_signal_id
        ],
    )
    return InvestigationDetailResponse(
        id=file.id,
        head_signal_id=file.head_signal_id,
        version=file.version,
        created_at=file.created_at,
        updated_at=file.updated_at,
        members=[
            InvestigationMemberResponse(
                added_at=member.added_at,
                added_by=member.added_by,
                signal=signal_details[member.signal_id],
            )
            for member in members
        ],
        events=[
            InvestigationEventResponse(
                sequence=event.sequence,
                action=event.action,
                signal_id=event.signal_id,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                reason_code=event.reason_code,
            )
            for event in events
        ],
        technical_sheet=projection.technical_sheet,
        technical_sheet_provenance=projection.provenance,
        technical_sheet_conflicts=projection.conflicts,
    )


@router.get("/investigations/{file_id}", response_model=InvestigationDetailResponse)
async def get_investigation(file_id: UUID, session: Session) -> InvestigationDetailResponse:
    return await _investigation_detail(session, file_id)


def _raise_write_error(error: Exception) -> None:
    if isinstance(error, InvestigationConcurrencyConflict):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "investigation_version_conflict",
                "expected_version": error.expected_version,
                "current_version": error.current_version,
            },
        ) from error
    if isinstance(error, InvestigationOperationConflict):
        raise HTTPException(status_code=409, detail={"code": "operation_key_conflict"}) from error
    if isinstance(error, LastInvestigationMemberError):
        raise HTTPException(
            status_code=409, detail={"code": "investigation_requires_member"}
        ) from error
    if isinstance(error, HeadInvestigationMemberError):
        raise HTTPException(
            status_code=409, detail={"code": "investigation_head_cannot_be_removed"}
        ) from error
    if isinstance(error, InvestigationMemberNotFound):
        raise HTTPException(
            status_code=404, detail={"code": "investigation_member_not_found"}
        ) from error
    if isinstance(error, IntegrityError):
        raise HTTPException(status_code=409, detail={"code": "signal_already_assigned"}) from error
    raise error


async def _require_triage(session: AsyncSession, signal_id: UUID) -> None:
    workflow = await session.get(IndividualSignalWorkflowModel, signal_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail={"code": "individual_signal_not_found"})
    if workflow.state != "triage":
        raise HTTPException(
            status_code=409,
            detail={"code": "signal_not_in_triage", "current_state": workflow.state},
        )


@router.post("/investigations", response_model=InvestigationDetailResponse, status_code=201)
async def create_investigation(
    request: CreateInvestigationRequest, session: Session, actor: Actor
) -> InvestigationDetailResponse:
    await _require_triage(session, request.signal_id)
    repository = SqlAlchemyInvestigationRepository(session)
    try:
        file = await repository.create_file(
            request.signal_id, actor, request.operation_key, datetime.now(UTC)
        )
    except Exception as error:
        _raise_write_error(error)
    return await _investigation_detail(session, file.id)


@router.post(
    "/investigations/{file_id}/members/{signal_id}", response_model=InvestigationDetailResponse
)
async def add_investigation_member(
    file_id: UUID, signal_id: UUID, request: ChangeMemberRequest, session: Session, actor: Actor
) -> InvestigationDetailResponse:
    await _require_triage(session, signal_id)
    try:
        await SqlAlchemyInvestigationRepository(session).add_member(
            file_id,
            signal_id,
            actor,
            request.operation_key,
            request.expected_version,
            datetime.now(UTC),
        )
    except Exception as error:
        _raise_write_error(error)
    return await _investigation_detail(session, file_id)


@router.post(
    "/investigations/{file_id}/members/{signal_id}/removals",
    response_model=InvestigationDetailResponse,
)
async def remove_investigation_member(
    file_id: UUID, signal_id: UUID, request: RemoveMemberRequest, session: Session, actor: Actor
) -> InvestigationDetailResponse:
    try:
        await SqlAlchemyInvestigationRepository(session).remove_member(
            file_id,
            signal_id,
            actor,
            request.operation_key,
            request.expected_version,
            datetime.now(UTC),
            request.reason_code,
        )
    except Exception as error:
        _raise_write_error(error)
    return await _investigation_detail(session, file_id)


@router.post(
    "/investigations/{file_id}/members/{signal_id}/transfers",
    response_model=InvestigationTransferResponse,
)
async def transfer_investigation_member(
    file_id: UUID,
    signal_id: UUID,
    request: TransferMemberRequest,
    session: Session,
    actor: Actor,
) -> InvestigationTransferResponse:
    if file_id == request.destination_file_id:
        raise HTTPException(
            status_code=409,
            detail={"code": "investigation_transfer_same_file"},
        )
    await _require_triage(session, signal_id)
    try:
        await SqlAlchemyInvestigationRepository(session).transfer_member(
            file_id,
            request.destination_file_id,
            signal_id,
            actor,
            request.operation_key,
            request.source_expected_version,
            request.destination_expected_version,
            datetime.now(UTC),
            request.reason_code,
        )
    except Exception as error:
        _raise_write_error(error)
    return InvestigationTransferResponse(
        source=await _investigation_detail(session, file_id),
        destination=await _investigation_detail(session, request.destination_file_id),
    )
