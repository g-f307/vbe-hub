from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import TechnicalSheetExtractionModel
from vbe_hub.adapters.persistence.repositories import (
    SqlAlchemyExtractionRepository,
    SqlAlchemyRawRecordRepository,
)
from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    FieldEvidence,
    ProviderErrorCode,
)
from vbe_hub.application.ai.extraction import ExtractionRecord
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


async def persisted_normalized_record(session: AsyncSession) -> NormalizedRecord:
    raw = RawRecord.create(
        source_kind=SourceKind.COMMUNITY,
        source_name="synthetic-community",
        external_id=f"extraction-{uuid4()}",
        published_at=NOW,
        title=None,
        body="Relato sintético sem evidência suficiente.",
        source_url=None,
        language="pt-BR",
        original_payload={"synthetic": True},
    )
    repository = SqlAlchemyRawRecordRepository(session)
    await repository.add(
        raw,
        Provenance(
            adapter_name="synthetic",
            adapter_version="1",
            collected_at=NOW,
        ),
    )
    normalized = NormalizedRecord(
        id=uuid4(),
        raw_record_id=raw.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
        normalized_data={"text": raw.body},
    )
    await repository.save_normalized(normalized)
    return normalized


def succeeded_record(normalized_id: UUID, cache_key: str = "c" * 64) -> ExtractionRecord:
    return ExtractionRecord(
        id=uuid4(),
        normalized_record_id=normalized_id,
        cache_key=cache_key,
        input_hash="8" * 64,
        technical_sheet={"record_nature": None, "evidence": []},
        evidence=(FieldEvidence(field="record_nature", excerpt="Relato sintético"),),
        metadata=AIExecutionMetadata(
            provider="gemini",
            model="gemini-test-model",
            contract_version="technical-sheet-v1",
            prompt_version="extract-v1",
            started_at=NOW,
            duration_ms=120,
            status=ExecutionStatus.SUCCEEDED,
            input_units=20,
            output_units=10,
        ),
        sanitized_error=None,
        created_at=NOW,
    )


@pytest.mark.integration
async def test_persists_and_recovers_validated_sheet_with_audit_metadata(
    db_session: AsyncSession,
) -> None:
    normalized = await persisted_normalized_record(db_session)
    repository = SqlAlchemyExtractionRepository(db_session)
    record = succeeded_record(normalized.id)

    await repository.save(record)
    await db_session.commit()
    recovered = await repository.get_succeeded(record.cache_key)

    assert recovered == record


@pytest.mark.integration
async def test_retry_updates_failed_cache_entry_without_duplicate_result(
    db_session: AsyncSession,
) -> None:
    normalized = await persisted_normalized_record(db_session)
    repository = SqlAlchemyExtractionRepository(db_session)
    success = succeeded_record(normalized.id, cache_key="d" * 64)
    failure = replace(
        success,
        technical_sheet=None,
        evidence=(),
        sanitized_error="Gemini request timed out.",
        metadata=replace(
            success.metadata,
            status=ExecutionStatus.FAILED,
            input_units=None,
            output_units=None,
            error_code=ProviderErrorCode.TIMEOUT,
            retryable=True,
        ),
    )

    await repository.save(failure)
    assert await repository.get_succeeded(failure.cache_key) is None
    await repository.save(success)
    await db_session.commit()

    count = await db_session.scalar(select(func.count()).select_from(TechnicalSheetExtractionModel))
    assert count == 1
    assert await repository.get_succeeded(success.cache_key) == success
