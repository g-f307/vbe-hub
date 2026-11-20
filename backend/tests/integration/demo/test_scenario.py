from collections import Counter

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.investigation_models import (
    IndividualSignalModel,
    SignalRelationSuggestionModel,
)
from vbe_hub.adapters.persistence.models import RawRecordModel, TechnicalSheetExtractionModel
from vbe_hub.api.app import create_app
from vbe_hub.api.signals import get_signal_read_session
from vbe_hub.synthetic import importer
from vbe_hub.synthetic.demo import load_individual_demo_batch


@pytest.mark.integration
async def test_demo_information_refresh_is_bounded_idempotent_and_preserves_sources(
    db_session: AsyncSession,
) -> None:
    from vbe_hub.synthetic.demo import refresh_demo_information

    await load_individual_demo_batch(db_session)
    rows = list(await db_session.scalars(select(RawRecordModel)))
    head = next(row for row in rows if row.external_id == "demo:dengue-compensa:media")
    untouched = rows[-1]
    untouched.original_payload = {"synthetic": False, "demo_scenario": "custom"}
    head.original_payload = {
        "synthetic": True, "demo_scenario": "dengue-compensa", "preserved": "yes",
        "signal_information": {"confidentiality": "Nível 2"},
    }
    # Simulate old demo rows, without operational metadata.
    for row in rows:
        if row not in (head, untouched):
            row.original_payload = {
                key: value for key, value in row.original_payload.items()
                if key != "signal_information"
            }
    await db_session.flush()
    before = [(row.id, row.body, row.title, row.content_hash, row.updated_at) for row in rows]

    result = await refresh_demo_information(db_session)
    repeated = await refresh_demo_information(db_session)

    assert result == {"matched": 39, "updated": 39}
    assert repeated == {"matched": 39, "updated": 0}
    assert before == [
        (row.id, row.body, row.title, row.content_hash, row.updated_at) for row in rows
    ]
    assert untouched.original_payload == {"synthetic": False, "demo_scenario": "custom"}
    assert head.original_payload["preserved"] == "yes"
    info = head.original_payload["signal_information"]
    assert info["confidentiality"] == "Nível 2"
    assert info["etiology"] == "Dengue (suspeita)"
    assert info["hazard_general"] == "Arbovirose"
    assert info["hazard_specific"] == "Dengue"
    assert info["signal_type"] == "Abertura"
    assert "dengue" in info["tags"]
    assert info["signal_date"] == "2026-10-10T08:00:00+00:00"
    assert info["notified_at"] == "2026-10-10T08:30:00+00:00"


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


@pytest.mark.integration
async def test_individual_demo_batch_leaves_titled_signals_pending_for_live_ai_processing(
    db_session: AsyncSession,
) -> None:
    result = await load_individual_demo_batch(db_session)
    await db_session.commit()

    community_titles = (
        await db_session.scalars(
            select(RawRecordModel.title).where(
                RawRecordModel.source_kind == "community",
                RawRecordModel.external_id.not_like("%:community"),
            )
        )
    ).all()
    suggestions = list(
        await db_session.scalars(
            select(SignalRelationSuggestionModel).where(
                SignalRelationSuggestionModel.left_signal_id.in_(result.signal_ids),
                SignalRelationSuggestionModel.right_signal_id.in_(result.signal_ids),
            )
        )
    )
    technical_sheets = list(
        await db_session.scalars(
            select(TechnicalSheetExtractionModel)
            .join(
                IndividualSignalModel,
                IndividualSignalModel.normalized_record_id
                == TechnicalSheetExtractionModel.normalized_record_id,
            )
            .where(IndividualSignalModel.id.in_(result.signal_ids))
        )
    )

    assert len(result.signal_ids) == 40
    assert len(community_titles) == 30
    assert all(title and title.strip() for title in community_titles)
    assert suggestions == []
    assert technical_sheets == []
    raw_records = list(await db_session.scalars(select(RawRecordModel)))
    for record in raw_records:
        information = record.original_payload["signal_information"]
        assert information["confidentiality"] == "Nível 1"
        assert information["signal_type"] == "Abertura"
        assert information["etiology"].endswith("(suspeita)")
        assert information["hazard_general"]
        assert information["hazard_specific"]
        assert information["tags"]
        assert information["signal_date"]
        assert information["notified_at"]
