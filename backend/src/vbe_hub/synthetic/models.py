"""Public contracts used by the deterministic synthetic-data generator."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class RelationKind(StrEnum):
    """Expected semantic relation between two generated records."""

    DUPLICATE = "duplicate"
    CORROBORATION = "corroboration"
    UPDATE = "update"
    RELATED_CONTEXT = "related_context"
    UNRELATED = "unrelated"


class ScenarioKind(StrEnum):
    """Required situations represented by the verification dataset."""

    DUPLICATE = "duplicate"
    CORROBORATION = "corroboration"
    UPDATE = "update"
    RELATED_CONTEXT = "related_context"
    UNRELATED_TIME = "unrelated_time"
    UNRELATED_LOCATION = "unrelated_location"
    UNKNOWN_DISEASE = "unknown_disease"
    KNOWN_PARTIAL = "known_partial"
    LOCATION_VARIATION = "location_variation"
    DATE_VARIATION = "date_variation"
    MAGNITUDE_VARIATION = "magnitude_variation"
    IRRELEVANT = "irrelevant"


def _default_relations() -> dict[RelationKind, int]:
    return {relation: 1 for relation in RelationKind}


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Validated, explicit inputs that make a generation run reproducible."""

    seed: int = 307
    total_records: int = 120
    media_ratio: float = 0.6
    event_count: int = 12
    relation_distribution: Mapping[RelationKind, float] = field(
        default_factory=_default_relations
    )
    languages: tuple[str, ...] = ("pt-BR",)
    noise_level: float = 0.2
    missing_field_rate: float = 0.1
    start_date: date = date(2026, 1, 1)
    end_date: date = date(2026, 3, 31)
    allowed_locations: tuple[str, ...] = ("Manaus",)
    generator_version: str = "1.0.0"
    scenario_kinds: tuple[ScenarioKind, ...] = field(
        default_factory=lambda: tuple(ScenarioKind)
    )

    def __post_init__(self) -> None:
        if self.total_records <= 0:
            raise ValueError("total_records must be greater than zero")
        if not 0 <= self.media_ratio <= 1:
            raise ValueError("media_ratio must be between zero and one")
        if self.event_count <= 0:
            raise ValueError("event_count must be greater than zero")
        if not 0 <= self.noise_level <= 1:
            raise ValueError("noise_level must be between zero and one")
        if not 0 <= self.missing_field_rate <= 1:
            raise ValueError("missing_field_rate must be between zero and one")
        if self.start_date > self.end_date:
            raise ValueError("generation period start must not follow its end")
        if not self.languages:
            raise ValueError("languages must not be empty")
        if not self.allowed_locations:
            raise ValueError("allowed_locations must not be empty")
        if not self.scenario_kinds:
            raise ValueError("scenario_kinds must not be empty")
        if not self.relation_distribution:
            raise ValueError("relation_distribution must not be empty")
        if any(weight < 0 for weight in self.relation_distribution.values()):
            raise ValueError("relation_distribution weights must not be negative")
        if sum(self.relation_distribution.values()) <= 0:
            raise ValueError("relation_distribution must have a positive total weight")

    @classmethod
    def defaults_dict(cls) -> dict[str, Any]:
        """Return independent constructor values, convenient for controlled overrides."""

        return {
            "seed": 307,
            "total_records": 120,
            "media_ratio": 0.6,
            "event_count": 12,
            "relation_distribution": _default_relations(),
            "languages": ("pt-BR",),
            "noise_level": 0.2,
            "missing_field_rate": 0.1,
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 3, 31),
            "allowed_locations": ("Manaus",),
            "generator_version": "1.0.0",
            "scenario_kinds": tuple(ScenarioKind),
        }


@dataclass(frozen=True, slots=True)
class GeneratedRecord:
    """A generated input record whose shape is safe for the ingestion pipeline."""

    id: str
    source_kind: str
    source_name: str
    external_id: str
    published_at: str
    title: str
    body: str
    source_url: str
    language: str
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize without evaluation-only identifiers or labels."""

        return {
            "id": self.id,
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "external_id": self.external_id,
            "published_at": self.published_at,
            "title": self.title,
            "body": self.body,
            "source_url": self.source_url,
            "language": self.language,
            "payload": dict(self.payload),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class GoldLabel:
    """Evaluation-only classification for one generated record."""

    record_id: str
    scenario_id: str
    gold_event_id: str | None
    scenario_kind: ScenarioKind


@dataclass(frozen=True, slots=True)
class ExpectedRelation:
    """Evaluation-only expected relation between two records."""

    left_record_id: str
    right_record_id: str
    relation: RelationKind


@dataclass(frozen=True, slots=True)
class SyntheticDataset:
    """Generated inputs and a physically separable evaluation reference."""

    records: tuple[GeneratedRecord, ...]
    labels: tuple[GoldLabel, ...]
    relations: tuple[ExpectedRelation, ...]
