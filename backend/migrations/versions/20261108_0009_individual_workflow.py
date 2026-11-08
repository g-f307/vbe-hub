"""Add workflow-v2 for individual signals and investigation files."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261108_0009"
down_revision: str | None = "20261108_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "individual_signal_workflows",
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("state_machine_version", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('detected','triage','closed')",
            name="individual_signal_workflows_state_check",
        ),
        sa.CheckConstraint(
            "version >= 0", name="individual_signal_workflows_version_nonnegative_check"
        ),
    )
    op.create_index(
        "individual_signal_workflows_state_updated_idx",
        "individual_signal_workflows",
        ["state", "updated_at"],
    )
    op.create_table(
        "investigation_workflows",
        sa.Column(
            "investigation_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_files.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("state_machine_version", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('verification','risk_assessment','closed')",
            name="investigation_workflows_state_check",
        ),
        sa.CheckConstraint("version >= 1", name="investigation_workflows_version_positive_check"),
    )
    op.create_index(
        "investigation_workflows_state_updated_idx",
        "investigation_workflows",
        ["state", "updated_at"],
    )
    op.create_table(
        "workflow_v2_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_key", sa.Text(), nullable=False),
        sa.Column("operation_fingerprint", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("individual_signals.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "investigation_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_files.id", ondelete="RESTRICT"),
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("workflow_version", sa.BigInteger(), nullable=False),
        sa.Column("workflow_state", sa.Text(), nullable=False),
        sa.Column("state_machine_version", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=False),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason_code", sa.Text()),
        sa.Column("comment", sa.Text()),
        sa.CheckConstraint(
            "(subject_type = 'signal' AND signal_id IS NOT NULL AND "
            "investigation_file_id IS NULL) OR "
            "(subject_type = 'investigation' AND signal_id IS NULL AND "
            "investigation_file_id IS NOT NULL)",
            name="workflow_v2_events_subject_check",
        ),
        sa.CheckConstraint("sequence > 0", name="workflow_v2_events_sequence_positive_check"),
        sa.CheckConstraint(
            "workflow_version = sequence",
            name="workflow_v2_events_version_sequence_check",
        ),
        sa.CheckConstraint(
            "workflow_state IN ('detected','triage','verification','risk_assessment','closed')",
            name="workflow_v2_events_state_check",
        ),
        sa.CheckConstraint(
            "char_length(operation_key) BETWEEN 1 AND 128",
            name="workflow_v2_events_operation_key_length_check",
        ),
        sa.CheckConstraint(
            "operation_fingerprint ~ '^[0-9a-f]{64}$'",
            name="workflow_v2_events_fingerprint_check",
        ),
        sa.CheckConstraint(
            "char_length(actor_id) BETWEEN 1 AND 100",
            name="workflow_v2_events_actor_length_check",
        ),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500",
            name="workflow_v2_events_comment_length_check",
        ),
    )
    op.create_index(
        "workflow_v2_events_operation_key_uidx",
        "workflow_v2_events",
        ["operation_key"],
        unique=True,
    )
    op.create_index(
        "workflow_v2_events_signal_sequence_uidx",
        "workflow_v2_events",
        ["signal_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("signal_id IS NOT NULL"),
    )
    op.create_index(
        "workflow_v2_events_file_sequence_uidx",
        "workflow_v2_events",
        ["investigation_file_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("investigation_file_id IS NOT NULL"),
    )
    op.execute(
        """
        INSERT INTO individual_signal_workflows
            (signal_id, state, version, state_machine_version, updated_at)
        SELECT id, 'detected', 0, 'workflow-v2', created_at
        FROM individual_signals
        ON CONFLICT (signal_id) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE FUNCTION initialize_individual_signal_workflow() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO individual_signal_workflows
                (signal_id, state, version, state_machine_version, updated_at)
            VALUES (NEW.id, 'detected', 0, 'workflow-v2', NEW.created_at);
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER individual_signal_workflow_on_insert
        AFTER INSERT ON individual_signals
        FOR EACH ROW EXECUTE FUNCTION initialize_individual_signal_workflow()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_workflow_v2_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'workflow_v2_events is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER workflow_v2_events_append_only
        BEFORE UPDATE OR DELETE ON workflow_v2_events
        FOR EACH ROW EXECUTE FUNCTION reject_workflow_v2_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER workflow_v2_events_append_only ON workflow_v2_events")
    op.execute("DROP FUNCTION reject_workflow_v2_event_mutation()")
    op.execute("DROP TRIGGER individual_signal_workflow_on_insert ON individual_signals")
    op.execute("DROP FUNCTION initialize_individual_signal_workflow()")
    op.drop_table("workflow_v2_events")
    op.drop_table("investigation_workflows")
    op.drop_table("individual_signal_workflows")
