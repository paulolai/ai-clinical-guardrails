"""SQLAlchemy model for Recording."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from pwa.backend.database import Base


class RecordingModel(Base):  # type: ignore
    """SQLAlchemy model representing a clinical recording in the database."""

    __tablename__ = "recordings"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Identifiers
    patient_id: Mapped[str] = mapped_column(String, nullable=False)
    clinician_id: Mapped[str] = mapped_column(String, nullable=False)

    # Audio metadata
    audio_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_file_size: Mapped[int | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Results
    transcript: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_recordings_patient_id", "patient_id"),
        Index("ix_recordings_clinician_id", "clinician_id"),
        Index("ix_recordings_status", "status"),
        Index("ix_recordings_created_at", "created_at"),
    )
