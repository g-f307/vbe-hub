"""Add versioned human review workflow and immutable audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261006_0007"
down_revision: str | None = "20261003_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_workflows",
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consolidated_signals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("state_machine_version", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('detected','triage','verification','risk_assessment','closed')",
            name="signal_workflows_state_check",
        ),
        sa.CheckConstraint(
            "version >= 0",
            name="signal_workflows_version_nonnegative_check",
        ),
    )
    op.create_index("signal_workflows_state_idx", "signal_workflows", ["state"])

    op.create_table(
        "review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_key", sa.Text(), nullable=False),
        sa.Column("operation_fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signal_workflows.signal_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("workflow_version", sa.BigInteger(), nullable=False),
        sa.Column("workflow_state", sa.Text(), nullable=False),
        sa.Column("state_machine_version", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text()),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=False),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason_code", sa.Text()),
        sa.Column("comment", sa.Text()),
        sa.CheckConstraint("sequence > 0", name="review_events_sequence_positive_check"),
        sa.CheckConstraint(
            "workflow_version = sequence",
            name="review_events_workflow_version_sequence_check",
        ),
        sa.CheckConstraint(
            "workflow_state IN ('detected','triage','verification','risk_assessment','closed')",
            name="review_events_state_check",
        ),
        sa.CheckConstraint(
            "action IN ('transition','accept','correct','reject')",
            name="review_events_action_check",
        ),
        sa.CheckConstraint(
            "target_type IS NULL OR target_type IN "
            "('relation','membership','grouping','priority')",
            name="review_events_target_type_check",
        ),
        sa.CheckConstraint(
            "char_length(operation_key) BETWEEN 1 AND 128",
            name="review_events_operation_key_length_check",
        ),
        sa.CheckConstraint(
            "operation_fingerprint ~ '^[0-9a-f]{64}$'",
            name="review_events_operation_fingerprint_check",
        ),
        sa.CheckConstraint(
            "char_length(actor_id) BETWEEN 1 AND 100",
            name="review_events_actor_id_length_check",
        ),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500",
            name="review_events_comment_length_check",
        ),
    )
    op.create_index(
        "review_events_operation_key_uidx",
        "review_events",
        ["operation_key"],
        unique=True,
    )
    op.create_index(
        "review_events_signal_sequence_uidx",
        "review_events",
        ["signal_id", "sequence"],
        unique=True,
    )
    op.create_index(
        "review_events_target_idx",
        "review_events",
        ["signal_id", "target_type", "target_id"],
    )
    op.create_index("review_events_actor_id_idx", "review_events", ["actor_id"])
    op.execute(
        """
        CREATE FUNCTION reject_review_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'review_events is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER review_events_append_only
        BEFORE UPDATE OR DELETE ON review_events
        FOR EACH ROW EXECUTE FUNCTION reject_review_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER review_events_append_only ON review_events")
    op.drop_table("review_events")
    op.execute("DROP FUNCTION reject_review_event_mutation()")
    op.drop_table("signal_workflows")
