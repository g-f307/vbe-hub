from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from vbe_hub.adapters.persistence.models import Base


class SuggestedPriorityModel(Base):
    __tablename__ = "suggested_priorities"
    __table_args__ = (
        CheckConstraint(
            "char_length(identity_key) = 64",
            name="suggested_priorities_identity_length_check",
        ),
        CheckConstraint(
            "char_length(configuration_hash) = 64",
            name="suggested_priorities_configuration_length_check",
        ),
        CheckConstraint(
            "score >= 0 AND score <= 100",
            name="suggested_priorities_score_range_check",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="suggested_priorities_confidence_range_check",
        ),
        CheckConstraint(
            "band IN ('routine','attention','prompt')",
            name="suggested_priorities_band_check",
        ),
        Index("suggested_priorities_identity_uidx", "identity_key", unique=True),
        Index(
            "suggested_priorities_signal_evaluated_idx",
            "signal_id",
            "evaluated_at",
        ),
        Index("suggested_priorities_policy_version_idx", "policy_version"),
        Index("suggested_priorities_score_idx", "score"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    identity_key: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(Text)
    configuration_hash: Mapped[str] = mapped_column(Text)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    signal_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("consolidated_signals.id", ondelete="RESTRICT"),
    )
    signal_identity_key: Mapped[str] = mapped_column(Text)
    signal_policy_version: Mapped[str] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(SmallInteger)
    band: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(SmallInteger)
    components: Mapped[dict[str, dict[str, Any]]] = mapped_column(JSONB)
    gaps: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
