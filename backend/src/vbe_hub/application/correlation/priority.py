from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from vbe_hub.application.ai import RelationKind
from vbe_hub.application.correlation.signals import ConsolidatedSignal
from vbe_hub.domain.records import SourceKind

_PRIORITY_NAMESPACE = UUID("b21e4602-a48c-427d-b0b3-5882925b0c9a")


class TriageBand(StrEnum):
    ROUTINE = "routine"
    ATTENTION = "attention"
    PROMPT = "prompt"


@dataclass(frozen=True, slots=True)
class PriorityWeights:
    corroboration: float = 0.20
    recency: float = 0.15
    geography: float = 0.10
    magnitude: float = 0.15
    severity: float = 0.20
    completeness: float = 0.10
    consistency: float = 0.10

    def __post_init__(self) -> None:
        values = asdict(self).values()
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("priority weights must be between zero and one")
        if abs(sum(values) - 1) > 1e-9:
            raise ValueError("priority weights must sum to one")


@dataclass(frozen=True, slots=True)
class PriorityPolicy:
    version: str
    weights: PriorityWeights
    attention_threshold: int = 35
    prompt_threshold: int = 65
    recent_days: int = 2
    current_days: int = 7
    relevant_days: int = 14
    stale_days: int = 30
    severe_symptoms: tuple[str, ...] = (
        "alteração da consciência",
        "convulsão",
        "dificuldade para respirar",
        "sangramento",
    )

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("priority policy version must not be empty")
        if not 0 <= self.attention_threshold < self.prompt_threshold <= 100:
            raise ValueError("priority thresholds must be ordered between zero and 100")
        days = (self.recent_days, self.current_days, self.relevant_days, self.stale_days)
        if tuple(sorted(days)) != days or self.recent_days < 0:
            raise ValueError("recency day boundaries must be non-negative and ordered")

    @classmethod
    def v1(
        cls,
        *,
        version: str = "priority-v1",
        weights: PriorityWeights | None = None,
        attention_threshold: int = 35,
        prompt_threshold: int = 65,
    ) -> PriorityPolicy:
        return cls(
            version=version,
            weights=weights or PriorityWeights(),
            attention_threshold=attention_threshold,
            prompt_threshold=prompt_threshold,
        )

    @property
    def configuration(self) -> Mapping[str, Any]:
        return {
            "version": self.version,
            "weights": asdict(self.weights),
            "thresholds": {
                "attention": self.attention_threshold,
                "prompt": self.prompt_threshold,
            },
            "recency_days": [
                self.recent_days,
                self.current_days,
                self.relevant_days,
                self.stale_days,
            ],
            "severe_symptoms": list(self.severe_symptoms),
        }

    @property
    def configuration_hash(self) -> str:
        return _sha256(self.configuration)


@dataclass(frozen=True, slots=True)
class PriorityRecord:
    record_id: UUID
    source_kind: SourceKind
    source_name: str
    technical_sheet: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PriorityRelation:
    assessment_id: UUID
    relation: RelationKind
    record_ids: tuple[UUID, UUID]


@dataclass(frozen=True, slots=True)
class PriorityComponent:
    value: float | None
    weight: float
    contribution: float | None
    explanation: str
    facts: Mapping[str, Any]
    origin_ids: tuple[UUID, ...]
    relation_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class SuggestedPriority:
    id: UUID
    identity_key: str
    policy_version: str
    configuration_hash: str
    configuration: Mapping[str, Any]
    signal_id: UUID
    signal_identity_key: str
    signal_policy_version: str
    evaluated_at: datetime
    score: int
    band: TriageBand
    confidence: int
    components: Mapping[str, PriorityComponent]
    gaps: tuple[str, ...]


