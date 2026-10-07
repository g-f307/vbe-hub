from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class SignalWorkflowModel(Base):
    __tablename__ = "signal_workflows"
    __table_args__ = (
        CheckConstraint(
            "state IN ('detected','triage','verification','risk_assessment','closed')",
            name="signal_workflows_state_check",
        ),
        CheckConstraint("version >= 0", name="signal_workflows_version_nonnegative_check"),
        Index("signal_workflows_state_idx", "state"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("consolidated_signals.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(BigInteger)
    state_machine_version: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewEventModel(Base):
    __tablename__ = "review_events"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="review_events_sequence_positive_check"),
        CheckConstraint(
            "workflow_version = sequence",
            name="review_events_workflow_version_sequence_check",
        ),
        CheckConstraint(
            "workflow_state IN ('detected','triage','verification','risk_assessment','closed')",
            name="review_events_state_check",
        ),
        CheckConstraint(
            "action IN ('transition','accept','correct','reject')",
            name="review_events_action_check",
        ),
        CheckConstraint(
            "target_type IS NULL OR target_type IN ('relation','membership','grouping','priority')",
            name="review_events_target_type_check",
        ),
        CheckConstraint(
            "char_length(operation_key) BETWEEN 1 AND 128",
            name="review_events_operation_key_length_check",
        ),
        CheckConstraint(
            "operation_fingerprint ~ '^[0-9a-f]{64}$'",
            name="review_events_operation_fingerprint_check",
        ),
        CheckConstraint(
            "char_length(actor_id) BETWEEN 1 AND 100",
            name="review_events_actor_id_length_check",
        ),
        CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500",
            name="review_events_comment_length_check",
        ),
        Index("review_events_operation_key_uidx", "operation_key", unique=True),
        Index("review_events_signal_sequence_uidx", "signal_id", "sequence", unique=True),
        Index("review_events_target_idx", "signal_id", "target_type", "target_id"),
        Index("review_events_actor_id_idx", "actor_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    operation_key: Mapped[str] = mapped_column(Text)
    operation_fingerprint: Mapped[str] = mapped_column(Text)
    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("signal_workflows.signal_id", ondelete="RESTRICT"),
    )
    sequence: Mapped[int] = mapped_column(BigInteger)
    workflow_version: Mapped[int] = mapped_column(BigInteger)
    workflow_state: Mapped[str] = mapped_column(Text)
    state_machine_version: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(Text)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    previous_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reason_code: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
