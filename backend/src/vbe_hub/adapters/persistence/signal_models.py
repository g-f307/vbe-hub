from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class ConsolidatedSignalModel(Base):
    __tablename__ = "consolidated_signals"
    __table_args__ = (
        CheckConstraint(
            "processing_state IN ('suggested','accepted','corrected','rejected')",
            name="consolidated_signals_state_check",
        ),
        CheckConstraint(
            "char_length(identity_key) = 64",
            name="consolidated_signals_identity_length_check",
        ),
        CheckConstraint(
            "current_estimated_cases IS NULL OR current_estimated_cases >= 0",
            name="consolidated_signals_cases_nonnegative_check",
        ),
        CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_end >= period_start",
            name="consolidated_signals_period_order_check",
        ),
        Index("consolidated_signals_identity_uidx", "identity_key", unique=True),
        Index("consolidated_signals_policy_version_idx", "policy_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    identity_key: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(Text)
    processing_state: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    location: Mapped[dict[str, Any]] = mapped_column(JSONB)
    conditions: Mapped[list[str]] = mapped_column(JSONB)
    symptoms: Mapped[list[str]] = mapped_column(JSONB)
    magnitude_history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    current_estimated_cases: Mapped[int | None] = mapped_column(BigInteger)
    field_provenance: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(JSONB)
    divergence_codes: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignalMemberModel(Base):
    __tablename__ = "signal_members"
    __table_args__ = (
        PrimaryKeyConstraint("signal_id", "normalized_record_id"),
        CheckConstraint("role IN ('core','context')", name="signal_members_role_check"),
        Index("signal_members_record_id_idx", "normalized_record_id"),
        Index("signal_members_joined_by_relation_id_idx", "joined_by_relation_id"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("consolidated_signals.id", ondelete="CASCADE"),
    )
    normalized_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="RESTRICT"),
    )
    role: Mapped[str] = mapped_column(Text)
    joined_by_relation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("relation_assessments.id", ondelete="SET NULL"),
    )


class SignalRelationLinkModel(Base):
    __tablename__ = "signal_relation_links"
    __table_args__ = (
        PrimaryKeyConstraint("signal_id", "relation_assessment_id"),
        CheckConstraint(
            "role IN ('supporting','context')", name="signal_relation_links_role_check"
        ),
        Index("signal_relation_links_assessment_id_idx", "relation_assessment_id"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("consolidated_signals.id", ondelete="CASCADE"),
    )
    relation_assessment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("relation_assessments.id", ondelete="RESTRICT"),
    )
    role: Mapped[str] = mapped_column(Text)


class SignalGroupingConflictModel(Base):
    __tablename__ = "signal_grouping_conflicts"
    __table_args__ = (
        Index(
            "signal_grouping_conflicts_policy_relation_code_uidx",
            "policy_version",
            "relation_assessment_id",
            "code",
            unique=True,
        ),
        Index(
            "signal_grouping_conflicts_relation_id_idx",
            "relation_assessment_id",
        ),
        Index("signal_grouping_conflicts_left_record_id_idx", "left_record_id"),
        Index("signal_grouping_conflicts_right_record_id_idx", "right_record_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    policy_version: Mapped[str] = mapped_column(Text)
    relation_assessment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("relation_assessments.id", ondelete="RESTRICT"),
    )
    left_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="RESTRICT"),
    )
    right_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