class PriorityCalculator:
    def __init__(self, policy: PriorityPolicy) -> None:
        self._policy = policy

    def calculate(
        self,
        *,
        signal: ConsolidatedSignal,
        records: Sequence[PriorityRecord],
        relations: Sequence[PriorityRelation],
        evaluated_at: datetime,
    ) -> SuggestedPriority:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must include timezone information")
        records_by_id = {item.record_id: item for item in records}
        missing = set(signal.core_record_ids) - records_by_id.keys()
        if missing:
            raise ValueError("all core signal records are required for priority calculation")
        core_records = tuple(records_by_id[item] for item in signal.core_record_ids)
        components = {
            "corroboration": self._corroboration(core_records, relations),
            "recency": self._recency(signal, evaluated_at.date()),
            "geography": self._geography(core_records),
            "magnitude": self._magnitude(signal),
            "severity": self._severity(signal),
            "completeness": self._completeness(signal, core_records),
            "consistency": self._consistency(signal),
        }
        known_weight = sum(item.weight for item in components.values() if item.value is not None)
        weighted_value = sum(
            item.contribution or 0 for item in components.values() if item.value is not None
        )
        score = round(100 * weighted_value / known_weight) if known_weight else 0
        completeness = components["completeness"].value or 0
        consistency = components["consistency"].value or 0
        confidence = round(100 * (0.7 * completeness + 0.3 * consistency))
        gaps = tuple(sorted(self._gaps(components)))
        identity_payload = {
            "signal_id": str(signal.id),
            "signal_identity_key": signal.identity_key,
            "signal_policy_version": signal.policy_version,
            "priority_policy_version": self._policy.version,
            "configuration_hash": self._policy.configuration_hash,
            "evaluated_at": evaluated_at.astimezone(UTC).isoformat(),
        }
        identity_key = _sha256(identity_payload)
        return SuggestedPriority(
            id=uuid5(_PRIORITY_NAMESPACE, identity_key),
            identity_key=identity_key,
            policy_version=self._policy.version,
            configuration_hash=self._policy.configuration_hash,
            configuration=self._policy.configuration,
            signal_id=signal.id,
            signal_identity_key=signal.identity_key,
            signal_policy_version=signal.policy_version,
            evaluated_at=evaluated_at.astimezone(UTC),
            score=score,
            band=self._band(score),
            confidence=confidence,
            components=components,
            gaps=gaps,
        )

    def _corroboration(
        self,
        records: Sequence[PriorityRecord],
        relations: Sequence[PriorityRelation],
    ) -> PriorityComponent:
        sources: dict[tuple[str, str], list[UUID]] = {}
        for item in records:
            key = (item.source_kind.value, item.source_name.strip().casefold())
            sources.setdefault(key, []).append(item.record_id)
        source_count = len(sources)
        value = 0.0 if source_count <= 1 else 0.7 if source_count == 2 else 1.0
        relevant = tuple(
            sorted(
                (
                    item
                    for item in relations
                    if item.relation in {RelationKind.CORROBORATES, RelationKind.UPDATES}
                ),
                key=lambda item: str(item.assessment_id),
            )
        )
        if any(item.relation is RelationKind.UPDATES for item in relevant):
            value = min(1.0, value + 0.1)
        origins = tuple(sorted((item.record_id for item in records), key=str))
        relation_ids = tuple(item.assessment_id for item in relevant)
        return self._component(
            "corroboration",
            value,
            "Diversidade de fontes centrais, sem multiplicar registros do mesmo emissor.",
            {
                "independent_sources": source_count,
                "corroborations": sum(
                    item.relation is RelationKind.CORROBORATES for item in relevant
                ),
                "updates": sum(item.relation is RelationKind.UPDATES for item in relevant),
            },
            origins,
            relation_ids,
        )

    def _recency(self, signal: ConsolidatedSignal, evaluated_on: date) -> PriorityComponent:
        if signal.period_end is None:
            return self._component(
                "recency", None, "Período não informado.", {"age_days": None}, ()
            )
        age_days = max(0, (evaluated_on - signal.period_end).days)
        if age_days <= self._policy.recent_days:
            age_value = 1.0
        elif age_days <= self._policy.current_days:
            age_value = 0.75
        elif age_days <= self._policy.relevant_days:
            age_value = 0.5
        elif age_days <= self._policy.stale_days:
            age_value = 0.25
        else:
            age_value = 0.0
        span_days = (
            max(0, (signal.period_end - signal.period_start).days)
            if signal.period_start is not None
            else None
        )
        concentration = (
            1.0
            if span_days is None or span_days <= 2
            else 0.75
            if span_days <= 7
            else 0.5
            if span_days <= 14
            else 0.25
        )
        value = age_value * concentration
        origins = _origins_for(signal, "temporal.start", "temporal.end")
        return self._component(
            "recency",
            value,
            "Recência da última data observada combinada à concentração temporal.",
            {"age_days": age_days, "span_days": span_days},
            origins,
        )

    def _geography(self, records: Sequence[PriorityRecord]) -> PriorityComponent:
        scale = {"country": 0.25, "state": 0.5, "municipality": 0.75, "district": 1.0}
        observed = [
            (item.record_id, _nested_text(item.technical_sheet, "location", "precision"))
            for item in records
        ]
        known = [(record_id, value) for record_id, value in observed if value in scale]
        if not known:
            return self._component(
                "geography", None, "Precisão geográfica não informada.", {"precision": None}, ()
            )
        best = max((precision for _, precision in known), key=lambda item: scale[item])
        origins = tuple(
            sorted(
                (record_id for record_id, precision in known if precision == best),
                key=str,
            )
        )
        return self._component(
            "geography",
            scale[best],
            "Maior precisão geográfica explicitamente informada pelas fichas centrais.",
            {"precision": best},
            origins,
        )

    def _magnitude(self, signal: ConsolidatedSignal) -> PriorityComponent:
        cases = signal.current_estimated_cases
        origins = _origins_for(signal, "estimated_cases")
        if cases is None:
            return self._component(
                "magnitude",
                None,
                "Magnitude não informada; o valor não foi convertido em zero.",
                {"estimated_cases": None},
                origins,
            )
        if cases == 0:
            value = 0.0
        elif cases < 5:
            value = 0.2
        elif cases < 20:
            value = 0.5
        elif cases < 50:
            value = 0.75
        else:
            value = 1.0
        return self._component(
            "magnitude",
            value,
            "Magnitude reportada, sem extrapolação além das origens.",
            {"estimated_cases": cases},
            origins,
        )

    def _severity(self, signal: ConsolidatedSignal) -> PriorityComponent:
        death_observations = [
            item for item in signal.magnitude_history if item.estimated_deaths is not None
        ]
        reported_deaths = (
            max(item.estimated_deaths or 0 for item in death_observations)
            if death_observations
            else None
        )
        configured = {item.casefold() for item in self._policy.severe_symptoms}
        severe = sorted(item for item in signal.symptoms if item.casefold() in configured)
        if reported_deaths is not None and reported_deaths > 0:
            value: float | None = 1.0
        elif severe:
            value = 0.6
        elif reported_deaths is not None:
            value = 0.0
        else:
            value = None
        origins = tuple(
            sorted(
                {
                    item.record_id
                    for item in death_observations
                }
                | set(_origins_for(signal, "symptoms")),
                key=str,
            )
        )
        return self._component(
            "severity",
            value,
            (
                "Gravidade baseada somente em óbitos ou sinais graves explicitamente relatados."
                if value is not None
                else (
                    "Gravidade não informada; ausência de campo não significa ausência "
                    "de gravidade."
                )
            ),
            {"reported_deaths": reported_deaths, "severe_symptoms": severe},
            origins,
        )

    def _completeness(
        self, signal: ConsolidatedSignal, records: Sequence[PriorityRecord]
    ) -> PriorityComponent:
        known = {
            "condition": bool(signal.conditions),
            "symptoms": bool(signal.symptoms),
            "temporal": signal.period_start is not None or signal.period_end is not None,
            "geography": any(
                _nested_text(item.technical_sheet, "location", "precision") for item in records
            ),
            "magnitude": signal.current_estimated_cases is not None,
            "severity": any(
                item.estimated_deaths is not None for item in signal.magnitude_history
            ),
        }
        value = sum(known.values()) / len(known)
        return self._component(
            "completeness",
            value,
            "Proporção de grupos informativos explicitamente disponíveis.",
            {
                "known_fields": sorted(key for key, present in known.items() if present),
                "missing_fields": sorted(key for key, present in known.items() if not present),
            },
            tuple(sorted(signal.core_record_ids, key=str)),
        )

    def _consistency(self, signal: ConsolidatedSignal) -> PriorityComponent:
        divergences = sorted(signal.divergence_codes)
        value = max(0.0, 1 - 0.2 * len(divergences))
        return self._component(
            "consistency",
            value,
            "Concordância reduzida por divergências explícitas entre as origens.",
            {"divergences": divergences},
            tuple(sorted(signal.core_record_ids, key=str)),
        )

    def _component(
        self,
        name: str,
        value: float | None,
        explanation: str,
        facts: Mapping[str, Any],
        origins: tuple[UUID, ...],
        relation_ids: tuple[UUID, ...] = (),
    ) -> PriorityComponent:
        weight = getattr(self._policy.weights, name)
        return PriorityComponent(
            value=value,
            weight=weight,
            contribution=None if value is None else value * weight,
            explanation=explanation,
            facts=facts,
            origin_ids=origins,
            relation_ids=relation_ids,
        )

    @staticmethod
    def _gaps(components: Mapping[str, PriorityComponent]) -> set[str]:
        names = {
            "recency": "temporal_unknown",
            "geography": "geography_unknown",
            "magnitude": "magnitude_unknown",
            "severity": "severity_unknown",
        }
        return {gap for name, gap in names.items() if components[name].value is None}

    def _band(self, score: int) -> TriageBand:
        if score >= self._policy.prompt_threshold:
            return TriageBand.PROMPT
        if score >= self._policy.attention_threshold:
            return TriageBand.ATTENTION
        return TriageBand.ROUTINE


def _origins_for(signal: ConsolidatedSignal, *fields: str) -> tuple[UUID, ...]:
    return tuple(
        sorted(
            {
                record_id
                for field in fields
                for value in signal.field_provenance.get(field, ())
                for record_id in value.record_ids
            },
            key=str,
        )
    )


def _nested_text(value: Mapping[str, Any], parent: str, child: str) -> str | None:
    nested = value.get(parent)
    result = nested.get(child) if isinstance(nested, Mapping) else None
    return result.strip() if isinstance(result, str) and result.strip() else None


def _sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
