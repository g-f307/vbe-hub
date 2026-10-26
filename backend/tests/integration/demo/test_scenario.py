from collections import Counter

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.api.app import create_app
from vbe_hub.api.signals import get_signal_read_session
from vbe_hub.synthetic import importer


@pytest.mark.integration
async def test_demo_scenario_materializes_reproducible_signals_for_the_panel(
    db_session: AsyncSession,
) -> None:
    first = await importer.load_demo_scenario(db_session)
    await db_session.commit()

    assert first.created == {
        "raw_records": 6,
        "normalized_records": 6,
        "technical_sheets": 6,
        "relations": 3,
        "signals": 3,
        "priorities": 3,
        "workflow_events": 3,
    }

    second = await importer.load_demo_scenario(db_session)
    await db_session.commit()

    assert second.created == {key: 0 for key in first.created}

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        queue = await client.get("/signals?page_size=10")
        first_detail = await client.get(f"/signals/{first.signal_ids[0]}")

    assert queue.status_code == 200
    items = queue.json()["items"]
    assert queue.json()["total"] == 3
    assert Counter(item["workflow"]["state"] for item in items) == {
        "detected": 1,
        "triage": 1,
        "verification": 1,
    }
    assert all(item["priority"] is not None for item in items)

    assert first_detail.status_code == 200
    detail = first_detail.json()
    assert {source["source_kind"] for source in detail["sources"]} == {"media", "community"}
    assert all(source["technical_sheet"] is not None for source in detail["sources"])
    assert detail["relations"]
