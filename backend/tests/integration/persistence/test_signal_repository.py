from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.relation_repository import (
    SqlAlchemyRelationAssessmentRepository,
)
from vbe_hub.adapters.persistence.repositories import SqlAlchemyRawRecordRepository
from vbe_hub.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from vbe_hub.application.ai import AIExecutionMetadata, ExecutionStatus, RelationKind
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
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def sheet(municipality: str, cases: int) -> dict:
    return {
        "disease_or_condition": "Sarampo",
        "syndrome": "Síndrome febril exantemática",
        "symptoms": ["febre", "manchas vermelhas"],
        "estimated_cases": cases,
        "estimated_deaths": None,
        "temporal": {"start": "2026-01-01", "end": None, "precision": "day"},
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": municipality,
            "district": None,
            "specific": None,
            "precision": "municipality",
        },
    }


async def normalized(session: AsyncSession, index: int) -> NormalizedRecord:
    raw = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="synthetic-media",
        external_id=f"signal-{index}-{uuid4()}",
        published_at=NOW,
        title="Sinal sintético",
        body="Texto sintético sem dados pessoais.",
        source_url=None,
        language="pt-BR",
        original_payload={"synthetic": True},
    )
    raw_repository = SqlAlchemyRawRecordRepository(session)
    await raw_repository.add(
        raw, Provenance(adapter_name="synthetic", adapter_version="1", collected_at=NOW)
    )
    item = NormalizedRecord(
        id=uuid4(),
        raw_record_id=raw.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
        normalized_data={"text": raw.body},
    )
    await raw_repository.save_normalized(item)
    return item


async def stored_relation(
    session: AsyncSession,
    left_id: UUID,
    right_id: UUID,
    kind: RelationKind,
    *,
    assessment_id: UUID | None = None,
) -> RelationAssessmentRecord:
    item = RelationAssessmentRecord(
        id=assessment_id or uuid4(),
        cache_key=uuid4().hex + uuid4().hex,
        left_id=min(left_id, right_id, key=str),
        right_id=max(left_id, right_id, key=str),
        relation=kind,
        method=RelationMethod.PROVIDER,
        confidence=0.95,
        justification="Relação sintética para teste.",
        updating_record_id=None,
        rules_version="relation-rules-v1",
        metadata=AIExecutionMetadata(
            provider="fake",
            model="fake-relation",
            contract_version="relation-v1",
            prompt_version="relate-v2.1",
            started_at=NOW,
            duration_ms=1,
            status=ExecutionStatus.SUCCEEDED,
        ),
        sanitized_error=None,
        created_at=NOW,
    )
    await SqlAlchemyRelationAssessmentRepository(session).save(item)
    return item


@pytest.mark.integration
async def test_signal_repository_is_idempotent_and_recovers_audit_links(
    db_session: AsyncSession,
) -> None:
    first = await normalized(db_session, 1)
    second = await normalized(db_session, 2)
    assessment = await stored_relation(
        db_session, first.id, second.id, RelationKind.CORROBORATES
    )
    result = SignalConsolidationService(
        ConsolidationPolicy(version="signal-policy-v1")
    ).consolidate(
        records=[
            SignalRecord(first.id, sheet("Manaus", 3)),
            SignalRecord(second.id, sheet("Manaus", 4)),
        ],
        relations=[
            SignalRelationInput(
                assessment.id,
                first.id,
                second.id,
                assessment.relation,
            )
        ],
    )
    repository = SqlAlchemySignalRepository(db_session)

    await repository.save(result)
    await repository.save(result)
    await db_session.commit()

    recovered = await repository.get(result.signals[0].id)
    assert recovered == result.signals[0]
    assert await repository.list_by_policy("signal-policy-v1") == [result.signals[0]]


@pytest.mark.integration
async def test_signal_repository_preserves_multiple_policy_versions(
    db_session: AsyncSession,
) -> None:
    first = await normalized(db_session, 3)
    second = await normalized(db_session, 4)
    assessment = await stored_relation(
        db_session, first.id, second.id, RelationKind.CORROBORATES
    )
    records = [
        SignalRecord(first.id, sheet("Manaus", 3)),
        SignalRecord(second.id, sheet("Manaus", 4)),
    ]
    relations = [
        SignalRelationInput(assessment.id, first.id, second.id, assessment.relation)
    ]
    repository = SqlAlchemySignalRepository(db_session)

    for version in ("signal-policy-v1", "signal-policy-v2"):
        await repository.save(
            SignalConsolidationService(ConsolidationPolicy(version=version)).consolidate(
                records=records,
                relations=relations,
            )
        )
    await db_session.commit()

    assert len(await repository.list_by_policy("signal-policy-v1")) == 1
    assert len(await repository.list_by_policy("signal-policy-v2")) == 1


@pytest.mark.integration
async def test_signal_repository_persists_explained_grouping_conflict(
    db_session: AsyncSession,
) -> None:
    first = await normalized(db_session, 5)
    bridge = await normalized(db_session, 6)
    conflicting = await normalized(db_session, 7)
    accepted = await stored_relation(
        db_session,
        first.id,
        bridge.id,
        RelationKind.CORROBORATES,
        assessment_id=UUID(int=101),
    )
    blocked = await stored_relation(
        db_session,
        bridge.id,
        conflicting.id,
        RelationKind.CORROBORATES,
        assessment_id=UUID(int=102),
    )
    result = SignalConsolidationService(
        ConsolidationPolicy(version="signal-policy-v1")
    ).consolidate(
        records=[
            SignalRecord(first.id, sheet("Manaus", 3)),
            SignalRecord(bridge.id, sheet("", 4)),
            SignalRecord(conflicting.id, sheet("Parintins", 5)),
        ],
        relations=[
            SignalRelationInput(accepted.id, first.id, bridge.id, accepted.relation),
            SignalRelationInput(blocked.id, bridge.id, conflicting.id, blocked.relation),
        ],
    )
    repository = SqlAlchemySignalRepository(db_session)

    await repository.save(result)
    await db_session.commit()

    conflicts = await repository.list_conflicts("signal-policy-v1")
    assert len(conflicts) == 1
    assert conflicts[0].relation_id == blocked.id
    assert conflicts[0].code == "geographic_conflict"
