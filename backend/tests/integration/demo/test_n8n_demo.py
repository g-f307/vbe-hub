from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.individual_workflow_models import (
    IndividualSignalWorkflowModel,
)
from vbe_hub.adapters.persistence.investigation_models import (
    InvestigationFileMemberModel,
    SignalRelationSuggestionModel,
)
from vbe_hub.adapters.persistence.models import RawRecordModel
from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    RelationKind,
    RelationResult,
    StructuredExtractionResult,
)
from vbe_hub.synthetic.n8n_demo import N8nDemoService


class RecordingExtractor:
    def __init__(self) -> None:
        self.requests = []

    async def extract(self, request):
        self.requests.append(request)
        return StructuredExtractionResult(
            technical_sheet={
                "schema_version": "technical-sheet-v1",
                "record_nature": request.normalized_data["source_kind"],
                "disease_or_condition": "Dengue",
                "symptoms": ["febre"],
                "estimated_cases": 10,
                "estimated_deaths": None,
                "temporal": {"start": None, "end": None, "precision": "unknown"},
                "location": {
                    "country": "Brasil",
                    "state": "Amazonas",
                    "municipality": "Manaus",
                    "district": "Compensa",
                    "specific": None,
                    "precision": "district",
                },
                "confidence": 0.9,
                "evidence": [],
            },
            evidence=(),
            metadata=AIExecutionMetadata(
                provider="openai",
                model="test-model",
                contract_version="technical-sheet-v1",
                prompt_version="extract-v3",
                started_at=datetime(2026, 11, 5, tzinfo=UTC),
                duration_ms=1,
                status=ExecutionStatus.SUCCEEDED,
                input_units=10,
                output_units=5,
            ),
        )


class RecordingRelationJudge:
    def __init__(self, relation: RelationKind) -> None:
        self.relation = relation
        self.requests = []

    async def judge(self, request):
        self.requests.append(request)
        return RelationResult(
            relation=self.relation,
            justification="As fontes descrevem locais ou eventos diferentes.",
            confidence=0.86,
            metadata=AIExecutionMetadata(
                provider="openai",
                model="test-model",
                contract_version="relation-v1",
                prompt_version=request.prompt_version,
                started_at=datetime(2026, 11, 5, tzinfo=UTC),
                duration_ms=1,
                status=ExecutionStatus.SUCCEEDED,
                input_units=12,
                output_units=4,
            ),
        )


@pytest.mark.integration
async def test_offline_n8n_demo_persists_two_detected_signals_without_composing_a_file(
    db_session: AsyncSession,
) -> None:
    service = N8nDemoService(session=db_session)

    first = await service.run(scenario="related", mode="offline")
    await db_session.commit()
    repeated = await service.run(scenario="related", mode="offline")
    await db_session.commit()

    assert first["scenario"] == "related"
    assert first["mode"] == "offline"
    assert first["relation"] == "corroborates"
    assert len(first["signal_ids"]) == 2
    assert first["evidence_mode"] == "recorded_fixture"
    assert first["association_status"] == "unassociated"
    assert set(first["created"]) == {
        "raw_records",
        "normalized_records",
        "technical_sheets",
        "relations",
        "individual_signals",
        "relation_suggestions",
    }
    assert repeated["signal_ids"] == first["signal_ids"]
    assert repeated["created"] == {key: 0 for key in first["created"]}
    assert [item["source_kind"] for item in first["sources"]] == ["media", "community"]
    assert first["review_notice"] == "Sugestão de IA; requer revisão humana."
    workflows = list((await db_session.scalars(select(IndividualSignalWorkflowModel))).all())
    file_members = list(
        (
            await db_session.scalars(
                select(InvestigationFileMemberModel).where(
                    InvestigationFileMemberModel.signal_id.in_(first["signal_ids"])
                )
            )
        ).all()
    )
    suggestions = list(
        (await db_session.scalars(select(SignalRelationSuggestionModel))).all()
    )
    assert {workflow.state for workflow in workflows} == {"detected"}
    assert len(file_members) == 0
    assert len(suggestions) == 1
    assert suggestions[0].status == "ready"


@pytest.mark.integration
async def test_online_n8n_demo_extracts_both_normalized_sources_with_configured_provider(
    db_session: AsyncSession,
) -> None:
    extractor = RecordingExtractor()
    judge = RecordingRelationJudge(RelationKind.CORROBORATES)
    service = N8nDemoService(
        session=db_session,
        extractor=extractor,
        relation_judge=judge,
        extraction_model="test-model",
    )

    result = await service.run(scenario="related", mode="online")
    await db_session.commit()

    assert result["created"]["technical_sheets"] == 2
    assert len(extractor.requests) == 2
    assert {request.normalized_data["source_kind"] for request in extractor.requests} == {
        "media",
        "community",
    }
    assert result["evidence_mode"] == "live_openai"


