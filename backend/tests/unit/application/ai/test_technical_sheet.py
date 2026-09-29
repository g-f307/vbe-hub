import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vbe_hub.application.ai.technical_sheet import (
    SCHEMA_VERSION,
    TechnicalSheet,
    validate_grounded_sheet,
)

FIXTURES = Path("tests/fixtures/ai/technical-sheet/v1")
SCHEMA = Path("src/vbe_hub/application/ai/assets/technical-sheet-v1.schema.json")


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_versioned_json_schema_matches_the_runtime_model() -> None:
    committed_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert SCHEMA_VERSION == "technical-sheet-v1"
    assert committed_schema == TechnicalSheet.model_json_schema()
    assert committed_schema["additionalProperties"] is False


def test_valid_sheet_preserves_explicit_nulls_and_grounded_evidence() -> None:
    source_text = (
        "community. "
        "Relato sintético: moradores do bairro Flores apresentam febre e manchas vermelhas. "
        "A investigação epidemiológica está em andamento."
    )

    sheet = validate_grounded_sheet(load_fixture("success.json"), source_text=source_text)

    assert sheet.disease_or_condition == "sarampo"
    assert sheet.pathogen is None
    assert sheet.estimated_deaths is None
    assert sheet.location.district == "Flores"
    assert sheet.confidence == 0.82


def test_sheet_rejects_unknown_fields_and_invalid_confidence() -> None:
    payload = load_fixture("success.json")
    payload["diagnosis_confirmed"] = True

    with pytest.raises(ValidationError, match="diagnosis_confirmed"):
        TechnicalSheet.model_validate(payload)

    payload = load_fixture("success.json")
    payload["confidence"] = 1.1

    with pytest.raises(ValidationError, match="confidence"):
        TechnicalSheet.model_validate(payload)


def test_non_null_field_without_evidence_is_rejected() -> None:
    payload = load_fixture("success.json")
    payload["evidence"] = [
        evidence for evidence in payload["evidence"] if evidence["field"] != "disease_or_condition"
    ]

    with pytest.raises(ValueError, match="disease_or_condition.*evidence"):
        validate_grounded_sheet(
            payload,
            source_text=(
                "community. Relato sintético: moradores do bairro Flores apresentam febre e "
                "manchas "
                "vermelhas. A investigação epidemiológica está em andamento."
            ),
        )


def test_evidence_must_be_a_bounded_literal_excerpt_of_the_source() -> None:
    payload = load_fixture("success.json")
    payload["evidence"][0]["excerpt"] = "texto inventado pelo modelo"

    with pytest.raises(ValueError, match="literal excerpt"):
        validate_grounded_sheet(payload, source_text="Possível sarampo com febre em Flores.")

    payload = load_fixture("success.json")
    payload["evidence"][0]["excerpt"] = "x" * 241

    with pytest.raises(ValidationError, match="excerpt"):
        TechnicalSheet.model_validate(payload)


def test_null_only_sheet_is_valid_without_evidence() -> None:
    sheet = validate_grounded_sheet(
        load_fixture("nulls.json"),
        source_text="Narrativa sintética sem elementos epidemiológicos suficientes.",
    )

    assert sheet.disease_or_condition is None
    assert sheet.symptoms == []
    assert sheet.evidence == []
