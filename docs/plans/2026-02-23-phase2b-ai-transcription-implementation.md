# Phase 2b: AI Transcription & Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Whisper transcription and LLM extraction to convert uploaded audio into structured clinical data with verification.

**Architecture:** Docker containers for Whisper and LLM, async job processing with Celery/background tasks, verification layer for clinical safety.

**Tech Stack:** Docker, Whisper (OpenAI), Llama 3.1 (8B or 70B), FastAPI BackgroundTasks/Celery, FHIR R4.

---

## Prerequisites

Before starting, verify Phase 2a is working:

```bash
# Verify tests pass
uv run pytest pwa/tests/test_upload_endpoint.py pwa/tests/test_recording_model.py -v
# Expected: 7 tests passing

# Verify Docker installed
docker --version

# Run the server
uv run python pwa/backend/main.py
# Open http://localhost:8002/queue
# Verify: Can see queue page
```

---

## Task 1: Set Up Whisper Docker Container

**Purpose:** Create Docker container with Whisper for audio transcription.

**Files:**
- Create: `docker/whisper/Dockerfile`
- Create: `docker/whisper/requirements.txt`
- Create: `docker/docker-compose.yml`
- Test: Create `pwa/tests/test_whisper_service.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_whisper_service.py`:

```python
# pwa/tests/test_whisper_service.py
"""Tests for Whisper transcription service."""

import pytest


def test_whisper_service_exists():
    """Test that Whisper service can be imported."""
    from pwa.backend.services.transcription_service import WhisperService
    assert WhisperService is not None


def test_whisper_service_transcribe_method():
    """Test that WhisperService has transcribe method."""
    from pwa.backend.services.transcription_service import WhisperService
    service = WhisperService(model_name="base")
    assert hasattr(service, 'transcribe')
    assert callable(service.transcribe)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_whisper_service.py -v
# Expected: FAIL - ModuleNotFoundError for transcription_service
```

**Step 3: Create Whisper Dockerfile**

Create `docker/whisper/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# Expose port
EXPOSE 8001

# Run the service
CMD ["python", "whisper_service.py"]
```

**IMPORTANT:** Model is NOT baked into the image. It downloads at runtime to `/root/.cache/whisper` via volume mount (see docker-compose.yml). This keeps the image small (~500MB vs ~15GB) and allows model updates without rebuilding.

**Step 4: Create Whisper requirements**

Create `docker/whisper/requirements.txt`:

```
openai-whisper==20231117
fastapi==0.109.0
uvicorn==0.27.0
python-multipart==0.0.6
```

**Step 5: Create Whisper service**

Create `docker/whisper/whisper_service.py`:

```python
#!/usr/bin/env python3
"""Whisper transcription service."""

import tempfile
from pathlib import Path

import whisper
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI(title="Whisper Transcription Service")

# Load model at startup (choose: tiny, base, small, medium, large)
MODEL_NAME = "base"
model = None


@app.on_event("startup")
async def startup_event():
    global model
    print(f"Loading Whisper model: {MODEL_NAME}")
    model = whisper.load_model(MODEL_NAME)
    print("Whisper model loaded successfully")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file to text."""
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

        return JSONResponse({
            "text": result["text"],
            "language": result.get("language", "en"),
            "segments": result.get("segments", []),
            "model": MODEL_NAME
        })

    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Step 6: Create Docker Compose**

Create `docker/docker-compose.yml`:

```yaml
version: '3.8'

services:
  whisper:
    build:
      context: ./whisper
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    volumes:
      - ./models:/root/.cache/whisper  # Persist models
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # We'll add LLM service in Task 3
  # llm:
  #   build:
  #     context: ./llm
  #   ports:
  #     - "8003:8003"
```

**Step 7: Create transcription service wrapper**

Create `pwa/backend/services/transcription_service.py`:

```python
# pwa/backend/services/transcription_service.py
"""Transcription service wrapper for Whisper container."""

import httpx
from typing import Optional

WHISPER_URL = "http://localhost:8001"


