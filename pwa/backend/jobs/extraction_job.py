# pwa/backend/jobs/extraction_job.py
"""Background job for clinical data extraction."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from pwa.backend.database import get_db
from pwa.backend.services.extraction_service import LLMService
from pwa.backend.services.recording_service import RecordingService

logger = logging.getLogger(__name__)


async def process_extraction(recording_id: UUID) -> None:
    """Process extraction for a recording after transcription."""
    async for db in get_db():
        service = RecordingService(db)
        llm = LLMService()

        try:
            # Get recording
            recording = await service.get_recording(recording_id)
            if not recording or not recording.final_transcript:
                logger.warning("[Extraction] Recording %s not ready", recording_id)
                return

            # Update status
            await service.update_recording(recording_id, extraction_started_at=datetime.now(UTC))

            # Extract
            logger.info("[Extraction] Starting extraction for %s", recording_id)
            result = await llm.extract(recording.final_transcript, recording.patient_id)

            # Update with results
            await service.update_recording(
                recording_id, fhir_bundle=result, llm_model=result["model"], extraction_completed_at=datetime.now(UTC)
            )

            logger.info("[Extraction] Completed for %s", recording_id)

        except Exception as e:
            logger.error("[Extraction] Error for %s: %s", recording_id, e)
