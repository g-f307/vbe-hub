from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class RelationAssessmentModel(Base):
    __tablename__ = "relation_assessments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('succeeded', 'failed')", name="relation_assessments_state_check"
        ),
        CheckConstraint("method IN ('rule', 'provider')", name="relation_assessments_method_check"),
        CheckConstraint(
            "relation IS NULL OR relation IN ('duplicate','corroborates','updates',"
            "'related_context','unrelated')",
            name="relation_assessments_relation_check",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="relation_assessments_confidence_check",
        ),
        Index("relation_assessments_cache_key_uidx", "cache_key", unique=True),
        Index("relation_assessments_pair_idx", "left_id", "right_id"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    cache_key: Mapped[str] = mapped_column(Text)
    left_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("normalized_records.id", ondelete="CASCADE")
    )
    right_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("normalized_records.id", ondelete="CASCADE")
    )
    relation: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None]
    justification: Mapped[str | None] = mapped_column(Text)
    updating_record_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("normalized_records.id", ondelete="CASCADE")
    )
    rules_version: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    contract_version: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(BigInteger)
    input_units: Mapped[int | None] = mapped_column(BigInteger)
    output_units: Mapped[int | None] = mapped_column(BigInteger)
    cache_hit: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool | None] = mapped_column(Boolean)
    sanitized_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
