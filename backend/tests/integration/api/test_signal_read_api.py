from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.persistence.test_extraction_repository import succeeded_record
from tests.integration.persistence.test_priority_repository import NOW, stored_signal
from vbe_hub.adapters.persistence.priority_repository import SqlAlchemyPriorityRepository
from vbe_hub.adapters.persistence.repositories import SqlAlchemyExtractionRepository
from vbe_hub.adapters.persistence.workflow_models import SignalWorkflowModel
from vbe_hub.adapters.persistence.workflow_repository import SqlAlchemyWorkflowRepository
from vbe_hub.api.app import create_app
from vbe_hub.api.signals import get_signal_read_session
from vbe_hub.application.ai import ExecutionStatus, ProviderErrorCode
from vbe_hub.application.correlation.priority import PriorityCalculator, PriorityPolicy
from vbe_hub.application.workflow import TransitionCommand, WorkflowService, WorkflowState


@pytest.mark.integration
async def test_signal_read_api_lists_an_empty_canonical_queue() -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/signals")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 25,
        "total": 0,
    }


@pytest.mark.integration
async def test_signal_read_api_serializes_persisted_signal_without_materializing_workflow(
    db_session: AsyncSession,
) -> None:
    signal, source = await stored_signal(db_session)
    priority = PriorityCalculator(PriorityPolicy.v1()).calculate(
        signal=signal,
        records=[source],
        relations=[],
        evaluated_at=NOW,
    )
    await SqlAlchemyPriorityRepository(db_session).save(priority)

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "id": str(signal.id),
            "title": signal.title,
            "summary": signal.summary,
            "conditions": list(signal.conditions),
            "symptoms": list(signal.symptoms),
            "period_start": signal.period_start.isoformat(),
            "period_end": signal.period_end.isoformat(),
            "location": {
                "country": "Brasil",
                "state": "Amazonas",
                "municipality": "Manaus",
                "district": None,
                "precision": None,
            },
            "source_counts": {"media": 1, "community": 0, "total": 1},
            "priority": {
                "id": str(priority.id),
                "band": priority.band.value,
                "score": priority.score,
                "confidence": priority.confidence,
                "policy_version": priority.policy_version,
                "identity_key": priority.identity_key,
            },
            "workflow": {"state": "detected", "version": 0},
        }
    ]
    workflows = list(
        (await db_session.scalars(select(SignalWorkflowModel))).all()
    )
    assert workflows == []


@pytest.mark.integration
async def test_signal_read_api_returns_investigation_with_source_provenance(
    db_session: AsyncSession,
) -> None:
    signal, _source = await stored_signal(db_session)

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/signals/{signal.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"] == {
        "id": str(signal.id),
        "title": signal.title,
        "summary": signal.summary,
        "conditions": list(signal.conditions),
        "symptoms": list(signal.symptoms),
        "period_start": signal.period_start.isoformat(),
        "period_end": signal.period_end.isoformat(),
        "location": {
            "country": "Brasil",
            "state": "Amazonas",
            "municipality": "Manaus",
            "district": None,
            "precision": None,
        },
        "source_counts": {"media": 1, "community": 0, "total": 1},
        "priority": None,
        "workflow": {"state": "detected", "version": 0},
    }
    assert payload["grouping"] == {
        "identity_key": signal.identity_key,
        "policy_version": signal.policy_version,
        "processing_state": signal.processing_state,
        "divergence_codes": [],
    }
    assert payload["sources"] == [
        {
            "normalized_record_id": str(signal.core_record_ids[0]),
            "role": "core",
            "source_kind": "media",
            "source_name": "synthetic-media",
            "published_at": NOW.isoformat().replace("+00:00", "Z"),
            "title": "Sinal sintético",
            "excerpt": "Texto sintético sem dados pessoais.",
            "technical_sheet": None,
        }
    ]
    assert payload["relations"] == []
    assert payload["audit_events"] == []


@pytest.mark.integration
async def test_signal_read_api_filters_queue_by_canonical_state_priority_and_source_metadata(
    db_session: AsyncSession,
) -> None:
    detected_signal, _detected_source = await stored_signal(db_session)
    triaged_signal, triaged_source = await stored_signal(db_session)
    priority = PriorityCalculator(PriorityPolicy.v1()).calculate(
        signal=triaged_signal,
        records=[triaged_source],
        relations=[],
        evaluated_at=NOW,
    )
    await SqlAlchemyPriorityRepository(db_session).save(priority)
    workflow_service = WorkflowService(
        SqlAlchemyWorkflowRepository(db_session), now=lambda: NOW
    )
    await workflow_service.transition(
        TransitionCommand(
            signal_id=triaged_signal.id,
            operation_key=f"triage-{uuid4()}",
            actor_id="synthetic-analyst",
            expected_version=0,
            target_state=WorkflowState.TRIAGE,
        )
    )

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        triage = await client.get("/signals?state=triage")
        detected = await client.get("/signals?state=detected")
        attention = await client.get("/signals?priority_band=attention")
        community = await client.get("/signals?source_kind=community")
        other_condition = await client.get("/signals?condition=dengue")
        later_period = await client.get("/signals?period_start=2026-11-01")

    assert [item["id"] for item in triage.json()["items"]] == [str(triaged_signal.id)]
    assert [item["id"] for item in detected.json()["items"]] == [str(detected_signal.id)]
    assert [item["id"] for item in attention.json()["items"]] == [str(triaged_signal.id)]
    assert community.json()["items"] == []
    assert other_condition.json()["items"] == []
    assert later_period.json()["items"] == []


@pytest.mark.integration
async def test_signal_read_api_keeps_latest_successful_technical_sheet_available(
    db_session: AsyncSession,
) -> None:
    signal, source = await stored_signal(db_session)
    success = succeeded_record(source.record_id)
    failure = replace(
        success,
        id=uuid4(),
        cache_key="e" * 64,
        technical_sheet=None,
        sanitized_error="Falha sintética posterior.",
        metadata=replace(
            success.metadata,
            status=ExecutionStatus.FAILED,
            input_units=None,
            output_units=None,
            error_code=ProviderErrorCode.TIMEOUT,
            retryable=True,
        ),
        created_at=NOW + timedelta(minutes=1),
    )
    repository = SqlAlchemyExtractionRepository(db_session)
    await repository.save(success)
    await repository.save(failure)

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/signals/{signal.id}")

    assert response.status_code == 200
    assert response.json()["sources"][0]["technical_sheet"] == success.technical_sheet
