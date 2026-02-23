# pwa/backend/services/recording_service.py
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
        self, patient_id: str, clinician_id: str, duration_seconds: int, audio_file_path: str | None = None
    ) -> Recording:
        """Create a new recording."""
        recording_model = RecordingModel(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
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
        self, recording_id: UUID, status: RecordingStatus, error_message: str | None = None
    ) -> Recording | None:
        """Update the status of a recording."""
        result = await self.db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
        recording_model = result.scalar_one_or_none()
        if recording_model is None:
            return None

        recording_model.status = status.value
        if error_message:
            recording_model.error_message = error_message

        await self.db.commit()
        await self.db.refresh(recording_model)
        return Recording.model_validate(recording_model)
