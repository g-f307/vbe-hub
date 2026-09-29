from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base
from vbe_hub.application.ai.embeddings import EMBEDDING_DIMENSIONS


class EmbeddingModel(Base):
    __tablename__ = "record_embeddings"
    __table_args__ = (
        CheckConstraint(
            f"dimensions = {EMBEDDING_DIMENSIONS}", name="record_embeddings_dimensions_check"
        ),
        CheckConstraint("char_length(input_hash) = 64", name="record_embeddings_input_hash_check"),
        Index("record_embeddings_normalized_record_id_idx", "normalized_record_id"),
        Index(
            "record_embeddings_version_uidx",
            "normalized_record_id",
            "provider",
            "model",
            "representation_version",
            "dimensions",
            unique=True,
        ),
        Index(
            "record_embeddings_embedding_hnsw_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    normalized_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("normalized_records.id", ondelete="CASCADE"),
    )
    input_hash: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    representation_version: Mapped[str] = mapped_column(Text)
    dimensions: Mapped[int] = mapped_column(BigInteger)
    embedding: Mapped[Sequence[float]] = mapped_column(VECTOR(EMBEDDING_DIMENSIONS))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
