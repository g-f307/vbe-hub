from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.embedding_repository import SqlAlchemyEmbeddingRepository
from vbe_hub.adapters.persistence.repositories import SqlAlchemyRawRecordRepository
from vbe_hub.application.ai.embeddings import EmbeddingRecord
from vbe_hub.domain.records import (
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
DIMENSIONS = 768


async def normalized(session: AsyncSession, suffix: str) -> NormalizedRecord:
    raw = RawRecord.create(
        source_kind=SourceKind.MEDIA,
        source_name="synthetic-media",
        external_id=f"embedding-{suffix}-{uuid4()}",
        published_at=NOW,
        title="Sinal sintético",
        body="Texto sintético sem dados pessoais.",
        source_url=None,
        language="pt-BR",
        original_payload={"synthetic": True},
    )
    raw_repository = SqlAlchemyRawRecordRepository(session)
    await raw_repository.add(
        raw, Provenance(adapter_name="synthetic", adapter_version="1", collected_at=NOW)
    )
    item = NormalizedRecord(
        id=uuid4(),
        raw_record_id=raw.id,
        normalizer_version="1.0.0",
        status=NormalizationStatus(state=ProcessingState.SUCCEEDED),
        normalized_data={"text": raw.body},
    )
    await raw_repository.save_normalized(item)
    return item


def vector(first: float, second: float = 0.0) -> tuple[float, ...]:
    return (first, second, *([0.0] * (DIMENSIONS - 2)))


def record(normalized_id, embedding, *, model="gemini-embedding-2") -> EmbeddingRecord:
    return EmbeddingRecord(
        id=uuid4(),
        normalized_record_id=normalized_id,
        input_hash="a" * 64,
        provider="gemini",
        model=model,
        representation_version="embedding-text-v1",
        dimensions=DIMENSIONS,
        embedding=embedding,
        created_at=NOW,
    )


@pytest.mark.integration
async def test_search_orders_compatible_vectors_by_cosine_similarity(
    db_session: AsyncSession,
) -> None:
    query_item = await normalized(db_session, "query")
    close_item = await normalized(db_session, "close")
    far_item = await normalized(db_session, "far")
    incompatible_item = await normalized(db_session, "old")
    repository = SqlAlchemyEmbeddingRepository(db_session)
    for item in (
        record(query_item.id, vector(1.0)),
        record(close_item.id, vector(0.9, 0.1)),
        record(far_item.id, vector(0.0, 1.0)),
        record(incompatible_item.id, vector(1.0), model="old-model"),
    ):
        await repository.save(item)
    await db_session.commit()

    neighbors = await repository.nearest(
        query=vector(1.0),
        exclude_normalized_record_id=query_item.id,
        provider="gemini",
        model="gemini-embedding-2",
        representation_version="embedding-text-v1",
        dimensions=DIMENSIONS,
        limit=5,
    )

    assert [item.normalized_record_id for item in neighbors] == [close_item.id, far_item.id]
    assert neighbors[0].score > neighbors[1].score


@pytest.mark.integration
async def test_reprocessing_same_version_updates_without_duplicate(
    db_session: AsyncSession,
) -> None:
    item = await normalized(db_session, "upsert")
    repository = SqlAlchemyEmbeddingRepository(db_session)

    await repository.save(record(item.id, vector(1.0)))
    await repository.save(record(item.id, vector(0.0, 1.0)))
    await db_session.commit()

    stored = await repository.get(
        normalized_record_id=item.id,
        provider="gemini",
        model="gemini-embedding-2",
        representation_version="embedding-text-v1",
        dimensions=DIMENSIONS,
    )
    assert stored is not None
    assert tuple(stored.embedding[:2]) == (0.0, 1.0)
