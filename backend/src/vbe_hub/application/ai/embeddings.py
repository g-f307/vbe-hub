from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from vbe_hub.application.ai.contracts import EmbeddingProvider, EmbeddingRequest

REPRESENTATION_VERSION = "embedding-text-v1"
EMBEDDING_DIMENSIONS = 768


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    id: UUID
    normalized_record_id: UUID
    input_hash: str
    provider: str
    model: str
    representation_version: str
    dimensions: int
    embedding: Sequence[float]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EmbeddingNeighbor:
    normalized_record_id: UUID
    score: float


class EmbeddingRepository(Protocol):
    async def save(self, record: EmbeddingRecord) -> None: ...


class EmbeddingIndexService:
    def __init__(
        self,
        *,
        provider: EmbeddingProvider,
        repository: EmbeddingRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._now = now

    async def index(
        self, *, normalized_record_id: UUID, input_hash: str, technical_sheet: Mapping[str, Any]
    ) -> EmbeddingRecord:
        result = await self._provider.embed(
            EmbeddingRequest(
                stable_id=normalized_record_id,
                input_hash=input_hash,
                text=build_embedding_text(technical_sheet),
                expected_dimensions=EMBEDDING_DIMENSIONS,
            )
        )
        record = EmbeddingRecord(
            id=uuid4(),
            normalized_record_id=normalized_record_id,
            input_hash=input_hash,
            provider=result.metadata.provider,
            model=result.metadata.model,
            representation_version=REPRESENTATION_VERSION,
            dimensions=result.dimensions,
            embedding=result.vector,
            created_at=self._now(),
        )
        await self._repository.save(record)
        return record


def build_embedding_text(sheet: Mapping[str, Any]) -> str:
    temporal = sheet.get("temporal") if isinstance(sheet.get("temporal"), Mapping) else {}
    location = sheet.get("location") if isinstance(sheet.get("location"), Mapping) else {}
    symptoms = sheet.get("symptoms")
    values = (
        ("doenca_agravo", sheet.get("disease_or_condition")),
        ("patogeno", sheet.get("pathogen")),
        ("sindrome", sheet.get("syndrome")),
        ("sintomas", "; ".join(symptoms) if isinstance(symptoms, list) and symptoms else None),
        ("casos_estimados", sheet.get("estimated_cases")),
        ("obitos_estimados", sheet.get("estimated_deaths")),
        ("grupo_afetado", sheet.get("affected_group")),
        ("ambiente", sheet.get("environment")),
        ("inicio_evento", temporal.get("start")),
        ("fim_evento", temporal.get("end")),
        ("pais", location.get("country")),
        ("estado", location.get("state")),
        ("municipio", location.get("municipality")),
        ("bairro_distrito", location.get("district")),
        ("local_especifico", location.get("specific")),
    )
    lines = [f"{label}: {value}" for label, value in values if value is not None and value != ""]
    if not lines:
        raise ValueError("technical sheet has no semantic content to embed")
    return "\n".join(lines)
