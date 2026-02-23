# pwa/backend/jobs/extraction_job.py
"""Background job for clinical data extraction."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from pwa.backend.database import get_db
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.extraction_service import LLMService
from pwa.backend.services.recording_service import RecordingService
from pwa.backend.services.verification_service import VerificationService

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

            logger.info("[Extraction] Completed for %s", recording_id)

            # Verify
            logger.info("[Verification] Starting verification for %s", recording_id)
            verifier = VerificationService()
            verification = verifier.verify(result)

            # Update with everything including verification
            await service.update_recording(
                recording_id,
                fhir_bundle=result,
                llm_model=result["model"],
                verification_results=verification,
                verification_score=verification["score"],
                verified_at=datetime.now(UTC),
                extraction_completed_at=datetime.now(UTC),
                status=RecordingStatus.COMPLETED if verification["passed"] else RecordingStatus.ERROR,
            )

            if not verification["passed"]:
                logger.warning("[Verification] FAILED for %s: %s", recording_id, verification["issues"])

        except Exception as e:
            logger.exception(f"[Extraction] Error for {recording_id}: {e}")
            await service.update_recording_status(
                recording_id, RecordingStatus.ERROR, error_message=f"Extraction failed: {str(e)}"
            )
