from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vbe_hub.adapters.persistence.models import (
    NormalizedRecordModel,
    RawRecordModel,
    TechnicalSheetExtractionModel,
)
from vbe_hub.adapters.persistence.priority_models import SuggestedPriorityModel
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.adapters.persistence.signal_models import (
    ConsolidatedSignalModel,
    SignalMemberModel,
    SignalRelationLinkModel,
)
from vbe_hub.adapters.persistence.workflow_models import ReviewEventModel, SignalWorkflowModel
from vbe_hub.application.ai import ExecutionStatus
from vbe_hub.application.workflow import WorkflowState
from vbe_hub.infrastructure.settings import get_settings

router = APIRouter(prefix="/signals", tags=["signals"])


class LocationResponse(BaseModel):
    country: str | None
    state: str | None
    municipality: str | None
    district: str | None
    precision: str | None


class SourceCountsResponse(BaseModel):
    media: int = 0
    community: int = 0
    total: int = 0


class PriorityResponse(BaseModel):
    id: UUID
    band: str
    score: int
    confidence: int
    policy_version: str
    identity_key: str


class WorkflowSummaryResponse(BaseModel):
    state: WorkflowState
    version: int


class SignalQueueItemResponse(BaseModel):
    id: UUID
    title: str
    summary: str
    conditions: list[str]
    symptoms: list[str]
    period_start: date | None
    period_end: date | None
    location: LocationResponse
    source_counts: SourceCountsResponse
    priority: PriorityResponse | None
    workflow: WorkflowSummaryResponse


class SignalQueueResponse(BaseModel):
    items: list[SignalQueueItemResponse]
    page: int
    page_size: int
    total: int


class GroupingResponse(BaseModel):
    identity_key: str
    policy_version: str
    processing_state: str
    divergence_codes: list[str]


class SourceEvidenceResponse(BaseModel):
    normalized_record_id: UUID
    role: str
    source_kind: str
    source_name: str
    published_at: datetime
    title: str | None
    excerpt: str
    technical_sheet: dict[str, Any] | None


class RelationResponse(BaseModel):
    id: UUID
    role: str
    relation: str | None
    confidence: float | None
    justification: str | None
    method: str
    state: str


class AuditEventResponse(BaseModel):
    id: UUID
    sequence: int
    workflow_version: int
    workflow_state: str
    actor_id: str
    occurred_at: datetime
    action: str
    target_type: str | None
    target_id: UUID
    previous_value: dict[str, Any]
    new_value: dict[str, Any]
    reason_code: str | None
    comment: str | None


class SignalDetailResponse(BaseModel):
    signal: SignalQueueItemResponse
    grouping: GroupingResponse
    sources: list[SourceEvidenceResponse]
    relations: list[RelationResponse]
    audit_events: list[AuditEventResponse]


async def get_signal_read_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


SignalReadSession = Annotated[AsyncSession, Depends(get_signal_read_session)]


@router.get("", response_model=SignalQueueResponse)
async def list_signals(
    session: SignalReadSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    state: WorkflowState | None = None,
    priority_band: Literal["routine", "attention", "prompt"] | None = None,
    query: str | None = Query(default=None, max_length=200),
    condition: str | None = Query(default=None, max_length=200),
    municipality: str | None = Query(default=None, max_length=200),
    district: str | None = Query(default=None, max_length=200),
    source_kind: Literal["media", "community"] | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> SignalQueueResponse:
    if period_start is not None and period_end is not None and period_start > period_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_period_range"},
        )
    signals = list((await session.scalars(select(ConsolidatedSignalModel))).all())
    signal_ids = [signal.id for signal in signals]
    priorities = await _latest_priorities(session, signal_ids)
    workflows = await _workflows(session, signal_ids)
    source_counts = await _source_counts(session, signal_ids)
    items = [
        (
            signal,
            _queue_item(
                signal,
                priority=priorities.get(signal.id),
                workflow=workflows.get(signal.id),
                source_counts=source_counts.get(signal.id, SourceCountsResponse()),
            ),
        )
        for signal in signals
    ]
    filtered = [
        item
        for item in items
        if _matches_queue_filters(
            item[1],
            state=state,
            priority_band=priority_band,
            query=query,
            condition=condition,
            municipality=municipality,
            district=district,
            source_kind=source_kind,
            period_start=period_start,
            period_end=period_end,
        )
    ]
    filtered.sort(key=_queue_sort_key)
    total = len(filtered)
    start = (page - 1) * page_size
    return SignalQueueResponse(
        items=[item for _signal, item in filtered[start : start + page_size]],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{signal_id}", response_model=SignalDetailResponse)
async def get_signal(signal_id: UUID, session: SignalReadSession) -> SignalDetailResponse:
    signal = await session.get(ConsolidatedSignalModel, signal_id)
    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "signal_not_found"},
        )
    priorities = await _latest_priorities(session, [signal_id])
    workflows = await _workflows(session, [signal_id])
    source_counts = await _source_counts(session, [signal_id])
    return SignalDetailResponse(
        signal=_queue_item(
            signal,
            priority=priorities.get(signal_id),
            workflow=workflows.get(signal_id),
            source_counts=source_counts.get(signal_id, SourceCountsResponse()),
        ),
        grouping=GroupingResponse(
            identity_key=signal.identity_key,
            policy_version=signal.policy_version,
            processing_state=signal.processing_state,
            divergence_codes=_strings(signal.divergence_codes),
        ),
        sources=await _sources(session, signal_id),
        relations=await _relations(session, signal_id),
        audit_events=await _audit_events(session, signal_id),
    )


