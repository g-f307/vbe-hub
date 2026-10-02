"""Store versioned consolidated signals and audit links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261002_0005"
down_revision: str | None = "20260930_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consolidated_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("processing_state", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("location", postgresql.JSONB(), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("symptoms", postgresql.JSONB(), nullable=False),
        sa.Column("magnitude_history", postgresql.JSONB(), nullable=False),
        sa.Column("current_estimated_cases", sa.BigInteger()),
        sa.Column("field_provenance", postgresql.JSONB(), nullable=False),
        sa.Column("divergence_codes", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "processing_state IN ('suggested','accepted','corrected','rejected')",
            name="consolidated_signals_state_check",
        ),
        sa.CheckConstraint(
            "char_length(identity_key) = 64",
            name="consolidated_signals_identity_length_check",
        ),
        sa.CheckConstraint(
            "current_estimated_cases IS NULL OR current_estimated_cases >= 0",
            name="consolidated_signals_cases_nonnegative_check",
        ),
        sa.CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_end >= period_start",
            name="consolidated_signals_period_order_check",
        ),
    )
    op.create_index(
        "consolidated_signals_identity_uidx",
        "consolidated_signals",
        ["identity_key"],
        unique=True,
    )
    op.create_index(
        "consolidated_signals_policy_version_idx",
        "consolidated_signals",
        ["policy_version"],
    )

    op.create_table(
        "signal_members",
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consolidated_signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "normalized_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "joined_by_relation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relation_assessments.id", ondelete="SET NULL"),
        ),
        sa.PrimaryKeyConstraint("signal_id", "normalized_record_id"),
        sa.CheckConstraint("role IN ('core','context')", name="signal_members_role_check"),
    )
    op.create_index(
        "signal_members_record_id_idx", "signal_members", ["normalized_record_id"]
    )
    op.create_index(
        "signal_members_joined_by_relation_id_idx",
        "signal_members",
        ["joined_by_relation_id"],
    )

    op.create_table(
        "signal_relation_links",
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consolidated_signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "relation_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relation_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("signal_id", "relation_assessment_id"),
        sa.CheckConstraint(
            "role IN ('supporting','context')",
            name="signal_relation_links_role_check",
        ),
    )
    op.create_index(
        "signal_relation_links_assessment_id_idx",
        "signal_relation_links",
        ["relation_assessment_id"],
    )

    op.create_table(
        "signal_grouping_conflicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column(
            "relation_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relation_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "left_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "right_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "signal_grouping_conflicts_policy_relation_code_uidx",
        "signal_grouping_conflicts",
        ["policy_version", "relation_assessment_id", "code"],
        unique=True,
    )
    op.create_index(
        "signal_grouping_conflicts_relation_id_idx",
        "signal_grouping_conflicts",
        ["relation_assessment_id"],
    )
    op.create_index(
        "signal_grouping_conflicts_left_record_id_idx",
        "signal_grouping_conflicts",
        ["left_record_id"],
    )
    op.create_index(
        "signal_grouping_conflicts_right_record_id_idx",
        "signal_grouping_conflicts",
        ["right_record_id"],
    )


def downgrade() -> None:
    op.drop_table("signal_grouping_conflicts")
    op.drop_table("signal_relation_links")
    op.drop_table("signal_members")
    op.drop_table("consolidated_signals")
