from datetime import UTC, datetime

from vbe_hub.domain.records import ProcessingState, RawRecord, SourceKind
from vbe_hub.normalization.service import NORMALIZER_VERSION, NormalizationService


def _record(index: int, *, payload: dict[str, object]) -> RawRecord:
    return RawRecord.create(
        source_kind=SourceKind.MEDIA if index % 2 == 0 else SourceKind.COMMUNITY,
        source_name="Fonte sintética",
        external_id=f"source-{index}",
        published_at=datetime(2026, 2, 3, 14, 30, tzinfo=UTC),
        title="Alerta" if index % 2 == 0 else None,
        body="Relato agregado sintético.",
        source_url=f"https://dados-sinteticos.invalid/source-{index}",
        language="pt-BR",
        original_payload=payload,
    )


def test_batch_keeps_processing_after_an_invalid_record() -> None:
    records = [
        _record(0, payload={"estimated_cases": 4}),
        _record(1, payload={"estimated_cases": -1}),
        _record(2, payload={"estimated_cases": 6}),
    ]

    results = NormalizationService().normalize_batch(records)

    assert [result.status.state for result in results] == [
        ProcessingState.SUCCEEDED,
        ProcessingState.FAILED,
        ProcessingState.SUCCEEDED,
    ]
    assert results[1].status.error == {
        "code": "invalid_field",
        "message": "estimated_cases must be a non-negative integer or null",
    }
    assert results[1].normalized_data == {}


def test_results_preserve_source_identity_and_normalizer_version() -> None:
    source = _record(0, payload={})

    result = NormalizationService().normalize_batch([source])[0]

    assert result.raw_record_id == source.id
    assert result.normalizer_version == NORMALIZER_VERSION
    assert result.status.state is ProcessingState.SUCCEEDED
    assert result.status.error is None
    assert result.status.retryable is False
