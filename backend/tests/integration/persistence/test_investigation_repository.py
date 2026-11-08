from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.investigation_repository import (
    SqlAlchemyInvestigationRepository,
)
from vbe_hub.adapters.persistence.repositories import SqlAlchemyRawRecordRepository
from vbe_hub.domain.investigations import InvestigationConcurrencyConflict
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


async def stored_normalized(session: AsyncSession, index: int) -> NormalizedRecord:
    raw = RawRecord.create(
        source_kind=SourceKind.MEDIA if index % 2 else SourceKind.COMMUNITY,
        source_name="issue-69-test",
        external_id=f"individual-{index}-{uuid4()}",
        published_at=NOW,
        title="Registro para teste",
        body="Conteúdo sem dados pessoais para validar proveniência.",
        source_url=None,
        language="pt-BR",
        original_payload={"test": True},
    )
    raw_repository = SqlAlchemyRawRecordRepository(session)
    await raw_repository.add(
        raw,
        Provenance(adapter_name="test", adapter_version="1", collected_at=NOW),
    )
    normalized = NormalizedRecord(
        id=uuid4(),
        raw_record_id=raw.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
        normalized_data={"text": raw.body},
    )
    await raw_repository.save_normalized(normalized)
    return normalized


@pytest.mark.integration
async def test_get_or_create_individual_signal_is_idempotent_and_preserves_provenance(
    db_session: AsyncSession,
) -> None:
    normalized = await stored_normalized(db_session, 1)
    repository = SqlAlchemyInvestigationRepository(db_session)

    first = await repository.get_or_create_signal(
        normalized.id, contract_version="individual-signal-v1", created_at=NOW
    )
    replay = await repository.get_or_create_signal(
        normalized.id, contract_version="individual-signal-v1", created_at=NOW
    )

    assert replay == first
    assert first.normalized_record_id == normalized.id
    assert (await repository.get_signal(first.id)) == first


@pytest.mark.integration
async def test_investigation_membership_is_human_owned_versioned_and_auditable(
    db_session: AsyncSession,
) -> None:
    first_source = await stored_normalized(db_session, 2)
    second_source = await stored_normalized(db_session, 3)
    rejected_source = await stored_normalized(db_session, 6)
    repository = SqlAlchemyInvestigationRepository(db_session)
    first = await repository.get_or_create_signal(first_source.id, "individual-signal-v1", NOW)
    second = await repository.get_or_create_signal(second_source.id, "individual-signal-v1", NOW)
    rejected_candidate = await repository.get_or_create_signal(
        rejected_source.id, "individual-signal-v1", NOW
    )

    investigation = await repository.create_file(
        signal_id=first.id,
        actor_id="analyst-1",
        operation_key=f"create-{uuid4()}",
        occurred_at=NOW,
    )
    operation_key = f"add-{uuid4()}"
    updated = await repository.add_member(
        investigation_file_id=investigation.id,
        signal_id=second.id,
        actor_id="analyst-1",
        operation_key=operation_key,
        expected_version=1,
        occurred_at=NOW,
    )
    replay = await repository.add_member(
        investigation_file_id=investigation.id,
        signal_id=second.id,
        actor_id="analyst-1",
        operation_key=operation_key,
        expected_version=1,
        occurred_at=NOW,
    )
    rejected = await repository.reject_suggestion(
        investigation.id,
        rejected_candidate.id,
        "analyst-1",
        f"reject-{uuid4()}",
        expected_version=2,
        occurred_at=NOW,
        reason_code="different-territory",
    )
    removed = await repository.remove_member(
        investigation.id,
        second.id,
        "analyst-1",
        f"remove-{uuid4()}",
        expected_version=3,
        occurred_at=NOW,
        reason_code="analyst-correction",
    )

    assert updated.version == 2
    assert replay.version == 2
    assert rejected.version == 3
    assert removed.version == 4
    active_signal_ids = [
        item.signal_id for item in await repository.list_active_members(updated.id)
    ]
    assert active_signal_ids == [first.id]
    assert [event.action for event in await repository.list_events(updated.id)] == [
        "add",
        "add",
        "reject",
        "remove",
    ]

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    "UPDATE investigation_membership_events "
                    "SET actor_id = 'changed' WHERE investigation_file_id = :file_id"
                ),
                {"file_id": investigation.id},
            )


@pytest.mark.integration
async def test_investigation_rejects_stale_version_and_double_active_membership(
    db_session: AsyncSession,
) -> None:
    source = await stored_normalized(db_session, 4)
    other_source = await stored_normalized(db_session, 5)
    repository = SqlAlchemyInvestigationRepository(db_session)
    signal = await repository.get_or_create_signal(source.id, "individual-signal-v1", NOW)
    other = await repository.get_or_create_signal(other_source.id, "individual-signal-v1", NOW)
    first_file = await repository.create_file(
        signal.id, "analyst-1", f"create-{uuid4()}", NOW
    )
    second_file = await repository.create_file(
        other.id, "analyst-1", f"create-{uuid4()}", NOW
    )

    with pytest.raises(InvestigationConcurrencyConflict):
        await repository.reject_suggestion(
            first_file.id,
            other.id,
            "analyst-1",
            f"reject-{uuid4()}",
            expected_version=0,
            occurred_at=NOW,
            reason_code="not-related",
        )

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await repository.add_member(
                second_file.id,
                signal.id,
                "analyst-1",
                f"duplicate-{uuid4()}",
                expected_version=1,
                occurred_at=NOW,
            )