async def _latest_priorities(
    session: AsyncSession, signal_ids: list[UUID]
) -> dict[UUID, SuggestedPriorityModel]:
    if not signal_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(SuggestedPriorityModel)
                .where(SuggestedPriorityModel.signal_id.in_(signal_ids))
                .order_by(
                    SuggestedPriorityModel.signal_id,
                    SuggestedPriorityModel.evaluated_at.desc(),
                    SuggestedPriorityModel.created_at.desc(),
                )
            )
        ).all()
    )
    latest: dict[UUID, SuggestedPriorityModel] = {}
    for row in rows:
        latest.setdefault(row.signal_id, row)
    return latest


async def _workflows(
    session: AsyncSession, signal_ids: list[UUID]
) -> dict[UUID, SignalWorkflowModel]:
    if not signal_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(SignalWorkflowModel).where(SignalWorkflowModel.signal_id.in_(signal_ids))
            )
        ).all()
    )
    return {row.signal_id: row for row in rows}


async def _source_counts(
    session: AsyncSession, signal_ids: list[UUID]
) -> dict[UUID, SourceCountsResponse]:
    if not signal_ids:
        return {}
    rows = (
        await session.execute(
            select(SignalMemberModel.signal_id, RawRecordModel.source_kind)
            .join(
                NormalizedRecordModel,
                NormalizedRecordModel.id == SignalMemberModel.normalized_record_id,
            )
            .join(RawRecordModel, RawRecordModel.id == NormalizedRecordModel.raw_record_id)
            .where(SignalMemberModel.signal_id.in_(signal_ids))
        )
    ).all()
    counts = {signal_id: SourceCountsResponse() for signal_id in signal_ids}
    for signal_id, source_kind in rows:
        current = counts[signal_id]
        if source_kind == "media":
            current.media += 1
        elif source_kind == "community":
            current.community += 1
        current.total += 1
    return counts


def _queue_item(
    signal: ConsolidatedSignalModel,
    *,
    priority: SuggestedPriorityModel | None,
    workflow: SignalWorkflowModel | None,
    source_counts: SourceCountsResponse,
) -> SignalQueueItemResponse:
    return SignalQueueItemResponse(
        id=signal.id,
        title=signal.title,
        summary=signal.summary,
        conditions=_strings(signal.conditions),
        symptoms=_strings(signal.symptoms),
        period_start=signal.period_start,
        period_end=signal.period_end,
        location=_location(signal.location),
        source_counts=source_counts,
        priority=(
            PriorityResponse(
                id=priority.id,
                band=priority.band,
                score=priority.score,
                confidence=priority.confidence,
                policy_version=priority.policy_version,
                identity_key=priority.identity_key,
            )
            if priority is not None
            else None
        ),
        workflow=WorkflowSummaryResponse(
            state=WorkflowState(workflow.state) if workflow else WorkflowState.DETECTED,
            version=workflow.version if workflow else 0,
        ),
    )


async def _sources(
    session: AsyncSession, signal_id: UUID
) -> list[SourceEvidenceResponse]:
    rows = (
        await session.execute(
            select(SignalMemberModel, NormalizedRecordModel, RawRecordModel)
            .join(
                NormalizedRecordModel,
                NormalizedRecordModel.id == SignalMemberModel.normalized_record_id,
            )
            .join(RawRecordModel, RawRecordModel.id == NormalizedRecordModel.raw_record_id)
            .where(SignalMemberModel.signal_id == signal_id)
            .order_by(
                case((SignalMemberModel.role == "core", 0), else_=1),
                SignalMemberModel.normalized_record_id,
            )
        )
    ).all()
    normalized_ids = [normalized.id for _member, normalized, _raw in rows]
    sheets = await _latest_sheets(session, normalized_ids)
    return [
        SourceEvidenceResponse(
            normalized_record_id=normalized.id,
            role=member.role,
            source_kind=raw.source_kind,
            source_name=raw.source_name,
            published_at=raw.published_at,
            title=raw.title,
            excerpt=raw.body[:500],
            technical_sheet=(
                sheets[normalized.id].technical_sheet if normalized.id in sheets else None
            ),
        )
        for member, normalized, raw in rows
    ]


