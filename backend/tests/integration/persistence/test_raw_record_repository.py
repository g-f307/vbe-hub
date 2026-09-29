from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.repositories import (
    DuplicateExternalRecordError,
    SqlAlchemyEvaluationRepository,
    SqlAlchemyRawRecordRepository,
)
from vbe_hub.domain.records import (
    EvaluationLabel,
    NormalizationStatus,
    NormalizedRecord,
    Provenance,
    RawRecord,
    SourceKind,
)


def make_record(
    *,
    source_kind: SourceKind,
    external_id: str | None,
    body: str = "Relato sintético sobre febre e manchas vermelhas.",
) -> RawRecord:
    return RawRecord.create(
        source_kind=source_kind,
        source_name=f"{source_kind.value}-synthetic-source",
        external_id=external_id,
        published_at=datetime(2026, 9, 28, 12, tzinfo=UTC),
        title="Alerta sintético" if source_kind is SourceKind.MEDIA else None,
        body=body,
        source_url="https://example.invalid/item" if source_kind is SourceKind.MEDIA else None,
        language="pt-BR",
        original_payload={
            "municipality": "Manaus",
            "neighborhood": "Flores",
            "symptoms": ["febre", "manchas vermelhas"],
        },
    )


def make_provenance() -> Provenance:
    return Provenance(
        adapter_name="synthetic-importer",
        adapter_version="1.0.0",
        generator_name="vbe-synthetic",
        generator_version="1.0.0",
        seed=307,
        scenario_id="measles-manaus-001",
        collected_at=datetime(2026, 9, 28, 13, tzinfo=UTC),
    )


@pytest.mark.integration
@pytest.mark.parametrize("source_kind", [SourceKind.MEDIA, SourceKind.COMMUNITY])
async def test_inserts_and_recovers_record_with_provenance(
    db_session: AsyncSession, source_kind: SourceKind
) -> None:
    repository = SqlAlchemyRawRecordRepository(db_session)
    record = make_record(source_kind=source_kind, external_id=f"{source_kind.value}-001")
    provenance = make_provenance()

    result = await repository.add(record, provenance)
    await db_session.commit()
    recovered = await repository.get(record.id)

    assert result.created is True
    assert recovered is not None
    assert recovered.record == record
    assert recovered.provenance == provenance
    assert recovered.record.original_payload["neighborhood"] == "Flores"


@pytest.mark.integration
async def test_reprocessing_same_external_record_is_idempotent(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRawRecordRepository(db_session)
    original = make_record(source_kind=SourceKind.MEDIA, external_id="news-idempotent")
    duplicate = make_record(source_kind=SourceKind.MEDIA, external_id="news-idempotent")

    first = await repository.add(original, make_provenance())
    second = await repository.add(duplicate, make_provenance())
    await db_session.commit()

    assert first.created is True
    assert second.created is False
    assert second.record.id == original.id


@pytest.mark.integration
async def test_reprocessing_same_content_without_external_id_is_idempotent(
    db_session: AsyncSession,
) -> None:
    repository = SqlAlchemyRawRecordRepository(db_session)
    first_record = make_record(source_kind=SourceKind.COMMUNITY, external_id=None)
    second_record = make_record(source_kind=SourceKind.COMMUNITY, external_id=None)

    first = await repository.add(first_record, make_provenance())
    second = await repository.add(second_record, make_provenance())
    await db_session.commit()

    assert first.created is True
    assert second.created is False
    assert second.record.id == first_record.id


@pytest.mark.integration
async def test_rejects_external_id_reused_for_different_content(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRawRecordRepository(db_session)
    original = make_record(source_kind=SourceKind.MEDIA, external_id="news-conflict")
    conflicting = make_record(
        source_kind=SourceKind.MEDIA,
        external_id="news-conflict",
        body="Conteúdo diferente para o mesmo identificador.",
    )
    await repository.add(original, make_provenance())

    with pytest.raises(DuplicateExternalRecordError, match="news-conflict"):
        await repository.add(conflicting, make_provenance())


@pytest.mark.integration
async def test_normalization_failure_does_not_remove_raw_record(db_session: AsyncSession) -> None:
    repository = SqlAlchemyRawRecordRepository(db_session)
    raw_record = make_record(source_kind=SourceKind.COMMUNITY, external_id="report-failed")
    await repository.add(raw_record, make_provenance())
    failed = NormalizedRecord(
        id=raw_record.id,
        raw_record_id=raw_record.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus.failed(
            code="invalid_location", message="Município ausente", retryable=True
        ),
        normalized_data={},
    )

    await repository.save_normalized(failed)
    await db_session.commit()

    assert await repository.get(raw_record.id) is not None
    assert await repository.get_normalized(raw_record.id, "1.0.0") == failed


@pytest.mark.integration
async def test_evaluation_label_is_stored_separately_from_pipeline_record(
    db_session: AsyncSession,
) -> None:
    raw_repository = SqlAlchemyRawRecordRepository(db_session)
    evaluation_repository = SqlAlchemyEvaluationRepository(db_session)
    raw_record = make_record(source_kind=SourceKind.MEDIA, external_id="news-labeled")
    await raw_repository.add(raw_record, make_provenance())
    label = EvaluationLabel(raw_record_id=raw_record.id, gold_event_id="gold-event-001")
    await evaluation_repository.add(label)
    await db_session.commit()

    pipeline_record = await raw_repository.get(raw_record.id)

    assert pipeline_record is not None
    assert not hasattr(pipeline_record.record, "gold_event_id")
    assert await evaluation_repository.get(raw_record.id) == label
