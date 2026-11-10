from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.persistence.test_investigation_repository import NOW, stored_normalized
from vbe_hub.adapters.persistence.investigation_repository import (
    SqlAlchemyInvestigationRepository,
    SqlAlchemySignalSuggestionRepository,
)
from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.api.app import create_app
from vbe_hub.api.individual_signals import get_individual_signal_session


@pytest.mark.integration
async def test_v1_individual_signal_queue_is_bounded() -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/signals?state=closed")
        invalid = await client.get("/v1/signals?limit=101")

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}
    assert invalid.status_code == 422


@pytest.mark.integration
async def test_v1_contract_is_published_without_replacing_legacy_paths() -> None:
    app = create_app()
    schema = app.openapi()

    assert "/signals" in schema["paths"]
    assert "/v1/signals" in schema["paths"]
    assert "/v1/signals/{signal_id}/related" in schema["paths"]
    assert "/v1/investigations" in schema["paths"]


@pytest.mark.integration
async def test_v1_signal_detail_and_precomputed_related_states_preserve_sources(
    db_session: AsyncSession,
) -> None:
    records = [await stored_normalized(db_session, index) for index in (101, 102, 103, 104)]
    investigations = SqlAlchemyInvestigationRepository(db_session)
    signals = [
        await investigations.get_or_create_signal(record.id, "individual-signal-v1", NOW)
        for record in records
    ]
    suggestions = SqlAlchemySignalSuggestionRepository(db_session, now=lambda: NOW)
    await suggestions.mark_pending(signals[0].id, signals[1].id, "related-signal-v1")
    await suggestions.mark_pending(signals[0].id, signals[2].id, "related-signal-v1")
    await suggestions.mark_failed(
        signals[0].id, signals[2].id, "related-signal-v1", "provider_timeout"
    )
    assessment_id = uuid4()
    db_session.add(
        RelationAssessmentModel(
            id=assessment_id,
            cache_key=assessment_id.hex * 2,
            left_id=records[0].id,
            right_id=records[3].id,
            relation="corroborates",
            method="provider",
            confidence=0.88,
            justification="As fontes convergem em tempo, lugar e sintomas.",
            updating_record_id=None,
            rules_version="relation-rules-v1",
            provider="openai",
            model="gpt-6-luna",
            contract_version="relation-v1",
            prompt_version="relate-v2.1",
            state="succeeded",
            started_at=NOW,
            duration_ms=20,
            input_units=50,
            output_units=10,
            cache_hit=False,
            error_code=None,
            retryable=None,
            sanitized_error=None,
            created_at=NOW,
        )
    )
    await db_session.flush()
    await suggestions.mark_pending(signals[0].id, signals[3].id, "related-signal-v1")
    await suggestions.mark_ready(signals[0].id, signals[3].id, "related-signal-v1", assessment_id)

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_individual_signal_session] = session_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        detail = await client.get(f"/v1/signals/{signals[0].id}")
        related = await client.get(f"/v1/signals/{signals[0].id}/related")

    assert detail.status_code == 200
    assert detail.json()["source"]["body"] == (
        "Conteúdo sem dados pessoais para validar proveniência."
    )
    assert detail.json()["provenance"]["adapter_name"] == "test"
    assert {item["status"] for item in related.json()["items"]} == {
        "pending",
        "failed",
        "ready",
    }
    failed = next(item for item in related.json()["items"] if item["status"] == "failed")
    assert failed["error_code"] == "provider_timeout"
    assert failed["candidate"]["source"]["excerpt"].startswith("Conteúdo sem dados")
    ready = next(item for item in related.json()["items"] if item["status"] == "ready")
    assert ready["relation"] == "corroborates"
    assert ready["confidence"] == 0.88
    assert ready["justification"] == "As fontes convergem em tempo, lugar e sintomas."


@pytest.mark.integration
async def test_v1_human_commands_are_atomic_idempotent_and_versioned(
    db_session: AsyncSession,
) -> None:
    records = [await stored_normalized(db_session, index) for index in (201, 202, 203)]
    repository = SqlAlchemyInvestigationRepository(db_session)
    signals = [
        await repository.get_or_create_signal(record.id, "individual-signal-v1", NOW)
        for record in records
    ]
    suggestions = SqlAlchemySignalSuggestionRepository(db_session, now=lambda: NOW)
    await suggestions.mark_pending(signals[0].id, signals[1].id, "related-signal-v1")

    async def session_override():
        yield db_session

    app = create_app(review_actor_id="analyst-test")
    app.dependency_overrides[get_individual_signal_session] = session_override
    transport = ASGITransport(app=app)
    create_key = f"create-{uuid4()}"
    add_key = f"add-{uuid4()}"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for signal in signals:
            triaged = await client.post(
                f"/v1/signals/{signal.id}/workflow/transitions",
                json={
                    "operation_key": f"triage-{signal.id}",
                    "expected_version": 0,
                    "target_state": "triage",
                },
            )
            assert triaged.status_code == 200
        created = await client.post(
            "/v1/investigations",
            json={"signal_id": str(signals[0].id), "operation_key": create_key},
        )
        replay = await client.post(
            "/v1/investigations",
            json={"signal_id": str(signals[0].id), "operation_key": create_key},
        )
        conflicting_replay = await client.post(
            "/v1/investigations",
            json={"signal_id": str(signals[1].id), "operation_key": create_key},
        )
        file_id = created.json()["id"]
        added = await client.post(
            f"/v1/investigations/{file_id}/members/{signals[1].id}",
            json={"operation_key": add_key, "expected_version": 1},
        )
        queue_after_composition = await client.get("/v1/signals")
        related_after_composition = await client.get(
            f"/v1/signals/{signals[0].id}/related"
        )
        stale = await client.post(
            f"/v1/investigations/{file_id}/members/{signals[2].id}",
            json={"operation_key": f"stale-{uuid4()}", "expected_version": 1},
        )
        remove_key = f"remove-{uuid4()}"
        removed = await client.post(
            f"/v1/investigations/{file_id}/members/{signals[1].id}/removals",
            json={
                "operation_key": remove_key,
                "expected_version": 2,
                "reason_code": "analyst-correction",
            },
        )
        remove_replay = await client.post(
            f"/v1/investigations/{file_id}/members/{signals[1].id}/removals",
            json={
                "operation_key": remove_key,
                "expected_version": 2,
                "reason_code": "analyst-correction",
            },
        )

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == file_id
    assert created.json()["events"] == replay.json()["events"]
    assert conflicting_replay.status_code == 409
    assert conflicting_replay.json()["detail"]["code"] == "operation_key_conflict"
    assert added.status_code == 200
    assert added.json()["head_signal_id"] == str(signals[0].id)
    assert added.json()["version"] == 2
    assert [member["signal"]["id"] for member in added.json()["members"]] == [
        str(signals[0].id),
        str(signals[1].id),
    ]
    assert all(member["signal"]["source"]["body"] for member in added.json()["members"])
    assert str(signals[1].id) not in {
        item["id"] for item in queue_after_composition.json()["items"]
    }
    assert related_after_composition.json()["items"] == []
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "investigation_version_conflict"
    assert removed.status_code == 200
    assert remove_replay.status_code == 200
    assert removed.json()["version"] == 3
    assert remove_replay.json()["events"] == removed.json()["events"]
    assert [member["signal"]["id"] for member in removed.json()["members"]] == [str(signals[0].id)]
