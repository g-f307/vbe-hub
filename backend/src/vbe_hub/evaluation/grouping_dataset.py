from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from vbe_hub.application.ai import RelationKind
from vbe_hub.application.correlation.signals import SignalRecord, SignalRelationInput

Split = Literal["calibration", "evaluation"]
_SCENARIOS = (
    "complete",
    "missing_condition",
    "missing_location",
    "partial_date",
    "conflicting_bridge",
    "weak_context_bridge",
)
_CONDITIONS = ("sarampo", "dengue", "influenza", "leptospirose")
_MUNICIPALITIES = ("Manaus", "Parintins", "Itacoatiara")


@dataclass(frozen=True, slots=True)
class SyntheticReview:
    relation_id: UUID
    action: str
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return {
            "relation_id": str(self.relation_id),
            "action": self.action,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class GroupingInputs:
    dataset_version: str
    split: Split
    seed: int
    records: tuple[SignalRecord, ...]
    automatic_relations: tuple[SignalRelationInput, ...]
    reviewed_relations: tuple[SignalRelationInput, ...]
    reviews: tuple[SyntheticReview, ...]
    scenario_counts: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "dataset_version": self.dataset_version,
            "split": self.split,
            "seed": self.seed,
            "records": [
                {"record_id": str(item.record_id), "technical_sheet": item.technical_sheet}
                for item in self.records
            ],
            "automatic_relations": [_relation_dict(item) for item in self.automatic_relations],
            "reviewed_relations": [_relation_dict(item) for item in self.reviewed_relations],
            "reviews": [item.to_dict() for item in self.reviews],
            "scenario_counts": self.scenario_counts,
        }


@dataclass(frozen=True, slots=True)
class GroupingGold:
    dataset_version: str
    event_by_record: dict[str, str]
    scenario_by_event: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "dataset_version": self.dataset_version,
            "event_by_record": self.event_by_record,
            "scenario_by_event": self.scenario_by_event,
        }


@dataclass(frozen=True, slots=True)
class GroupingDataset:
    inputs: GroupingInputs
    gold: GroupingGold


def build_grouping_dataset(*, split: Split, event_count: int, seed: int) -> GroupingDataset:
    if split not in {"calibration", "evaluation"}:
        raise ValueError("split must be calibration or evaluation")
    if event_count < 13:
        raise ValueError("event_count must be at least 13")
    year = 2025 if split == "calibration" else 2026
    records: list[SignalRecord] = []
    relations: list[SignalRelationInput] = []
    event_by_record: dict[str, str] = {}
    scenario_by_event: dict[str, str] = {}
    members_by_event: list[list[UUID]] = []

    for event_index in range(event_count):
        event_id = f"{split}-event-{event_index:03d}"
        scenario = _SCENARIOS[event_index % len(_SCENARIOS)]
        scenario_by_event[event_id] = scenario
        member_count = 4 + event_index % 2
        member_ids: list[UUID] = []
        for member_index in range(member_count):
            record_id = _identifier(split, seed, event_index, member_index, "record")
            member_ids.append(record_id)
            event_by_record[str(record_id)] = event_id
            records.append(
                SignalRecord(
                    record_id=record_id,
                    technical_sheet=_sheet(year, event_index, member_index, scenario),
                )
            )
            if member_index:
                kind = (
                    RelationKind.DUPLICATE
                    if member_index == 1
                    else RelationKind.CORROBORATES
                    if member_index % 2 == 0
                    else RelationKind.UPDATES
                )
                relations.append(
                    SignalRelationInput(
                        assessment_id=_identifier(
                            split, seed, event_index, member_index, "relation"
                        ),
                        left_id=member_ids[member_index - 1],
                        right_id=record_id,
                        relation=kind,
                        updating_record_id=(
                            record_id if kind is RelationKind.UPDATES else None
                        ),
                    )
                )
        members_by_event.append(member_ids)

    erroneous = SignalRelationInput(
        assessment_id=_identifier(split, seed, 0, 12, "erroneous-bridge"),
        left_id=members_by_event[0][0],
        right_id=members_by_event[12][0],
        relation=RelationKind.CORROBORATES,
    )
    weak_bridge = SignalRelationInput(
        assessment_id=_identifier(split, seed, 1, 7, "weak-bridge"),
        left_id=members_by_event[1][0],
        right_id=members_by_event[7][0],
        relation=RelationKind.RELATED_CONTEXT,
    )
    conflicting_bridge = SignalRelationInput(
        assessment_id=_identifier(split, seed, 2, 9, "conflicting-bridge"),
        left_id=members_by_event[2][0],
        right_id=members_by_event[9][0],
        relation=RelationKind.CORROBORATES,
    )
    automatic_relations = tuple(relations + [erroneous, weak_bridge, conflicting_bridge])
    reviewed_relations = tuple(relations + [weak_bridge, conflicting_bridge])
    inputs = GroupingInputs(
        dataset_version=f"grouping-{split}-v1",
        split=split,
        seed=seed,
        records=tuple(records),
        automatic_relations=automatic_relations,
        reviewed_relations=reviewed_relations,
        reviews=(SyntheticReview(erroneous.assessment_id, "reject", "different_event"),),
        scenario_counts=dict(sorted(Counter(scenario_by_event.values()).items())),
    )
    gold = GroupingGold(
        dataset_version=f"grouping-{split}-v1-gold",
        event_by_record=event_by_record,
        scenario_by_event=scenario_by_event,
    )
    return GroupingDataset(inputs, gold)


def _sheet(year: int, event_index: int, member_index: int, scenario: str) -> dict:
    condition = _CONDITIONS[event_index % len(_CONDITIONS)]
    municipality = _MUNICIPALITIES[event_index % len(_MUNICIPALITIES)]
    start = date(year, 1, 1) + timedelta(days=event_index)
    return {
        "disease_or_condition": None if scenario == "missing_condition" else condition,
        "syndrome": "síndrome febril" if scenario == "missing_condition" else None,
        "symptoms": ["febre", f"sintoma-{event_index % 4}"],
        "estimated_cases": (event_index + 1) * (member_index + 1),
        "estimated_deaths": None,
        "temporal": {
            "start": None if scenario == "partial_date" and member_index else start.isoformat(),
            "end": None,
            "precision": "unknown" if scenario == "partial_date" else "day",
        },
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": (
                None if scenario == "missing_location" and member_index else municipality
            ),
            "district": f"bairro-{event_index % 8}",
            "specific": None,
            "precision": "district",
        },
        "record_nature": "media" if member_index % 2 == 0 else "community",
    }


def _identifier(split: str, seed: int, left: int, right: int, role: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"vbe-hub:{split}:{seed}:{left}:{right}:{role}")


def _relation_dict(item: SignalRelationInput) -> dict:
    return {
        "assessment_id": str(item.assessment_id),
        "left_id": str(item.left_id),
        "right_id": str(item.right_id),
        "relation": item.relation.value if item.relation else None,
        "updating_record_id": (
            str(item.updating_record_id) if item.updating_record_id else None
        ),
        "succeeded": item.succeeded,
    }
