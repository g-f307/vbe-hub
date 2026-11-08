from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.persistence.test_investigation_repository import NOW, stored_normalized
from vbe_hub.adapters.persistence.investigation_repository import (
    SqlAlchemyInvestigationRepository,
)
from vbe_hub.api.app import create_app
from vbe_hub.api.individual_signals import get_individual_signal_session


async def individual_signal(db_session: AsyncSession, index: int):
    normalized = await stored_normalized(db_session, index)
    return await SqlAlchemyInvestigationRepository(db_session).get_or_create_signal(
        normalized.id, "individual-signal-v1", NOW
    )


def app_for(db_session: AsyncSession):
    async def session_override():
        yield db_session

    app = create_app(review_actor_id="analyst-test")
    app.dependency_overrides[get_individual_signal_session] = session_override
    return app


@pytest.mark.integration
async def test_new_individual_signal_starts_detected_and_triage_is_explicit(
    db_session: AsyncSession,
) -> None:
    signal = await individual_signal(db_session, 301)
    transport = ASGITransport(app=app_for(db_session))
    operation_key = f"triage-{uuid4()}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.get(f"/v1/signals/{signal.id}/workflow")
        triaged = await client.post(
            f"/v1/signals/{signal.id}/workflow/transitions",
            json={
                "operation_key": operation_key,
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        replay = await client.post(
            f"/v1/signals/{signal.id}/workflow/transitions",
            json={
                "operation_key": operation_key,
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        queue = await client.get("/v1/signals?state=triage")

    assert initial.status_code == 200
    assert initial.json()["state"] == "detected"
    assert initial.json()["version"] == 0
    assert triaged.status_code == replay.status_code == 200
    assert triaged.json()["event"]["id"] == replay.json()["event"]["id"]
    assert triaged.json()["event"]["actor_id"] == "analyst-test"
    assert str(signal.id) in {item["id"] for item in queue.json()["items"]}


@pytest.mark.integration
async def test_detected_signal_cannot_be_associated_before_human_triage(
    db_session: AsyncSession,
) -> None:
    signal = await individual_signal(db_session, 302)
    transport = ASGITransport(app=app_for(db_session))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={
                "signal_id": str(signal.id),
                "operation_key": f"create-{uuid4()}",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "signal_not_in_triage",
        "current_state": "detected",
    }


@pytest.mark.integration
async def test_investigation_owns_workflow_from_verification_and_preserves_signal_history(
    db_session: AsyncSession,
) -> None:
    first = await individual_signal(db_session, 303)
    second = await individual_signal(db_session, 304)
    transport = ASGITransport(app=app_for(db_session))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for signal in (first, second):
            response = await client.post(
                f"/v1/signals/{signal.id}/workflow/transitions",
                json={
                    "operation_key": f"triage-{signal.id}",
                    "expected_version": 0,
                    "target_state": "triage",
                },
            )
            assert response.status_code == 200
        created = await client.post(
            "/v1/investigations",
            json={
                "signal_id": str(first.id),
                "operation_key": f"create-{uuid4()}",
            },
        )
        file_id = created.json()["id"]
        added = await client.post(
            f"/v1/investigations/{file_id}/members/{second.id}",
            json={"operation_key": f"add-{uuid4()}", "expected_version": 1},
        )
        verification = await client.post(
            f"/v1/investigations/{file_id}/workflow/transitions",
            json={
                "operation_key": f"verify-{uuid4()}",
                "expected_version": 0,
                "target_state": "verification",
            },
        )
        first_history = await client.get(f"/v1/signals/{first.id}/audit-events")
        file_history = await client.get(f"/v1/investigations/{file_id}/audit-events")
        removed = await client.post(
            f"/v1/investigations/{file_id}/members/{second.id}/removals",
            json={
                "operation_key": f"remove-{uuid4()}",
                "expected_version": 2,
                "reason_code": "analyst-correction",
            },
        )
        removed_signal = await client.get(f"/v1/signals/{second.id}")
        risk = await client.post(
            f"/v1/investigations/{file_id}/workflow/transitions",
            json={
                "operation_key": f"risk-{uuid4()}",
                "expected_version": 1,
                "target_state": "risk_assessment",
            },
        )
        closed = await client.post(
            f"/v1/investigations/{file_id}/workflow/transitions",
            json={
                "operation_key": f"close-{uuid4()}",
                "expected_version": 2,
                "target_state": "closed",
                "reason_code": "resolved",
            },
        )

    assert created.status_code == 201
    assert added.status_code == 200
    assert verification.status_code == 200
    assert verification.json()["workflow"]["state"] == "verification"
    assert verification.json()["workflow"]["state_machine_version"] == "workflow-v2"
    assert [event["new_value"] for event in first_history.json()] == [{"state": "triage"}]
    assert file_history.json()[0]["previous_value"] == {"state": "triage"}
    assert file_history.json()[0]["new_value"] == {"state": "verification"}
    assert removed.status_code == 200
    assert removed_signal.json()["state"] == "triage"
    assert risk.json()["workflow"]["state"] == "risk_assessment"
    assert closed.json()["workflow"]["state"] == "closed"
    assert closed.json()["event"]["reason_code"] == "resolved"


@pytest.mark.integration
async def test_individual_workflow_rejects_stale_version_and_requires_closure_reason(
    db_session: AsyncSession,
) -> None:
    signal = await individual_signal(db_session, 305)
    transport = ASGITransport(app=app_for(db_session))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            f"/v1/signals/{signal.id}/workflow/transitions",
            json={
                "operation_key": f"triage-{uuid4()}",
                "expected_version": 0,
                "target_state": "triage",
            },
        )
        stale = await client.post(
            f"/v1/signals/{signal.id}/workflow/transitions",
            json={
                "operation_key": f"stale-{uuid4()}",
                "expected_version": 0,
                "target_state": "closed",
                "reason_code": "insufficient_evidence",
            },
        )
        missing_reason = await client.post(
            f"/v1/signals/{signal.id}/workflow/transitions",
            json={
                "operation_key": f"close-{uuid4()}",
                "expected_version": 1,
                "target_state": "closed",
            },
        )

    assert stale.status_code == 409
    assert stale.json()["detail"] == {
        "code": "workflow_version_conflict",
        "expected_version": 0,
        "current_version": 1,
    }
    assert missing_reason.status_code == 422
    assert missing_reason.json()["detail"]["code"] == "closure_reason_required"


@pytest.mark.integration
async def test_v2_metrics_count_signals_and_investigations_as_distinct_units(
    db_session: AsyncSession,
) -> None:
    await individual_signal(db_session, 306)
    transport = ASGITransport(app=app_for(db_session))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "workflow-metrics-v2"
    assert payload["signals"]["total"] >= 1
    assert payload["signals"]["by_state"]["detected"] >= 1
    assert payload["investigations"]["total"] == 0
    assert payload["investigations"]["members"] == 0


@pytest.mark.integration
async def test_transfer_between_active_investigations_is_atomic_and_idempotent(
    db_session: AsyncSession,
) -> None:
    signals = [await individual_signal(db_session, index) for index in (307, 308, 309)]
    transport = ASGITransport(app=app_for(db_session))

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for signal in signals:
            await client.post(
                f"/v1/signals/{signal.id}/workflow/transitions",
                json={
                    "operation_key": f"triage-{signal.id}",
                    "expected_version": 0,
                    "target_state": "triage",
                },
            )
        source = await client.post(
            "/v1/investigations",
            json={
                "signal_id": str(signals[0].id),
                "operation_key": f"source-{uuid4()}",
            },
        )
        destination = await client.post(
            "/v1/investigations",
            json={
                "signal_id": str(signals[2].id),
                "operation_key": f"destination-{uuid4()}",
            },
        )
        source_id = source.json()["id"]
        destination_id = destination.json()["id"]
        await client.post(
            f"/v1/investigations/{source_id}/members/{signals[1].id}",
            json={"operation_key": f"add-{uuid4()}", "expected_version": 1},
        )
        operation_key = f"transfer-{uuid4()}"
        payload = {
            "operation_key": operation_key,
            "destination_file_id": destination_id,
            "source_expected_version": 2,
            "destination_expected_version": 1,
            "reason_code": "analyst-correction",
        }
        transferred = await client.post(
            f"/v1/investigations/{source_id}/members/{signals[1].id}/transfers",
            json=payload,
        )
        replay = await client.post(
            f"/v1/investigations/{source_id}/members/{signals[1].id}/transfers",
            json=payload,
        )

    assert transferred.status_code == replay.status_code == 200
    assert transferred.json() == replay.json()
    assert transferred.json()["source"]["version"] == 3
    assert transferred.json()["destination"]["version"] == 2
    assert [item["signal"]["id"] for item in transferred.json()["source"]["members"]] == [
        str(signals[0].id)
    ]
    assert {
        item["signal"]["id"] for item in transferred.json()["destination"]["members"]
    } == {str(signals[1].id), str(signals[2].id)}
