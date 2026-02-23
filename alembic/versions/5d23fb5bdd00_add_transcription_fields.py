"""add_transcription_fields

Revision ID: 5d23fb5bdd00
Revises: 48c0c98075f2
Create Date: 2026-02-23 21:52:30.136916

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d23fb5bdd00"
down_revision: Union[str, Sequence[str], None] = "48c0c98075f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new transcription-related columns
    with op.batch_alter_table("recordings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("draft_transcript", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("final_transcript", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("local_storage_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("upload_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("whisper_model", sa.String(length=50), nullable=False, server_default="base"))
        batch_op.add_column(sa.Column("transcription_started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("transcription_completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("recordings", schema=None) as batch_op:
        batch_op.drop_column("transcription_completed_at")
        batch_op.drop_column("transcription_started_at")
        batch_op.drop_column("whisper_model")
        batch_op.drop_column("upload_attempts")
        batch_op.drop_column("local_storage_key")
        batch_op.drop_column("final_transcript")
        batch_op.drop_column("draft_transcript")
