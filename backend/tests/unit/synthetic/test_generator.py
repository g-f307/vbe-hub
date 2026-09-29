from collections import Counter

from vbe_hub.synthetic.generator import generate_dataset
from vbe_hub.synthetic.models import GeneratorConfig, ScenarioKind


def test_generation_is_deterministic_for_the_same_configuration() -> None:
    config = GeneratorConfig()

    first = generate_dataset(config)
    second = generate_dataset(config)

    assert first == second


def test_generation_covers_required_scenarios_and_source_ratio() -> None:
    config = GeneratorConfig(total_records=120, media_ratio=0.6)

    dataset = generate_dataset(config)

    assert len(dataset.records) == 120
    assert {label.scenario_kind for label in dataset.labels} == set(ScenarioKind)
    assert Counter(record.source_kind for record in dataset.records) == {
        "media": 72,
        "community": 48,
    }
    assert len(dataset.labels) == len(dataset.records)
    assert dataset.relations


def test_generated_records_respect_allowed_values_and_contain_no_gold_labels() -> None:
    config = GeneratorConfig(
        languages=("pt-BR", "es"),
        allowed_locations=("Manaus", "Iranduba"),
    )

    dataset = generate_dataset(config)

    for record in dataset.records:
        serialized = record.to_dict()
        assert record.language in config.languages
        assert record.payload.get("municipality") in (*config.allowed_locations, None)
        assert record.source_url.startswith("https://")
        assert ".invalid/" in record.source_url
        assert "scenario_id" not in serialized
        assert "gold_event_id" not in serialized
        assert "scenario_id" not in serialized["provenance"]
        assert "gold_event_id" not in serialized["provenance"]


def test_safety_contract_excludes_personal_identifiers() -> None:
    forbidden_keys = {"name", "phone", "email", "cpf", "address", "exact_age"}

    dataset = generate_dataset(GeneratorConfig())

    for record in dataset.records:
        assert forbidden_keys.isdisjoint(record.payload)
        assert "sintétic" in f"{record.source_name} {record.body}".lower()
