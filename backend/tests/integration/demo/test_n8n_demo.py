from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import RawRecordModel
from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
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


@pytest.mark.integration
async def test_offline_n8n_demo_persists_one_card_with_two_sources_idempotently(
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
    assert len(first["signal_ids"]) == 1
    assert first["created"] == {
        "raw_records": 2,
        "normalized_records": 2,
        "technical_sheets": 2,
        "relations": 1,
        "signals": 1,
        "priorities": 1,
        "workflow_events": 0,
    }
    assert repeated["signal_ids"] == first["signal_ids"]
    assert repeated["created"] == {key: 0 for key in first["created"]}
    assert [item["source_kind"] for item in first["sources"]] == ["media", "community"]
    assert first["review_notice"] == "Sugestão de IA; requer revisão humana."


@pytest.mark.integration
async def test_online_n8n_demo_extracts_both_normalized_sources_with_configured_provider(
    db_session: AsyncSession,
) -> None:
    extractor = RecordingExtractor()
    service = N8nDemoService(
        session=db_session,
        extractor=extractor,
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


@pytest.mark.integration
async def test_incompatible_demo_keeps_sources_as_two_signals(
    db_session: AsyncSession,
) -> None:
    service = N8nDemoService(session=db_session)

    result = await service.run(scenario="incompatible", mode="offline")
    await db_session.commit()

    assert result["relation"] == "unrelated"
    assert len(result["signal_ids"]) == 2
    assert result["created"]["signals"] == 2
    assert result["created"]["priorities"] == 2


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
async def test_ten_case_catalog_creates_ten_consolidated_signals_from_twenty_sources(
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

    assert sum(item["created"]["raw_records"] for item in results) == 20
    assert sum(item["created"]["signals"] for item in results) == 10
    assert len({item["signal_ids"][0] for item in results}) == 10
    assert all(item["relation"] == "corroborates" for item in results)


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
