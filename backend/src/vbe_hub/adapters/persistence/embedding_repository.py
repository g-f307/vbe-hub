from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.embedding_models import EmbeddingModel
from vbe_hub.application.ai.embeddings import EmbeddingNeighbor, EmbeddingRecord


class SqlAlchemyEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: EmbeddingRecord) -> None:
        values = {
            "id": record.id,
            "normalized_record_id": record.normalized_record_id,
            "input_hash": record.input_hash,
            "provider": record.provider,
            "model": record.model,
            "representation_version": record.representation_version,
            "dimensions": record.dimensions,
            "embedding": list(record.embedding),
            "created_at": record.created_at,
        }
        statement = (
            insert(EmbeddingModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    "normalized_record_id",
                    "provider",
                    "model",
                    "representation_version",
                    "dimensions",
                ],
                set_=values,
            )
        )
        await self._session.execute(statement)
        await self._session.flush()

    async def get(
        self,
        *,
        normalized_record_id: UUID,
        provider: str,
        model: str,
        representation_version: str,
        dimensions: int,
    ) -> EmbeddingRecord | None:
        query = select(EmbeddingModel).where(
            EmbeddingModel.normalized_record_id == normalized_record_id,
            EmbeddingModel.provider == provider,
            EmbeddingModel.model == model,
            EmbeddingModel.representation_version == representation_version,
            EmbeddingModel.dimensions == dimensions,
        )
        row = await self._session.scalar(query)
        return None if row is None else self._to_record(row)

    async def nearest(
        self,
        *,
        query: tuple[float, ...],
        exclude_normalized_record_id: UUID,
        provider: str,
        model: str,
        representation_version: str,
        dimensions: int,
        limit: int,
    ) -> list[EmbeddingNeighbor]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        distance = EmbeddingModel.embedding.cosine_distance(list(query))
        statement = (
            select(EmbeddingModel.normalized_record_id, distance.label("distance"))
            .where(
                EmbeddingModel.normalized_record_id != exclude_normalized_record_id,
                EmbeddingModel.provider == provider,
                EmbeddingModel.model == model,
                EmbeddingModel.representation_version == representation_version,
                EmbeddingModel.dimensions == dimensions,
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            EmbeddingNeighbor(normalized_record_id=row.normalized_record_id, score=1 - row.distance)
            for row in rows
        ]

    @staticmethod
    def _to_record(row: EmbeddingModel) -> EmbeddingRecord:
        return EmbeddingRecord(
            id=row.id,
            normalized_record_id=row.normalized_record_id,
            input_hash=row.input_hash,
            provider=row.provider,
            model=row.model,
            representation_version=row.representation_version,
            dimensions=row.dimensions,
            embedding=tuple(row.embedding),
            created_at=row.created_at,
        )
