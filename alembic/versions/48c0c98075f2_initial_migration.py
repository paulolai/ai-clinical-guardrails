"""Initial migration

Revision ID: 48c0c98075f2
Revises:
Create Date: 2026-02-23 14:51:02.193595

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "48c0c98075f2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create recordings table
    op.create_table(
        "recordings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("clinician_id", sa.String(), nullable=False),
        sa.Column("audio_file_path", sa.String(), nullable=True),
        sa.Column("audio_file_size", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("transcript", sa.String(), nullable=True),
        sa.Column("verification_results", sa.JSON(), nullable=True),
    )

    # Create indexes
    op.create_index("ix_recordings_patient_id", "recordings", ["patient_id"])
    op.create_index("ix_recordings_clinician_id", "recordings", ["clinician_id"])
    op.create_index("ix_recordings_status", "recordings", ["status"])
    op.create_index("ix_recordings_created_at", "recordings", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_recordings_created_at", table_name="recordings")
    op.drop_index("ix_recordings_status", table_name="recordings")
    op.drop_index("ix_recordings_clinician_id", table_name="recordings")
    op.drop_index("ix_recordings_patient_id", table_name="recordings")
    op.drop_table("recordings")
