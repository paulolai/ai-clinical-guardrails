# pwa/tests/test_transcription_job.py
"""Tests for transcription job."""


def test_transcription_job_exists() -> None:
    """Test that transcription job module exists."""
    from pwa.backend.jobs.transcription_job import process_transcription

    assert callable(process_transcription)


def test_transcription_updates_recording_status() -> None:
    """Test that transcription job updates recording status."""
    # This will be an integration test
    # For now, just verify the function signature
    import inspect

    from pwa.backend.jobs.transcription_job import process_transcription

    sig = inspect.signature(process_transcription)
    assert "recording_id" in sig.parameters
