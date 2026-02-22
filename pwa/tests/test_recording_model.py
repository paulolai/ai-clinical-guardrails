# pwa/tests/test_recording_model.py
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
