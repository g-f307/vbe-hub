"""Store versioned and explainable suggested priorities."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261003_0006"
down_revision: str | None = "20261002_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suggested_priorities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("configuration_hash", sa.Text(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consolidated_signals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("signal_identity_key", sa.Text(), nullable=False),
        sa.Column("signal_policy_version", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("band", sa.Text(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column("gaps", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(identity_key) = 64",
            name="suggested_priorities_identity_length_check",
        ),
        sa.CheckConstraint(
            "char_length(configuration_hash) = 64",
            name="suggested_priorities_configuration_length_check",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="suggested_priorities_score_range_check",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="suggested_priorities_confidence_range_check",
        ),
        sa.CheckConstraint(
            "band IN ('routine','attention','prompt')",
            name="suggested_priorities_band_check",
        ),
    )
    op.create_index(
        "suggested_priorities_identity_uidx",
        "suggested_priorities",
        ["identity_key"],
        unique=True,
    )
    op.create_index(
        "suggested_priorities_signal_evaluated_idx",
        "suggested_priorities",
        ["signal_id", "evaluated_at"],
    )
    op.create_index(
        "suggested_priorities_policy_version_idx",
        "suggested_priorities",
        ["policy_version"],
    )
    op.create_index(
        "suggested_priorities_score_idx",
        "suggested_priorities",
        ["score"],
    )


def downgrade() -> None:
    op.drop_table("suggested_priorities")
