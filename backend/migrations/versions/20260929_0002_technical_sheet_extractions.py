"""Store idempotent technical-sheet extraction results and failures."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0002"
down_revision: str | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_sheet_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "normalized_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text()),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("technical_sheet", postgresql.JSONB()),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("input_units", sa.BigInteger()),
        sa.Column("output_units", sa.BigInteger()),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.Text()),
        sa.Column("retryable", sa.Boolean()),
        sa.Column("sanitized_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('succeeded', 'failed')",
            name="technical_sheet_extractions_state_check",
        ),
        sa.CheckConstraint(
            "char_length(cache_key) = 64 AND char_length(input_hash) = 64",
            name="technical_sheet_extractions_hash_length_check",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0 AND (input_units IS NULL OR input_units >= 0) "
            "AND (output_units IS NULL OR output_units >= 0)",
            name="technical_sheet_extractions_usage_nonnegative_check",
        ),
    )
    op.create_index(
        "technical_sheet_extractions_cache_key_uidx",
        "technical_sheet_extractions",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        "technical_sheet_extractions_normalized_record_id_idx",
        "technical_sheet_extractions",
        ["normalized_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "technical_sheet_extractions_normalized_record_id_idx",
        table_name="technical_sheet_extractions",
    )
    op.drop_index(
        "technical_sheet_extractions_cache_key_uidx",
        table_name="technical_sheet_extractions",
    )
    op.drop_table("technical_sheet_extractions")
