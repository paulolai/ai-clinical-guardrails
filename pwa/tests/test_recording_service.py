# pwa/tests/test_recording_service.py
from uuid import uuid4

import pytest

from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService


@pytest.fixture  # type: ignore[untyped-decorator]
def service() -> RecordingService:
    return RecordingService()


def test_create_recording(service: RecordingService) -> None:
    """Test creating a new recording."""
    recording = service.create_recording(patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120)

    assert recording.patient_id == "patient-123"
    assert recording.status == RecordingStatus.PENDING
    assert recording.duration_seconds == 120


def test_get_recording(service: RecordingService) -> None:
    """Test retrieving a recording by ID."""
    # Create a recording first
    created = service.create_recording(patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120)

    # Retrieve it
    retrieved = service.get_recording(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.patient_id == "patient-123"


def test_get_nonexistent_recording(service: RecordingService) -> None:
    """Test retrieving a recording that doesn't exist."""
    retrieved = service.get_recording(uuid4())
    assert retrieved is None
