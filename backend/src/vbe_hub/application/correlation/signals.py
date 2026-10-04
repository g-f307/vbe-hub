from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid5

from vbe_hub.application.ai import RelationKind

_SIGNAL_NAMESPACE = UUID("8a69de67-bafd-4f8f-935e-15cb05b5709b")
_STRONG_RELATIONS = frozenset(
    {RelationKind.DUPLICATE, RelationKind.CORROBORATES, RelationKind.UPDATES}
)


@dataclass(frozen=True, slots=True)
class ConsolidationPolicy:
    version: str
    maximum_temporal_gap_days: int = 14

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("policy version must not be empty")
        if self.maximum_temporal_gap_days < 0:
            raise ValueError("maximum temporal gap must be non-negative")


@dataclass(frozen=True, slots=True)
class SignalRecord:
    record_id: UUID
    technical_sheet: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SignalRelationInput:
    assessment_id: UUID
    left_id: UUID
    right_id: UUID
    relation: RelationKind | None
    updating_record_id: UUID | None = None
    succeeded: bool = True


@dataclass(frozen=True, slots=True)
class FieldValue:
    value: Any
    record_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class MagnitudeObservation:
    record_id: UUID
    observed_at: date | None
    estimated_cases: int | None
    estimated_deaths: int | None


@dataclass(frozen=True, slots=True)
class ConsolidationConflict:
    relation_id: UUID
    left_id: UUID
    right_id: UUID
    code: str
    details: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ConsolidatedSignal:
    id: UUID
    identity_key: str
    policy_version: str
    processing_state: str
    title: str
    summary: str
    core_record_ids: tuple[UUID, ...]
    context_record_ids: tuple[UUID, ...]
    relation_ids: tuple[UUID, ...]
    relation_roles: Mapping[UUID, str]
    period_start: date | None
    period_end: date | None
    location: Mapping[str, Any]
    conditions: tuple[str, ...]
    symptoms: tuple[str, ...]
    magnitude_history: tuple[MagnitudeObservation, ...]
    current_estimated_cases: int | None
    field_provenance: Mapping[str, tuple[FieldValue, ...]]
    divergence_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsolidationResult:
    signals: tuple[ConsolidatedSignal, ...]
    conflicts: tuple[ConsolidationConflict, ...]


class _Components:
    def __init__(self, record_ids: Sequence[UUID]) -> None:
        self.parent = {record_id: record_id for record_id in record_ids}
        self.members = {record_id: {record_id} for record_id in record_ids}

    def root(self, record_id: UUID) -> UUID:
        parent = self.parent[record_id]
        if parent != record_id:
            self.parent[record_id] = self.root(parent)
        return self.parent[record_id]

    def group(self, record_id: UUID) -> set[UUID]:
        return self.members[self.root(record_id)]

    def union(self, left_id: UUID, right_id: UUID) -> UUID:
        left_root, right_root = self.root(left_id), self.root(right_id)
        if left_root == right_root:
            return left_root
        keep, remove = sorted((left_root, right_root), key=str)
        self.parent[remove] = keep
        self.members[keep].update(self.members.pop(remove))
        return keep


