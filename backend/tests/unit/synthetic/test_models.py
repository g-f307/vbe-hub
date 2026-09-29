from datetime import date

import pytest

from vbe_hub.synthetic.models import (
    GeneratedRecord,
    GeneratorConfig,
    RelationKind,
    ScenarioKind,
)


def test_accepts_reproducible_generator_configuration() -> None:
    config = GeneratorConfig(
        seed=307,
        total_records=120,
        media_ratio=0.6,
        event_count=12,
        relation_distribution={relation: 1 for relation in RelationKind},
        languages=("pt-BR", "es"),
        noise_level=0.25,
        missing_field_rate=0.15,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        allowed_locations=("Manaus", "Iranduba", "Itacoatiara"),
    )

    assert config.seed == 307
    assert config.total_records == 120
    assert config.scenario_kinds == tuple(ScenarioKind)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("total_records", 0, "total_records"),
        ("media_ratio", 1.1, "media_ratio"),
        ("event_count", 0, "event_count"),
        ("noise_level", -0.1, "noise_level"),
        ("missing_field_rate", 2, "missing_field_rate"),
    ],
)
def test_rejects_invalid_numeric_configuration(field: str, value: object, match: str) -> None:
    values = GeneratorConfig.defaults_dict()
    values[field] = value

    with pytest.raises(ValueError, match=match):
        GeneratorConfig(**values)


def test_rejects_inverted_period() -> None:
    values = GeneratorConfig.defaults_dict()
    values["start_date"] = date(2026, 2, 1)
    values["end_date"] = date(2026, 1, 1)

    with pytest.raises(ValueError, match="period"):
        GeneratorConfig(**values)


def test_pipeline_record_has_no_evaluation_identifiers() -> None:
    record = GeneratedRecord(
        id="30700000-0000-5000-8000-000000000001",
        source_kind="media",
        source_name="Agência Sentinela Sintética",
        external_id="media-000001",
        published_at="2026-01-10T12:00:00+00:00",
        title="Alerta sintético",
        body="Texto inteiramente sintético.",
        source_url="https://sentinela.invalid/media-000001",
        language="pt-BR",
        payload={"municipality": "Manaus"},
        provenance={"generator": "vbe-hub", "version": "1.0.0", "seed": 307},
    )

    serialized = record.to_dict()

    assert "gold_event_id" not in serialized
    assert "scenario_id" not in serialized
    assert serialized["provenance"]["seed"] == 307
