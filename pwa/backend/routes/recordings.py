# pwa/backend/routes/recordings.py
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.database import get_db
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])


class CreateRecordingRequest(BaseModel):
    patient_id: str
    duration_seconds: int
    audio_file_path: str | None = None


class RecordingResponse(BaseModel):
    id: str
    patient_id: str
    clinician_id: str
    duration_seconds: int
    status: str
    created_at: str


class UploadRecordingResponse(BaseModel):
    """Response for uploaded recording."""

    id: str
    patient_id: str
    clinician_id: str
    duration_seconds: int
    status: str
    local_storage_key: str | None = None
    created_at: str


@router.post("", response_model=RecordingResponse, status_code=201)
async def create_recording(
    request: CreateRecordingRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RecordingResponse:
    """Create a new recording."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"  # Placeholder

    service = RecordingService(db)
    recording = await service.create_recording(
        patient_id=request.patient_id,
        clinician_id=clinician_id,
        duration_seconds=request.duration_seconds,
        audio_file_path=request.audio_file_path,
    )

    return RecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds or 0,
        status=recording.status.value,
        created_at=recording.created_at.isoformat(),
    )


@router.post("/upload", response_model=UploadRecordingResponse, status_code=201)
async def upload_recording(
    audio: UploadFile = File(...),  # noqa: B008
    patient_id: str = Form(...),  # noqa: B008
    duration_seconds: int = Form(...),  # noqa: B008
    local_storage_key: str | None = Form(None),  # noqa: B008
    draft_transcript: str | None = Form(None),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadRecordingResponse:
    """Upload a recording with audio file."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    # Read audio content
    audio_content = await audio.read()
    audio_file_size = len(audio_content)

    # TODO: Save audio file to disk (Phase 2a - basic implementation)
    # For now, just store the size
    audio_file_path = f"/tmp/recordings/{local_storage_key or 'unknown'}.wav"

    service = RecordingService(db)
    recording = await service.create_recording(
        patient_id=patient_id,
        clinician_id=clinician_id,
        duration_seconds=duration_seconds,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        local_storage_key=local_storage_key,
        draft_transcript=draft_transcript,
    )

    return UploadRecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds or 0,
        status=recording.status.value,
        local_storage_key=recording.local_storage_key,
        created_at=recording.created_at.isoformat(),
    )


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RecordingResponse:
    """Get a recording by ID."""
    service = RecordingService(db)
    recording = await service.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    return RecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds or 0,
        status=recording.status.value,
        created_at=recording.created_at.isoformat(),
    )


@router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    status: RecordingStatus | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[RecordingResponse]:
    """List recordings for the current clinician."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    service = RecordingService(db)
    recordings = await service.get_recordings_for_clinician(clinician_id, status)

    return [
        RecordingResponse(
            id=str(r.id),
            patient_id=r.patient_id,
            clinician_id=r.clinician_id,
            duration_seconds=r.duration_seconds or 0,
            status=r.status.value,
            created_at=r.created_at.isoformat(),
        )
        for r in recordings
    ]