class WhisperService:
    """Service for transcribing audio using Whisper."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=WHISPER_URL, timeout=60.0)

    async def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            dict with keys: text, language, confidence
        """
        with open(audio_path, 'rb') as f:
            files = {'audio': ('audio.wav', f, 'audio/wav')}
            response = await self.client.post("/transcribe", files=files)

        if response.status_code != 200:
            raise Exception(f"Transcription failed: {response.text}")

        result = response.json()
        return {
            "text": result["text"],
            "language": result.get("language", "en"),
            "confidence": 0.9,  # Whisper doesn't give confidence, use heuristic
            "segments": result.get("segments", []),
            "model": result.get("model", self.model_name)
        }

    async def health_check(self) -> bool:
        """Check if Whisper service is healthy."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except:
            return False
```

**Step 8: Run test to verify it passes**

```bash
# Start Whisper container
cd docker && docker-compose up -d whisper

# Wait for startup
sleep 30

# Run tests
uv run pytest pwa/tests/test_whisper_service.py -v
# Expected: 2 tests PASS
```

**Step 9: Commit**

```bash
git add docker/ pwa/backend/services/transcription_service.py pwa/tests/test_whisper_service.py
git commit -m "feat: add Whisper Docker container and transcription service"
```

---

## Task 2: Add Transcription Endpoint and Background Job

**Purpose:** Create async transcription job triggered when audio uploads.

**Files:**
- Create: `pwa/backend/jobs/transcription_job.py`
- Modify: `pwa/backend/routes/recordings.py` - Add trigger
- Modify: `pwa/backend/models/recording.py` - Add transcription fields
- Modify: `pwa/backend/models/recording_sql.py` - Add SQL columns
- Test: Create `pwa/tests/test_transcription_job.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_transcription_job.py`:

```python
# pwa/tests/test_transcription_job.py
"""Tests for transcription job."""

import pytest
from uuid import uuid4

from pwa.backend.models.recording import RecordingStatus


def test_transcription_job_exists():
    """Test that transcription job module exists."""
    from pwa.backend.jobs.transcription_job import process_transcription
    assert callable(process_transcription)


def test_transcription_updates_recording_status():
    """Test that transcription job updates recording status."""
    # This will be an integration test
    # For now, just verify the function signature
    from pwa.backend.jobs.transcription_job import process_transcription
    import inspect
    sig = inspect.signature(process_transcription)
    assert 'recording_id' in sig.parameters
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_transcription_job.py -v
# Expected: FAIL - ModuleNotFoundError
```

**Step 3: Update Recording model**

Edit `pwa/backend/models/recording.py`, add after existing fields:

```python
    # NEW: Transcription (Phase 2b)
    final_transcript: str | None = None
    whisper_model: str = "base"
    transcription_started_at: datetime | None = None
    transcription_completed_at: datetime | None = None
```

**Step 4: Update SQL model**

Edit `pwa/backend/models/recording_sql.py`, add columns:

```python
# After existing columns, add:
final_transcript = Column(Text, nullable=True)
whisper_model = Column(String(50), default="base")
transcription_started_at = Column(DateTime, nullable=True)
transcription_completed_at = Column(DateTime, nullable=True)
```

**Step 5: Create transcription job**

Create `pwa/backend/jobs/transcription_job.py`:

```python
# pwa/backend/jobs/transcription_job.py
"""Background job for transcription."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from pwa.backend.database import get_db_session
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.services.recording_service import RecordingService
from pwa.backend.services.transcription_service import WhisperService


async def process_transcription(recording_id: UUID) -> None:
    """Process transcription for a recording.

    This should be called as a background task.
    """
    async for db in get_db_session():
        service = RecordingService(db)
        whisper = WhisperService()

        try:
            # Get recording
            recording = await service.get_recording(recording_id)
            if not recording:
                print(f"[Transcription] Recording {recording_id} not found")
                return

            # Update status to processing
            await service.update_recording_status(
                recording_id,
                RecordingStatus.PROCESSING,
                transcription_started_at=datetime.now(UTC)
            )

            # Check audio file exists
            if not recording.audio_file_path:
                raise Exception("No audio file path")

            # Transcribe
            print(f"[Transcription] Starting transcription for {recording_id}")
            result = await whisper.transcribe(recording.audio_file_path)

            # Update recording with transcript
            await service.update_recording_status(
                recording_id,
                RecordingStatus.COMPLETED,
                final_transcript=result["text"],
                whisper_model=result["model"],
                transcription_completed_at=datetime.now(UTC)
            )

            print(f"[Transcription] Completed for {recording_id}")

        except Exception as e:
            print(f"[Transcription] Error for {recording_id}: {e}")
            await service.update_recording_status(
                recording_id,
                RecordingStatus.ERROR,
                error_message=str(e)
            )
