from datetime import UTC, datetime
from uuid import UUID

from vbe_hub.application.ai import (
    AIExecutionMetadata,
    EmbeddingRequest,
    EmbeddingResult,
    ExecutionStatus,
)
from vbe_hub.application.ai.embeddings import EmbeddingIndexService, EmbeddingRecord

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
RECORD_ID = UUID("00000000-0000-0000-0000-000000000010")


class Repository:
    def __init__(self) -> None:
        self.saved: list[EmbeddingRecord] = []

    async def save(self, record: EmbeddingRecord) -> None:
        self.saved.append(record)


class Provider:
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(
            request=request,
            vector=tuple([0.5] * request.expected_dimensions),
            dimensions=request.expected_dimensions,
            metadata=AIExecutionMetadata(
                provider="gemini",
                model="gemini-embedding-2",
                contract_version="embedding-text-v1",
                prompt_version=None,
                started_at=NOW,
                duration_ms=10,
                status=ExecutionStatus.SUCCEEDED,
            ),
        )


async def test_service_builds_and_persists_versioned_embedding() -> None:
    repository = Repository()
    service = EmbeddingIndexService(provider=Provider(), repository=repository, now=lambda: NOW)

    saved = await service.index(
        normalized_record_id=RECORD_ID,
        input_hash="a" * 64,
        technical_sheet={"disease_or_condition": "Sarampo", "location": {"municipality": "Manaus"}},
    )

    assert saved == repository.saved[0]
    assert saved.provider == "gemini"
    assert saved.model == "gemini-embedding-2"
    assert saved.representation_version == "embedding-text-v1"
    assert saved.dimensions == 768
    assert len(saved.embedding) == 768
