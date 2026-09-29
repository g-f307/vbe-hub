from datetime import date
from uuid import UUID

import pytest

from vbe_hub.application.correlation.candidates import (
    CandidateInput,
    CandidatePolicy,
    CandidateSelector,
    GeographicLevel,
)

ANCHOR_ID = UUID("00000000-0000-0000-0000-000000000011")


def sheet(
    *,
    start: date | None = date(2026, 3, 10),
    country: str | None = "Brasil",
    state: str | None = "Amazonas",
    municipality: str | None = "Manaus",
    district: str | None = "Centro",
    disease: str | None = "Sarampo",
    syndrome: str | None = "síndrome febril exantemática",
    symptoms: tuple[str, ...] = ("febre", "manchas vermelhas"),
) -> dict[str, object]:
    return {
        "disease_or_condition": disease,
        "syndrome": syndrome,
        "symptoms": list(symptoms),
        "temporal": {"start": start, "end": None},
        "location": {
            "country": country,
            "state": state,
            "municipality": municipality,
            "district": district,
        },
    }


def candidate(identifier: int, semantic_score: float, **changes: object) -> CandidateInput:
    return CandidateInput(
        normalized_record_id=UUID(f"00000000-0000-0000-0000-{identifier:012d}"),
        semantic_score=semantic_score,
        technical_sheet=sheet(**changes),
    )


def selector(**changes: object) -> CandidateSelector:
    values = {
        "max_temporal_gap_days": 14,
        "geographic_level": GeographicLevel.MUNICIPALITY,
        "minimum_semantic_score": 0.70,
        "minimum_total_score": 0.65,
    }
    values.update(changes)
    return CandidateSelector(CandidatePolicy(**values))


@pytest.mark.parametrize("gap_days,included", [(14, True), (15, False)])
def test_temporal_window_includes_boundary_and_excludes_day_after(
    gap_days: int, included: bool
) -> None:
    result = selector().select(
        anchor_id=ANCHOR_ID,
        anchor_sheet=sheet(),
        neighbors=[candidate(12, 0.90, start=date(2026, 3, 10 + gap_days))],
    )

    assert result.decisions[0].included is included
    assert ("temporal_gap_exceeded" in result.decisions[0].reasons) is not included


def test_geographic_conflict_respects_configured_level() -> None:
    manacapuru = candidate(12, 0.95, municipality="Manacapuru", district=None)

    strict = selector(geographic_level=GeographicLevel.MUNICIPALITY).select(
        anchor_id=ANCHOR_ID, anchor_sheet=sheet(), neighbors=[manacapuru]
    )
    state_level = selector(geographic_level=GeographicLevel.STATE).select(
        anchor_id=ANCHOR_ID, anchor_sheet=sheet(), neighbors=[manacapuru]
    )

    assert strict.decisions[0].included is False
    assert strict.decisions[0].reasons == ("geographic_conflict:municipality",)
    assert state_level.decisions[0].included is True


def test_iso_dates_use_the_same_temporal_boundary_as_date_objects() -> None:
    anchor = sheet()
    anchor["temporal"] = {"start": "2026-03-10", "end": None}
    neighbor = candidate(12, 0.90)
    neighbor.technical_sheet["temporal"] = {"start": "2026-03-25", "end": None}

    result = selector().select(
        anchor_id=ANCHOR_ID, anchor_sheet=anchor, neighbors=[neighbor]
    )

    assert result.decisions[0].included is False
    assert result.decisions[0].reasons == ("temporal_gap_exceeded",)


def test_incomplete_record_is_included_with_semantic_and_clinical_evidence() -> None:
    incomplete = candidate(
        12,
        0.92,
        start=None,
        country=None,
        state=None,
        municipality=None,
        district=None,
        disease=None,
    )

    result = selector().select(
        anchor_id=ANCHOR_ID, anchor_sheet=sheet(), neighbors=[incomplete]
    )

    decision = result.decisions[0]
    assert decision.included is True
    assert decision.components.semantic == 0.92
    assert decision.components.clinical == 1.0
    assert decision.components.temporal == 0.5
    assert decision.components.geographic == 0.5
    assert "temporal_unknown" in decision.reasons
    assert "geographic_unknown" in decision.reasons
    assert "candidate_selected" in decision.reasons


def test_low_evidence_neighbor_records_exclusion_reason() -> None:
    result = selector().select(
        anchor_id=ANCHOR_ID,
        anchor_sheet=sheet(),
        neighbors=[
            candidate(
                12,
                0.30,
                disease="Dengue",
                syndrome="síndrome febril",
                symptoms=("dor no corpo",),
            )
        ],
    )

    decision = result.decisions[0]
    assert decision.included is False
    assert decision.reasons == ("semantic_score_below_minimum", "total_score_below_minimum")


def test_output_is_deterministic_and_ordered_by_score_then_id() -> None:
    first = candidate(12, 0.90)
    second = candidate(13, 0.90)

    forward = selector().select(
        anchor_id=ANCHOR_ID, anchor_sheet=sheet(), neighbors=[second, first]
    )
    reverse = selector().select(
        anchor_id=ANCHOR_ID, anchor_sheet=sheet(), neighbors=[first, second]
    )

    assert forward == reverse
    assert [item.normalized_record_id for item in forward.included] == [
        first.normalized_record_id,
        second.normalized_record_id,
    ]


def test_policy_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="max_temporal_gap_days"):
        selector(max_temporal_gap_days=-1)
    with pytest.raises(ValueError, match="minimum_semantic_score"):
        selector(minimum_semantic_score=1.1)
