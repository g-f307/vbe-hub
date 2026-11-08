from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from vbe_hub.api.app import create_app


@dataclass
class StubDemoService:
    calls: list[tuple[str, str]]

    async def run(self, *, scenario: str, mode: str):
        self.calls.append((scenario, mode))
        return {
            "scenario": scenario,
            "mode": mode,
            "relation": "corroborates",
            "relation_explanation": "Fontes sintéticas complementares.",
            "signal_ids": [
                UUID("10000000-0000-0000-0000-000000000001"),
                UUID("10000000-0000-0000-0000-000000000002"),
            ],
            "created": {"raw_records": 2, "individual_signals": 2},
            "sources": [
                {"source_kind": "media", "external_id": "demo:related:media"},
                {"source_kind": "community", "external_id": "demo:related:community"},
            ],
            "evidence_mode": "recorded_fixture",
            "association_status": "unassociated",
            "review_notice": "Sugestão de IA; requer revisão humana.",
        }


def test_demo_run_accepts_only_named_synthetic_scenarios() -> None:
    service = StubDemoService(calls=[])
    client = TestClient(create_app(demo_service=service))

    response = client.post("/demo/scenarios/related/runs", json={"mode": "offline"})

    assert response.status_code == 200
    assert service.calls == [("related", "offline")]
    assert response.json() == {
        "scenario": "related",
        "mode": "offline",
        "relation": "corroborates",
        "relation_explanation": "Fontes sintéticas complementares.",
        "signal_ids": [
            "10000000-0000-0000-0000-000000000001",
            "10000000-0000-0000-0000-000000000002",
        ],
        "created": {"raw_records": 2, "individual_signals": 2},
        "sources": [
            {"source_kind": "media", "external_id": "demo:related:media"},
            {"source_kind": "community", "external_id": "demo:related:community"},
        ],
        "evidence_mode": "recorded_fixture",
        "association_status": "unassociated",
        "review_notice": "Sugestão de IA; requer revisão humana.",
    }


def test_demo_run_rejects_unknown_scenario_and_mode_before_service_call() -> None:
    service = StubDemoService(calls=[])
    client = TestClient(create_app(demo_service=service))

    scenario = client.post("/demo/scenarios/arbitrary/runs", json={"mode": "offline"})
    mode = client.post("/demo/scenarios/related/runs", json={"mode": "unbounded"})

    assert scenario.status_code == 422
    assert mode.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    "case_id",
    [
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
    ],
)
def test_demo_run_accepts_each_allowlisted_batch_case(case_id: str) -> None:
    service = StubDemoService(calls=[])
    client = TestClient(create_app(demo_service=service))

    response = client.post(f"/demo/scenarios/{case_id}/runs", json={"mode": "offline"})

    assert response.status_code == 200
    assert service.calls == [(case_id, "offline")]
