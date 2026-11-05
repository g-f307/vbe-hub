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
from vbe_hub.normalization.adapters import CommunityNormalizer, MediaNormalizer

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
    media_title: str
    media_body: str
    community_body: str


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
        media_title="Unidades registram aumento de atendimentos por dengue na Compensa",
        media_body=(
            "Serviços de saúde da zona oeste observaram crescimento na procura por atendimento "
            "de pessoas com febre, dor no corpo e sinais de sangramento na Compensa."
        ),
        community_body=(
            "Moradores da Compensa comentam que várias famílias procuraram atendimento nos "
            "últimos dias por febre alta, dores no corpo e mal-estar."
        ),
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
        media_title="Após alagamentos, moradores procuram atendimento com sintomas febris",
        media_body=(
            "Unidades de Manaus atenderam pessoas com febre, dor muscular e náusea depois do "
            "contato com água acumulada durante as chuvas."
        ),
        community_body=(
            "No Jorge Teixeira, moradores relatam febre forte e dores nas pernas depois de "
            "atravessarem áreas alagadas para chegar em casa."
        ),
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
        media_title="Crianças com febre e manchas na pele mobilizam atendimento na Cidade Nova",
        media_body=(
            "Famílias buscaram avaliação para crianças com febre e manchas avermelhadas na pele "
            "em diferentes pontos da Cidade Nova."
        ),
        community_body=(
            "Responsáveis relatam em grupos do bairro crianças com febre, olhos irritados e "
            "manchas vermelhas pelo corpo ao longo desta semana."
        ),
    ),
)

