"""Store versioned relation assessments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260930_0004"
down_revision: str | None = "20260930_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "relation_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column(
            "left_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "right_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation", sa.Text()),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("justification", sa.Text()),
        sa.Column(
            "updating_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="CASCADE"),
        ),
        sa.Column("rules_version", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("input_units", sa.BigInteger()),
        sa.Column("output_units", sa.BigInteger()),
        sa.Column("cache_hit", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("retryable", sa.Boolean()),
        sa.Column("sanitized_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('succeeded', 'failed')", name="relation_assessments_state_check"
        ),
        sa.CheckConstraint(
            "method IN ('rule', 'provider')", name="relation_assessments_method_check"
        ),
        sa.CheckConstraint(
            "relation IS NULL OR relation IN ('duplicate','corroborates','updates',"
            "'related_context','unrelated')",
            name="relation_assessments_relation_check",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="relation_assessments_confidence_check",
        ),
    )
    op.create_index(
        "relation_assessments_cache_key_uidx", "relation_assessments", ["cache_key"], unique=True
    )
    op.create_index(
        "relation_assessments_pair_idx", "relation_assessments", ["left_id", "right_id"]
    )


def downgrade() -> None:
    op.drop_table("relation_assessments")
