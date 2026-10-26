"""Deterministic canonical scenario used to demonstrate the local panel."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.priority_repository import SqlAlchemyPriorityRepository
from vbe_hub.adapters.persistence.relation_repository import (
    SqlAlchemyRelationAssessmentRepository,
)
from vbe_hub.adapters.persistence.repositories import (
    SqlAlchemyExtractionRepository,
    SqlAlchemyRawRecordRepository,
)
from vbe_hub.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from vbe_hub.adapters.persistence.workflow_repository import SqlAlchemyWorkflowRepository
from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    FieldEvidence,
    RelationKind,
)
from vbe_hub.application.ai.extraction import ExtractionRecord
from vbe_hub.application.correlation.priority import (
    PriorityCalculator,
    PriorityPolicy,
    PriorityRecord,
    PriorityRelation,
)
from vbe_hub.application.correlation.relations import (
    RelationAssessmentRecord,
    RelationMethod,
)
from vbe_hub.application.correlation.signals import (
    ConsolidationPolicy,
    SignalConsolidationService,
    SignalRecord,
    SignalRelationInput,
)
from vbe_hub.application.workflow import (
    TransitionCommand,
    WorkflowService,
    WorkflowState,
)
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

_NAMESPACE = UUID("c64400c7-6a6e-4b94-b3d7-31abf4899965")
_NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
_NORMALIZER_VERSION = "demo-normalizer-v1"
_EXTRACTION_VERSION = "technical-sheet-v1"
_CONSOLIDATION_VERSION = "demo-signal-consolidation-v1"
_PRIORITY_VERSION = "demo-priority-v1"


@dataclass(frozen=True, slots=True)
class DemoLoadResult:
    """Counts created in one idempotent load and canonical signal identities."""

    created: Mapping[str, int]
    signal_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class _Scenario:
    key: str
    condition: str
    syndrome: str
    symptoms: tuple[str, ...]
    estimated_cases: int
    published_at: datetime
    location: Mapping[str, str | None]
    target_state: WorkflowState


_SCENARIOS = (
    _Scenario(
        key="dengue-compensa",
        condition="Dengue",
        syndrome="Síndrome febril aguda",
        symptoms=("febre", "dor no corpo", "sangramento"),
        estimated_cases=60,
        published_at=datetime(2026, 10, 10, 8, 0, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Compensa",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
    ),
    _Scenario(
        key="leptospirose-jorge-teixeira",
        condition="Leptospirose",
        syndrome="Síndrome febril aguda",
        symptoms=("febre", "dor muscular", "náusea"),
        estimated_cases=12,
        published_at=datetime(2026, 9, 22, 9, 0, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": None,
            "precision": "municipality",
        },
        target_state=WorkflowState.TRIAGE,
    ),
    _Scenario(
        key="sarampo-cidade-nova",
        condition="Sarampo ou síndrome compatível",
        syndrome="Síndrome febril exantemática",
        symptoms=("febre", "manchas vermelhas"),
        estimated_cases=0,
        published_at=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": None,
            "municipality": None,
            "district": None,
            "precision": "country",
        },
        target_state=WorkflowState.VERIFICATION,
    ),
)


async def load_demo_scenario(session: AsyncSession) -> DemoLoadResult:
    """Materialize the small offline scenario used by the manual panel demonstration.

    It intentionally uses the domain records and persistence adapters instead of SQL fixtures.
    Repeating the call preserves prior human actions and creates no duplicate entities.
    """

    created = {
        "raw_records": 0,
        "normalized_records": 0,
        "technical_sheets": 0,
        "relations": 0,
        "signals": 0,
        "priorities": 0,
        "workflow_events": 0,
    }
    raw_repository = SqlAlchemyRawRecordRepository(session)
    extraction_repository = SqlAlchemyExtractionRepository(session)
    relation_repository = SqlAlchemyRelationAssessmentRepository(session)
    signal_repository = SqlAlchemySignalRepository(session)
    priority_repository = SqlAlchemyPriorityRepository(session)
    workflow_service = WorkflowService(SqlAlchemyWorkflowRepository(session), now=lambda: _NOW)
    signal_ids: list[UUID] = []

    for scenario in _SCENARIOS:
        records = await _store_records(
            scenario,
            raw_repository=raw_repository,
            extraction_repository=extraction_repository,
            created=created,
        )
        relation = await _store_relation(
            scenario,
            records[0].id,
            records[1].id,
            relation_repository=relation_repository,
            created=created,
        )
        result = SignalConsolidationService(
            ConsolidationPolicy(version=_CONSOLIDATION_VERSION)
        ).consolidate(
            records=[SignalRecord(record.id, _sheet(scenario)) for record in records],
            relations=[
                SignalRelationInput(
                    relation.id,
                    records[0].id,
                    records[1].id,
                    relation.relation,
                )
            ],
        )
        signal = result.signals[0]
        if await signal_repository.get(signal.id) is None:
            created["signals"] += 1
        await signal_repository.save(result)

        priority = PriorityCalculator(
            PriorityPolicy.v1(
                version=_PRIORITY_VERSION,
                attention_threshold=50,
                prompt_threshold=80,
            )
        ).calculate(
            signal=signal,
            records=[
                PriorityRecord(
                    record_id=record.id,
                    source_kind=source_kind,
                    source_name=source_name,
                    technical_sheet=_sheet(scenario),
                )
                for record, source_kind, source_name in zip(
                    records,
                    (SourceKind.MEDIA, SourceKind.COMMUNITY),
                    ("demo-news", "demo-community"),
                    strict=True,
                )
            ],
            relations=[
                PriorityRelation(
                    assessment_id=relation.id,
                    relation=RelationKind.CORROBORATES,
                    record_ids=(records[0].id, records[1].id),
                )
            ],
            evaluated_at=_NOW,
        )
        if await priority_repository.get(priority.id) is None:
            created["priorities"] += 1
        await priority_repository.save(priority)
        created["workflow_events"] += await _ensure_workflow(
            workflow_service, signal.id, scenario.key, scenario.target_state
        )
        signal_ids.append(signal.id)

    return DemoLoadResult(
        created=MappingProxyType(created),
        signal_ids=tuple(signal_ids),
    )


async def _store_records(
    scenario: _Scenario,
    *,
    raw_repository: SqlAlchemyRawRecordRepository,
    extraction_repository: SqlAlchemyExtractionRepository,
    created: dict[str, int],
) -> tuple[NormalizedRecord, NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for source_kind, source_name, title, body in _source_rows(scenario):
        raw_id = _id(f"raw:{scenario.key}:{source_kind.value}")
        raw = replace(
            RawRecord.create(
                source_kind=source_kind,
                source_name=source_name,
                external_id=f"demo:{scenario.key}:{source_kind.value}",
                published_at=scenario.published_at,
                title=title,
                body=body,
                source_url=None,
                language="pt-BR",
                original_payload={"synthetic": True, "demo_scenario": scenario.key},
            ),
            id=raw_id,
            created_at=scenario.published_at,
            updated_at=scenario.published_at,
        )
        ingestion = await raw_repository.add(
            raw,
            Provenance(
                adapter_name="demo-scenario",
                adapter_version="1.0.0",
                generator_name="vbe-hub-demo",
                generator_version="1.0.0",
                seed=54,
                scenario_id=scenario.key,
                collected_at=scenario.published_at,
            ),
        )
        if ingestion.created:
            created["raw_records"] += 1
        normalized = await raw_repository.get_normalized(raw_id, _NORMALIZER_VERSION)
        if normalized is None:
            normalized = NormalizedRecord(
                id=_id(f"normalized:{scenario.key}:{source_kind.value}"),
                raw_record_id=raw_id,
                normalizer_version=_NORMALIZER_VERSION,
                status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
                normalized_data={"text": raw.body, "synthetic": True},
                created_at=scenario.published_at,
                updated_at=scenario.published_at,
            )
            await raw_repository.save_normalized(normalized)
            created["normalized_records"] += 1
        cache_key = _hash(f"extraction:{scenario.key}:{source_kind.value}")
        if await extraction_repository.get_succeeded(cache_key) is None:
            await extraction_repository.save(
                ExtractionRecord(
                    id=_id(f"extraction:{scenario.key}:{source_kind.value}"),
                    normalized_record_id=normalized.id,
                    cache_key=cache_key,
                    input_hash=_hash(raw.content_hash),
                    technical_sheet=_sheet(scenario),
                    evidence=(
                        FieldEvidence(
                            field="disease_or_condition",
                            excerpt=scenario.condition,
                        ),
                    ),
                    metadata=AIExecutionMetadata(
                        provider="synthetic-demo",
                        model="precomputed-fixture",
                        contract_version=_EXTRACTION_VERSION,
                        prompt_version="demo-fixture-v1",
                        started_at=scenario.published_at,
                        duration_ms=0,
                        status=ExecutionStatus.SUCCEEDED,
                        input_units=0,
                        output_units=0,
                        cache_hit=True,
                    ),
                    sanitized_error=None,
                    created_at=scenario.published_at,
                )
            )
            created["technical_sheets"] += 1
        records.append(normalized)
    return records[0], records[1]


async def _store_relation(
    scenario: _Scenario,
    left_id: UUID,
    right_id: UUID,
    *,
    relation_repository: SqlAlchemyRelationAssessmentRepository,
    created: dict[str, int],
) -> RelationAssessmentRecord:
    cache_key = _hash(f"relation:{scenario.key}")
    existing = await relation_repository.get(cache_key)
    if existing is not None:
        return existing
    relation = RelationAssessmentRecord(
        id=_id(f"relation:{scenario.key}"),
        cache_key=cache_key,
        left_id=min(left_id, right_id, key=str),
        right_id=max(left_id, right_id, key=str),
        relation=RelationKind.CORROBORATES,
        method=RelationMethod.PROVIDER,
        confidence=0.88,
        justification="Fontes sintéticas independentes descrevem o mesmo sinal demonstrativo.",
        updating_record_id=None,
        rules_version="demo-relation-v1",
        metadata=AIExecutionMetadata(
            provider="synthetic-demo",
            model="precomputed-fixture",
            contract_version="relation-v1",
            prompt_version="demo-fixture-v1",
            started_at=scenario.published_at,
            duration_ms=0,
            status=ExecutionStatus.SUCCEEDED,
            input_units=0,
            output_units=0,
            cache_hit=True,
        ),
        sanitized_error=None,
        created_at=scenario.published_at,
    )
    await relation_repository.save(relation)
    created["relations"] += 1
    return relation


async def _ensure_workflow(
    service: WorkflowService,
    signal_id: UUID,
    scenario_key: str,
    target: WorkflowState,
) -> int:
    if target is WorkflowState.DETECTED:
        return 0
    transitions = (
        (WorkflowState.TRIAGE, 0),
        (WorkflowState.VERIFICATION, 1),
    )
    workflow = await service.get(signal_id)
    created = 0
    for state, expected_version in transitions:
        if state is WorkflowState.VERIFICATION and target is not WorkflowState.VERIFICATION:
            break
        if workflow.version != expected_version:
            continue
        outcome = await service.transition(
            TransitionCommand(
                signal_id=signal_id,
                operation_key=f"demo-{scenario_key}-{state.value}",
                actor_id="synthetic-demo",
                expected_version=expected_version,
                target_state=state,
                comment="Transição pré-carregada para demonstrar o fluxo com dados sintéticos.",
            )
        )
        workflow = outcome.workflow
        created += 1
    return created


def _source_rows(scenario: _Scenario) -> tuple[tuple[SourceKind, str, str | None, str], ...]:
    district = (
        scenario.location["district"]
        or scenario.location["municipality"]
        or "área não especificada"
    )
    return (
        (
            SourceKind.MEDIA,
            "demo-news",
            f"Notícia sintética: {scenario.condition} em {district}",
            (
                f"Notícia sintética relata {scenario.estimated_cases} menções de "
                f"{scenario.condition} em {district}."
            ),
        ),
        (
            SourceKind.COMMUNITY,
            "demo-community",
            None,
            (
                f"Relato comunitário sintético menciona {scenario.condition} e sintomas "
                f"compatíveis em {district}."
            ),
        ),
    )


def _sheet(scenario: _Scenario) -> dict[str, Any]:
    return {
        "schema_version": _EXTRACTION_VERSION,
        "disease_or_condition": scenario.condition,
        "syndrome": scenario.syndrome,
        "symptoms": list(scenario.symptoms),
        "estimated_cases": scenario.estimated_cases,
        "estimated_deaths": None,
        "temporal": {
            "start": scenario.published_at.date().isoformat(),
            "end": scenario.published_at.date().isoformat(),
            "precision": "day",
        },
        "location": {
            **scenario.location,
            "specific": None,
        },
    }


def _id(value: str) -> UUID:
    return uuid5(_NAMESPACE, value)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
