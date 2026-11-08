"""Expand persistence for individual signals and human investigation files."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0008"
down_revision: str | None = "20261006_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "individual_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "normalized_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(contract_version) BETWEEN 1 AND 100",
            name="individual_signals_contract_version_length_check",
        ),
    )
    op.create_index(
        "individual_signals_record_contract_uidx",
        "individual_signals",
        ["normalized_record_id", "contract_version"],
        unique=True,
    )

    op.create_table(
        "signal_relation_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "left_signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "right_signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "relation_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relation_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "left_signal_id < right_signal_id",
            name="signal_relation_suggestions_canonical_pair_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending','ready','failed')",
            name="signal_relation_suggestions_status_check",
        ),
        sa.CheckConstraint(
            "(status = 'ready' AND relation_assessment_id IS NOT NULL AND error_code IS NULL) "
            "OR (status = 'pending' AND relation_assessment_id IS NULL AND error_code IS NULL) "
            "OR (status = 'failed' AND relation_assessment_id IS NULL AND error_code IS NOT NULL)",
            name="signal_relation_suggestions_result_check",
        ),
        sa.CheckConstraint(
            "char_length(contract_version) BETWEEN 1 AND 100",
            name="signal_relation_suggestions_contract_version_length_check",
        ),
    )
    op.create_index(
        "signal_relation_suggestions_pair_contract_uidx",
        "signal_relation_suggestions",
        ["left_signal_id", "right_signal_id", "contract_version"],
        unique=True,
    )
    op.create_index(
        "signal_relation_suggestions_assessment_uidx",
        "signal_relation_suggestions",
        ["relation_assessment_id"],
        unique=True,
        postgresql_where=sa.text("relation_assessment_id IS NOT NULL"),
    )
    op.create_index(
        "signal_relation_suggestions_left_status_idx",
        "signal_relation_suggestions",
        ["left_signal_id", "status", "updated_at"],
    )
    op.create_index(
        "signal_relation_suggestions_right_status_idx",
        "signal_relation_suggestions",
        ["right_signal_id", "status", "updated_at"],
    )

    op.create_table(
        "investigation_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 0", name="investigation_files_version_nonnegative_check"),
    )

    op.create_table(
        "investigation_file_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigation_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_files.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("added_by", sa.Text(), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.Column("removed_by", sa.Text()),
        sa.Column("removal_reason", sa.Text()),
        sa.CheckConstraint(
            "(removed_at IS NULL AND removed_by IS NULL AND removal_reason IS NULL) OR "
            "(removed_at IS NOT NULL AND removed_by IS NOT NULL AND removal_reason IS NOT NULL)",
            name="investigation_members_removal_fields_check",
        ),
        sa.CheckConstraint(
            "char_length(added_by) BETWEEN 1 AND 100 AND "
            "(removed_by IS NULL OR char_length(removed_by) BETWEEN 1 AND 100)",
            name="investigation_members_actor_length_check",
        ),
    )
    op.create_index(
        "investigation_members_active_signal_uidx",
        "investigation_file_members",
        ["signal_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.create_index(
        "investigation_members_file_active_idx",
        "investigation_file_members",
        ["investigation_file_id", "added_at"],
        postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.create_index(
        "investigation_members_file_signal_idx",
        "investigation_file_members",
        ["investigation_file_id", "signal_id"],
    )

    op.create_table(
        "investigation_membership_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_key", sa.Text(), nullable=False),
        sa.Column("operation_fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "investigation_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_files.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("file_version", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=False),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason_code", sa.Text()),
        sa.Column("comment", sa.Text()),
        sa.CheckConstraint("sequence > 0", name="investigation_events_sequence_positive_check"),
        sa.CheckConstraint(
            "file_version = sequence",
            name="investigation_events_file_version_sequence_check",
        ),
        sa.CheckConstraint(
            "action IN ('add','remove','reject')",
            name="investigation_events_action_check",
        ),
        sa.CheckConstraint(
            "char_length(operation_key) BETWEEN 1 AND 128",
            name="investigation_events_operation_key_length_check",
        ),
        sa.CheckConstraint(
            "operation_fingerprint ~ '^[0-9a-f]{64}$'",
            name="investigation_events_operation_fingerprint_check",
        ),
        sa.CheckConstraint(
            "char_length(actor_id) BETWEEN 1 AND 100",
            name="investigation_events_actor_id_length_check",
        ),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500",
            name="investigation_events_comment_length_check",
        ),
    )
    op.create_index(
        "investigation_events_operation_key_uidx",
        "investigation_membership_events",
        ["operation_key"],
        unique=True,
    )
    op.create_index(
        "investigation_events_file_sequence_uidx",
        "investigation_membership_events",
        ["investigation_file_id", "sequence"],
        unique=True,
    )
    op.create_index(
        "investigation_events_signal_idx",
        "investigation_membership_events",
        ["signal_id", "occurred_at"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_investigation_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'investigation_membership_events is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER investigation_events_append_only
        BEFORE UPDATE OR DELETE ON investigation_membership_events
        FOR EACH ROW EXECUTE FUNCTION reject_investigation_event_mutation()
        """
    )

    # Non-destructive backfill: successful normalized sources become individual signals.
    # Legacy consolidation tables remain untouched and readable during expand/contract.
    op.execute(
        """
        INSERT INTO individual_signals (id, normalized_record_id, contract_version, created_at)
        SELECT
            md5('vbe-hub:individual-signal-v1:' || id::text)::uuid,
            id,
            'individual-signal-v1',
            created_at
        FROM normalized_records
        WHERE state = 'succeeded'
        ON CONFLICT (normalized_record_id, contract_version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER investigation_events_append_only ON investigation_membership_events"
    )
    op.drop_table("investigation_membership_events")
    op.execute("DROP FUNCTION reject_investigation_event_mutation()")
    op.drop_table("investigation_file_members")
    op.drop_table("investigation_files")
    op.drop_table("signal_relation_suggestions")
    op.drop_table("individual_signals")
