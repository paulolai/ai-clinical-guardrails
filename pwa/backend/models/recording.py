# pwa/backend/models/recording.py
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RecordingStatus(StrEnum):
    """Status of a recording."""

    PENDING = "pending"  # Recorded, waiting for upload/processing
    UPLOADING = "uploading"  # Currently uploading to server
    QUEUED = "queued"  # Uploaded, waiting for transcription
    PROCESSING = "processing"  # Being transcribed/verified
    COMPLETED = "completed"  # Ready for review
    ERROR = "error"  # Processing failed


class Recording(BaseModel):
    """Model representing a clinical recording."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: str = Field(..., description="Patient identifier")
    clinician_id: str = Field(..., description="Clinician who recorded")

    # Audio
    audio_file_path: str | None = None
    audio_file_size: int | None = None
    duration_seconds: int | None = None

    # Status
    status: RecordingStatus = RecordingStatus.PENDING
    error_message: str | None = None
    retry_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None

    # Results (populated after processing)
    transcript: str | None = None
    verification_results: dict[str, Any] | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "patient_id": "patient-123",
                "clinician_id": "clinician-456",
                "duration_seconds": 120,
                "status": "pending",
            }
        },
    )