@pytest.mark.integration
async def test_online_n8n_demo_returns_cached_or_fresh_ai_suggestion_without_association(
    db_session: AsyncSession,
) -> None:
    extractor = RecordingExtractor()
    judge = RecordingRelationJudge(RelationKind.UNRELATED)
    service = N8nDemoService(
        session=db_session,
        extractor=extractor,
        relation_judge=judge,
        extraction_model="test-model",
    )

    result = await service.run(scenario="dengue-compensa", mode="online")
    await db_session.commit()

    assert result["relation"] in {"corroborates", "related_context", "unrelated"}
    assert len(result["signal_ids"]) == 2
    assert result["association_status"] == "unassociated"


@pytest.mark.integration
async def test_incompatible_demo_keeps_sources_as_two_signals(
    db_session: AsyncSession,
) -> None:
    service = N8nDemoService(session=db_session)

    result = await service.run(scenario="incompatible", mode="offline")
    await db_session.commit()

    assert result["relation"] == "unrelated"
    assert len(result["signal_ids"]) == 2
    assert result["created"]["individual_signals"] in {0, 2}
    assert result["created"]["relation_suggestions"] == 0


@pytest.mark.integration
async def test_ambiguous_demo_marks_relation_for_human_review(
    db_session: AsyncSession,
) -> None:
    service = N8nDemoService(session=db_session)

    result = await service.run(scenario="ambiguous", mode="offline")
    await db_session.commit()

    assert result["relation"] == "related_context"
    assert len(result["signal_ids"]) == 2
    assert "revisão" in result["relation_explanation"]


@pytest.mark.integration
async def test_ten_case_catalog_creates_twenty_detected_signals_and_ten_suggestions(
    db_session: AsyncSession,
) -> None:
    case_ids = (
        "dengue-compensa",
        "sarampo-cidade-nova",
        "leptospirose-jorge-teixeira",
        "malaria-taruma",
        "doenca-diarreica-educandos",
        "influenza-parque-dez",
        "hepatite-a-colonia-antonio-aleixo",
        "chikungunya-ponta-negra",
        "meningite-zumbi",
        "febre-amarela-reserva-ducke",
    )
    service = N8nDemoService(session=db_session)

    results = [
        await service.run(scenario=case_id, mode="offline") for case_id in case_ids
    ]
    await db_session.commit()

    signal_ids = {signal_id for item in results for signal_id in item["signal_ids"]}
    assert len(signal_ids) == 20
    assert all(item["relation"] == "corroborates" for item in results)
    workflows = list(
        (
            await db_session.scalars(
                select(IndividualSignalWorkflowModel).where(
                    IndividualSignalWorkflowModel.signal_id.in_(signal_ids)
                )
            )
        ).all()
    )
    suggestions = list(
        (
            await db_session.scalars(
                select(SignalRelationSuggestionModel).where(
                    SignalRelationSuggestionModel.left_signal_id.in_(signal_ids),
                    SignalRelationSuggestionModel.right_signal_id.in_(signal_ids),
                )
            )
        ).all()
    )
    file_members = list(
        (
            await db_session.scalars(
                select(InvestigationFileMemberModel).where(
                    InvestigationFileMemberModel.signal_id.in_(signal_ids)
                )
            )
        ).all()
    )
    assert len(workflows) == 20
    assert all(workflow.state == "detected" for workflow in workflows)
    assert len(suggestions) == 10
    assert all(suggestion.status == "ready" for suggestion in suggestions)
    assert len(file_members) == 0


@pytest.mark.integration
async def test_batch_source_content_is_natural_but_metadata_remains_synthetic(
    db_session: AsyncSession,
) -> None:
    service = N8nDemoService(session=db_session)

    await service.run(scenario="malaria-taruma", mode="offline")
    await db_session.commit()
    records = list(
        (
            await db_session.execute(
                select(RawRecordModel).where(
                    RawRecordModel.external_id.like("demo:malaria-taruma:%")
                )
            )
        ).scalars()
    )

    assert len(records) == 2
    assert {record.source_kind for record in records} == {"media", "community"}
    assert all(record.original_payload["synthetic"] is True for record in records)
    assert all("sintétic" not in f"{record.title} {record.body}".casefold() for record in records)
