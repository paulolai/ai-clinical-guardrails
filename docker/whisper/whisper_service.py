#!/usr/bin/env python3
"""Whisper transcription service."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import whisper
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper Transcription Service")

# Load model at startup (choose: tiny, base, small, medium, large)
MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
model: Any = None


@app.on_event("startup")
async def startup_event() -> None:
    global model
    print(f"Loading Whisper model: {MODEL_NAME}")
    model = whisper.load_model(MODEL_NAME)
    print("Whisper model loaded successfully")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),  # noqa: B008
) -> JSONResponse:
    """Transcribe audio file to text."""
    if model is None:
        return JSONResponse({"error": "Model not loaded"}, status_code=503)

    tmp_path: str | None = None
    try:
        # Save uploaded file to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe
        result = model.transcribe(tmp_path)

        return JSONResponse(
            {
                "text": result["text"],
                "language": result.get("language", "en"),
                "segments": result.get("segments", []),
                "model": MODEL_NAME,
            }
        )

    except Exception:
        logger.exception("Transcription failed")
        return JSONResponse({"error": "Transcription failed"}, status_code=500)
    finally:
        # Cleanup temp file
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink()
            except OSError:
                logger.warning(f"Failed to cleanup temp file: {tmp_path}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
