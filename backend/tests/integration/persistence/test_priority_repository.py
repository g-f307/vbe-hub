from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.priority_repository import SqlAlchemyPriorityRepository
from vbe_hub.adapters.persistence.repositories import SqlAlchemyRawRecordRepository
from vbe_hub.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from vbe_hub.application.correlation.priority import (
    PriorityCalculator,
    PriorityPolicy,
    PriorityRecord,
)
from vbe_hub.application.correlation.signals import (
    ConsolidationPolicy,
    SignalConsolidationService,
    SignalRecord,
)
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def sheet() -> dict:
    return {
        "disease_or_condition": "Sarampo",
        "syndrome": "Síndrome febril exantemática",
        "symptoms": ["febre"],
        "estimated_cases": 10,
        "estimated_deaths": None,
        "temporal": {"start": "2026-10-02", "end": None, "precision": "day"},
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": None,
            "specific": None,
            "precision": "municipality",
        },
    }


async def stored_signal(db_session: AsyncSession):
    raw = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="synthetic-media",
        external_id=f"priority-{uuid4()}",
        published_at=NOW,
        title="Sinal sintético",
        body="Texto sintético sem dados pessoais.",
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
        records=[SignalRecord(normalized.id, sheet())],
        relations=[],
    )
    await SqlAlchemySignalRepository(db_session).save(result)
    return result.signals[0], PriorityRecord(
        record_id=normalized.id,
        source_kind=raw.source_kind,
        source_name=raw.source_name,
        technical_sheet=sheet(),
    )


@pytest.mark.integration
async def test_priority_repository_is_idempotent_and_recovers_explanation(
    db_session: AsyncSession,
) -> None:
    signal, source = await stored_signal(db_session)
    priority = PriorityCalculator(PriorityPolicy.v1()).calculate(
        signal=signal,
        records=[source],
        relations=[],
        evaluated_at=NOW,
    )
    repository = SqlAlchemyPriorityRepository(db_session)

    await repository.save(priority)
    await repository.save(priority)
    await db_session.commit()

    assert await repository.get(priority.id) == priority
    assert await repository.list_by_signal(signal.id) == [priority]


@pytest.mark.integration
async def test_priority_repository_preserves_recalculations_with_new_policy(
    db_session: AsyncSession,
) -> None:
    signal, source = await stored_signal(db_session)
    repository = SqlAlchemyPriorityRepository(db_session)

    for version in ("priority-v1", "priority-v2"):
        await repository.save(
            PriorityCalculator(PriorityPolicy.v1(version=version)).calculate(
                signal=signal,
                records=[source],
                relations=[],
                evaluated_at=NOW,
            )
        )
    await db_session.commit()

    recovered = await repository.list_by_signal(signal.id)
    assert [item.policy_version for item in recovered] == ["priority-v1", "priority-v2"]
    assert len({item.id for item in recovered}) == 2

