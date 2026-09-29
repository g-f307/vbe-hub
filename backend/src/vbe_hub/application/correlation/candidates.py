from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID


class GeographicLevel(StrEnum):
    COUNTRY = "country"
    STATE = "state"
    MUNICIPALITY = "municipality"
    DISTRICT = "district"


@dataclass(frozen=True, slots=True)
class CandidatePolicy:
    max_temporal_gap_days: int
    geographic_level: GeographicLevel
    minimum_semantic_score: float
    minimum_total_score: float

    def __post_init__(self) -> None:
        if self.max_temporal_gap_days < 0:
            raise ValueError("max_temporal_gap_days must be non-negative")
        for name in ("minimum_semantic_score", "minimum_total_score"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CandidateInput:
    normalized_record_id: UUID
    semantic_score: float
    technical_sheet: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not 0 <= self.semantic_score <= 1:
            raise ValueError("semantic_score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ScoreComponents:
    semantic: float
    clinical: float
    temporal: float
    geographic: float


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    normalized_record_id: UUID
    included: bool
    score: float
    components: ScoreComponents
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateSelectionResult:
    included: tuple[CandidateDecision, ...]
    decisions: tuple[CandidateDecision, ...]


class CandidateSelector:
    def __init__(self, policy: CandidatePolicy) -> None:
        self._policy = policy

    def select(
        self,
        *,
        anchor_id: UUID,
        anchor_sheet: Mapping[str, Any],
        neighbors: Sequence[CandidateInput],
    ) -> CandidateSelectionResult:
        decisions = [
            self._evaluate(anchor_sheet=anchor_sheet, candidate=item)
            for item in neighbors
            if item.normalized_record_id != anchor_id
        ]
        ordered = tuple(
            sorted(decisions, key=lambda item: (-item.score, str(item.normalized_record_id)))
        )
        return CandidateSelectionResult(
            included=tuple(item for item in ordered if item.included), decisions=ordered
        )

    def _evaluate(
        self,
        *,
        anchor_sheet: Mapping[str, Any],
        candidate: CandidateInput,
    ) -> CandidateDecision:
        temporal_score, temporal_reason = _temporal_compatibility(
            anchor_sheet, candidate.technical_sheet, self._policy.max_temporal_gap_days
        )
        geographic_score, geographic_reason = _geographic_compatibility(
            anchor_sheet, candidate.technical_sheet, self._policy.geographic_level
        )
        components = ScoreComponents(
            semantic=candidate.semantic_score,
            clinical=_clinical_similarity(anchor_sheet, candidate.technical_sheet),
            temporal=temporal_score,
            geographic=geographic_score,
        )
        total = round(
            0.50 * components.semantic
            + 0.25 * components.clinical
            + 0.125 * components.temporal
            + 0.125 * components.geographic,
            6,
        )
        reasons = [reason for reason in (temporal_reason, geographic_reason) if reason]
        hard_exclusion = any(
            reason == "temporal_gap_exceeded" or reason.startswith("geographic_conflict:")
            for reason in reasons
        )
        if candidate.semantic_score < self._policy.minimum_semantic_score:
            reasons.append("semantic_score_below_minimum")
        if total < self._policy.minimum_total_score:
            reasons.append("total_score_below_minimum")
        included = not hard_exclusion and not any(
            reason.endswith("below_minimum") for reason in reasons
        )
        if included:
            reasons.append("candidate_selected")
        return CandidateDecision(
            normalized_record_id=candidate.normalized_record_id,
            included=included,
            score=total,
            components=components,
            reasons=tuple(reasons),
        )


def _temporal_compatibility(
    left: Mapping[str, Any], right: Mapping[str, Any], max_gap_days: int
) -> tuple[float, str | None]:
    left_range = _date_range(left)
    right_range = _date_range(right)
    if left_range is None or right_range is None:
        return 0.5, "temporal_unknown"
    left_start, left_end = left_range
    right_start, right_end = right_range
    gap = max(0, (right_start - left_end).days, (left_start - right_end).days)
    if gap > max_gap_days:
        return 0.0, "temporal_gap_exceeded"
    if max_gap_days == 0:
        return 1.0, None
    return round(1 - gap / max_gap_days, 6), None


def _date_range(sheet: Mapping[str, Any]) -> tuple[date, date] | None:
    temporal = sheet.get("temporal")
    if not isinstance(temporal, Mapping):
        return None
    start = _as_date(temporal.get("start"))
    end = _as_date(temporal.get("end")) or start
    if start is None or end is None:
        return None
    return (min(start, end), max(start, end))


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _geographic_compatibility(
    left: Mapping[str, Any], right: Mapping[str, Any], level: GeographicLevel
) -> tuple[float, str | None]:
    levels = ("country", "state", "municipality", "district")
    selected = levels[: levels.index(level.value) + 1]
    left_location = left.get("location")
    right_location = right.get("location")
    if not isinstance(left_location, Mapping) or not isinstance(right_location, Mapping):
        return 0.5, "geographic_unknown"
    comparable = []
    for field in selected:
        left_value = _normalized(left_location.get(field))
        right_value = _normalized(right_location.get(field))
        if left_value is None or right_value is None:
            continue
        if left_value != right_value:
            return 0.0, f"geographic_conflict:{field}"
        comparable.append(field)
    if not comparable:
        return 0.5, "geographic_unknown"
    completeness = len(comparable) / len(selected)
    reason = None if completeness == 1 else "geographic_partial"
    return round(0.5 + 0.5 * completeness, 6), reason


def _clinical_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    comparisons: list[float] = []
    for field in ("disease_or_condition", "pathogen", "syndrome"):
        left_value = _normalized(left.get(field))
        right_value = _normalized(right.get(field))
        if left_value is not None and right_value is not None:
            comparisons.append(float(left_value == right_value))
    left_symptoms = _normalized_set(left.get("symptoms"))
    right_symptoms = _normalized_set(right.get("symptoms"))
    if left_symptoms and right_symptoms:
        comparisons.append(
            len(left_symptoms & right_symptoms) / len(left_symptoms | right_symptoms)
        )
    return round(sum(comparisons) / len(comparisons), 6) if comparisons else 0.5


def _normalized(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.casefold().split())


def _normalized_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {normalized for item in value if (normalized := _normalized(item)) is not None}
