"""Tests for database persistence verification."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from uuid import UUID
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pwa.backend.database import Base
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService

# Use file-based SQLite for persistence test
TEST_DB_URL = "sqlite+aiosqlite:///./data/test_persistence.db"


@pytest_asyncio.fixture  # type: ignore[untyped-decorator]
async def persistence_db() -> AsyncGenerator[sessionmaker[AsyncSession], None]:
    """Create a database connection that persists across the test."""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_local = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    yield async_session_local

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_data_persists_across_sessions(
    persistence_db: sessionmaker[AsyncSession],
) -> None:
    """Verify that data persists after closing and reopening database connection.

    This test simulates the scenario where:
    1. A recording is created
    2. The database connection is closed
    3. A new connection is opened
    4. The recording should still exist
    """
    recording_id = None
    patient_id = "persistence-test-patient"
    clinician_id = "persistence-test-clinician"
    duration = 150

    # Phase 1: Create recording with first connection
    async with persistence_db() as session1:
        service1 = RecordingService(session1)
        recording = await service1.create_recording(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration,
            audio_file_path="/test/audio.webm",
        )
        recording_id = recording.id
        assert recording.status == RecordingStatus.PENDING
        print(f"\nCreated recording: {recording_id}")

    # Phase 2: Verify recording exists with NEW connection
    async with persistence_db() as session2:
        service2 = RecordingService(session2)
        retrieved = await service2.get_recording(recording_id)

        assert retrieved is not None, "Recording should exist after reconnecting"
        assert retrieved.id == recording_id
        assert retrieved.patient_id == patient_id
        assert retrieved.clinician_id == clinician_id
        assert retrieved.duration_seconds == duration
        assert retrieved.status == RecordingStatus.PENDING
        print(f"Retrieved recording: {retrieved.id} - Status: {retrieved.status}")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_data_persists_after_status_update(
    persistence_db: sessionmaker[AsyncSession],
) -> None:
    """Verify that status updates persist after closing and reopening connection."""

    recording_id: UUID | None = None

    # Phase 1: Create and update recording
    async with persistence_db() as session1:
        service1 = RecordingService(session1)
        recording = await service1.create_recording(
            patient_id="update-test-patient",
            clinician_id="update-test-clinician",
            duration_seconds=120,
        )
        recording_id = recording.id

        # Update status
        updated = await service1.update_recording_status(recording_id, RecordingStatus.COMPLETED)
        assert updated is not None
        assert updated.status == RecordingStatus.COMPLETED
        print(f"\nUpdated recording status: {recording_id} -> COMPLETED")

    # Phase 2: Verify update persisted
    async with persistence_db() as session2:
        service2 = RecordingService(session2)
        retrieved = await service2.get_recording(recording_id)

        assert retrieved is not None
        assert retrieved.status == RecordingStatus.COMPLETED
        print(f"Verified persisted status: {retrieved.id} -> {retrieved.status}")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_multiple_recordings_persist(
    persistence_db: sessionmaker[AsyncSession],
) -> None:
    """Verify multiple recordings persist after reconnect."""
    recording_ids = []

    # Phase 1: Create multiple recordings
    async with persistence_db() as session1:
        service1 = RecordingService(session1)

        for i in range(3):
            recording = await service1.create_recording(
                patient_id=f"multi-patient-{i}",
                clinician_id="multi-clinician",
                duration_seconds=60 * (i + 1),
            )
            recording_ids.append(recording.id)

        print(f"\nCreated {len(recording_ids)} recordings")

    # Phase 2: Verify all exist
    async with persistence_db() as session2:
        service2 = RecordingService(session2)

        for rec_id in recording_ids:
            retrieved = await service2.get_recording(rec_id)
            assert retrieved is not None, f"Recording {rec_id} should exist"
            print(f"  Found: {rec_id}")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_clinician_recordings_persist(
    persistence_db: sessionmaker[AsyncSession],
) -> None:
    """Verify clinician-specific queries work after reconnect."""
    clinician_id = "persist-clinician-test"

    # Phase 1: Create recordings for specific clinician
    async with persistence_db() as session1:
        service1 = RecordingService(session1)

        await service1.create_recording(
            patient_id="patient-a",
            clinician_id=clinician_id,
            duration_seconds=120,
        )
        await service1.create_recording(
            patient_id="patient-b",
            clinician_id=clinician_id,
            duration_seconds=180,
        )

        recordings = await service1.get_recordings_for_clinician(clinician_id)
        assert len(recordings) == 2
        print(f"\nCreated {len(recordings)} recordings for clinician {clinician_id}")

    # Phase 2: Verify query still works
    async with persistence_db() as session2:
        service2 = RecordingService(session2)
        recordings = await service2.get_recordings_for_clinician(clinician_id)

        assert len(recordings) == 2
        assert all(r.clinician_id == clinician_id for r in recordings)
        print(f"Retrieved {len(recordings)} recordings after reconnect")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_data_survives_server_restart_simulation(
    persistence_db: sessionmaker[AsyncSession],
) -> None:
    """Simulate server restart by completely disposing and recreating engine.

    This is the most realistic test - it simulates what happens when:
    1. Server creates recording via API
    2. Server is restarted
    3. New server instance retrieves the recording
    """
    from uuid import uuid4

    test_db_path = "./data/test_restart_simulation.db"
    db_url = f"sqlite+aiosqlite:///{test_db_path}"

    recording_id = None
    patient_id = f"restart-test-{uuid4().hex[:8]}"

    # "Server 1": Create recording and dispose engine
    engine1 = create_async_engine(db_url, echo=False, future=True)
    async_session1 = sessionmaker(engine1, class_=AsyncSession, expire_on_commit=False, autoflush=False)

    async with engine1.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session1() as session:
        service = RecordingService(session)
        recording = await service.create_recording(
            patient_id=patient_id,
            clinician_id="restart-clinician",
            duration_seconds=200,
            audio_file_path="/restart/audio.webm",
        )
        recording_id = recording.id
        print(f"\n[Server 1] Created recording: {recording_id}")

    await engine1.dispose()
    print("[Server 1] Engine disposed (simulating shutdown)")

    # "Server 2": New engine, retrieve recording
    engine2 = create_async_engine(db_url, echo=False, future=True)
    async_session2 = sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False, autoflush=False)

    async with async_session2() as session:
        service = RecordingService(session)
        retrieved = await service.get_recording(recording_id)

        assert retrieved is not None, "Recording should survive 'server restart'"
        assert retrieved.patient_id == patient_id
        print(f"[Server 2] Retrieved recording: {retrieved.id}")
        print("[Server 2] Persistence verified!")

    await engine2.dispose()

    # Cleanup
    import contextlib
    import os

    with contextlib.suppress(FileNotFoundError):
        os.remove(test_db_path)
