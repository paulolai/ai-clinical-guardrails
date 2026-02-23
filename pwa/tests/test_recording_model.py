# pwa/tests/test_recording_model.py
"""Tests for Recording Pydantic model."""

from datetime import datetime
from uuid import uuid4

from pwa.backend.models.recording import Recording, RecordingStatus


def test_recording_model_creation() -> None:
    """Test that Recording model can be created with required fields."""
    recording = Recording(
        id=uuid4(),
        patient_id="test-patient-123",
        clinician_id="test-clinician-456",
        audio_file_path="/tmp/test.wav",
        duration_seconds=120,
        status=RecordingStatus.PENDING,
    )

    assert recording.id is not None
    assert recording.patient_id == "test-patient-123"
    assert recording.status == RecordingStatus.PENDING
    assert isinstance(recording.created_at, datetime)


def test_recording_with_draft_transcript() -> None:
    """Test recording with draft transcript field."""
    recording = Recording(
        patient_id="patient-123", clinician_id="clinician-456", draft_transcript="This is a draft", duration_seconds=120
    )

    assert recording.draft_transcript == "This is a draft"
    assert recording.final_transcript is None


def test_recording_with_upload_tracking() -> None:
    """Test recording with upload tracking fields."""
    recording = Recording(
        patient_id="patient-123", clinician_id="clinician-456", local_storage_key="local-uuid-123", duration_seconds=120
    )

    assert recording.local_storage_key == "local-uuid-123"
    assert recording.upload_attempts == 0


def test_recording_defaults() -> None:
    """Test recording default values."""
    recording = Recording(patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120)

    assert recording.draft_transcript is None
    assert recording.final_transcript is None
    assert recording.local_storage_key is None
    assert recording.upload_attempts == 0