_BATCH_SCENARIOS = _SCENARIOS + (
    _Scenario(
        key="malaria-taruma",
        condition="Malária",
        syndrome="Síndrome febril aguda",
        symptoms=("febre intermitente", "calafrios", "sudorese"),
        estimated_cases=18,
        published_at=datetime(2026, 10, 12, 7, 30, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Tarumã",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Casos de febre com calafrios levam moradores do Tarumã às unidades de saúde",
        media_body=(
            "Equipes registraram procura de moradores do Tarumã com episódios de febre que vai "
            "e volta, calafrios intensos e sudorese, principalmente no fim do dia."
        ),
        community_body=(
            "Moradores próximos a áreas de mata no Tarumã relatam vizinhos com febre em ciclos, "
            "tremores e suor intenso durante a noite."
        ),
    ),
    _Scenario(
        key="doenca-diarreica-educandos",
        condition="Doença diarreica aguda",
        syndrome="Síndrome gastrointestinal",
        symptoms=("diarreia", "vômito", "dor abdominal"),
        estimated_cases=34,
        published_at=datetime(2026, 10, 13, 11, 0, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Educandos",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Aumenta procura por atendimento após episódios de diarreia em Educandos",
        media_body=(
            "Moradores de Educandos buscaram atendimento com diarreia, vômito e dor abdominal. "
            "Os relatos se concentram em famílias de ruas próximas à orla."
        ),
        community_body=(
            "Famílias de Educandos dizem que adultos e crianças da mesma casa tiveram diarreia e "
            "vômitos depois do fim de semana."
        ),
    ),
    _Scenario(
        key="influenza-parque-dez",
        condition="Influenza ou síndrome gripal",
        syndrome="Síndrome respiratória aguda",
        symptoms=("febre", "tosse", "dor de garganta"),
        estimated_cases=45,
        published_at=datetime(2026, 10, 14, 8, 15, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Parque 10 de Novembro",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Síndrome gripal eleva ausências em escolas do Parque 10",
        media_body=(
            "Escolas do Parque 10 registraram aumento de faltas entre alunos com febre, tosse e "
            "dor de garganta durante a semana."
        ),
        community_body=(
            "Responsáveis de alunos do Parque 10 relatam muitas crianças em casa com tosse forte, "
            "febre e incômodo na garganta."
        ),
    ),
    _Scenario(
        key="hepatite-a-colonia-antonio-aleixo",
        condition="Hepatite A",
        syndrome="Síndrome ictérica aguda",
        symptoms=("pele amarelada", "náusea", "dor abdominal"),
        estimated_cases=9,
        published_at=datetime(2026, 10, 15, 10, 20, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Colônia Antônio Aleixo",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Pacientes com sinais de icterícia são atendidos na Colônia Antônio Aleixo",
        media_body=(
            "Serviços locais avaliaram pacientes com pele e olhos amarelados, náusea e dor "
            "abdominal na Colônia Antônio Aleixo."
        ),
        community_body=(
            "Moradores da Colônia Antônio Aleixo comentam casos de pessoas com olhos amarelados, "
            "enjoo persistente e dor na barriga."
        ),
    ),
    _Scenario(
        key="chikungunya-ponta-negra",
        condition="Chikungunya",
        syndrome="Síndrome febril com artralgia",
        symptoms=("febre", "dor nas articulações", "inchaço"),
        estimated_cases=21,
        published_at=datetime(2026, 10, 16, 9, 10, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Ponta Negra",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Dor intensa nas articulações motiva atendimentos na Ponta Negra",
        media_body=(
            "Pacientes da Ponta Negra procuraram atendimento com febre, inchaço e dores fortes "
            "nas articulações, com dificuldade para caminhar."
        ),
        community_body=(
            "Em grupos da Ponta Negra, moradores relatam febre seguida de dor muito forte nas "
            "mãos, pés e joelhos."
        ),
    ),
    _Scenario(
        key="meningite-zumbi",
        condition="Meningite ou síndrome compatível",
        syndrome="Síndrome meníngea",
        symptoms=("febre", "dor de cabeça", "rigidez de nuca"),
        estimated_cases=6,
        published_at=datetime(2026, 10, 17, 13, 40, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Zumbi dos Palmares",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Pacientes com febre e rigidez de nuca são avaliados na zona leste",
        media_body=(
            "Uma unidade da zona leste recebeu pacientes do Zumbi com febre alta, dor de cabeça "
            "intensa e dificuldade para movimentar o pescoço."
        ),
        community_body=(
            "Moradores do Zumbi relatam pessoas da mesma área com febre, dor de cabeça muito forte "
            "e pescoço endurecido."
        ),
    ),
    _Scenario(
        key="febre-amarela-reserva-ducke",
        condition="Febre amarela ou síndrome compatível",
        syndrome="Síndrome febril ictérica e hemorrágica",
        symptoms=("febre", "icterícia", "dor muscular"),
        estimated_cases=4,
        published_at=datetime(2026, 10, 18, 6, 50, tzinfo=UTC),
        location={
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": "Cidade de Deus",
            "precision": "district",
        },
        target_state=WorkflowState.DETECTED,
        media_title="Quadros febris após atividades em área de mata são investigados em Manaus",
        media_body=(
            "Pessoas que estiveram no entorno da Reserva Ducke foram atendidas com febre, dor "
            "muscular e coloração amarelada nos olhos."
        ),
        community_body=(
            "Moradores próximos à Reserva Ducke relatam trabalhadores com febre forte, dores no "
            "corpo e olhos amarelados depois de entrarem na mata."
        ),
    ),
)


async def load_demo_scenario(
    session: AsyncSession,
    *,
    scenario_keys: frozenset[str] | None = None,
    store_fixture_sheets: bool = True,
    relation_overrides: Mapping[str, RelationKind] | None = None,
) -> DemoLoadResult:
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

    scenarios = (
        _SCENARIOS
        if scenario_keys is None
        else tuple(item for item in _BATCH_SCENARIOS if item.key in scenario_keys)
    )
    if scenario_keys is not None and len(scenarios) != len(scenario_keys):
        raise ValueError("unknown demo scenario key")

    for scenario in scenarios:
        records = await _store_records(
            scenario,
            raw_repository=raw_repository,
            extraction_repository=extraction_repository,
            created=created,
            store_fixture_sheets=store_fixture_sheets,
        )
        relation_kind = (relation_overrides or {}).get(scenario.key, RelationKind.CORROBORATES)
        relation = await _store_relation(
            scenario,
            records[0].id,
            records[1].id,
            relation_kind=relation_kind,
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
        for signal in result.signals:
            if await signal_repository.get(signal.id) is None:
                created["signals"] += 1
        await signal_repository.save(result)
        source_metadata = dict(
            zip(
                (record.id for record in records),
                (
                    (SourceKind.MEDIA, "demo-news"),
                    (SourceKind.COMMUNITY, "demo-community"),
                ),
                strict=True,
            )
        )
        for signal in result.signals:
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
                        record_id=record_id,
                        source_kind=source_metadata[record_id][0],
                        source_name=source_metadata[record_id][1],
                        technical_sheet=_sheet(scenario),
                    )
                    for record_id in (*signal.core_record_ids, *signal.context_record_ids)
                ],
                relations=(
                    [
                        PriorityRelation(
                            assessment_id=relation.id,
                            relation=relation_kind,
                            record_ids=(records[0].id, records[1].id),
                        )
                    ]
                    if relation.id in signal.relation_ids
                    else []
                ),
                evaluated_at=_NOW,
            )
            if await priority_repository.get(priority.id) is None:
                created["priorities"] += 1
            await priority_repository.save(priority)
            created["workflow_events"] += await _ensure_workflow(
                workflow_service,
                signal.id,
                (
                    scenario.key
                    if relation_kind is RelationKind.CORROBORATES
                    else f"{scenario.key}-{relation_kind.value}-{signal.id}"
                ),
                scenario.target_state,
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
    store_fixture_sheets: bool,
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
                normalized_data=(
                    MediaNormalizer().normalize(raw)
                    if source_kind is SourceKind.MEDIA
                    else CommunityNormalizer().normalize(raw)
                )
                | {"synthetic": True},
                created_at=scenario.published_at,
                updated_at=scenario.published_at,
            )
            await raw_repository.save_normalized(normalized)
            created["normalized_records"] += 1
        cache_key = _hash(f"extraction:{scenario.key}:{source_kind.value}")
        if store_fixture_sheets and await extraction_repository.get_succeeded(cache_key) is None:
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
    relation_kind: RelationKind,
    relation_repository: SqlAlchemyRelationAssessmentRepository,
    created: dict[str, int],
) -> RelationAssessmentRecord:
    # Preserve the identifiers of the original corroborating demo so an upgrade does not
    # duplicate cards already loaded by `demo-load`. Alternative relations are separate fixtures.
    relation_identity = (
        f"relation:{scenario.key}"
        if relation_kind is RelationKind.CORROBORATES
        else f"relation:{scenario.key}:{relation_kind.value}"
    )
    cache_key = _hash(relation_identity)
    existing = await relation_repository.get(cache_key)
    if existing is not None:
        return existing
    relation = RelationAssessmentRecord(
        id=_id(relation_identity),
        cache_key=cache_key,
        left_id=min(left_id, right_id, key=str),
        right_id=max(left_id, right_id, key=str),
        relation=relation_kind,
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
    return (
        (
            SourceKind.MEDIA,
            "demo-news",
            scenario.media_title,
            scenario.media_body,
        ),
        (
            SourceKind.COMMUNITY,
            "demo-community",
            None,
            scenario.community_body,
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
