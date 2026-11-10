"""Persist the head signal of each investigation file."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110_0010"
down_revision: str | None = "20261108_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigation_files",
        sa.Column("head_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "investigation_files_head_signal_fk",
        "investigation_files",
        "individual_signals",
        ["head_signal_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # Existing files predate the head invariant. The first active member is the
    # only deterministic approximation available and remains fully auditable.
    op.execute(
        """
        UPDATE investigation_files AS file
        SET head_signal_id = (
            SELECT signal_id
            FROM investigation_file_members
            WHERE investigation_file_id = file.id AND removed_at IS NULL
            ORDER BY added_at, id
            LIMIT 1
        )
        """
    )
    op.alter_column("investigation_files", "head_signal_id", nullable=False)
    op.create_index(
        "investigation_files_head_signal_uidx",
        "investigation_files",
        ["head_signal_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("investigation_files_head_signal_uidx", table_name="investigation_files")
    op.drop_constraint(
        "investigation_files_head_signal_fk", "investigation_files", type_="foreignkey"
    )
    op.drop_column("investigation_files", "head_signal_id")
