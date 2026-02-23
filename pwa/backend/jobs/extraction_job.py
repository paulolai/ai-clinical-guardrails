# pwa/backend/jobs/extraction_job.py
"""Background job for clinical data extraction with verification."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.verification_service import VerificationService


async def process_extraction(recording_id: UUID, extraction_result: dict[str, Any]) -> None:
    """Process extraction for a recording and run verification.

    Args:
        recording_id: The UUID of the recording
        extraction_result: The extracted clinical data from LLM
    """
    from pwa.backend.database import get_db
    from pwa.backend.services.recording_service import RecordingService

    async for db in get_db():
        service = RecordingService(db)

        try:
            # Get recording
            recording = await service.get_recording(recording_id)
            if not recording:
                print(f"[Extraction] Recording {recording_id} not found")
                return

            if not recording.final_transcript:
                print(f"[Extraction] Recording {recording_id} not ready (no transcript)")
                return

            print(f"[Extraction] Completed for {recording_id}")

            # Verify
            print(f"[Verification] Starting verification for {recording_id}")
            verifier = VerificationService()
            verification = verifier.verify(extraction_result)

            # Update with everything
            result = await service.update_recording_status(
                recording_id,
                RecordingStatus.COMPLETED if verification["passed"] else RecordingStatus.ERROR,
            )

            # Update additional fields
            if result:
                recording_model = await _get_recording_model(db, recording_id)
                if recording_model:
                    recording_model.fhir_bundle = extraction_result
                    recording_model.llm_model = extraction_result.get("model")
                    recording_model.verification_results = verification
                    recording_model.verification_score = verification["score"]
                    recording_model.verified_at = datetime.now(UTC)
                    recording_model.extraction_completed_at = datetime.now(UTC)
                    await db.commit()

            if not verification["passed"]:
                print(f"[Verification] FAILED for {recording_id}: {verification['issues']}")
            else:
                print(f"[Verification] PASSED for {recording_id}")

        except Exception as e:
            print(f"[Extraction] Error for {recording_id}: {e}")
            await service.update_recording_status(recording_id, RecordingStatus.ERROR, error_message=str(e))


async def _get_recording_model(db: AsyncSession, recording_id: UUID) -> Any | None:
    """Helper to get the SQL model directly."""
    from sqlalchemy import select

    from pwa.backend.models.recording_sql import RecordingModel

    result = await db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
    return result.scalar_one_or_none()
