"""Tests for Whisper transcription service."""


def test_whisper_service_exists() -> None:
    """Test that Whisper service can be imported."""
    from pwa.backend.services.transcription_service import WhisperService

    assert WhisperService is not None


def test_whisper_service_transcribe_method() -> None:
    """Test that WhisperService has transcribe method."""
    from pwa.backend.services.transcription_service import WhisperService

    service = WhisperService(model_name="base")
    assert hasattr(service, "transcribe")
    assert callable(service.transcribe)