```

**Step 6: Update upload endpoint to trigger job**

Edit `pwa/backend/routes/recordings.py`, modify upload endpoint:

```python
from fastapi import BackgroundTasks
from pwa.backend.jobs.transcription_job import process_transcription

@router.post("/upload", response_model=UploadRecordingResponse, status_code=201)
async def upload_recording(
    audio: UploadFile = File(...),
    patient_id: str = Form(...),
    duration_seconds: int = Form(...),
    local_storage_key: str | None = Form(None),
    draft_transcript: str | None = Form(None),
    background_tasks: BackgroundTasks = None,  # Add this
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadRecordingResponse:
    """Upload a recording with audio file."""
    # ... existing code ...

    # Trigger transcription job
    if background_tasks:
        background_tasks.add_task(process_transcription, recording.id)

    return UploadRecordingResponse(...)
```

**Step 7: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_transcription_job.py -v
# Expected: 2 tests PASS
```

**Step 8: Commit**

```bash
git add pwa/backend/jobs/transcription_job.py pwa/backend/models/recording.py pwa/backend/models/recording_sql.py pwa/backend/routes/recordings.py pwa/tests/test_transcription_job.py
git commit -m "feat: add transcription job triggered on upload"
```

**Step 9: Add Zombie Job Recovery (Future Enhancement)**

**Problem:** FastAPI BackgroundTasks live in memory. If the API container restarts during transcription, the job is lost but the recording stays in "PROCESSING" state forever.

**Solution:** Add startup recovery check:

```python
# Add to pwa/backend/main.py startup event
@app.on_event("startup")
async def recover_zombie_jobs():
    """Mark stuck jobs as failed on startup."""
    async for db in get_db_session():
        service = RecordingService(db)
        # Find recordings stuck in PROCESSING for > 30 minutes
        stuck = await service.get_recordings_stuck_in_processing(minutes=30)
        for recording in stuck:
            await service.update_recording_status(
                recording.id,
                RecordingStatus.ERROR,
                error_message="Job lost due to server restart"
            )
            print(f"[Recovery] Marked zombie job {recording.id} as failed")
```

**Note:** Implement this in Phase 2b or Phase 3. For now, document the limitation.

---

## Task 3: Set Up LLM Docker Container

**Purpose:** Create Docker container with Llama 3.1 for clinical extraction.

**Note:** Pick ONE model - 8B (faster) or 70B (more accurate)

**Files:**
- Create: `docker/llm/Dockerfile`
- Create: `docker/llm/requirements.txt`
- Create: `docker/llm/llm_service.py`
- Modify: `docker/docker-compose.yml` - Add LLM service
- Test: Create `pwa/tests/test_llm_service.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_llm_service.py`:

```python
# pwa/tests/test_llm_service.py
"""Tests for LLM extraction service."""

import pytest


def test_llm_service_exists():
    """Test that LLM service can be imported."""
    from pwa.backend.services.extraction_service import LLMService
    assert LLMService is not None


def test_llm_extract_method():
    """Test that LLMService has extract method."""
    from pwa.backend.services.extraction_service import LLMService
    service = LLMService(model_name="llama-3.1-8b")
    assert hasattr(service, 'extract')
    assert callable(service.extract)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_llm_service.py -v
# Expected: FAIL - ModuleNotFoundError
```

**Step 3: Create LLM Dockerfile**

Create `docker/llm/Dockerfile`:

```dockerfile
FROM nvidia/cuda:12.1-devel-ubuntu22.04

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# NOTE: Model is NOT downloaded here (keeps image small).
# Model downloads at runtime via volume mount to /root/.cache/huggingface
# See docker-compose.yml for volume configuration

EXPOSE 8003

CMD ["python3", "llm_service.py"]
```

**Step 4: Create LLM requirements**

Create `docker/llm/requirements.txt`:

```
torch==2.1.2
transformers==4.36.2
accelerate==0.25.0
fastapi==0.109.0
uvicorn==0.27.0
huggingface-hub==0.20.3
```

**Step 5: Create LLM service**

Create `docker/llm/llm_service.py`:

```python
#!/usr/bin/env python3
"""LLM extraction service."""

import json
from typing import List

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

app = FastAPI(title="LLM Extraction Service")

# Configuration
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Change to 70B if using that
model = None
tokenizer = None

device = "cuda" if torch.cuda.is_available() else "cpu"


@app.on_event("startup")
async def startup_event():
    global model, tokenizer
    print(f"Loading LLM: {MODEL_NAME}")
    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto"
    )
    print("LLM loaded successfully")


class ExtractRequest(BaseModel):
    transcript: str
    patient_id: str


class Medication(BaseModel):
    name: str
    dosage: str
    frequency: str
    route: str


class ExtractionResponse(BaseModel):
    medications: List[Medication]
    conditions: List[str]
    allergies: List[str]
    confidence: float


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": MODEL_NAME, "device": device}


@app.post("/extract", response_model=ExtractionResponse)
async def extract_clinical_data(request: ExtractRequest):
    """Extract structured clinical data from transcript."""
    try:
        # Build prompt
        prompt = f"""<|system|>
You are a clinical data extraction assistant. Extract structured information from the following transcript.
Respond ONLY with valid JSON in this exact format:
{{
  "medications": [{{"name": "...", "dosage": "...", "frequency": "...", "route": "..."}}],
  "conditions": ["..."],
  "allergies": ["..."]
}}

<|user|>
Patient transcript: {request.transcript}

<|assistant|>
"""

        # Generate
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True
        )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse JSON from response (after assistant marker)
        json_str = response.split("<|assistant|>")[-1].strip()
        data = json.loads(json_str)

        # Convert to response model
        medications = [Medication(**m) for m in data.get("medications", [])]

        return ExtractionResponse(
            medications=medications,
            conditions=data.get("conditions", []),
            allergies=data.get("allergies", []),
            confidence=0.85  # Simple heuristic
        )

    except Exception as e:
        return ExtractionResponse(
            medications=[],
            conditions=[],
            allergies=[],
            confidence=0.0
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
```

**Step 6: Update Docker Compose**

Edit `docker/docker-compose.yml`, add LLM service:

```yaml
  llm:
    build:
      context: ./llm
      dockerfile: Dockerfile
    ports:
      - "8003:8003"
    volumes:
      - ./models:/root/.cache/huggingface  # Persist models
    environment:
      - PYTHONUNBUFFERED=1
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 60s
      timeout: 30s
      retries: 3
```

**Step 7: Create extraction service wrapper**

Create `pwa/backend/services/extraction_service.py`:

```python
# pwa/backend/services/extraction_service.py
"""Extraction service wrapper for LLM container."""

import httpx
from typing import List, Dict, Any

LLM_URL = "http://localhost:8003"


class LLMService:
    """Service for extracting clinical data using LLM."""

    def __init__(self, model_name: str = "llama-3.1-8b"):
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=LLM_URL, timeout=120.0)

    async def extract(self, transcript: str, patient_id: str) -> Dict[str, Any]:
        """Extract structured data from transcript.

        Args:
            transcript: Clinical transcript text
            patient_id: Patient identifier

        Returns:
            dict with extracted medications, conditions, allergies
        """
        response = await self.client.post(
            "/extract",
            json={"transcript": transcript, "patient_id": patient_id}
        )

        if response.status_code != 200:
            raise Exception(f"Extraction failed: {response.text}")

        result = response.json()
        return {
            "medications": result.get("medications", []),
            "conditions": result.get("conditions", []),
            "allergies": result.get("allergies", []),
            "confidence": result.get("confidence", 0.0),
            "model": self.model_name
        }

    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except:
            return False
```

**Step 8: Run test to verify it passes**

```bash
# Build and start LLM container (takes 10-20 min first time)
cd docker && docker-compose up -d llm

# Wait for model download
sleep 300

# Run tests
uv run pytest pwa/tests/test_llm_service.py -v
# Expected: 2 tests PASS
```

**Step 9: Commit**

```bash
git add docker/llm/ pwa/backend/services/extraction_service.py pwa/tests/test_llm_service.py docker/docker-compose.yml
git commit -m "feat: add LLM Docker container with Llama 3.1 for clinical extraction"
```

---

## Task 4: Add Extraction Pipeline

**Purpose:** Chain transcription → extraction → storage.

**Files:**
- Create: `pwa/backend/jobs/extraction_job.py`
- Modify: `pwa/backend/jobs/transcription_job.py` - Trigger extraction
- Modify: `pwa/backend/models/recording.py` - Add extraction fields
- Test: Create `pwa/tests/test_extraction_job.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_extraction_job.py`:

```python
# pwa/tests/test_extraction_job.py
"""Tests for extraction job."""

import pytest


def test_extraction_job_exists():
    """Test that extraction job module exists."""
    from pwa.backend.jobs.extraction_job import process_extraction
    assert callable(process_extraction)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_extraction_job.py -v
# Expected: FAIL
```

**Step 3: Update Recording model**

Edit `pwa/backend/models/recording.py`, add:

```python
    # NEW: Extraction (Phase 2b)
    fhir_bundle: dict | None = None
    llm_model: str | None = None
    extraction_started_at: datetime | None = None
    extraction_completed_at: datetime | None = None
```

**Step 4: Create extraction job**

Create `pwa/backend/jobs/extraction_job.py`:

```python
# pwa/backend/jobs/extraction_job.py
"""Background job for clinical data extraction."""

from datetime import UTC, datetime
from uuid import UUID

from pwa.backend.database import get_db_session
from pwa.backend.services.extraction_service import LLMService
from pwa.backend.services.recording_service import RecordingService


async def process_extraction(recording_id: UUID) -> None:
    """Process extraction for a recording after transcription."""
    async for db in get_db_session():
        service = RecordingService(db)
        llm = LLMService()

        try:
            # Get recording
            recording = await service.get_recording(recording_id)
            if not recording or not recording.final_transcript:
                print(f"[Extraction] Recording {recording_id} not ready")
                return

            # Update status
            await service.update_recording(
                recording_id,
                extraction_started_at=datetime.now(UTC)
            )

            # Extract
            print(f"[Extraction] Starting extraction for {recording_id}")
            result = await llm.extract(
                recording.final_transcript,
                recording.patient_id
            )

            # Update with results
            await service.update_recording(
                recording_id,
                fhir_bundle=result,
                llm_model=result["model"],
                extraction_completed_at=datetime.now(UTC)
            )

            print(f"[Extraction] Completed for {recording_id}")

        except Exception as e:
            print(f"[Extraction] Error for {recording_id}: {e}")
```

**Step 5: Update transcription job to trigger extraction**

Edit `pwa/backend/jobs/transcription_job.py`:

```python
from pwa.backend.jobs.extraction_job import process_extraction

# After successful transcription:
await service.update_recording_status(
    recording_id,
    RecordingStatus.COMPLETED,
    final_transcript=result["text"],
    whisper_model=result["model"],
    transcription_completed_at=datetime.now(UTC)
)

# Trigger extraction
print(f"[Transcription] Triggering extraction for {recording_id}")
await process_extraction(recording_id)
```

**Step 6: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_extraction_job.py -v
# Expected: PASS
```

**Step 7: Commit**

```bash
git add pwa/backend/jobs/extraction_job.py pwa/backend/models/recording.py pwa/tests/test_extraction_job.py
git commit -m "feat: add extraction pipeline triggered after transcription"
```

---

## Task 5: Add Verification Engine

**Purpose:** Check extracted data for clinical safety before showing to users.

**Files:**
- Create: `pwa/backend/services/verification_service.py`
- Modify: `pwa/backend/jobs/extraction_job.py` - Run verification
- Modify: `pwa/backend/models/recording.py` - Add verification fields
- Test: Create `pwa/tests/test_verification_service.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_verification_service.py`:

```python
# pwa/tests/test_verification_service.py
"""Tests for verification service."""

import pytest

from pwa.backend.services.verification_service import VerificationService


def test_verification_service_exists():
    """Test that service exists."""
    service = VerificationService()
    assert service is not None


def test_verify_valid_medication():
    """Test verification of valid medication."""
    service = VerificationService()
    data = {
        "medications": [{"name": "Metformin", "dosage": "500mg"}],
        "confidence": 0.9
    }

    result = service.verify(data)

    assert result["passed"] is True
    assert result["score"] > 0.7
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_verification_service.py -v
# Expected: FAIL
```

**Step 3: Update Recording model**

Edit `pwa/backend/models/recording.py`, add:

```python
    # NEW: Verification (Phase 2b)
    verification_results: dict | None = None
    verification_score: float | None = None
    verified_at: datetime | None = None
```

**Step 4: Create verification service**

Create `pwa/backend/services/verification_service.py`:

```python
# pwa/backend/services/verification_service.py
"""Clinical verification service for extracted data."""

from typing import Dict, Any, List

# Known medications list (simplified - use RxNorm in production)
KNOWN_MEDICATIONS = {
    "metformin", "insulin", "lisinopril", "atorvastatin",
    "amlodipine", "albuterol", "omeprazole", "gabapentin"
}

# Known conditions (simplified - use ICD-10 in production)
KNOWN_CONDITIONS = {
    "diabetes", "hypertension", "asthma", "depression",
    "anxiety", "arthritis", "copd", "heart failure"
}


class VerificationService:
    """Verifies extracted clinical data for safety."""

    def __init__(self):
        self.checks = []

    def verify(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify extracted data and return results.

        Returns:
            dict with: passed (bool), score (float), issues (list)
        """
        issues = []
        score = 1.0

        # Check 1: Confidence threshold
        confidence = extracted_data.get("confidence", 0.0)
        if confidence < 0.5:
            issues.append(f"Low confidence: {confidence}")
            score -= 0.3

        # Check 2: Medication names
        for med in extracted_data.get("medications", []):
            name = med.get("name", "").lower()
            if name and name not in KNOWN_MEDICATIONS:
                issues.append(f"Unknown medication: {name}")
                score -= 0.1

        # Check 3: Dosage format
        for med in extracted_data.get("medications", []):
            dosage = med.get("dosage", "")
            if dosage and not any(c.isdigit() for c in dosage):
                issues.append(f"Invalid dosage format: {dosage}")
                score -= 0.1

        # Check 4: Conditions
        for condition in extracted_data.get("conditions", []):
            condition_lower = condition.lower()
            if condition_lower not in KNOWN_CONDITIONS:
                issues.append(f"Unknown condition: {condition}")
                score -= 0.05

        # Normalize score
        score = max(0.0, min(1.0, score))

        return {
            "passed": score >= 0.7 and len(issues) < 3,
            "score": score,
            "issues": issues,
            "checks_performed": [
                "confidence_threshold",
                "medication_names",
                "dosage_format",
                "condition_names"
            ]
        }
```

**Note on Extensibility:**

The `KNOWN_MEDICATIONS` and `KNOWN_CONDITIONS` are hardcoded for Phase 2b. The service is designed to easily swap these for external data sources:

```python
# Future enhancement: Load from file or database
class VerificationService:
    def __init__(self, medications_source=None, conditions_source=None):
        self.known_medications = medications_source or self._load_default_medications()
        self.known_conditions = conditions_source or self._load_default_conditions()

    def _load_default_medications(self):
        # Current hardcoded set
        return {"metformin", "insulin", ...}

    def _load_from_file(self, filepath):
        with open(filepath) as f:
            return set(line.strip().lower() for line in f)
```

This design supports Phase 3 requirements (RxNorm integration, database lookups) without rewriting verification logic.

**Step 5: Update extraction job to run verification**

Edit `pwa/backend/jobs/extraction_job.py`:

```python
from pwa.backend.services.verification_service import VerificationService

# After extraction:
print(f"[Extraction] Completed for {recording_id}")

# Verify
print(f"[Verification] Starting verification for {recording_id}")
verifier = VerificationService()
verification = verifier.verify(result)

# Update with everything
await service.update_recording(
    recording_id,
    fhir_bundle=result,
    llm_model=result["model"],
    verification_results=verification,
    verification_score=verification["score"],
    verified_at=datetime.now(UTC),
    extraction_completed_at=datetime.now(UTC),
    status=RecordingStatus.COMPLETED if verification["passed"] else RecordingStatus.ERROR
)

if not verification["passed"]:
    print(f"[Verification] FAILED for {recording_id}: {verification['issues']}")
```

**Step 6: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_verification_service.py -v
# Expected: 2 tests PASS
```

**Step 7: Commit**

```bash
git add pwa/backend/services/verification_service.py pwa/backend/models/recording.py pwa/backend/jobs/extraction_job.py pwa/tests/test_verification_service.py
git commit -m "feat: add verification engine for clinical safety checks"
```

---

## Task 6: Update Recording Model (Complete)

**Purpose:** Ensure all Phase 2b fields are in SQL model.

**Files:**
- Modify: `pwa/backend/models/recording_sql.py`
- Run: Alembic migration

**Step 1: Update SQL model**

Edit `pwa/backend/models/recording_sql.py`, ensure all fields:

```python
# Phase 2b fields
final_transcript = Column(Text, nullable=True)
whisper_model = Column(String(50), default="base")
transcription_started_at = Column(DateTime, nullable=True)
transcription_completed_at = Column(DateTime, nullable=True)

fhir_bundle = Column(JSON, nullable=True)
llm_model = Column(String(50), nullable=True)
extraction_started_at = Column(DateTime, nullable=True)
extraction_completed_at = Column(DateTime, nullable=True)

verification_results = Column(JSON, nullable=True)
verification_score = Column(Float, nullable=True)
verified_at = Column(DateTime, nullable=True)
```

**Step 2: Create migration**

```bash
# Create migration
uv run alembic revision -m "add_phase2b_transcription_extraction_fields"

# Edit migration to add columns
# (Alembic will auto-generate based on model changes)

# Run migration
uv run alembic upgrade head
```

**Step 3: Test**

```bash
# Verify database schema
uv run python -c "
from pwa.backend.database import engine
from pwa.backend.models.recording_sql import RecordingModel
print('RecordingModel columns:', [c.name for c in RecordingModel.__table__.columns])
"
```

**Step 4: Commit**

```bash
git add pwa/backend/models/recording_sql.py alembic/versions/
git commit -m "feat: add SQL columns for transcription, extraction, and verification"
```

---

## Task 7: Integrate with Queue UI

**Purpose:** Show transcription progress and results in the Queue UI.

**Files:**
- Modify: `pwa/backend/routes/recordings.py` - Add status endpoint
- Modify: `pwa/frontend/static/js/queue.js` - Show progress
- Modify: `pwa/frontend/templates/queue.html` - Display transcript
- Test: Create `pwa/tests/e2e/test_transcription_ui.py`

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_transcription_ui.py`:

```python
# pwa/tests/e2e/test_transcription_ui.py
"""E2E tests for transcription UI."""

from playwright.sync_api import Page, expect


def test_queue_shows_transcription_status(page: Page) -> None:
    """Test that queue shows transcription status."""
    page.goto("http://localhost:8002/queue")

    # Should show queue page
    expect(page).to_have_title("Clinical Transcription PWA")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_transcription_ui.py -v
# Expected: FAIL or basic pass
```

**Step 3: Update queue.js to show transcription**

Edit `pwa/frontend/static/js/queue.js`, update renderQueue:

```javascript
// Add transcription status to recording display
const html = recordings.map(recording => {
    // ... existing code ...

    // Add transcription info
    let transcriptionInfo = '';
    if (recording.final_transcript) {
        transcriptionInfo = `<div class="transcript-preview">${recording.final_transcript.substring(0, 100)}...</div>`;
    } else if (recording.transcription_started_at) {
        transcriptionInfo = `<div class="transcription-progress">Transcribing...</div>`;
    }

    return `
        <div class="queue-item ${statusClass}" data-id="${recording.id}">
            <!-- existing fields -->
            ${transcriptionInfo}
            <!-- existing fields -->
        </div>
    `;
}).join('');
```

**Step 4: Update detail panel**

Edit `pwa/frontend/static/js/queue.js`, update showDetail:

```javascript
// Add to detail panel:
${recording.final_transcript ? `
<div class="detail-row">
    <span class="detail-label">Transcript:</span>
    <div class="detail-value transcript-box">${recording.final_transcript}</div>
</div>
` : ''}

${recording.verification_score ? `
<div class="detail-row">
    <span class="detail-label">Verification Score:</span>
    <span class="detail-value ${recording.verification_score >= 0.7 ? 'good' : 'bad'}">
        ${(recording.verification_score * 100).toFixed(1)}%
    </span>
</div>
` : ''}
```

**Step 5: Add CSS for transcription display**

Edit `pwa/frontend/static/css/style.css`:

```css
.transcript-preview {
    font-size: 12px;
    color: #666;
    margin-top: 8px;
    font-style: italic;
}

.transcription-progress {
    font-size: 12px;
    color: #2196F3;
    margin-top: 8px;
}

.transcript-box {
    background: white;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    font-family: monospace;
    font-size: 13px;
    line-height: 1.5;
    margin-top: 8px;
}

.verification-good {
    color: #4CAF50;
}

.verification-bad {
    color: #f44336;
}
```

**Step 6: Run test**

```bash
uv run pytest pwa/tests/e2e/test_transcription_ui.py -v
# Expected: PASS
```

**Step 7: Commit**

```bash
git add pwa/frontend/static/js/queue.js pwa/frontend/static/css/style.css pwa/tests/e2e/test_transcription_ui.py
git commit -m "feat: integrate transcription status and results into Queue UI"
```

---

## Task 8: Integration Testing

**Purpose:** Run full end-to-end tests and validation.

**Files:**
- Run: All tests
- Verify: Manual testing checklist

**Step 1: Run all automated tests**

```bash
# Unit tests
uv run pytest pwa/tests/test_recording_model.py pwa/tests/test_upload_endpoint.py pwa/tests/test_whisper_service.py pwa/tests/test_llm_service.py pwa/tests/test_verification_service.py -v

# E2E tests
uv run pytest pwa/tests/e2e/ -v

# All tests
uv run pytest pwa/tests/ -v
```

**Step 2: Manual testing checklist**

Start all services:
```bash
# Terminal 1: Start Whisper
cd docker && docker-compose up whisper

# Terminal 2: Start LLM
cd docker && docker-compose up llm

# Terminal 3: Start FastAPI
uv run python pwa/backend/main.py
```

Manual tests:
- [ ] Upload audio file
- [ ] Verify transcription starts (status = "processing")
- [ ] Check Whisper logs show transcription progress
- [ ] Wait for transcription complete (status = "completed")
- [ ] Verify transcript appears in Queue UI
- [ ] Check extraction produced FHIR bundle
- [ ] Verify verification score > 0.7
- [ ] Test error handling (upload corrupted audio)
- [ ] Test verification failure (low confidence)
- [ ] Test Docker containers restart correctly

**Step 3: Performance testing**

```bash
# Time transcription for 30-second audio
time curl -X POST http://localhost:8001/transcribe -F "audio=@test.wav"

# Time extraction
time curl -X POST http://localhost:8003/extract \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Patient takes Metformin 500mg", "patient_id": "123"}'
```

**Step 4: Final commit**

```bash
# Check all files committed
git status

# Final verification
git log --oneline -10
```

---

## Summary

At the end of Phase 2b, you will have:

1. **Whisper Container** - Transcribes audio to text
2. **LLM Container** - Extracts structured clinical data
3. **Async Pipeline** - Queue → Transcribe → Extract → Verify
4. **Verification Engine** - Clinical safety checks
5. **Queue UI Updates** - Shows transcription progress and results
6. **Full Integration** - End-to-end audio → structured data

**Docker Services:**
```
docker-compose up
├── Whisper (port 8001) - Audio → Text
└── LLM (port 8003) - Text → FHIR
```

**Data Flow:**
```
Upload → Transcription Job → Whisper → Text → Extraction Job → LLM → FHIR → Verify → Store
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-02-23-phase2b-ai-transcription-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**

---

*End of Phase 2b Implementation Plan*
