# pwa/backend/services/recording_service.py
from uuid import UUID

from pwa.backend.models.recording import Recording, RecordingStatus


class RecordingService:
    """Service for managing recordings."""

    # In-memory storage for now (will be replaced with DB)
    _recordings: dict[UUID, Recording] = {}

    def create_recording(
        self, patient_id: str, clinician_id: str, duration_seconds: int, audio_file_path: str | None = None
    ) -> Recording:
        """Create a new recording."""
        recording = Recording(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
            status=RecordingStatus.PENDING,
        )
        self._recordings[recording.id] = recording
        return recording

    def get_recording(self, recording_id: UUID) -> Recording | None:
        """Get a recording by ID."""
        return self._recordings.get(recording_id)

    def get_recordings_for_clinician(self, clinician_id: str, status: RecordingStatus | None = None) -> list[Recording]:
        """Get all recordings for a clinician, optionally filtered by status."""
        recordings = [r for r in self._recordings.values() if r.clinician_id == clinician_id]
        if status:
            recordings = [r for r in recordings if r.status == status]
        return recordings

    def update_recording_status(
        self, recording_id: UUID, status: RecordingStatus, error_message: str | None = None
    ) -> Recording | None:
        """Update the status of a recording."""
        recording = self._recordings.get(recording_id)
        if recording:
            recording.status = status
            if error_message:
                recording.error_message = error_message
        return recording
