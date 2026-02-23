# pwa/tests/test_recording_service.py
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService


@pytest_asyncio.fixture
async def service(test_db_session: AsyncSession) -> RecordingService:
    """Create a RecordingService with a test database session."""
    return RecordingService(test_db_session)


@pytest.mark.asyncio
async def test_create_recording(service: RecordingService) -> None:
    """Test creating a new recording."""
    recording = await service.create_recording(
        patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120
    )

    assert recording.patient_id == "patient-123"
    assert recording.status == RecordingStatus.PENDING
    assert recording.duration_seconds == 120


@pytest.mark.asyncio
async def test_get_recording(service: RecordingService) -> None:
    """Test retrieving a recording by ID."""
    # Create a recording first
    created = await service.create_recording(
        patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120
    )

    # Retrieve it
    retrieved = await service.get_recording(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.patient_id == "patient-123"


@pytest.mark.asyncio
async def test_get_nonexistent_recording(service: RecordingService) -> None:
    """Test retrieving a recording that doesn't exist."""
    retrieved = await service.get_recording(uuid4())
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_recordings_for_clinician(service: RecordingService) -> None:
    """Test getting all recordings for a clinician."""
    # Create recordings for different clinicians
    await service.create_recording(patient_id="patient-1", clinician_id="clinician-a", duration_seconds=60)
    await service.create_recording(patient_id="patient-2", clinician_id="clinician-a", duration_seconds=120)
    await service.create_recording(patient_id="patient-3", clinician_id="clinician-b", duration_seconds=180)

    # Get recordings for clinician-a
    recordings = await service.get_recordings_for_clinician("clinician-a")
    assert len(recordings) == 2
    assert all(r.clinician_id == "clinician-a" for r in recordings)


@pytest.mark.asyncio
async def test_get_recordings_for_clinician_with_status(service: RecordingService) -> None:
    """Test getting recordings filtered by status."""
    # Create a recording
    recording = await service.create_recording(patient_id="patient-1", clinician_id="clinician-a", duration_seconds=60)

    # Update status to ERROR
    await service.update_recording_status(recording.id, RecordingStatus.ERROR, "Test error")

    # Get pending recordings
    pending = await service.get_recordings_for_clinician("clinician-a", RecordingStatus.PENDING)
    assert len(pending) == 0

    # Get error recordings
    error_recordings = await service.get_recordings_for_clinician("clinician-a", RecordingStatus.ERROR)
    assert len(error_recordings) == 1
    assert error_recordings[0].status == RecordingStatus.ERROR
    assert error_recordings[0].error_message == "Test error"


@pytest.mark.asyncio
async def test_update_recording_status(service: RecordingService) -> None:
    """Test updating a recording's status."""
    # Create a recording
    created = await service.create_recording(
        patient_id="patient-123", clinician_id="clinician-456", duration_seconds=120
    )
    assert created.status == RecordingStatus.PENDING

    # Update status
    updated = await service.update_recording_status(created.id, RecordingStatus.COMPLETED)
    assert updated is not None
    assert updated.status == RecordingStatus.COMPLETED

    # Verify persisted
    retrieved = await service.get_recording(created.id)
    assert retrieved is not None
    assert retrieved.status == RecordingStatus.COMPLETED


@pytest.mark.asyncio
async def test_update_nonexistent_recording(service: RecordingService) -> None:
    """Test updating a recording that doesn't exist."""
    result = await service.update_recording_status(uuid4(), RecordingStatus.COMPLETED)
    assert result is None
