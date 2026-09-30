from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

RELATIONS = ("duplicate", "corroborates", "updates", "related_context", "unrelated")

_CONDITIONS = (
    ("Sarampo", "síndrome febril exantemática", ("febre", "manchas vermelhas")),
    ("Dengue", "síndrome febril", ("febre", "dor no corpo")),
    ("Influenza", "síndrome gripal", ("febre", "tosse")),
    ("Febre amarela", "síndrome febril ictérica", ("febre", "icterícia")),
    ("Coqueluche", "síndrome respiratória", ("tosse persistente", "vômito")),
)
_MUNICIPALITIES = ("Manaus", "Parintins", "Itacoatiara", "Manacapuru", "Tefé")


@dataclass(frozen=True, slots=True)
class RelationPairInput:
    left_id: UUID
    right_id: UUID
    semantic_score: float
    left: dict[str, Any]
    right: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_id": str(self.left_id),
            "right_id": str(self.right_id),
            "semantic_score": self.semantic_score,
            "left": self.left,
            "right": self.right,
        }


@dataclass(frozen=True, slots=True)
class RelationGold:
    left_id: UUID
    right_id: UUID
    relation: str


@dataclass(frozen=True, slots=True)
class RelationDataset:
    split: str
    seed: int
    inputs: tuple[RelationPairInput, ...]
    gold: tuple[RelationGold, ...]

    @property
    def relation_counts(self) -> dict[str, int]:
        return dict(Counter(item.relation for item in self.gold))


def build_relation_dataset(
    *, split: Literal["calibration", "evaluation"], cases_per_relation: int, seed: int
) -> RelationDataset:
    if cases_per_relation <= 0:
        raise ValueError("cases_per_relation must be positive")
    inputs: list[RelationPairInput] = []
    gold: list[RelationGold] = []
    for relation in RELATIONS:
        for index in range(cases_per_relation):
            left_id = _identifier(split, seed, relation, index, "left")
            right_id = _identifier(split, seed, relation, index, "right")
            left, right = _target_sheets(relation, index)
            inputs.append(
                RelationPairInput(left_id, right_id, _target_score(relation), left, right)
            )
            gold.append(RelationGold(left_id, right_id, relation))
            for decoy in range(4):
                decoy_id = _identifier(split, seed, relation, index, f"decoy-{decoy}")
                inputs.append(
                    RelationPairInput(
                        left_id,
                        decoy_id,
                        0.95,
                        left,
                        _decoy_sheet(left, index, decoy),
                    )
                )
    return RelationDataset(split, seed, tuple(inputs), tuple(gold))


def _identifier(split: str, seed: int, relation: str, index: int, side: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"vbe-hub:{split}:{seed}:{relation}:{index}:{side}")


def _target_sheets(relation: str, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    condition, syndrome, symptoms = _CONDITIONS[index % len(_CONDITIONS)]
    municipality = _MUNICIPALITIES[index % len(_MUNICIPALITIES)]
    start = date(2026, 1, 1) + timedelta(days=index * 2)
    left = _sheet(
        nature="media",
        condition=condition,
        syndrome=syndrome,
        symptoms=symptoms,
        cases=3 + index % 12,
        start=start,
        municipality=municipality,
    )
    if relation == "duplicate":
        return left, dict(left)
    if relation == "corroborates":
        return left, _sheet(
            nature="community",
            condition=None if index % 2 == 0 else condition,
            syndrome=syndrome,
            symptoms=symptoms,
            cases=4 + index % 12,
            start=start,
            municipality=municipality,
        )
    if relation == "updates":
        return left, _sheet(
            nature="media",
            condition=condition,
            syndrome=syndrome,
            symptoms=symptoms,
            cases=12 + index % 15,
            start=start + timedelta(days=1),
            municipality=municipality,
        )
    if relation == "related_context":
        context = _sheet(
            nature="media",
            condition=condition,
            syndrome=None,
            symptoms=(),
            cases=None,
            start=start,
            municipality=municipality,
        )
        context["ongoing_action"] = "campanha preventiva de vacinação e orientação"
        context["is_relevant_signal"] = False
        return left, context
    other, other_syndrome, other_symptoms = _CONDITIONS[(index + 1) % len(_CONDITIONS)]
    return left, _sheet(
        nature="community",
        condition=other,
        syndrome=other_syndrome,
        symptoms=other_symptoms,
        cases=3 + index % 12,
        start=start,
        municipality=municipality,
    )


def _sheet(
    *,
    nature: str,
    condition: str | None,
    syndrome: str | None,
    symptoms: tuple[str, ...],
    cases: int | None,
    start: date,
    municipality: str,
) -> dict[str, Any]:
    return {
        "record_nature": nature,
        "disease_or_condition": condition,
        "syndrome": syndrome,
        "symptoms": list(symptoms),
        "estimated_cases": cases,
        "temporal": {"start": start.isoformat(), "end": start.isoformat()},
        "location": {"country": "Brasil", "state": "Amazonas", "municipality": municipality},
        "environment": "comunidade",
        "ongoing_action": None,
        "is_relevant_signal": True,
    }


def _decoy_sheet(left: dict[str, Any], index: int, decoy: int) -> dict[str, Any]:
    value = {**left, "location": dict(left["location"]), "temporal": dict(left["temporal"])}
    value["location"]["municipality"] = f"Município incompatível {index}-{decoy}"
    return value


def _target_score(relation: str) -> float:
    return 0.85 if relation == "unrelated" else 0.9
