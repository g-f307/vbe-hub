from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class IndividualSignalModel(Base):
    __tablename__ = "individual_signals"
    __table_args__ = (
        CheckConstraint(
            "char_length(contract_version) BETWEEN 1 AND 100",
            name="individual_signals_contract_version_length_check",
        ),
        Index(
            "individual_signals_record_contract_uidx",
            "normalized_record_id",
            "contract_version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    normalized_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="RESTRICT"),
    )
    contract_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignalRelationSuggestionModel(Base):
    __tablename__ = "signal_relation_suggestions"
    __table_args__ = (
        CheckConstraint(
            "left_signal_id < right_signal_id",
            name="signal_relation_suggestions_canonical_pair_check",
        ),
        CheckConstraint(
            "status IN ('pending','ready','failed')",
            name="signal_relation_suggestions_status_check",
        ),
        CheckConstraint(
            "char_length(contract_version) BETWEEN 1 AND 100",
            name="signal_relation_suggestions_contract_version_length_check",
        ),
        CheckConstraint(
            "(status = 'ready' AND relation_assessment_id IS NOT NULL AND error_code IS NULL) "
            "OR (status = 'pending' AND relation_assessment_id IS NULL AND error_code IS NULL) "
            "OR (status = 'failed' AND relation_assessment_id IS NULL AND error_code IS NOT NULL)",
            name="signal_relation_suggestions_result_check",
        ),
        Index(
            "signal_relation_suggestions_pair_contract_uidx",
            "left_signal_id",
            "right_signal_id",
            "contract_version",
            unique=True,
        ),
        Index(
            "signal_relation_suggestions_assessment_uidx",
            "relation_assessment_id",
            unique=True,
            postgresql_where=text("relation_assessment_id IS NOT NULL"),
        ),
        Index(
            "signal_relation_suggestions_left_status_idx",
            "left_signal_id",
            "status",
            "updated_at",
        ),
        Index(
            "signal_relation_suggestions_right_status_idx",
            "right_signal_id",
            "status",
            "updated_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    left_signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("individual_signals.id", ondelete="RESTRICT")
    )
    right_signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("individual_signals.id", ondelete="RESTRICT")
    )
    relation_assessment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("relation_assessments.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(Text)
    contract_version: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvestigationFileModel(Base):
    __tablename__ = "investigation_files"
    __table_args__ = (
        CheckConstraint("version >= 0", name="investigation_files_version_nonnegative_check"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InvestigationFileMemberModel(Base):
    __tablename__ = "investigation_file_members"
    __table_args__ = (
        CheckConstraint(
            "(removed_at IS NULL AND removed_by IS NULL AND removal_reason IS NULL) OR "
            "(removed_at IS NOT NULL AND removed_by IS NOT NULL AND removal_reason IS NOT NULL)",
            name="investigation_members_removal_fields_check",
        ),
        CheckConstraint(
            "char_length(added_by) BETWEEN 1 AND 100 AND "
            "(removed_by IS NULL OR char_length(removed_by) BETWEEN 1 AND 100)",
            name="investigation_members_actor_length_check",
        ),
        Index(
            "investigation_members_active_signal_uidx",
            "signal_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index(
            "investigation_members_file_active_idx",
            "investigation_file_id",
            "added_at",
            postgresql_where=text("removed_at IS NULL"),
        ),
        Index(
            "investigation_members_file_signal_idx",
            "investigation_file_id",
            "signal_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    investigation_file_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("investigation_files.id", ondelete="RESTRICT")
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("individual_signals.id", ondelete="RESTRICT")
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[str] = mapped_column(Text)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by: Mapped[str | None] = mapped_column(Text)
    removal_reason: Mapped[str | None] = mapped_column(Text)


class InvestigationMembershipEventModel(Base):
    __tablename__ = "investigation_membership_events"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="investigation_events_sequence_positive_check"),
        CheckConstraint(
            "file_version = sequence",
            name="investigation_events_file_version_sequence_check",
        ),
        CheckConstraint(
            "action IN ('add','remove','reject')",
            name="investigation_events_action_check",
        ),
        CheckConstraint(
            "char_length(operation_key) BETWEEN 1 AND 128",
            name="investigation_events_operation_key_length_check",
        ),
        CheckConstraint(
            "operation_fingerprint ~ '^[0-9a-f]{64}$'",
            name="investigation_events_operation_fingerprint_check",
        ),
        CheckConstraint(
            "char_length(actor_id) BETWEEN 1 AND 100",
            name="investigation_events_actor_id_length_check",
        ),
        CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500",
            name="investigation_events_comment_length_check",
        ),
        Index("investigation_events_operation_key_uidx", "operation_key", unique=True),
        Index(
            "investigation_events_file_sequence_uidx",
            "investigation_file_id",
            "sequence",
            unique=True,
        ),
        Index("investigation_events_signal_idx", "signal_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    operation_key: Mapped[str] = mapped_column(Text)
    operation_fingerprint: Mapped[str] = mapped_column(Text)
    investigation_file_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("investigation_files.id", ondelete="RESTRICT")
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("individual_signals.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int] = mapped_column(BigInteger)
    file_version: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reason_code: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
