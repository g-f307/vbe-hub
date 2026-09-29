from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProcessingRunModel(Base):
    __tablename__ = "processing_runs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed')",
            name="processing_runs_state_check",
        ),
        CheckConstraint(
            "received_count >= 0 AND processed_count >= 0 "
            "AND skipped_count >= 0 AND failed_count >= 0",
            name="processing_runs_counts_nonnegative_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    run_type: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    component_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    received_count: Mapped[int] = mapped_column(BigInteger, default=0)
    processed_count: Mapped[int] = mapped_column(BigInteger, default=0)
    skipped_count: Mapped[int] = mapped_column(BigInteger, default=0)
    failed_count: Mapped[int] = mapped_column(BigInteger, default=0)
    sanitized_error: Mapped[dict[str, str] | None] = mapped_column(JSONB)


class RawRecordModel(Base):
    __tablename__ = "raw_records"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('media', 'community')", name="raw_records_source_kind_check"
        ),
        CheckConstraint("char_length(content_hash) = 64", name="raw_records_content_hash_check"),
        Index(
            "raw_records_external_source_uidx",
            "source_kind",
            "source_name",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "raw_records_hash_source_uidx",
            "source_kind",
            "source_name",
            "content_hash",
            unique=True,
            postgresql_where=text("external_id IS NULL"),
        ),
        Index("raw_records_ingestion_run_id_idx", "ingestion_run_id"),
        Index("raw_records_published_at_idx", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    source_kind: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text)
    original_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(Text)
    ingestion_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("processing_runs.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProvenanceModel(Base):
    __tablename__ = "record_provenance"
    __table_args__ = (Index("record_provenance_scenario_id_idx", "scenario_id"),)

    raw_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("raw_records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    adapter_name: Mapped[str] = mapped_column(Text)
    adapter_version: Mapped[str] = mapped_column(Text)
    generator_name: Mapped[str | None] = mapped_column(Text)
    generator_version: Mapped[str | None] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(BigInteger)
    scenario_id: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NormalizedRecordModel(Base):
    __tablename__ = "normalized_records"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed')",
            name="normalized_records_state_check",
        ),
        Index("normalized_records_raw_record_id_idx", "raw_record_id"),
        Index(
            "normalized_records_record_version_uidx",
            "raw_record_id",
            "normalizer_version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    raw_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("raw_records.id", ondelete="CASCADE")
    )
    normalizer_version: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    error: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvaluationLabelModel(Base):
    __tablename__ = "evaluation_labels"

    raw_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("raw_records.id", ondelete="CASCADE"),
        primary_key=True,
    )
    gold_event_id: Mapped[str] = mapped_column(Text)


class TechnicalSheetExtractionModel(Base):
    __tablename__ = "technical_sheet_extractions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('succeeded', 'failed')",
            name="technical_sheet_extractions_state_check",
        ),
        CheckConstraint(
            "char_length(cache_key) = 64 AND char_length(input_hash) = 64",
            name="technical_sheet_extractions_hash_length_check",
        ),
        CheckConstraint(
            "duration_ms >= 0 AND (input_units IS NULL OR input_units >= 0) "
            "AND (output_units IS NULL OR output_units >= 0)",
            name="technical_sheet_extractions_usage_nonnegative_check",
        ),
        Index(
            "technical_sheet_extractions_cache_key_uidx",
            "cache_key",
            unique=True,
        ),
        Index(
            "technical_sheet_extractions_normalized_record_id_idx",
            "normalized_record_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    normalized_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="CASCADE"),
    )
    cache_key: Mapped[str] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    technical_sheet: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    evidence: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(BigInteger)
    input_units: Mapped[int | None] = mapped_column(BigInteger)
    output_units: Mapped[int | None] = mapped_column(BigInteger)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool | None] = mapped_column(Boolean)
    sanitized_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
