"""Transcription service wrapper for Whisper container."""

import os
from typing import Any

import httpx

WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:8001")


class TranscriptionError(Exception):
    """Raised when transcription fails."""

    pass


class WhisperService:
    """Service for transcribing audio using Whisper."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=WHISPER_URL, timeout=60.0)

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self.client.aclose()

    async def __aenter__(self) -> "WhisperService":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def transcribe(self, audio_path: str) -> dict[str, Any]:
        """Transcribe audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            dict with keys: text, language, confidence

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            with open(audio_path, "rb") as f:
                files = {"audio": ("audio.wav", f, "audio/wav")}
                response = await self.client.post("/transcribe", files=files)
        except OSError as e:
            raise TranscriptionError(f"Failed to read audio file: {e}") from e

        if response.status_code != 200:
            raise TranscriptionError(f"Transcription failed: {response.text}")

        result = response.json()
        return {
            "text": result["text"],
            "language": result.get("language", "en"),
            "confidence": 0.9,  # Whisper doesn't give confidence, use heuristic
            "segments": result.get("segments", []),
            "model": result.get("model", self.model_name),
        }

    async def health_check(self) -> bool:
        """Check if Whisper service is healthy."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