async def _latest_sheets(
    session: AsyncSession, normalized_ids: list[UUID]
) -> dict[UUID, TechnicalSheetExtractionModel]:
    if not normalized_ids:
        return {}
    rows = list(
        (
            await session.scalars(
                select(TechnicalSheetExtractionModel)
                .where(
                    TechnicalSheetExtractionModel.normalized_record_id.in_(normalized_ids),
                    TechnicalSheetExtractionModel.state == ExecutionStatus.SUCCEEDED.value,
                )
                .order_by(
                    TechnicalSheetExtractionModel.normalized_record_id,
                    TechnicalSheetExtractionModel.created_at.desc(),
                )
            )
        ).all()
    )
    latest: dict[UUID, TechnicalSheetExtractionModel] = {}
    for row in rows:
        latest.setdefault(row.normalized_record_id, row)
    return latest


async def _relations(session: AsyncSession, signal_id: UUID) -> list[RelationResponse]:
    rows = (
        await session.execute(
            select(SignalRelationLinkModel, RelationAssessmentModel)
            .join(
                RelationAssessmentModel,
                RelationAssessmentModel.id == SignalRelationLinkModel.relation_assessment_id,
            )
            .where(SignalRelationLinkModel.signal_id == signal_id)
            .order_by(SignalRelationLinkModel.relation_assessment_id)
        )
    ).all()
    return [
        RelationResponse(
            id=assessment.id,
            role=link.role,
            relation=assessment.relation,
            confidence=assessment.confidence,
            justification=assessment.justification,
            method=assessment.method,
            state=assessment.state,
        )
        for link, assessment in rows
    ]


async def _audit_events(session: AsyncSession, signal_id: UUID) -> list[AuditEventResponse]:
    rows = list(
        (
            await session.scalars(
                select(ReviewEventModel)
                .where(ReviewEventModel.signal_id == signal_id)
                .order_by(ReviewEventModel.sequence)
            )
        ).all()
    )
    return [
        AuditEventResponse(
            id=row.id,
            sequence=row.sequence,
            workflow_version=row.workflow_version,
            workflow_state=row.workflow_state,
            actor_id=row.actor_id,
            occurred_at=row.occurred_at,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            previous_value=row.previous_value,
            new_value=row.new_value,
            reason_code=row.reason_code,
            comment=row.comment,
        )
        for row in rows
    ]


def _location(value: dict[str, Any]) -> LocationResponse:
    return LocationResponse(
        country=_text(value.get("country")),
        state=_text(value.get("state")),
        municipality=_text(value.get("municipality")),
        district=_text(value.get("district")),
        precision=_text(value.get("precision")),
    )


def _strings(values: list[object]) -> list[str]:
    return [item for item in values if isinstance(item, str)]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _matches_queue_filters(
    item: SignalQueueItemResponse,
    *,
    state: WorkflowState | None,
    priority_band: str | None,
    query: str | None,
    condition: str | None,
    municipality: str | None,
    district: str | None,
    source_kind: Literal["media", "community"] | None,
    period_start: date | None,
    period_end: date | None,
) -> bool:
    if state is not None and item.workflow.state is not state:
        return False
    if priority_band is not None and (
        item.priority is None or item.priority.band != priority_band
    ):
        return False
    if condition is not None and not _has_text(item.conditions, condition):
        return False
    if municipality is not None and not _same_text(item.location.municipality, municipality):
        return False
    if district is not None and not _same_text(item.location.district, district):
        return False
    if source_kind is not None and getattr(item.source_counts, source_kind) == 0:
        return False
    if not _period_overlaps(item.period_start, item.period_end, period_start, period_end):
        return False
    if query is not None:
        searchable = [
            item.title,
            item.summary,
            *item.conditions,
            *item.symptoms,
            item.location.municipality or "",
            item.location.district or "",
        ]
        if not _has_text(searchable, query):
            return False
    return True


def _has_text(values: list[str], query: str) -> bool:
    needle = query.strip().casefold()
    return bool(needle) and any(needle in value.casefold() for value in values)


def _same_text(value: str | None, expected: str) -> bool:
    return value is not None and value.casefold() == expected.strip().casefold()


def _period_overlaps(
    item_start: date | None,
    item_end: date | None,
    filter_start: date | None,
    filter_end: date | None,
) -> bool:
    if filter_start is None and filter_end is None:
        return True
    if item_start is None and item_end is None:
        return False
    start = item_start or item_end
    end = item_end or item_start
    if filter_start is not None and end is not None and end < filter_start:
        return False
    if filter_end is not None and start is not None and start > filter_end:
        return False
    return True


def _queue_sort_key(
    value: tuple[ConsolidatedSignalModel, SignalQueueItemResponse],
) -> tuple[int, int, float, str]:
    signal, item = value
    priority = item.priority
    band_rank = {"prompt": 3, "attention": 2, "routine": 1}
    return (
        -band_rank.get(priority.band if priority else "", 0),
        -(priority.score if priority else -1),
        -signal.created_at.timestamp(),
        str(signal.id),
    )
