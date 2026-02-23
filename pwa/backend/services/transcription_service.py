"""Transcription service wrapper for Whisper container."""

from typing import Any

import httpx

WHISPER_URL = "http://localhost:8001"


class WhisperService:
    """Service for transcribing audio using Whisper."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=WHISPER_URL, timeout=60.0)

    async def transcribe(self, audio_path: str) -> dict[str, Any]:
        """Transcribe audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            dict with keys: text, language, confidence
        """
        with open(audio_path, "rb") as f:
            files = {"audio": ("audio.wav", f, "audio/wav")}
            response = await self.client.post("/transcribe", files=files)

        if response.status_code != 200:
            raise Exception(f"Transcription failed: {response.text}")

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
