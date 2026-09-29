from datetime import UTC, datetime

import pytest

from vbe_hub.domain.records import RawRecord, SourceKind
from vbe_hub.normalization.adapters import CommunityNormalizer, MediaNormalizer
from vbe_hub.normalization.errors import NormalizationError


def _raw_record(*, source_kind: SourceKind, payload: dict[str, object]) -> RawRecord:
    return RawRecord.create(
        source_kind=source_kind,
        source_name="Fonte sintética",
        external_id="source-001",
        published_at=datetime(2026, 2, 3, 14, 30, tzinfo=UTC),
        title="Alerta local" if source_kind is SourceKind.MEDIA else None,
        body="Várias pessoas relataram febre e manchas vermelhas.",
        source_url="https://dados-sinteticos.invalid/source-001",
        language="PT_br",
        original_payload=payload,
    )


def test_media_adapter_produces_the_common_normalized_contract() -> None:
    record = _raw_record(
        source_kind=SourceKind.MEDIA,
        payload={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Cidade Nova",
            "geographic_precision": "district",
            "symptoms": ["febre", "manchas vermelhas"],
            "estimated_cases": 12,
            "estimated_deaths": 1,
            "affected_group": "comunidade escolar",
            "environment": "escola",
            "topic": "sarampo",
        },
    )

    normalized = MediaNormalizer().normalize(record)

    assert normalized == {
        "source_kind": "media",
        "source_name": "Fonte sintética",
        "external_id": "source-001",
        "published_at": "2026-02-03T14:30:00+00:00",
        "language": "pt-BR",
        "title": "Alerta local",
        "text": "Várias pessoas relataram febre e manchas vermelhas.",
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Cidade Nova",
            "specific": None,
            "precision": "district",
        },
        "magnitude": {"estimated_cases": 12, "estimated_deaths": 1},
        "symptoms": ["febre", "manchas vermelhas"],
        "affected_group": "comunidade escolar",
        "environment": "escola",
        "metadata": {
            "source_url": "https://dados-sinteticos.invalid/source-001",
            "reported_window_start": None,
            "reported_window_end": None,
            "topic": "sarampo",
        },
    }


def test_community_adapter_produces_the_same_contract_and_normalizes_window() -> None:
    record = _raw_record(
        source_kind=SourceKind.COMMUNITY,
        payload={
            "municipality": "Manaus",
            "neighborhood": "Cidade Nova",
            "geographic_precision": "neighborhood",
            "symptoms": ["febre"],
            "estimated_cases": 7,
            "report_window_start": "2026-02-01T08:00:00-04:00",
            "report_window_end": "2026-02-02T08:00:00-04:00",
        },
    )

    normalized = CommunityNormalizer().normalize(record)

    assert set(normalized) == {
        "source_kind",
        "source_name",
        "external_id",
        "published_at",
        "language",
        "title",
        "text",
        "location",
        "magnitude",
        "symptoms",
        "affected_group",
        "environment",
        "metadata",
    }
    assert normalized["location"] == {
        "country": None,
        "state": None,
        "municipality": "Manaus",
        "district": "Cidade Nova",
        "specific": None,
        "precision": "district",
    }
    assert normalized["magnitude"] == {
        "estimated_cases": 7,
        "estimated_deaths": None,
    }
    assert normalized["metadata"] == {
        "source_url": "https://dados-sinteticos.invalid/source-001",
        "reported_window_start": "2026-02-01T12:00:00+00:00",
        "reported_window_end": "2026-02-02T12:00:00+00:00",
        "topic": None,
    }


def test_unknown_values_remain_null_instead_of_becoming_zero_or_labels() -> None:
    record = _raw_record(
        source_kind=SourceKind.COMMUNITY,
        payload={
            "municipality": None,
            "geographic_precision": "unknown",
            "estimated_cases": None,
        },
    )

    normalized = CommunityNormalizer().normalize(record)

    assert normalized["location"]["municipality"] is None
    assert normalized["location"]["precision"] is None
    assert normalized["magnitude"]["estimated_cases"] is None
    assert normalized["magnitude"]["estimated_deaths"] is None
    assert normalized["symptoms"] == []


@pytest.mark.parametrize("value", [-1, "muitas", True])
def test_adapter_rejects_invalid_case_magnitude(value: object) -> None:
    record = _raw_record(
        source_kind=SourceKind.COMMUNITY,
        payload={"estimated_cases": value},
    )

    with pytest.raises(NormalizationError, match="estimated_cases"):
        CommunityNormalizer().normalize(record)


@pytest.mark.parametrize(
    ("adapter", "source_kind"),
    [
        (MediaNormalizer(), SourceKind.COMMUNITY),
        (CommunityNormalizer(), SourceKind.MEDIA),
    ],
)
def test_each_adapter_rejects_the_other_source_kind(
    adapter: MediaNormalizer | CommunityNormalizer,
    source_kind: SourceKind,
) -> None:
    record = _raw_record(source_kind=source_kind, payload={})

    with pytest.raises(NormalizationError, match="source kind"):
        adapter.normalize(record)
