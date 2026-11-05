from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

DemoScenario = Literal[
    "related",
    "incompatible",
    "ambiguous",
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
]
DemoMode = Literal["online", "offline"]


class DemoRunRequest(BaseModel):
    mode: DemoMode


class DemoSourceResponse(BaseModel):
    source_kind: Literal["media", "community"]
    external_id: str


class DemoRunResponse(BaseModel):
    scenario: DemoScenario
    mode: DemoMode
    relation: str
    relation_explanation: str
    signal_ids: list[UUID]
    created: dict[str, int]
    sources: list[DemoSourceResponse]
    review_notice: str


class DemoRunService(Protocol):
    async def run(self, *, scenario: str, mode: str) -> Mapping[str, Any]: ...


async def get_demo_service() -> DemoRunService:
    from vbe_hub.synthetic.n8n_demo import build_demo_service

    return build_demo_service()


DemoServiceDependency = Annotated[DemoRunService, Depends(get_demo_service)]
router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/scenarios/{scenario}/runs", response_model=DemoRunResponse)
async def run_demo_scenario(
    scenario: DemoScenario,
    request: DemoRunRequest,
    service: DemoServiceDependency,
) -> Mapping[str, Any]:
    return await service.run(scenario=scenario, mode=request.mode)
