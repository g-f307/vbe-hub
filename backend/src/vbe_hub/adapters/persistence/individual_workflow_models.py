from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class IndividualSignalWorkflowModel(Base):
    __tablename__ = "individual_signal_workflows"
    __table_args__ = (
        CheckConstraint(
            "state IN ('detected','triage','closed')",
            name="individual_signal_workflows_state_check",
        ),
        CheckConstraint(
            "version >= 0", name="individual_signal_workflows_version_nonnegative_check"
        ),
        Index("individual_signal_workflows_state_updated_idx", "state", "updated_at"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("individual_signals.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(BigInteger)
    state_machine_version: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvestigationWorkflowModel(Base):
    __tablename__ = "investigation_workflows"
    __table_args__ = (
        CheckConstraint(
            "state IN ('verification','risk_assessment','closed')",
            name="investigation_workflows_state_check",
        ),
        CheckConstraint("version >= 1", name="investigation_workflows_version_positive_check"),
        Index("investigation_workflows_state_updated_idx", "state", "updated_at"),
    )

    investigation_file_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("investigation_files.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(BigInteger)
    state_machine_version: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowV2EventModel(Base):
    __tablename__ = "workflow_v2_events"
    __table_args__ = (
        CheckConstraint(
            "(subject_type = 'signal' AND signal_id IS NOT NULL AND "
            "investigation_file_id IS NULL) OR "
            "(subject_type = 'investigation' AND signal_id IS NULL AND "
            "investigation_file_id IS NOT NULL)",
            name="workflow_v2_events_subject_check",
        ),
        CheckConstraint("sequence > 0", name="workflow_v2_events_sequence_positive_check"),
        CheckConstraint(
            "workflow_version = sequence", name="workflow_v2_events_version_sequence_check"
        ),
        CheckConstraint(
            "workflow_state IN ('detected','triage','verification','risk_assessment','closed')",
            name="workflow_v2_events_state_check",
        ),
        Index("workflow_v2_events_operation_key_uidx", "operation_key", unique=True),
        Index(
            "workflow_v2_events_signal_sequence_uidx",
            "signal_id",
            "sequence",
            unique=True,
            postgresql_where=text("signal_id IS NOT NULL"),
        ),
        Index(
            "workflow_v2_events_file_sequence_uidx",
            "investigation_file_id",
            "sequence",
            unique=True,
            postgresql_where=text("investigation_file_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    operation_key: Mapped[str] = mapped_column(Text)
    operation_fingerprint: Mapped[str] = mapped_column(Text)
    subject_type: Mapped[str] = mapped_column(Text)
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("individual_signals.id", ondelete="RESTRICT")
    )
    investigation_file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("investigation_files.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int] = mapped_column(BigInteger)
    workflow_version: Mapped[int] = mapped_column(BigInteger)
    workflow_state: Mapped[str] = mapped_column(Text)
    state_machine_version: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reason_code: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
