from datetime import UTC, datetime
from uuid import UUID

from vbe_hub.application.investigations.information import (
    compose_information,
    project_information,
)

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def test_simulated_collection_date_is_not_presented_as_real_detection() -> None:
    result = project_information(
        source_payload={}, technical_sheet=None, detected_at=NOW,
        collection_is_simulated=True,
    )
    assert result.detected_at is None
    assert "detected_at" not in result.origins


def test_information_preserves_missing_operational_fields_and_date_precision() -> None:
    result = project_information(
        source_payload={},
        technical_sheet={
            "disease_or_condition": "Dengue (suspeita)",
            "symptoms": ["febre"],
            "temporal": {"start": "2026-11-14", "precision": "day"},
            "confidence": 0.99,
        },
        detected_at=NOW,
    )

    assert result.etiology == "Dengue (suspeita)"
    assert result.signal_date == "2026-11-14"
    assert result.detected_at == NOW
    assert result.confidentiality is None
    assert result.signal_type is None
    assert result.notified_at is None
    assert result.hazard_general is None
    assert result.tags == []
    assert result.origins["etiology"] == "extraction:disease_or_condition"


def test_information_reads_explicit_source_fields_without_inventing_classifications() -> None:
    result = project_information(
        source_payload={"signal_information": {
            "confidentiality": "Nível 1", "signal_type": "Abertura",
            "hazard_general": "Arbovirose", "hazard_specific": "Dengue",
            "tags": ["dengue", "Febre", " febre ", "arbovirose"],
            "signal_date": "2026-11-14T01:00:00-04:00",
            "notified_at": "2026-11-20T08:00:00-04:00",
        }},
        technical_sheet=None,
        detected_at=NOW,
    )

    assert result.confidentiality == "Nível 1"
    assert result.signal_type == "Abertura"
    assert result.tags == ["dengue", "febre", "arbovirose"]
    assert result.signal_date == "2026-11-14T01:00:00-04:00"
    assert result.notified_at.isoformat() == "2026-11-20T08:00:00-04:00"
    assert result.origins["hazard_general"] == "source:signal_information.hazard_general"


def test_invalid_source_values_are_ignored_without_hiding_the_original_signal() -> None:
    result = project_information(
        source_payload={"signal_information": {
            "confidentiality": {"invalid": True}, "signal_date": "ontem",
            "notified_at": "2026-11-20", "tags": [42, "febre"],
        }}, technical_sheet=None, detected_at=NOW,
    )
    assert result.confidentiality is None
    assert result.signal_date is None
    assert result.notified_at is None
    assert result.tags == ["febre"]


def test_composition_complements_only_shared_fields_and_records_conflicts() -> None:
    head = project_information(source_payload={}, technical_sheet=None, detected_at=NOW)
    evidence = project_information(
        source_payload={"signal_information": {
            "confidentiality": "Nível 2", "signal_type": "Atualização",
            "hazard_general": "Arbovirose", "tags": ["dengue"],
            "notified_at": "2026-11-20T10:00:00Z",
        }}, technical_sheet={"disease_or_condition": "Dengue (suspeita)"}, detected_at=NOW,
    )
    other = evidence.model_copy(update={"hazard_general": "Outra categoria"})
    result = compose_information(UUID(int=1), head, [(UUID(int=2), evidence), (UUID(int=3), other)])

    assert result.information.etiology == "Dengue (suspeita)"
    assert result.information.tags == ["dengue"]
    assert result.information.confidentiality is None
    assert result.information.signal_type is None
    assert result.information.notified_at is None
    assert result.information.hazard_general == "Arbovirose"
    assert result.provenance["etiology"] == [str(UUID(int=2))]
    assert result.conflicts[0]["field"] == "hazard_general"
