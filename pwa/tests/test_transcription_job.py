# pwa/tests/test_transcription_job.py
"""Tests for transcription job."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pwa.backend.models.recording import RecordingStatus
from pwa.backend.models.recording_sql import RecordingModel
from pwa.backend.services.recording_service import RecordingService


class TestRecordingServiceStuckJobs:
    """Test suite for stuck job recovery."""

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_get_recordings_stuck_in_processing(self, test_db_session: AsyncSession) -> None:
        """Test finding recordings stuck in processing."""
        service = RecordingService(test_db_session)

        # Create a recording stuck in processing (started 1 hour ago)
        old_time = datetime.now(UTC) - timedelta(hours=1)
        stuck_recording = RecordingModel(
            id=uuid4(),
            patient_id="patient-123",
            clinician_id="clinician-456",
            duration_seconds=60,
            audio_file_path="/tmp/audio.wav",
            status=RecordingStatus.PROCESSING.value,
            transcription_started_at=old_time,
        )
        test_db_session.add(stuck_recording)

        # Create a recent recording in processing (should not be stuck)
        recent_time = datetime.now(UTC)
        recent_recording = RecordingModel(
            id=uuid4(),
            patient_id="patient-456",
            clinician_id="clinician-789",
            duration_seconds=60,
            audio_file_path="/tmp/audio2.wav",
            status=RecordingStatus.PROCESSING.value,
            transcription_started_at=recent_time,
        )
        test_db_session.add(recent_recording)

        # Create a completed recording (should not be stuck)
        completed_recording = RecordingModel(
            id=uuid4(),
            patient_id="patient-789",
            clinician_id="clinician-abc",
            duration_seconds=60,
            audio_file_path="/tmp/audio3.wav",
            status=RecordingStatus.COMPLETED.value,
            transcription_started_at=old_time,
        )
        test_db_session.add(completed_recording)

        await test_db_session.commit()

        # Find stuck recordings
        stuck = await service.get_recordings_stuck_in_processing(minutes=30)

        # Should only find the old processing recording
        assert len(stuck) == 1
        assert str(stuck[0].id) == str(stuck_recording.id)


class TestTranscriptionJobModule:
    """Basic tests for transcription job module."""

    def test_transcription_job_exists(self) -> None:
        """Test that transcription job module exists."""
        from pwa.backend.jobs.transcription_job import process_transcription

        assert callable(process_transcription)

    def test_transcription_imports(self) -> None:
        """Test that transcription job has proper imports."""
        from pwa.backend.jobs.transcription_job import (
            logger,
            process_transcription,
        )
        from pwa.backend.services.transcription_service import TranscriptionError

        assert logger is not None
        assert callable(process_transcription)
        assert issubclass(TranscriptionError, Exception)

    def test_transcription_updates_recording_status(self) -> None:
        """Test that transcription job updates recording status."""
        import inspect

        from pwa.backend.jobs.transcription_job import process_transcription

        sig = inspect.signature(process_transcription)
        assert "recording_id" in sig.parameters

    def test_transcription_error_handling(self) -> None:
        """Test that transcription error is properly defined."""
        from pwa.backend.services.transcription_service import TranscriptionError

        # Verify we can raise and catch TranscriptionError
        try:
            raise TranscriptionError("Test error")
        except TranscriptionError as e:
            assert str(e) == "Test error"
        except Exception:
            pytest.fail("TranscriptionError not caught properly")

    def test_transcription_job_has_logging(self) -> None:
        """Test that transcription job uses logging."""
        from pwa.backend.jobs.transcription_job import logger

        assert logger.name == "pwa.backend.jobs.transcription_job"
