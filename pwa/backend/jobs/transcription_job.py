# pwa/backend/jobs/transcription_job.py
"""Background job for transcription."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pwa.backend.database import get_db
from pwa.backend.jobs.extraction_job import process_extraction
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService
from pwa.backend.services.transcription_service import TranscriptionError, WhisperService

logger = logging.getLogger(__name__)


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
                logger.warning("Recording %s not found", recording_id)
                return

            # Update status to processing
            await service.update_recording_status(
                recording_id, RecordingStatus.PROCESSING, transcription_started_at=datetime.now(UTC)
            )

            # Check audio file exists
            if not recording.audio_file_path:
                raise TranscriptionError("No audio file path set for recording")

            audio_path = Path(recording.audio_file_path)
            if not audio_path.exists():
                raise TranscriptionError(f"Audio file not found: {recording.audio_file_path}")

            # Transcribe
            logger.info("Starting transcription for %s", recording_id)
            result = await whisper.transcribe(str(audio_path))

            # Update recording with transcript
            await service.update_recording_status(
                recording_id,
                RecordingStatus.COMPLETED,
                final_transcript=result["text"],
                whisper_model=result["model"],
                transcription_completed_at=datetime.now(UTC),
            )

            logger.info("Transcription completed for %s", recording_id)

            # Trigger extraction
            logger.info("[Transcription] Triggering extraction for %s", recording_id)
            await process_extraction(recording_id)

        except TranscriptionError as e:
            logger.error("Transcription failed for %s: %s", recording_id, e)
            await service.update_recording_status(recording_id, RecordingStatus.ERROR, error_message=str(e))
        except Exception as e:
            logger.exception("Unexpected error during transcription for %s", recording_id)
            await service.update_recording_status(
                recording_id, RecordingStatus.ERROR, error_message=f"Unexpected error: {e}"
            )
