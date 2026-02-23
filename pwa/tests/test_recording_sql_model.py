"""Tests for SQLAlchemy RecordingModel."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.database import Base, engine
from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.models.recording_sql import RecordingModel


@pytest.mark.asyncio
async def test_recording_model_table_exists():
    """Test that RecordingModel creates the recordings table."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings'"))
        table = result.scalar()
        assert table == "recordings"


@pytest.mark.asyncio
async def test_recording_model_has_all_columns():
    """Test that RecordingModel has all required columns."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA table_info(recordings)"))
        columns = {row[1] for row in result.fetchall()}

        expected_columns = {
            "id",
            "patient_id",
            "clinician_id",
            "audio_file_path",
            "audio_file_size",
            "duration_seconds",
            "status",
            "error_message",
            "retry_count",
            "created_at",
            "updated_at",
            "uploaded_at",
            "processed_at",
            "transcript",
            "verification_results",
        }
        assert expected_columns.issubset(columns)


@pytest.mark.asyncio
async def test_recording_model_indexes_exist():
    """Test that indexes are created for patient_id, clinician_id, status, created_at."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='recordings'"))
        indexes = {row[0] for row in result.fetchall()}

        expected_indexes = {
            "ix_recordings_patient_id",
            "ix_recordings_clinician_id",
            "ix_recordings_status",
            "ix_recordings_created_at",
        }
        assert expected_indexes.issubset(indexes)


@pytest.mark.asyncio
async def test_recording_model_json_field():
    """Test that verification_results JSON field stores and retrieves dict data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_data = {"confidence": 0.95, "matched_terms": ["term1", "term2"]}
    recording_id = uuid4()

    async with AsyncSession(engine) as session:
        recording = RecordingModel(
            id=recording_id,
            patient_id="patient-123",
            clinician_id="clinician-456",
            verification_results=test_data,
        )
        session.add(recording)
        await session.commit()

    # Query back in a new session to verify JSON data
    async with AsyncSession(engine) as session:
        result = await session.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
        recording = result.scalar_one_or_none()
        assert recording is not None
        assert recording.verification_results == test_data


@pytest.mark.asyncio
async def test_pydantic_to_sqlalchemy_mapping():
    """Test that Pydantic Recording can be converted to SQLAlchemy RecordingModel."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create Pydantic model
    pydantic_recording = Recording(
        id=uuid4(),
        patient_id="patient-123",
        clinician_id="clinician-456",
        audio_file_path="/tmp/test.wav",
        audio_file_size=1024,
        duration_seconds=120,
        status=RecordingStatus.PENDING,
        retry_count=0,
        verification_results={"confidence": 0.9},
    )

    # Convert to SQLAlchemy model
    sqlalchemy_recording = RecordingModel(
        id=pydantic_recording.id,
        patient_id=pydantic_recording.patient_id,
        clinician_id=pydantic_recording.clinician_id,
        audio_file_path=pydantic_recording.audio_file_path,
        audio_file_size=pydantic_recording.audio_file_size,
        duration_seconds=pydantic_recording.duration_seconds,
        status=pydantic_recording.status.value,
        retry_count=pydantic_recording.retry_count,
        verification_results=pydantic_recording.verification_results,
    )

    # Verify mapping
    assert sqlalchemy_recording.id == pydantic_recording.id
    assert sqlalchemy_recording.patient_id == pydantic_recording.patient_id
    assert sqlalchemy_recording.verification_results == {"confidence": 0.9}


@pytest.mark.asyncio
async def test_sqlalchemy_to_pydantic_mapping():
    """Test that SQLAlchemy RecordingModel can be converted to Pydantic Recording."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create SQLAlchemy model
        recording_id = uuid4()
        sqlalchemy_recording = RecordingModel(
            id=recording_id,
            patient_id="patient-123",
            clinician_id="clinician-456",
            status="pending",
            verification_results={"confidence": 0.95},
        )
        session.add(sqlalchemy_recording)
        await session.commit()
        await session.refresh(sqlalchemy_recording)

        # Convert to Pydantic using from_orm (via from_attributes=True)
        pydantic_recording = Recording.model_validate(sqlalchemy_recording)

        # Verify conversion
        assert pydantic_recording.id == recording_id
        assert pydantic_recording.patient_id == "patient-123"
        assert pydantic_recording.status == RecordingStatus.PENDING
        assert pydantic_recording.verification_results == {"confidence": 0.95}


@pytest.mark.asyncio
async def test_recording_model_timestamps():
    """Test that created_at and updated_at are set automatically."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        recording = RecordingModel(
            id=uuid4(),
            patient_id="patient-123",
            clinician_id="clinician-456",
        )
        session.add(recording)
        await session.commit()
        await session.refresh(recording)

        assert recording.created_at is not None
        assert recording.updated_at is not None
        assert isinstance(recording.created_at, datetime)
        assert isinstance(recording.updated_at, datetime)
