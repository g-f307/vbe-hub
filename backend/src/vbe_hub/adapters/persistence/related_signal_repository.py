from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.embedding_repository import SqlAlchemyEmbeddingRepository
from vbe_hub.adapters.persistence.investigation_models import IndividualSignalModel
from vbe_hub.adapters.persistence.models import TechnicalSheetExtractionModel
from vbe_hub.application.ai import ExecutionStatus
from vbe_hub.application.ai.embeddings import EMBEDDING_DIMENSIONS, REPRESENTATION_VERSION
from vbe_hub.application.correlation.precompute import PreparedSignal


class SqlAlchemyPreparedSignalSource:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding_model: str,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self._session = session
        self._embedding_model = embedding_model
        self._dimensions = dimensions
        self._embeddings = SqlAlchemyEmbeddingRepository(session)

    async def anchor(self, signal_id: UUID) -> PreparedSignal | None:
        row = (
            await self._session.execute(
                select(
                    IndividualSignalModel.id,
                    IndividualSignalModel.normalized_record_id,
                    TechnicalSheetExtractionModel.technical_sheet,
                )
                .join(
                    TechnicalSheetExtractionModel,
                    TechnicalSheetExtractionModel.normalized_record_id
                    == IndividualSignalModel.normalized_record_id,
                )
                .where(
                    IndividualSignalModel.id == signal_id,
                    TechnicalSheetExtractionModel.state == ExecutionStatus.SUCCEEDED.value,
                    TechnicalSheetExtractionModel.technical_sheet.is_not(None),
                )
                .order_by(TechnicalSheetExtractionModel.created_at.desc())
                .limit(1)
            )
        ).one_or_none()
        if row is None:
            return None
        return PreparedSignal(row.id, row.normalized_record_id, row.technical_sheet, 1.0)

    async def nearest(
        self, anchor: PreparedSignal, limit: int
    ) -> list[PreparedSignal]:
        embedding = await self._embeddings.get(
            normalized_record_id=anchor.normalized_record_id,
            provider="openai",
            model=self._embedding_model,
            representation_version=REPRESENTATION_VERSION,
            dimensions=self._dimensions,
        )
        if embedding is None:
            return []
        neighbors = await self._embeddings.nearest(
            query=tuple(embedding.embedding),
            exclude_normalized_record_id=anchor.normalized_record_id,
            provider="openai",
            model=self._embedding_model,
            representation_version=REPRESENTATION_VERSION,
            dimensions=self._dimensions,
            limit=limit,
        )
        if not neighbors:
            return []
        scores = {item.normalized_record_id: item.score for item in neighbors}
        rows = (
            await self._session.execute(
                select(
                    IndividualSignalModel.id,
                    IndividualSignalModel.normalized_record_id,
                    TechnicalSheetExtractionModel.technical_sheet,
                    TechnicalSheetExtractionModel.created_at,
                )
                .join(
                    TechnicalSheetExtractionModel,
                    TechnicalSheetExtractionModel.normalized_record_id
                    == IndividualSignalModel.normalized_record_id,
                )
                .where(
                    IndividualSignalModel.normalized_record_id.in_(scores),
                    TechnicalSheetExtractionModel.state == ExecutionStatus.SUCCEEDED.value,
                    TechnicalSheetExtractionModel.technical_sheet.is_not(None),
                )
                .order_by(
                    IndividualSignalModel.normalized_record_id,
                    TechnicalSheetExtractionModel.created_at.desc(),
                )
            )
        ).all()
        latest = {}
        for row in rows:
            latest.setdefault(row.normalized_record_id, row)
        return [
            PreparedSignal(
                latest[item.normalized_record_id].id,
                item.normalized_record_id,
                latest[item.normalized_record_id].technical_sheet,
                item.score,
            )
            for item in neighbors
            if item.normalized_record_id in latest
        ]
