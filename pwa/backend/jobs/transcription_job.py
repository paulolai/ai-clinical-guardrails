# pwa/backend/jobs/transcription_job.py
"""Background job for transcription."""

from datetime import UTC, datetime
from uuid import UUID

from pwa.backend.database import get_db
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService
from pwa.backend.services.transcription_service import WhisperService


async def process_transcription(recording_id: UUID) -> None:
    """Process transcription for a recording.

    This should be called as a background task.
    """
    async for db in get_db():
        service = RecordingService(db)
        whisper = WhisperService()

        try:
            # Get recording
            recording = await service.get_recording(recording_id)
            if not recording:
                print(f"[Transcription] Recording {recording_id} not found")
                return

            # Update status to processing
            await service.update_recording_status(
                recording_id, RecordingStatus.PROCESSING, transcription_started_at=datetime.now(UTC)
            )

            # Check audio file exists
            if not recording.audio_file_path:
                raise Exception("No audio file path")

            # Transcribe
            print(f"[Transcription] Starting transcription for {recording_id}")
            result = await whisper.transcribe(recording.audio_file_path)

            # Update recording with transcript
            await service.update_recording_status(
                recording_id,
                RecordingStatus.COMPLETED,
                final_transcript=result["text"],
                whisper_model=result["model"],
                transcription_completed_at=datetime.now(UTC),
            )

            print(f"[Transcription] Completed for {recording_id}")

        except Exception as e:
            print(f"[Transcription] Error for {recording_id}: {e}")
            await service.update_recording_status(recording_id, RecordingStatus.ERROR, error_message=str(e))
