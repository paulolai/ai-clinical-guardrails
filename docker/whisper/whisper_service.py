#!/usr/bin/env python3
"""Whisper transcription service."""

import tempfile
from pathlib import Path
from typing import Any

import whisper
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI(title="Whisper Transcription Service")

# Load model at startup (choose: tiny, base, small, medium, large)
MODEL_NAME = "base"
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

    try:
        # Save uploaded file to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe
        result = model.transcribe(tmp_path)

        # Cleanup
        Path(tmp_path).unlink()

        return JSONResponse(
            {
                "text": result["text"],
                "language": result.get("language", "en"),
                "segments": result.get("segments", []),
                "model": MODEL_NAME,
            }
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
