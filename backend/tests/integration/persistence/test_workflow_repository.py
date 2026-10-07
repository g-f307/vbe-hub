from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.repositories import SqlAlchemyRawRecordRepository
from vbe_hub.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from vbe_hub.adapters.persistence.workflow_repository import SqlAlchemyWorkflowRepository
from vbe_hub.application.correlation.signals import (
    ConsolidationPolicy,
    SignalConsolidationService,
    SignalRecord,
)
from vbe_hub.application.workflow import (
    ConcurrencyConflict,
    DecisionAction,
    ReviewCommand,
    ReviewTargetType,
    TransitionCommand,
    WorkflowNotFound,
    WorkflowService,
    WorkflowState,
)
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


@pytest.mark.integration
async def test_workflow_repository_rejects_unknown_signal(db_session: AsyncSession) -> None:
    with pytest.raises(WorkflowNotFound):
        await SqlAlchemyWorkflowRepository(db_session).get_or_create(UUID(int=999_999))


async def stored_signal(db_session: AsyncSession) -> UUID:
    raw = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="synthetic-media",
        external_id=f"workflow-{uuid4()}",
        published_at=NOW,
        title="Sinal sintético",
        body="Conteúdo sintético sem dados pessoais.",
        source_url=None,
        language="pt-BR",
        original_payload={"synthetic": True},
    )
    raw_repository = SqlAlchemyRawRecordRepository(db_session)
    await raw_repository.add(
        raw,
        Provenance(adapter_name="synthetic", adapter_version="1", collected_at=NOW),
    )
    normalized = NormalizedRecord(
        id=uuid4(),
        raw_record_id=raw.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
        normalized_data={"text": raw.body},
    )
    await raw_repository.save_normalized(normalized)
    result = SignalConsolidationService(
        ConsolidationPolicy(version="signal-policy-v1")
    ).consolidate(
        records=[
            SignalRecord(
                normalized.id,
                {
                    "disease_or_condition": "Sarampo",
                    "symptoms": ["febre"],
                    "estimated_cases": 3,
                    "estimated_deaths": None,
                    "temporal": {"start": "2026-10-05", "end": None},
                    "location": {"municipality": "Manaus"},
                },
            )
        ],
        relations=[],
    )
    await SqlAlchemySignalRepository(db_session).save(result)
    await db_session.flush()
    return result.signals[0].id


@pytest.mark.integration
async def test_workflow_repository_persists_idempotent_review_and_transition_history(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    repository = SqlAlchemyWorkflowRepository(db_session)
    service = WorkflowService(repository, now=lambda: NOW)
    signal = await SqlAlchemySignalRepository(db_session).get(signal_id)
    assert signal is not None

    initial = await service.get(signal_id)
    review_command = ReviewCommand(
        signal_id=signal_id,
        operation_key=f"accept-grouping-{uuid4()}",
        actor_id="synthetic-analyst",
        expected_version=0,
        target_type=ReviewTargetType.GROUPING,
        target_id=signal_id,
        suggestion_identity_key=signal.identity_key,
        action=DecisionAction.ACCEPT,
    )
    accepted = await service.review(review_command)
    replayed = await service.review(review_command)
    transitioned = await service.transition(
        TransitionCommand(
            signal_id=signal_id,
            operation_key=f"transition-triage-{uuid4()}",
            actor_id="synthetic-analyst",
            expected_version=1,
            target_state=WorkflowState.TRIAGE,
        )
    )
    await db_session.commit()

    history = await service.history(signal_id)
    assert initial.state is WorkflowState.DETECTED
    assert replayed.event.id == accepted.event.id
    assert transitioned.workflow.version == 2
    assert [(item.sequence, item.action) for item in history] == [
        (1, "accept"),
        (2, "transition"),
    ]


@pytest.mark.integration
async def test_workflow_repository_rejects_stale_version_atomically(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    service = WorkflowService(SqlAlchemyWorkflowRepository(db_session), now=lambda: NOW)
    await service.transition(
        TransitionCommand(
            signal_id=signal_id,
            operation_key=f"first-transition-{uuid4()}",
            actor_id="synthetic-analyst",
            expected_version=0,
            target_state=WorkflowState.TRIAGE,
        )
    )

    with pytest.raises(ConcurrencyConflict) as error:
        await service.transition(
            TransitionCommand(
                signal_id=signal_id,
                operation_key=f"stale-transition-{uuid4()}",
                actor_id="synthetic-analyst",
                expected_version=0,
                target_state=WorkflowState.TRIAGE,
            )
        )

    assert error.value.current_version == 1
    assert len(await service.history(signal_id)) == 1


@pytest.mark.integration
async def test_review_events_are_physically_append_only(db_session: AsyncSession) -> None:
    signal_id = await stored_signal(db_session)
    service = WorkflowService(SqlAlchemyWorkflowRepository(db_session), now=lambda: NOW)
    outcome = await service.transition(
        TransitionCommand(
            signal_id=signal_id,
            operation_key=f"immutable-transition-{uuid4()}",
            actor_id="synthetic-analyst",
            expected_version=0,
            target_state=WorkflowState.TRIAGE,
        )
    )
    await db_session.flush()

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE review_events SET actor_id = 'changed' WHERE id = :event_id"),
                {"event_id": outcome.event.id},
            )

    assert (await service.history(signal_id))[0].actor_id == "synthetic-analyst"
