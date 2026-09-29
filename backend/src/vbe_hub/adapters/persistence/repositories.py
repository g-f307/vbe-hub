from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vbe_hub.adapters.persistence.models import (
    EvaluationLabelModel,
    NormalizedRecordModel,
    ProvenanceModel,
    RawRecordModel,
)
from vbe_hub.application.repositories import IngestResult, StoredRawRecord
from vbe_hub.domain.records import (
    EvaluationLabel,
    NormalizationStatus,
    NormalizedRecord,
    ProcessingState,
    Provenance,
    RawRecord,
    SourceKind,
)


class DuplicateExternalRecordError(ValueError):
    pass


class SqlAlchemyRawRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RawRecord, provenance: Provenance) -> IngestResult:
        existing = await self._find_duplicate(record)
        if existing is not None:
            if existing.content_hash != record.content_hash:
                raise DuplicateExternalRecordError(
                    f"external identifier {record.external_id!r} already has different content"
                )
            return IngestResult(record=self._to_domain(existing), created=False)

        raw_model = RawRecordModel(
            id=record.id,
            source_kind=record.source_kind.value,
            source_name=record.source_name,
            external_id=record.external_id,
            published_at=record.published_at,
            title=record.title,
            body=record.body,
            source_url=record.source_url,
            language=record.language,
            original_payload=record.original_payload,
            content_hash=record.content_hash,
            ingestion_run_id=provenance.ingestion_run_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self._session.add(raw_model)
        await self._session.flush()
        self._session.add(
            ProvenanceModel(
                raw_record_id=record.id,
                adapter_name=provenance.adapter_name,
                adapter_version=provenance.adapter_version,
                generator_name=provenance.generator_name,
                generator_version=provenance.generator_version,
                seed=provenance.seed,
                scenario_id=provenance.scenario_id,
                collected_at=provenance.collected_at,
            )
        )
        await self._session.flush()
        return IngestResult(record=record, created=True)

    async def get(self, record_id: UUID) -> StoredRawRecord | None:
        row = await self._session.get(RawRecordModel, record_id)
        if row is None:
            return None
        provenance = await self._session.get(ProvenanceModel, record_id)
        if provenance is None:
            raise RuntimeError(f"record {record_id} has no provenance")
        return StoredRawRecord(
            record=self._to_domain(row),
            provenance=Provenance(
                adapter_name=provenance.adapter_name,
                adapter_version=provenance.adapter_version,
                generator_name=provenance.generator_name,
                generator_version=provenance.generator_version,
                seed=provenance.seed,
                scenario_id=provenance.scenario_id,
                ingestion_run_id=row.ingestion_run_id,
                collected_at=provenance.collected_at,
            ),
        )

    async def save_normalized(self, record: NormalizedRecord) -> None:
        self._session.add(
            NormalizedRecordModel(
                id=record.id,
                raw_record_id=record.raw_record_id,
                normalizer_version=record.normalizer_version,
                state=record.status.state.value,
                normalized_data=record.normalized_data,
                error=record.status.error,
                retryable=record.status.retryable,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
        await self._session.flush()

    async def get_normalized(
        self, raw_record_id: UUID, normalizer_version: str
    ) -> NormalizedRecord | None:
        query = select(NormalizedRecordModel).where(
            NormalizedRecordModel.raw_record_id == raw_record_id,
            NormalizedRecordModel.normalizer_version == normalizer_version,
        )
        row = await self._session.scalar(query)
        if row is None:
            return None
        return NormalizedRecord(
            id=row.id,
            raw_record_id=row.raw_record_id,
            normalizer_version=row.normalizer_version,
            status=NormalizationStatus(
                state=ProcessingState(row.state), error=row.error, retryable=row.retryable
            ),
            normalized_data=row.normalized_data,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _find_duplicate(self, record: RawRecord) -> RawRecordModel | None:
        query = select(RawRecordModel).where(
            RawRecordModel.source_kind == record.source_kind.value,
            RawRecordModel.source_name == record.source_name,
        )
        if record.external_id is not None:
            query = query.where(RawRecordModel.external_id == record.external_id)
        else:
            query = query.where(
                RawRecordModel.external_id.is_(None),
                RawRecordModel.content_hash == record.content_hash,
            )
        return await self._session.scalar(query)

    @staticmethod
    def _to_domain(row: RawRecordModel) -> RawRecord:
        return RawRecord(
            id=row.id,
            source_kind=SourceKind(row.source_kind),
            source_name=row.source_name,
            external_id=row.external_id,
            published_at=row.published_at,
            title=row.title,
            body=row.body,
            source_url=row.source_url,
            language=row.language,
            original_payload=row.original_payload,
            content_hash=row.content_hash,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SqlAlchemyEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, label: EvaluationLabel) -> None:
        self._session.add(
            EvaluationLabelModel(
                raw_record_id=label.raw_record_id,
                gold_event_id=label.gold_event_id,
            )
        )
        await self._session.flush()

    async def get(self, raw_record_id: UUID) -> EvaluationLabel | None:
        row = await self._session.get(EvaluationLabelModel, raw_record_id)
        if row is None:
            return None
        return EvaluationLabel(raw_record_id=row.raw_record_id, gold_event_id=row.gold_event_id)
