import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import NormalizedRecordModel, ProvenanceModel
from vbe_hub.api.app import create_app
from vbe_hub.api.signals import get_signal_read_session
from vbe_hub.synthetic.demo import load_demo_scenario


@pytest.mark.integration
async def test_metrics_summary_distinguishes_empty_persistence_from_unavailable_measurements(
    db_session: AsyncSession,
) -> None:
    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "metrics-summary-v1"
    assert payload["classification"] == "technical_operational"
    assert payload["dataset"] == {
        "kind": "synthetic",
        "status": "unavailable",
        "sources": [],
    }
    assert payload["window"] == {
        "start": None,
        "end": None,
        "latest_activity_at": None,
        "lag_seconds": None,
        "freshness": "unavailable",
    }
    assert payload["pipeline"]["raw_records"] == {
        "value": 0,
        "status": "empty",
        "origin": "raw_records",
    }
    assert payload["pipeline"]["failed_extractions"]["value"] == 0
    assert payload["pipeline"]["pending_human_review"]["value"] == 0
    assert payload["durations"] == {
        "technical_sheet_extraction": {
            "status": "unavailable",
            "samples": 0,
            "average_ms": None,
            "maximum_ms": None,
        },
        "relation_assessment": {
            "status": "unavailable",
            "samples": 0,
            "average_ms": None,
            "maximum_ms": None,
        },
    }
    assert payload["latest_run"] == {"status": "unavailable", "run": None}
    assert payload["reconciliation"] == [
        {
            "key": "normalization_coverage",
            "status": "unavailable",
            "expected": 0,
            "observed": 0,
            "difference": 0,
        },
        {
            "key": "extraction_coverage",
            "status": "unavailable",
            "expected": 0,
            "observed": 0,
            "difference": 0,
        },
        {
            "key": "priority_coverage",
            "status": "unavailable",
            "expected": 0,
            "observed": 0,
            "difference": 0,
        },
    ]
    assert {item["identity"] for item in payload["evaluations"]} == {
        "3260ec0dc1945093",
        "ce77f037927356db",
        "a23f1eb5c9300765",
    }
    assert all(item["classification"] == "synthetic_evaluation" for item in payload["evaluations"])
    assert all("gold" not in item for item in payload["evaluations"])
    assert "diagnóstico" in payload["interpretation"]


@pytest.mark.integration
async def test_metrics_summary_reconciles_the_canonical_demo_with_its_persisted_origins(
    db_session: AsyncSession,
) -> None:
    await load_demo_scenario(db_session)
    await db_session.commit()

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"] == {
        "kind": "synthetic",
        "status": "single",
        "sources": [
            {
                "generator": "vbe-hub-demo",
                "version": "1.0.0",
                "seed": 54,
                "records": 6,
            }
        ],
    }
    assert {key: item["value"] for key, item in payload["pipeline"].items()} == {
        "raw_records": 6,
        "normalized_records": 6,
        "failed_normalizations": 0,
        "technical_sheets": 6,
        "failed_extractions": 0,
        "assessed_pairs": 3,
        "failed_relations": 0,
        "signals": 3,
        "priorities": 3,
        "human_reviews": 3,
        "pending_human_review": 3,
    }
    assert all(item["status"] == "available" for item in payload["pipeline"].values())
    assert payload["window"]["start"] == "2026-08-01T10:00:00Z"
    assert payload["window"]["end"] == "2026-10-10T08:00:00Z"
    assert payload["window"]["freshness"] in {"current", "stale"}
    assert payload["window"]["lag_seconds"] >= 0
    assert payload["durations"] == {
        "technical_sheet_extraction": {
            "status": "available",
            "samples": 6,
            "average_ms": 0,
            "maximum_ms": 0,
        },
        "relation_assessment": {
            "status": "available",
            "samples": 3,
            "average_ms": 0,
            "maximum_ms": 0,
        },
    }
    assert payload["reconciliation"] == [
        {
            "key": "normalization_coverage",
            "status": "balanced",
            "expected": 6,
            "observed": 6,
            "difference": 0,
        },
        {
            "key": "extraction_coverage",
            "status": "balanced",
            "expected": 6,
            "observed": 6,
            "difference": 0,
        },
        {
            "key": "priority_coverage",
            "status": "balanced",
            "expected": 3,
            "observed": 3,
            "difference": 0,
        },
    ]
    relation_evaluation = next(
        item for item in payload["evaluations"] if item["identity"] == "ce77f037927356db"
    )
    assert relation_evaluation == {
        "identity": "ce77f037927356db",
        "classification": "synthetic_evaluation",
        "kind": "relation",
        "dataset_version": "relation-evaluation-v3",
        "evaluated_on": "2026-09-30",
        "status": "approve_with_caveats",
        "evidence_level": "exploratory",
        "artifact": "docs/correlation-evaluation.md",
        "metrics": {
            "candidate_recall": 1.0,
            "pair_reduction": 0.804,
            "macro_f1": 1.0,
            "operational_failure_rate": 0.0,
            "provider_calls": 44,
            "estimated_cost_usd": None,
        },
        "limitation": "small synthetic sample; limited statistical generalization",
        "scope": "technical synthetic validation; no clinical or epidemiological validity",
    }
    serialized = response.text.casefold()
    assert "gold_event" not in serialized
    assert "record_id" not in serialized
    assert "gemini_api_key" not in serialized


@pytest.mark.integration
async def test_metrics_summary_keeps_partial_failures_and_mixed_datasets_visible(
    db_session: AsyncSession,
) -> None:
    await load_demo_scenario(db_session)
    normalized = await db_session.scalar(
        select(NormalizedRecordModel).order_by(NormalizedRecordModel.id).limit(1)
    )
    provenance = await db_session.scalar(
        select(ProvenanceModel).order_by(ProvenanceModel.raw_record_id).limit(1)
    )
    assert normalized is not None
    assert provenance is not None
    normalized.state = "failed"
    normalized.error = {"code": "synthetic_test_failure"}
    provenance.seed = 55
    await db_session.commit()

    async def session_override():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_signal_read_session] = session_override
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["operational_status"] == "partial_failure"
    assert payload["dataset"]["status"] == "mixed"
    assert {item["seed"] for item in payload["dataset"]["sources"]} == {54, 55}
    assert payload["pipeline"]["failed_normalizations"] == {
        "value": 1,
        "status": "available",
        "origin": "normalized_records.state=failed",
    }
    assert payload["reconciliation"][0] == {
        "key": "normalization_coverage",
        "status": "gap",
        "expected": 6,
        "observed": 5,
        "difference": -1,
    }