class SignalConsolidationService:
    def __init__(self, policy: ConsolidationPolicy) -> None:
        self._policy = policy

    def consolidate(
        self,
        *,
        records: Sequence[SignalRecord],
        relations: Sequence[SignalRelationInput],
    ) -> ConsolidationResult:
        records_by_id = {item.record_id: item for item in records}
        if len(records_by_id) != len(records):
            raise ValueError("record ids must be unique")
        components = _Components(tuple(records_by_id))
        accepted_strong: list[SignalRelationInput] = []
        conflicts: list[ConsolidationConflict] = []

        for item in sorted(relations, key=lambda relation: str(relation.assessment_id)):
            if not item.succeeded or item.relation not in _STRONG_RELATIONS:
                continue
            self._require_known_endpoints(item, records_by_id)
            codes = self._component_conflicts(
                components.group(item.left_id),
                components.group(item.right_id),
                records_by_id,
            )
            if codes:
                conflicts.append(
                    ConsolidationConflict(
                        relation_id=item.assessment_id,
                        left_id=item.left_id,
                        right_id=item.right_id,
                        code=codes[0],
                        details={"codes": list(codes)},
                    )
                )
                continue
            components.union(item.left_id, item.right_id)
            accepted_strong.append(item)

        groups = self._groups(components, records_by_id)
        context_by_root: dict[UUID, set[UUID]] = {root: set() for root in groups}
        relations_by_root: dict[UUID, dict[UUID, str]] = {root: {} for root in groups}
        absorbed_roots: set[UUID] = set()

        for item in accepted_strong:
            root = components.root(item.left_id)
            relations_by_root[root][item.assessment_id] = "supporting"

        for item in sorted(relations, key=lambda relation: str(relation.assessment_id)):
            if not item.succeeded or item.relation is not RelationKind.RELATED_CONTEXT:
                continue
            self._require_known_endpoints(item, records_by_id)
            left_root, right_root = components.root(item.left_id), components.root(item.right_id)
            if left_root == right_root:
                relations_by_root[left_root][item.assessment_id] = "context"
                continue
            left_size, right_size = len(groups[left_root]), len(groups[right_root])
            if left_size > 1 and right_size == 1:
                context_by_root[left_root].update(groups[right_root])
                relations_by_root[left_root][item.assessment_id] = "context"
                absorbed_roots.add(right_root)
            elif right_size > 1 and left_size == 1:
                context_by_root[right_root].update(groups[left_root])
                relations_by_root[right_root][item.assessment_id] = "context"
                absorbed_roots.add(left_root)
            else:
                conflicts.append(
                    ConsolidationConflict(
                        relation_id=item.assessment_id,
                        left_id=item.left_id,
                        right_id=item.right_id,
                        code="weak_bridge_blocked",
                        details={
                            "left_component_size": left_size,
                            "right_component_size": right_size,
                        },
                    )
                )

        updating_ids = {
            item.updating_record_id
            for item in accepted_strong
            if item.relation is RelationKind.UPDATES and item.updating_record_id is not None
        }
        signals = [
            self._build_signal(
                core_ids=groups[root],
                context_ids=context_by_root[root],
                relation_roles=relations_by_root[root],
                records_by_id=records_by_id,
                updating_ids=updating_ids,
            )
            for root in sorted(groups, key=str)
            if root not in absorbed_roots
        ]
        signals.sort(key=lambda signal: tuple(str(item) for item in signal.core_record_ids))
        conflicts.sort(key=lambda item: (str(item.relation_id), item.code))
        return ConsolidationResult(tuple(signals), tuple(conflicts))

    @staticmethod
    def _require_known_endpoints(
        relation: SignalRelationInput, records_by_id: Mapping[UUID, SignalRecord]
    ) -> None:
        if relation.left_id not in records_by_id or relation.right_id not in records_by_id:
            raise ValueError("relation endpoint is absent from records")

    @staticmethod
    def _groups(
        components: _Components, records_by_id: Mapping[UUID, SignalRecord]
    ) -> dict[UUID, set[UUID]]:
        groups: dict[UUID, set[UUID]] = {}
        for record_id in records_by_id:
            groups.setdefault(components.root(record_id), set()).add(record_id)
        return groups

    def _component_conflicts(
        self,
        left_ids: set[UUID],
        right_ids: set[UUID],
        records_by_id: Mapping[UUID, SignalRecord],
    ) -> tuple[str, ...]:
        codes = {
            code
            for left_id in left_ids
            for right_id in right_ids
            for code in self._record_conflicts(
                records_by_id[left_id].technical_sheet,
                records_by_id[right_id].technical_sheet,
            )
        }
        return tuple(sorted(codes))

    def _record_conflicts(
        self, left: Mapping[str, Any], right: Mapping[str, Any]
    ) -> tuple[str, ...]:
        codes: list[str] = []
        left_municipality = _nested_text(left, "location", "municipality")
        right_municipality = _nested_text(right, "location", "municipality")
        if (
            left_municipality
            and right_municipality
            and left_municipality.casefold() != right_municipality.casefold()
        ):
            codes.append("geographic_conflict")

        left_condition = _text(left.get("disease_or_condition"))
        right_condition = _text(right.get("disease_or_condition"))
        if (
            left_condition
            and right_condition
            and left_condition.casefold() != right_condition.casefold()
        ):
            codes.append("clinical_conflict")

        left_date = _date_value(_nested_value(left, "temporal", "start"))
        right_date = _date_value(_nested_value(right, "temporal", "start"))
        if (
            left_date
            and right_date
            and abs((left_date - right_date).days) > self._policy.maximum_temporal_gap_days
        ):
            codes.append("temporal_conflict")
        return tuple(codes)

    def _build_signal(
        self,
        *,
        core_ids: set[UUID],
        context_ids: set[UUID],
        relation_roles: Mapping[UUID, str],
        records_by_id: Mapping[UUID, SignalRecord],
        updating_ids: set[UUID],
    ) -> ConsolidatedSignal:
        core = tuple(sorted(core_ids, key=str))
        context = tuple(sorted(context_ids, key=str))
        relation_tuple = tuple(sorted(relation_roles, key=str))
        identity_payload = json.dumps(
            {
                "policy": self._policy.version,
                "core": [str(item) for item in core],
                "context": [str(item) for item in context],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        identity_key = hashlib.sha256(identity_payload.encode()).hexdigest()
        signal_id = uuid5(_SIGNAL_NAMESPACE, identity_key)
        sheets = [(record_id, records_by_id[record_id].technical_sheet) for record_id in core]
        provenance = _field_provenance(sheets)
        starts = [
            value
            for _, sheet in sheets
            if (value := _date_value(_nested_value(sheet, "temporal", "start"))) is not None
        ]
        ends = [
            value
            for _, sheet in sheets
            if (
                value := _date_value(_nested_value(sheet, "temporal", "end"))
                or _date_value(_nested_value(sheet, "temporal", "start"))
            )
            is not None
        ]
        magnitude = tuple(
            sorted(
                (
                    MagnitudeObservation(
                        record_id=record_id,
                        observed_at=_date_value(_nested_value(sheet, "temporal", "start")),
                        estimated_cases=_integer(sheet.get("estimated_cases")),
                        estimated_deaths=_integer(sheet.get("estimated_deaths")),
                    )
                    for record_id, sheet in sheets
                    if sheet.get("estimated_cases") is not None
                    or sheet.get("estimated_deaths") is not None
                ),
                key=lambda item: (item.observed_at or date.min, str(item.record_id)),
            )
        )
        current_cases = _current_cases(magnitude, updating_ids)
        conditions = _unique_text(
            value
            for _, sheet in sheets
            for value in (sheet.get("disease_or_condition"), sheet.get("syndrome"))
        )
        symptoms = _unique_text(
            symptom for _, sheet in sheets for symptom in sheet.get("symptoms", [])
        )
        municipality = _first_value(provenance.get("location.municipality", ()))
        title_subject = _first_value(provenance.get("disease_or_condition", ())) or (
            conditions[0] if conditions else "evento de saúde"
        )
        location_label = municipality or "local não informado"
        divergence_codes = []
        distinct_cases = {
            item.estimated_cases for item in magnitude if item.estimated_cases is not None
        }
        if len(distinct_cases) > 1:
            divergence_codes.append("magnitude_values_differ")
        return ConsolidatedSignal(
            id=signal_id,
            identity_key=identity_key,
            policy_version=self._policy.version,
            processing_state="suggested",
            title=f"Sinal sugerido: {title_subject} em {location_label}",
            summary=(
                f"Sugestão automática baseada em {len(core)} origem(ns); "
                "requer revisão da vigilância."
            ),
            core_record_ids=core,
            context_record_ids=context,
            relation_ids=relation_tuple,
            relation_roles={item: relation_roles[item] for item in relation_tuple},
            period_start=min(starts) if starts else None,
            period_end=max(ends) if ends else None,
            location={
                "country": _first_value(provenance.get("location.country", ())),
                "state": _first_value(provenance.get("location.state", ())),
                "municipality": municipality,
                "district": _first_value(provenance.get("location.district", ())),
            },
            conditions=conditions,
            symptoms=symptoms,
            magnitude_history=magnitude,
            current_estimated_cases=current_cases,
            field_provenance=provenance,
            divergence_codes=tuple(divergence_codes),
        )


def _field_provenance(
    sheets: Sequence[tuple[UUID, Mapping[str, Any]]],
) -> dict[str, tuple[FieldValue, ...]]:
    fields: dict[str, list[tuple[Any, UUID]]] = {}
    for record_id, sheet in sheets:
        values = {
            "disease_or_condition": sheet.get("disease_or_condition"),
            "syndrome": sheet.get("syndrome"),
            "symptoms": sheet.get("symptoms"),
            "estimated_cases": sheet.get("estimated_cases"),
            "estimated_deaths": sheet.get("estimated_deaths"),
            "temporal.start": _nested_value(sheet, "temporal", "start"),
            "temporal.end": _nested_value(sheet, "temporal", "end"),
            "location.country": _nested_value(sheet, "location", "country"),
            "location.state": _nested_value(sheet, "location", "state"),
            "location.municipality": _nested_value(sheet, "location", "municipality"),
            "location.district": _nested_value(sheet, "location", "district"),
        }
        for field_name, value in values.items():
            if value is not None and value != []:
                fields.setdefault(field_name, []).append((value, record_id))

    result: dict[str, tuple[FieldValue, ...]] = {}
    for field_name, entries in fields.items():
        grouped: dict[str, tuple[Any, list[UUID]]] = {}
        for value, record_id in entries:
            key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            grouped.setdefault(key, (value, []))[1].append(record_id)
        result[field_name] = tuple(
            FieldValue(value=value, record_ids=tuple(sorted(record_ids, key=str)))
            for value, record_ids in (grouped[key] for key in sorted(grouped))
        )
    return result


def _current_cases(
    observations: Sequence[MagnitudeObservation], updating_ids: set[UUID]
) -> int | None:
    updates = [
        item
        for item in observations
        if item.record_id in updating_ids and item.estimated_cases is not None
    ]
    candidates = updates or [item for item in observations if item.estimated_cases is not None]
    return candidates[-1].estimated_cases if candidates else None


def _nested_value(sheet: Mapping[str, Any], parent: str, child: str) -> Any:
    value = sheet.get(parent)
    return value.get(child) if isinstance(value, Mapping) else None


def _nested_text(sheet: Mapping[str, Any], parent: str, child: str) -> str | None:
    return _text(_nested_value(sheet, parent, child))


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _date_value(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _unique_text(values) -> tuple[str, ...]:
    unique = {_text(value) for value in values}
    return tuple(sorted((value for value in unique if value), key=str.casefold))


def _first_value(values: Sequence[FieldValue]) -> Any:
    return values[0].value if values else None
