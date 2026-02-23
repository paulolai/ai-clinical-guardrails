# pwa/backend/services/recording_service.py
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.models.recording_sql import RecordingModel


class RecordingService:
    """Service for managing recordings with async SQLAlchemy database persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recording(
        self,
        patient_id: str,
        clinician_id: str,
        duration_seconds: int,
        audio_file_path: str | None = None,
        audio_file_size: int | None = None,
        local_storage_key: str | None = None,
        draft_transcript: str | None = None,
    ) -> Recording:
        """Create a new recording."""
        recording_model = RecordingModel(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
            audio_file_size=audio_file_size,
            local_storage_key=local_storage_key,
            draft_transcript=draft_transcript,
            status=RecordingStatus.PENDING.value,
        )
        self.db.add(recording_model)
        await self.db.commit()
        await self.db.refresh(recording_model)
        return Recording.model_validate(recording_model)

    async def get_recording(self, recording_id: UUID) -> Recording | None:
        """Get a recording by ID."""
        result = await self.db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
        recording_model = result.scalar_one_or_none()
        if recording_model is None:
            return None
        return Recording.model_validate(recording_model)

    async def get_recordings_for_clinician(
        self, clinician_id: str, status: RecordingStatus | None = None
    ) -> list[Recording]:
        """Get all recordings for a clinician, optionally filtered by status."""
        query = select(RecordingModel).where(RecordingModel.clinician_id == clinician_id)
        if status:
            query = query.where(RecordingModel.status == status.value)
        result = await self.db.execute(query)
        recording_models = result.scalars().all()
        return [Recording.model_validate(r) for r in recording_models]

    async def update_recording_status(
        self,
        recording_id: UUID,
        status: RecordingStatus,
        error_message: str | None = None,
        final_transcript: str | None = None,
        whisper_model: str | None = None,
        transcription_started_at: datetime | None = None,
        transcription_completed_at: datetime | None = None,
    ) -> Recording | None:
        """Update the status of a recording."""
        result = await self.db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
        recording_model = result.scalar_one_or_none()
        if recording_model is None:
            return None

        recording_model.status = status.value
        if error_message:
            recording_model.error_message = error_message
        if final_transcript is not None:
            recording_model.final_transcript = final_transcript
        if whisper_model is not None:
            recording_model.whisper_model = whisper_model
        if transcription_started_at is not None:
            recording_model.transcription_started_at = transcription_started_at
        if transcription_completed_at is not None:
            recording_model.transcription_completed_at = transcription_completed_at

        recording_model.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(recording_model)
        return Recording.model_validate(recording_model)

    async def update_recording(
        self,
        recording_id: UUID,
        extraction_started_at: datetime | None = None,
        fhir_bundle: dict[str, Any] | None = None,
        llm_model: str | None = None,
        extraction_completed_at: datetime | None = None,
        verification_results: dict[str, Any] | None = None,
        verification_score: float | None = None,
        verified_at: datetime | None = None,
        status: RecordingStatus | None = None,
    ) -> Recording | None:
        """Update recording with extraction results."""
        result = await self.db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
        recording_model = result.scalar_one_or_none()
        if recording_model is None:
            return None

        if extraction_started_at is not None:
            recording_model.extraction_started_at = extraction_started_at
        if fhir_bundle is not None:
            recording_model.fhir_bundle = fhir_bundle
        if llm_model is not None:
            recording_model.llm_model = llm_model
        if extraction_completed_at is not None:
            recording_model.extraction_completed_at = extraction_completed_at
        if verification_results is not None:
            recording_model.verification_results = verification_results
        if verification_score is not None:
            recording_model.verification_score = verification_score
        if verified_at is not None:
            recording_model.verified_at = verified_at
        if status is not None:
            recording_model.status = status.value

        recording_model.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(recording_model)
        return Recording.model_validate(recording_model)

    async def get_recordings_stuck_in_processing(self, minutes: int = 30) -> list[Recording]:
        """Get recordings stuck in PROCESSING status for longer than specified minutes."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)
        query = (
            select(RecordingModel)
            .where(RecordingModel.status == RecordingStatus.PROCESSING.value)
            .where(RecordingModel.transcription_started_at < cutoff_time)
        )
        result = await self.db.execute(query)
        recording_models = result.scalars().all()
        return [Recording.model_validate(r) for r in recording_models]
