from datetime import UTC, datetime
from uuid import UUID

import pytest

from vbe_hub.domain.records import (
    EvaluationLabel,
    NormalizationStatus,
    ProcessingRun,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)


def test_creates_media_record_with_canonical_hash() -> None:
    published_at = datetime(2026, 9, 28, 14, 30, tzinfo=UTC)
    first_payload = {"location": {"city": "Manaus"}, "topics": ["sarampo"]}
    reordered_payload = {"topics": ["sarampo"], "location": {"city": "Manaus"}}

    first = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="jornal-sintetico",
        external_id="news-001",
        published_at=published_at,
        title="Aumento de casos suspeitos",
        body="Moradores relatam manchas vermelhas.",
        source_url="https://example.invalid/news-001",
        language="pt-BR",
        original_payload=first_payload,
    )
    second = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="jornal-sintetico",
        external_id="news-001",
        published_at=published_at,
        title="Aumento de casos suspeitos",
        body="Moradores relatam manchas vermelhas.",
        source_url="https://example.invalid/news-001",
        language="pt-BR",
        original_payload=reordered_payload,
    )

    assert isinstance(first.id, UUID)
    assert first.original_payload == first_payload
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64


def test_creates_community_record_without_optional_media_fields() -> None:
    record = RawRecord.create(
        source_kind=SourceKind.COMMUNITY,
        source_name="guardioes-sintetico",
        external_id=None,
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        title=None,
        body="Relatos agregados de febre no bairro.",
        source_url=None,
        language="pt-BR",
        original_payload={"municipality": "Manaus", "neighborhood": "Flores"},
    )

    assert record.source_kind is SourceKind.COMMUNITY
    assert record.title is None
    assert record.source_url is None


def test_rejects_datetime_without_timezone() -> None:
    with pytest.raises(ValueError, match="timezone"):
        RawRecord.create(
            source_kind=SourceKind.MEDIA,
            source_name="jornal-sintetico",
            external_id=None,
            published_at=datetime(2026, 9, 28),
            title=None,
            body="Texto sintético.",
            source_url=None,
            language="pt-BR",
            original_payload={},
        )


def test_provenance_requires_timezone_aware_collection_time() -> None:
    with pytest.raises(ValueError, match="timezone"):
        Provenance(
            adapter_name="synthetic-importer",
            adapter_version="1.0.0",
            collected_at=datetime(2026, 9, 28),
        )


def test_evaluation_label_stays_outside_raw_record() -> None:
    record = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="jornal-sintetico",
        external_id="news-002",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        title="Notícia sintética",
        body="Conteúdo para avaliação.",
        source_url=None,
        language="pt-BR",
        original_payload={},
    )
    label = EvaluationLabel(raw_record_id=record.id, gold_event_id="event-001")

    assert label.raw_record_id == record.id
    assert not hasattr(record, "gold_event_id")


def test_normalization_failure_is_structured_and_retryable() -> None:
    failure = NormalizationStatus.failed(
        code="invalid_location",
        message="Município ausente",
        retryable=True,
    )

    assert failure.state == "failed"
    assert failure.error == {
        "code": "invalid_location",
        "message": "Município ausente",
    }
    assert failure.retryable is True


def test_processing_run_rejects_datetime_without_timezone() -> None:
    with pytest.raises(ValueError, match="timezone"):
        ProcessingRun(
            id=UUID("30700000-0000-0000-0000-000000000001"),
            run_type="synthetic_import",
            state=ProcessingState.RUNNING,
            started_at=datetime(2026, 9, 28),
        )


def test_processing_run_rejects_negative_counters() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ProcessingRun(
            id=UUID("30700000-0000-0000-0000-000000000002"),
            run_type="synthetic_import",
            state=ProcessingState.FAILED,
            started_at=datetime(2026, 9, 28, tzinfo=UTC),
            failed_count=-1,
        )
