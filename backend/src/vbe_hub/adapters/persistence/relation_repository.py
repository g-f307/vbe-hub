from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.relation_models import RelationAssessmentModel
from vbe_hub.application.ai import (
    AIExecutionMetadata,
    ExecutionStatus,
    ProviderErrorCode,
    RelationKind,
)
from vbe_hub.application.correlation.relations import RelationAssessmentRecord, RelationMethod


class SqlAlchemyRelationAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, cache_key: str) -> RelationAssessmentRecord | None:
        row = await self._session.scalar(
            select(RelationAssessmentModel).where(RelationAssessmentModel.cache_key == cache_key)
        )
        return None if row is None else self._to_record(row)

    async def save(self, record: RelationAssessmentRecord) -> None:
        m = record.metadata
        values = dict(
            id=record.id,
            cache_key=record.cache_key,
            left_id=record.left_id,
            right_id=record.right_id,
            relation=record.relation.value if record.relation else None,
            method=record.method.value,
            confidence=record.confidence,
            justification=record.justification,
            updating_record_id=record.updating_record_id,
            rules_version=record.rules_version,
            provider=m.provider,
            model=m.model,
            contract_version=m.contract_version,
            prompt_version=m.prompt_version,
            state=m.status.value,
            started_at=m.started_at,
            duration_ms=m.duration_ms,
            input_units=m.input_units,
            output_units=m.output_units,
            cache_hit=m.cache_hit,
            error_code=m.error_code.value if m.error_code else None,
            retryable=m.retryable,
            sanitized_error=record.sanitized_error,
            created_at=record.created_at,
        )
        statement = (
            insert(RelationAssessmentModel)
            .values(**values)
            .on_conflict_do_update(index_elements=["cache_key"], set_=values)
        )
        await self._session.execute(statement)
        await self._session.flush()

    @staticmethod
    def _to_record(row: RelationAssessmentModel) -> RelationAssessmentRecord:
        return RelationAssessmentRecord(
            id=row.id,
            cache_key=row.cache_key,
            left_id=row.left_id,
            right_id=row.right_id,
            relation=RelationKind(row.relation) if row.relation else None,
            method=RelationMethod(row.method),
            confidence=row.confidence,
            justification=row.justification,
            updating_record_id=row.updating_record_id,
            rules_version=row.rules_version,
            metadata=AIExecutionMetadata(
                provider=row.provider,
                model=row.model,
                contract_version=row.contract_version,
                prompt_version=row.prompt_version,
                started_at=row.started_at,
                duration_ms=row.duration_ms,
                status=ExecutionStatus(row.state),
                input_units=row.input_units,
                output_units=row.output_units,
                cache_hit=row.cache_hit,
                error_code=ProviderErrorCode(row.error_code) if row.error_code else None,
                retryable=row.retryable,
            ),
            sanitized_error=row.sanitized_error,
            created_at=row.created_at,
        )
