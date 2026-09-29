"""Store versioned semantic embeddings in pgvector."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "20260930_0003"
down_revision: str | None = "20260929_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "record_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "normalized_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("representation_version", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.BigInteger(), nullable=False),
        sa.Column("embedding", VECTOR(768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("dimensions = 768", name="record_embeddings_dimensions_check"),
        sa.CheckConstraint(
            "char_length(input_hash) = 64", name="record_embeddings_input_hash_check"
        ),
    )
    op.create_index(
        "record_embeddings_normalized_record_id_idx",
        "record_embeddings",
        ["normalized_record_id"],
    )
    op.create_index(
        "record_embeddings_version_uidx",
        "record_embeddings",
        [
            "normalized_record_id",
            "provider",
            "model",
            "representation_version",
            "dimensions",
        ],
        unique=True,
    )
    op.execute(
        "CREATE INDEX record_embeddings_embedding_hnsw_idx ON record_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("record_embeddings")
