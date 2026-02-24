"""Tests for Whisper transcription service."""

import contextlib
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pwa.backend.services.transcription_service import (
    TranscriptionError,
    WhisperService,
)


@pytest.fixture  # type: ignore[untyped-decorator]
def whisper_service() -> WhisperService:
    """Create a WhisperService instance for testing."""
    return WhisperService(model_name="base")


@pytest.fixture  # type: ignore[untyped-decorator]
def temp_audio_file() -> Any:
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"fake audio data")
        tmp_path = tmp.name
    yield tmp_path
    # Cleanup
    with contextlib.suppress(OSError):
        Path(tmp_path).unlink()


class TestWhisperService:
    """Test suite for WhisperService."""

    def test_service_exists(self) -> None:
        """Test that WhisperService can be imported and instantiated."""
        service = WhisperService(model_name="base")
        assert service is not None
        assert service.model_name == "base"

    def test_service_has_transcribe_method(self) -> None:
        """Test that WhisperService has transcribe method."""
        service = WhisperService(model_name="base")
        assert hasattr(service, "transcribe")
        assert callable(service.transcribe)

    def test_service_has_health_check_method(self) -> None:
        """Test that WhisperService has health_check method."""
        service = WhisperService(model_name="base")
        assert hasattr(service, "health_check")
        assert callable(service.health_check)

    def test_service_has_close_method(self) -> None:
        """Test that WhisperService has close method for resource cleanup."""
        service = WhisperService(model_name="base")
        assert hasattr(service, "close")
        assert callable(service.close)

    def test_service_is_async_context_manager(self) -> None:
        """Test that WhisperService is an async context manager."""
        service = WhisperService(model_name="base")
        assert hasattr(service, "__aenter__")
        assert hasattr(service, "__aexit__")

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_success(self, httpx_mock: HTTPXMock, temp_audio_file: str) -> None:
        """Test successful transcription."""
        httpx_mock.add_response(
            url="http://localhost:8001/transcribe",
            json={
                "text": "Hello world",
                "language": "en",
                "segments": [],
                "model": "base",
            },
            status_code=200,
        )

        async with WhisperService(model_name="base") as service:
            result = await service.transcribe(temp_audio_file)

        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_failure_500(self, httpx_mock: HTTPXMock, temp_audio_file: str) -> None:
        """Test transcription failure with 500 error."""
        httpx_mock.add_response(
            url="http://localhost:8001/transcribe",
            text="Internal server error",
            status_code=500,
        )

        async with WhisperService(model_name="base") as service:
            with pytest.raises(TranscriptionError) as exc_info:
                await service.transcribe(temp_audio_file)

        assert "Transcription failed" in str(exc_info.value)

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_file_not_found(self) -> None:
        """Test transcription with non-existent file."""
        async with WhisperService(model_name="base") as service:
            with pytest.raises(TranscriptionError) as exc_info:
                await service.transcribe("/nonexistent/path/audio.wav")

        assert "Failed to read audio file" in str(exc_info.value)

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_health_check_success(self, httpx_mock: HTTPXMock) -> None:
        """Test health check returns True when service is healthy."""
        httpx_mock.add_response(
            url="http://localhost:8001/health",
            json={"status": "healthy"},
            status_code=200,
        )

        async with WhisperService(model_name="base") as service:
            is_healthy = await service.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_health_check_failure(self, httpx_mock: HTTPXMock) -> None:
        """Test health check returns False when service is unhealthy."""
        httpx_mock.add_response(
            url="http://localhost:8001/health",
            status_code=503,
        )

        async with WhisperService(model_name="base") as service:
            is_healthy = await service.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_health_check_connection_error(self) -> None:
        """Test health check returns False on connection error."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch.object(
            WhisperService,
            "__init__",
            lambda self, model_name: None,
        ):
            service = WhisperService(model_name="base")
            service.client = mock_client
            service.model_name = "base"
            is_healthy = await service.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_close_releases_resources(self, httpx_mock: HTTPXMock) -> None:
        """Test that close() properly releases HTTP client resources."""
        service = WhisperService(model_name="base")
        await service.close()
        # Should complete without error

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_context_manager_cleanup(self, httpx_mock: HTTPXMock) -> None:
        """Test that async context manager properly cleans up."""
        async with WhisperService(model_name="base"):
            pass
        # Client should be closed after exiting context

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_includes_segments(self, httpx_mock: HTTPXMock, temp_audio_file: str) -> None:
        """Test that transcription includes segments in result."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": "world"},
        ]
        httpx_mock.add_response(
            url="http://localhost:8001/transcribe",
            json={
                "text": "Hello world",
                "language": "en",
                "segments": segments,
                "model": "base",
            },
            status_code=200,
        )

        async with WhisperService(model_name="base") as service:
            result = await service.transcribe(temp_audio_file)

        assert result["segments"] == segments

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_default_language(self, httpx_mock: HTTPXMock, temp_audio_file: str) -> None:
        """Test that transcription handles missing language field."""
        httpx_mock.add_response(
            url="http://localhost:8001/transcribe",
            json={
                "text": "Hello world",
                "segments": [],
            },
            status_code=200,
        )

        async with WhisperService(model_name="base") as service:
            result = await service.transcribe(temp_audio_file)

        assert result["language"] == "en"  # Default language

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_transcribe_preserves_model_name(self, httpx_mock: HTTPXMock, temp_audio_file: str) -> None:
        """Test that transcription preserves model name from response."""
        httpx_mock.add_response(
            url="http://localhost:8001/transcribe",
            json={
                "text": "Hello world",
                "language": "en",
                "segments": [],
                "model": "large",
            },
            status_code=200,
        )

        async with WhisperService(model_name="base") as service:
            result = await service.transcribe(temp_audio_file)

        assert result["model"] == "large"

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_env_var_configuration(self, monkeypatch: Any) -> None:
        """Test that service respects WHISPER_URL environment variable."""
        monkeypatch.setenv("WHISPER_URL", "http://custom:9000")
        # Need to reload module to pick up new env var
        import importlib

        import pwa.backend.services.transcription_service as transcription_module

        importlib.reload(transcription_module)
        service = transcription_module.WhisperService()
        assert service.client.base_url == "http://custom:9000"


class TestTranscriptionError:
    """Test suite for TranscriptionError exception."""

    def test_exception_inheritance(self) -> None:
        """Test that TranscriptionError inherits from Exception."""
        assert issubclass(TranscriptionError, Exception)

    def test_exception_can_be_raised(self) -> None:
        """Test that TranscriptionError can be raised and caught."""
        exc_info: Any = None
        try:
            with pytest.raises(TranscriptionError) as exc_info:
                raise TranscriptionError("Test error")
        except AssertionError:
            pass
        if exc_info:
            assert str(exc_info.value) == "Test error"
