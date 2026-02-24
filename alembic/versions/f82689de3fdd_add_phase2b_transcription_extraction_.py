"""add_phase2b_transcription_extraction_fields

Revision ID: f82689de3fdd
Revises: 5d23fb5bdd00
Create Date: 2026-02-23 22:56:02.765769

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "f82689de3fdd"
down_revision: str | Sequence[str] | None = "5d23fb5bdd00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - Add Phase 2b extraction and verification fields."""
    # Phase 2b: Extraction fields
    op.add_column("recordings", sa.Column("fhir_bundle", sa.JSON(), nullable=True))
    op.add_column("recordings", sa.Column("llm_model", sa.String(50), nullable=True))
    op.add_column("recordings", sa.Column("extraction_started_at", sa.DateTime(), nullable=True))
    op.add_column("recordings", sa.Column("extraction_completed_at", sa.DateTime(), nullable=True))

    # Phase 2b: Verification fields
    op.add_column("recordings", sa.Column("verification_score", sa.Float(), nullable=True))
    op.add_column("recordings", sa.Column("verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove Phase 2b extraction and verification fields."""
    # Remove Phase 2b: Verification fields
    op.drop_column("recordings", "verified_at")
    op.drop_column("recordings", "verification_score")

    # Remove Phase 2b: Extraction fields
    op.drop_column("recordings", "extraction_completed_at")
    op.drop_column("recordings", "extraction_started_at")
    op.drop_column("recordings", "llm_model")
    op.drop_column("recordings", "fhir_bundle")
