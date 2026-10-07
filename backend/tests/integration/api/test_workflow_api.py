from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.persistence.test_workflow_repository import NOW, stored_signal
from vbe_hub.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from vbe_hub.adapters.persistence.workflow_repository import SqlAlchemyWorkflowRepository
from vbe_hub.api.app import create_app
from vbe_hub.application.workflow import WorkflowService


def workflow_service(db_session: AsyncSession) -> WorkflowService:
    return WorkflowService(SqlAlchemyWorkflowRepository(db_session), now=lambda: NOW)


@pytest.mark.integration
async def test_workflow_api_records_human_review_without_accepting_client_actor(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    signal = await SqlAlchemySignalRepository(db_session).get(signal_id)
    assert signal is not None
    app = create_app(
        workflow_service=workflow_service(db_session),
        review_actor_id="synthetic-analyst",
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/signals/{signal_id}/reviews",
            json={
                "operation_key": f"api-review-{uuid4()}",
                "expected_version": 0,
                "target_type": "grouping",
                "target_id": str(signal_id),
                "suggestion_identity_key": signal.identity_key,
                "action": "accept",
                "comment": "Agrupamento sintético revisado.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"]["version"] == 1
    assert payload["event"]["actor_id"] == "synthetic-analyst"
    assert payload["event"]["new_value"] == {
        "decision": "accept",
        "suggestion_identity_key": signal.identity_key,
    }


@pytest.mark.integration
async def test_workflow_api_transitions_idempotently_and_exposes_history(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    app = create_app(
        workflow_service=workflow_service(db_session),
        review_actor_id="synthetic-analyst",
    )
    operation_key = f"api-triage-{uuid4()}"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.get(f"/signals/{signal_id}/workflow")
        first = await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": operation_key,
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        repeated = await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": operation_key,
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        history = await client.get(f"/signals/{signal_id}/audit-events")

    assert initial.status_code == 200
    assert initial.json()["state"] == "detected"
    assert first.status_code == repeated.status_code == 200
    assert first.json()["event"]["id"] == repeated.json()["event"]["id"]
    assert first.json()["event"]["actor_id"] == "synthetic-analyst"
    assert history.status_code == 200
    assert [(item["sequence"], item["action"]) for item in history.json()] == [
        (1, "transition")
    ]


@pytest.mark.integration
async def test_workflow_api_rejects_stale_version_with_stable_conflict(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    app = create_app(
        workflow_service=workflow_service(db_session),
        review_actor_id="synthetic-analyst",
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": f"first-{uuid4()}",
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        stale = await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": f"stale-{uuid4()}",
                "expected_version": 0,
                "target_state": "triage",
            },
        )

    assert stale.status_code == 409
    assert stale.json() == {
        "detail": {
            "code": "workflow_version_conflict",
            "expected_version": 0,
            "current_version": 1,
        }
    }


@pytest.mark.integration
async def test_workflow_api_validates_closure_and_rejects_extra_fields(
    db_session: AsyncSession,
) -> None:
    signal_id = await stored_signal(db_session)
    app = create_app(
        workflow_service=workflow_service(db_session),
        review_actor_id="synthetic-analyst",
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": f"to-triage-{uuid4()}",
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        missing_reason = await client.post(
            f"/signals/{signal_id}/workflow/transitions",
            json={
                "operation_key": f"close-{uuid4()}",
                "expected_version": 1,
                "target_state": "closed",
            },
        )
        extra_field = await client.post(
            f"/signals/{signal_id}/reviews",
            json={
                "operation_key": f"review-{uuid4()}",
                "expected_version": 1,
                "target_type": "priority",
                "target_id": str(UUID(int=20)),
                "suggestion_identity_key": "a" * 64,
                "action": "accept",
                "actor_id": "forged-actor",
            },
        )

    assert missing_reason.status_code == 422
    assert missing_reason.json()["detail"]["code"] == "closure_reason_required"
    assert extra_field.status_code == 422


@pytest.mark.integration
async def test_workflow_api_returns_not_found_without_creating_or_leaking_details(
    db_session: AsyncSession,
) -> None:
    app = create_app(
        workflow_service=workflow_service(db_session),
        review_actor_id="synthetic-analyst",
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/signals/{UUID(int=999_999)}/workflow")

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "workflow_signal_not_found"}}
