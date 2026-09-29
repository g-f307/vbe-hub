"""Create records, provenance, normalization and evaluation storage."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_type", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("component_versions", postgresql.JSONB(), nullable=False),
        sa.Column("received_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("processed_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sanitized_error", postgresql.JSONB()),
        sa.CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed')",
            name="processing_runs_state_check",
        ),
        sa.CheckConstraint(
            "received_count >= 0 AND processed_count >= 0 "
            "AND skipped_count >= 0 AND failed_count >= 0",
            name="processing_runs_counts_nonnegative_check",
        ),
    )
    op.create_table(
        "raw_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("original_payload", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_kind IN ('media', 'community')", name="raw_records_source_kind_check"
        ),
        sa.CheckConstraint("char_length(content_hash) = 64", name="raw_records_content_hash_check"),
    )
    op.create_index("raw_records_ingestion_run_id_idx", "raw_records", ["ingestion_run_id"])
    op.create_index("raw_records_published_at_idx", "raw_records", ["published_at"])
    op.create_index(
        "raw_records_external_source_uidx",
        "raw_records",
        ["source_kind", "source_name", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "raw_records_hash_source_uidx",
        "raw_records",
        ["source_kind", "source_name", "content_hash"],
        unique=True,
        postgresql_where=sa.text("external_id IS NULL"),
    )
    op.create_table(
        "record_provenance",
        sa.Column(
            "raw_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_records.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("adapter_name", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("generator_name", sa.Text()),
        sa.Column("generator_version", sa.Text()),
        sa.Column("seed", sa.BigInteger()),
        sa.Column("scenario_id", sa.Text()),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("record_provenance_scenario_id_idx", "record_provenance", ["scenario_id"])
    op.create_table(
        "normalized_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "raw_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("normalizer_version", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("normalized_data", postgresql.JSONB(), nullable=False),
        sa.Column("error", postgresql.JSONB()),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('pending', 'running', 'succeeded', 'failed')",
            name="normalized_records_state_check",
        ),
    )
    op.create_index("normalized_records_raw_record_id_idx", "normalized_records", ["raw_record_id"])
    op.create_index(
        "normalized_records_record_version_uidx",
        "normalized_records",
        ["raw_record_id", "normalizer_version"],
        unique=True,
    )
    op.create_table(
        "evaluation_labels",
        sa.Column(
            "raw_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_records.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("gold_event_id", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_labels")
    op.drop_index("normalized_records_record_version_uidx", table_name="normalized_records")
    op.drop_index("normalized_records_raw_record_id_idx", table_name="normalized_records")
    op.drop_table("normalized_records")
    op.drop_index("record_provenance_scenario_id_idx", table_name="record_provenance")
    op.drop_table("record_provenance")
    op.drop_index("raw_records_hash_source_uidx", table_name="raw_records")
    op.drop_index("raw_records_external_source_uidx", table_name="raw_records")
    op.drop_index("raw_records_published_at_idx", table_name="raw_records")
    op.drop_index("raw_records_ingestion_run_id_idx", table_name="raw_records")
    op.drop_table("raw_records")
    op.drop_table("processing_runs")
