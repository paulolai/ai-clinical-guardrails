# pwa/backend/routes/recordings.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


# Dependency
def get_recording_service() -> RecordingService:
    return RecordingService()


@router.post("", response_model=RecordingResponse, status_code=201)
async def create_recording(
    request: CreateRecordingRequest,
    service: RecordingService = Depends(get_recording_service),  # noqa: B008
) -> RecordingResponse:
    """Create a new recording."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"  # Placeholder

    recording = service.create_recording(
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


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: UUID,
    service: RecordingService = Depends(get_recording_service),  # noqa: B008
) -> RecordingResponse:
    """Get a recording by ID."""
    recording = service.get_recording(recording_id)
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
    service: RecordingService = Depends(get_recording_service),  # noqa: B008
) -> list[RecordingResponse]:
    """List recordings for the current clinician."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    recordings = service.get_recordings_for_clinician(clinician_id, status)

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
