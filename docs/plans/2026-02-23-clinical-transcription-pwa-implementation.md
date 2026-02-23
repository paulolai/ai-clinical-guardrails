# Clinical Transcription PWA - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Progressive Web Application for clinical voice transcription with offline-first capabilities, running entirely on-premise with local AI models (Whisper + Llama 3.1).

**Architecture:** HTMX frontend (server-rendered Jinja2 templates) with Service Worker for offline capabilities, FastAPI backend extending existing API, all AI processing local to Mac Studio via Docker Compose.

**Tech Stack:** Python 3.12, FastAPI, HTMX, Jinja2, PostgreSQL, Keycloak, Whisper, Llama.cpp/vLLM, Docker Compose

**Reference Design:** [2026-02-23-clinical-transcription-pwa-design.md](./2026-02-23-clinical-transcription-pwa-design.md)

---

## Phase 1: Foundation (Week 1-2)

### Task 1: Create PWA Directory Structure

**Files:**
- Create: `pwa/`
- Create: `pwa/frontend/`
- Create: `pwa/frontend/templates/`
- Create: `pwa/frontend/static/`
- Create: `pwa/frontend/static/js/`
- Create: `pwa/frontend/static/css/`
- Create: `pwa/backend/`
- Create: `pwa/backend/routes/`
- Create: `pwa/backend/models/`
- Create: `pwa/docker/`
- Create: `pwa/tests/`

**Step 1: Create directory structure**

```bash
mkdir -p pwa/frontend/templates pwa/frontend/static/js pwa/frontend/static/css
mkdir -p pwa/backend/routes pwa/backend/models
mkdir -p pwa/docker pwa/tests
```

**Step 2: Create __init__.py files**

```bash
touch pwa/__init__.py
 touch pwa/frontend/__init__.py
 touch pwa/backend/__init__.py
 touch pwa/backend/routes/__init__.py
 touch pwa/backend/models/__init__.py
 touch pwa/tests/__init__.py
```

**Step 3: Commit**

```bash
git add pwa/
git commit -m "chore: create PWA directory structure"
```

---

### Task 2: Create Basic FastAPI Application for PWA

**Files:**
- Create: `pwa/backend/main.py`
- Create: `pwa/backend/config.py`
- Create: `pwa/tests/test_main.py`

**Step 1: Write the failing test**

```python
# pwa/tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from pwa.backend.main import app

client = TestClient(app)

def test_health_check():
    """Test that the PWA API health endpoint works."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "pwa" in response.json()["components"]
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_main.py::test_health_check -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'pwa'"

**Step 3: Write minimal implementation**

```python
# pwa/backend/config.py
from pydantic_settings import BaseSettings

class PWASettings(BaseSettings):
    """Configuration for the PWA backend."""
    app_name: str = "Clinical Transcription PWA"
    debug: bool = False

    # Database
    database_url: str = "postgresql://localhost/pwa"

    # AI Services
    whisper_url: str = "http://localhost:9000"
    llm_url: str = "http://localhost:8001"

    # Auth
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "clinical-pwa"

    class Config:
        env_prefix = "PWA_"

settings = PWASettings()
```

```python
# pwa/backend/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pwa.backend.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

# CORS for PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for the PWA."""
    return {
        "status": "healthy",
        "components": {
            "pwa": "ok",
            "api": "ok"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_main.py::test_health_check -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add basic PWA FastAPI application with health check"
```

---

### Task 3: Create Recording Model and Database Schema

**Files:**
- Create: `pwa/backend/models/recording.py`
- Create: `pwa/tests/test_recording_model.py`

**Step 1: Write the failing test**

```python
# pwa/tests/test_recording_model.py
import pytest
from datetime import datetime
from uuid import UUID, uuid4
from pwa.backend.models.recording import Recording, RecordingStatus

def test_recording_model_creation():
    """Test that Recording model can be created with required fields."""
    recording = Recording(
        id=uuid4(),
        patient_id="test-patient-123",
        clinician_id="test-clinician-456",
        audio_file_path="/tmp/test.wav",
        duration_seconds=120,
        status=RecordingStatus.PENDING
    )

    assert recording.id is not None
    assert recording.patient_id == "test-patient-123"
    assert recording.status == RecordingStatus.PENDING
    assert isinstance(recording.created_at, datetime)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_model.py::test_recording_model_creation -v
```

Expected: FAIL with "ImportError: cannot import name 'Recording'"

**Step 3: Write minimal implementation**

```python
# pwa/backend/models/recording.py
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class RecordingStatus(str, Enum):
    """Status of a recording."""
    PENDING = "pending"           # Recorded, waiting for upload/processing
    UPLOADING = "uploading"       # Currently uploading to server
    QUEUED = "queued"             # Uploaded, waiting for transcription
    PROCESSING = "processing"     # Being transcribed/verified
    COMPLETED = "completed"       # Ready for review
    ERROR = "error"               # Processing failed

class Recording(BaseModel):
    """Model representing a clinical recording."""
    id: UUID = Field(default_factory=uuid4)
    patient_id: str = Field(..., description="Patient identifier")
    clinician_id: str = Field(..., description="Clinician who recorded")

    # Audio
    audio_file_path: Optional[str] = None
    audio_file_size: Optional[int] = None
    duration_seconds: Optional[int] = None

    # Status
    status: RecordingStatus = RecordingStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    # Results (populated after processing)
    transcript: Optional[str] = None
    verification_results: Optional[dict] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "patient_id": "patient-123",
                "clinician_id": "clinician-456",
                "duration_seconds": 120,
                "status": "pending"
            }
        }
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_recording_model.py::test_recording_model_creation -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add Recording model with status tracking"
```

---

### Task 4: Create Recording Repository/Service Layer

**Files:**
- Create: `pwa/backend/services/recording_service.py`
- Create: `pwa/tests/test_recording_service.py`

**Step 1: Write the failing test**

```python
# pwa/tests/test_recording_service.py
import pytest
from uuid import uuid4
from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.services.recording_service import RecordingService

@pytest.fixture
def service():
    return RecordingService()

def test_create_recording(service):
    """Test creating a new recording."""
    recording = service.create_recording(
        patient_id="patient-123",
        clinician_id="clinician-456",
        duration_seconds=120
    )

    assert recording.patient_id == "patient-123"
    assert recording.status == RecordingStatus.PENDING
    assert recording.duration_seconds == 120

def test_get_recording(service):
    """Test retrieving a recording by ID."""
    # Create a recording first
    created = service.create_recording(
        patient_id="patient-123",
        clinician_id="clinician-456",
        duration_seconds=120
    )

    # Retrieve it
    retrieved = service.get_recording(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.patient_id == "patient-123"

def test_get_nonexistent_recording(service):
    """Test retrieving a recording that doesn't exist."""
    retrieved = service.get_recording(uuid4())
    assert retrieved is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_service.py -v
```

Expected: FAIL with "ImportError: cannot import name 'RecordingService'"

**Step 3: Write minimal implementation**

```python
# pwa/backend/services/recording_service.py
from typing import Optional, List
from uuid import UUID
from pwa.backend.models.recording import Recording, RecordingStatus

class RecordingService:
    """Service for managing recordings."""

    # In-memory storage for now (will be replaced with DB)
    _recordings: dict = {}

    def create_recording(
        self,
        patient_id: str,
        clinician_id: str,
        duration_seconds: int,
        audio_file_path: Optional[str] = None
    ) -> Recording:
        """Create a new recording."""
        recording = Recording(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
            status=RecordingStatus.PENDING
        )
        self._recordings[recording.id] = recording
        return recording

    def get_recording(self, recording_id: UUID) -> Optional[Recording]:
        """Get a recording by ID."""
        return self._recordings.get(recording_id)

    def get_recordings_for_clinician(
        self,
        clinician_id: str,
        status: Optional[RecordingStatus] = None
    ) -> List[Recording]:
        """Get all recordings for a clinician, optionally filtered by status."""
        recordings = [
            r for r in self._recordings.values()
            if r.clinician_id == clinician_id
        ]
        if status:
            recordings = [r for r in recordings if r.status == status]
        return recordings

    def update_recording_status(
        self,
        recording_id: UUID,
        status: RecordingStatus,
        error_message: Optional[str] = None
    ) -> Optional[Recording]:
        """Update the status of a recording."""
        recording = self._recordings.get(recording_id)
        if recording:
            recording.status = status
            if error_message:
                recording.error_message = error_message
        return recording
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_recording_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add RecordingService with in-memory storage"
```

---

### Task 5: Create Recording API Endpoints

**Files:**
- Create: `pwa/backend/routes/recordings.py`
- Modify: `pwa/backend/main.py` to include routes
- Create: `pwa/tests/test_recording_routes.py`

**Step 1: Write the failing test**

```python
# pwa/tests/test_recording_routes.py
import pytest
from fastapi.testclient import TestClient
from pwa.backend.main import app

client = TestClient(app)

def test_create_recording_endpoint():
    """Test creating a recording via API."""
    response = client.post(
        "/api/v1/recordings",
        json={
            "patient_id": "patient-123",
            "duration_seconds": 120
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["duration_seconds"] == 120
    assert "id" in data

def test_get_recording_endpoint():
    """Test getting a recording by ID."""
    # Create first
    create_response = client.post(
        "/api/v1/recordings",
        json={
            "patient_id": "patient-123",
            "duration_seconds": 120
        }
    )
    recording_id = create_response.json()["id"]

    # Get
    response = client.get(f"/api/v1/recordings/{recording_id}")
    assert response.status_code == 200
    assert response.json()["id"] == recording_id

def test_get_nonexistent_recording():
    """Test getting a recording that doesn't exist."""
    response = client.get("/api/v1/recordings/123e4567-e89b-12d3-a456-426614174000")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_routes.py -v
```

Expected: FAIL with 404 errors (routes don't exist yet)

**Step 3: Write minimal implementation**

```python
# pwa/backend/routes/recordings.py
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.services.recording_service import RecordingService

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])

class CreateRecordingRequest(BaseModel):
    patient_id: str
    duration_seconds: int
    audio_file_path: Optional[str] = None

class RecordingResponse(BaseModel):
    id: str
    patient_id: str
    clinician_id: str
    duration_seconds: int
    status: str
    created_at: str

# Dependency
def get_recording_service():
    return RecordingService()

@router.post("", response_model=RecordingResponse, status_code=201)
async def create_recording(
    request: CreateRecordingRequest,
    service: RecordingService = Depends(get_recording_service)
):
    """Create a new recording."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"  # Placeholder

    recording = service.create_recording(
        patient_id=request.patient_id,
        clinician_id=clinician_id,
        duration_seconds=request.duration_seconds,
        audio_file_path=request.audio_file_path
    )

    return RecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds,
        status=recording.status.value,
        created_at=recording.created_at.isoformat()
    )

@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: UUID,
    service: RecordingService = Depends(get_recording_service)
):
    """Get a recording by ID."""
    recording = service.get_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    return RecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds or 0,
        status=recording.status.value,
        created_at=recording.created_at.isoformat()
    )

@router.get("", response_model=list[RecordingResponse])
async def list_recordings(
    status: Optional[RecordingStatus] = None,
    service: RecordingService = Depends(get_recording_service)
):
    """List recordings for the current clinician."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    recordings = service.get_recordings_for_clinician(clinician_id, status)

    return [
        RecordingResponse(
            id=str(r.id),
            patient_id=r.patient_id,
            clinician_id=r.clinician_id,
            duration_seconds=r.duration_seconds or 0,
            status=r.status.value,
            created_at=r.created_at.isoformat()
        )
        for r in recordings
    ]
```

```python
# Modify pwa/backend/main.py to include routes
from fastapi import FastAPI
from pwa.backend.routes import recordings

app = FastAPI(title="Clinical Transcription PWA")

# Include routes
app.include_router(recordings.router)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "components": {"pwa": "ok", "api": "ok"}}
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_recording_routes.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add recording API endpoints (CRUD)"
```

---

## Phase 2: Frontend Foundation (Week 2)

### Task 6: Create Base HTML Template with HTMX

**Files:**
- Create: `pwa/frontend/templates/base.html`
- Create: `pwa/frontend/static/css/style.css`
- Create: `pwa/backend/routes/pages.py`
- Modify: `pwa/backend/main.py` to serve static files and templates

**Step 1: Write the failing test**

```python
# pwa/tests/test_pages.py
from fastapi.testclient import TestClient
from pwa.backend.main import app

client = TestClient(app)

def test_home_page():
    """Test that the home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Clinical Transcription" in response.text
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_pages.py::test_home_page -v
```

Expected: FAIL with 404

**Step 3: Write minimal implementation**

```python
# pwa/backend/routes/pages.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="pwa/frontend/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with patient list."""
    return templates.TemplateResponse("base.html", {"request": request})
```

```html
<!-- pwa/frontend/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinical Transcription PWA</title>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Styles -->
    <link rel="stylesheet" href="/static/css/style.css">

    <!-- PWA Manifest (to be added later) -->
    <!-- <link rel="manifest" href="/static/manifest.json"> -->
</head>
<body>
    <header>
        <h1>Clinical Transcription</h1>
        <nav>
            <a href="/">Patients</a>
            <a href="/queue">Queue</a>
        </nav>
    </header>

    <main id="main-content">
        {% block content %}
        <p>Welcome to the Clinical Transcription PWA.</p>
        {% endblock %}
    </main>

    <footer>
        <p>Offline-capable • Local AI • Secure</p>
    </footer>

    <!-- Service Worker (to be added later) -->
    <!-- <script src="/static/js/sw-register.js"></script> -->
</body>
</html>
```

```css
/* pwa/frontend/static/css/style.css */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

header {
    background: #2c3e50;
    color: white;
    padding: 1rem;
    text-align: center;
}

header h1 {
    margin-bottom: 0.5rem;
}

nav a {
    color: white;
    text-decoration: none;
    margin: 0 1rem;
    opacity: 0.8;
}

nav a:hover {
    opacity: 1;
}

main {
    max-width: 800px;
    margin: 2rem auto;
    padding: 0 1rem;
}

footer {
    text-align: center;
    padding: 2rem;
    color: #666;
    font-size: 0.9rem;
}

/* Recording button styles */
.record-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #e74c3c;
    color: white;
    border: none;
    padding: 1rem 2rem;
    font-size: 1.1rem;
    border-radius: 50px;
    cursor: pointer;
    transition: all 0.2s;
}

.record-btn:hover {
    background: #c0392b;
    transform: scale(1.05);
}

.record-btn.recording {
    background: #95a5a6;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Status indicators */
.status-pending { color: #f39c12; }
.status-completed { color: #27ae60; }
.status-error { color: #e74c3c; }
```

```python
# Modify pwa/backend/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pwa.backend.routes import recordings, pages

app = FastAPI(title="Clinical Transcription PWA")

# Mount static files
app.mount("/static", StaticFiles(directory="pwa/frontend/static"), name="static")

# Include routes
app.include_router(recordings.router)
app.include_router(pages.router)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "components": {"pwa": "ok", "api": "ok"}}
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_pages.py::test_home_page -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add base HTML template with HTMX and styling"
```

---

### Task 7: Create Recording Interface Page

**Files:**
- Create: `pwa/frontend/templates/record.html`
- Create: `pwa/frontend/static/js/recorder.js`
- Modify: `pwa/backend/routes/pages.py` to add recording page

**Step 1: Create the recording interface**

```html
<!-- pwa/frontend/templates/record.html -->
{% extends "base.html" %}

{% block content %}
<div class="recording-interface">
    <h2>Record for Patient: {{ patient_id }}</h2>

    <div class="recorder-container">
        <button id="record-btn" class="record-btn" onclick="toggleRecording()">
            <span id="record-icon">●</span>
            <span id="record-text">Start Recording</span>
        </button>

        <div id="recording-status" class="hidden">
            <p>Recording... <span id="timer">00:00</span></p>
            <div class="waveform" id="waveform"></div>
        </div>

        <div id="upload-status" class="hidden">
            <p>Uploading...</p>
            <progress id="upload-progress" value="0" max="100"></progress>
        </div>
    </div>

    <div id="result" class="hidden">
        <h3>Recording Saved</h3>
        <p>Status: <span id="recording-status-text">Processing...</span></p>
        <p>Your recording has been queued for transcription.</p>
        <a href="/queue" class="btn">View Queue</a>
    </div>
</div>

<script src="/static/js/recorder.js"></script>
<script>
    // Initialize with patient ID from server
    const patientId = "{{ patient_id }}";
</script>
{% endblock %}
```

```javascript
// pwa/frontend/static/js/recorder.js
let mediaRecorder;
let audioChunks = [];
let recordingStartTime;
let timerInterval;
let isRecording = false;

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await uploadRecording(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();

        // Update UI
        document.getElementById('record-btn').classList.add('recording');
        document.getElementById('record-text').textContent = 'Stop Recording';
        document.getElementById('recording-status').classList.remove('hidden');

        // Start timer
        timerInterval = setInterval(updateTimer, 1000);

    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not start recording. Please ensure microphone access is allowed.');
    }
}

async function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;

        // Update UI
        document.getElementById('record-btn').classList.remove('recording');
        document.getElementById('record-text').textContent = 'Start Recording';
        document.getElementById('recording-status').classList.add('hidden');
        document.getElementById('upload-status').classList.remove('hidden');

        clearInterval(timerInterval);
    }
}

function updateTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('timer').textContent = `${minutes}:${seconds}`;
}

async function uploadRecording(audioBlob) {
    // TODO: Store locally if offline, or upload immediately if online
    // For now, always try to upload

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('patient_id', patientId || 'unknown');
    formData.append('duration_seconds', Math.floor((Date.now() - recordingStartTime) / 1000));

    try {
        const response = await fetch('/api/v1/recordings/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showResult(result);
        } else {
            // TODO: Store locally for retry
            console.error('Upload failed, storing locally for retry');
            await storeLocally(audioBlob);
            showLocalStorageMessage();
        }
    } catch (error) {
        console.error('Upload error:', error);
        // TODO: Store locally for retry
        await storeLocally(audioBlob);
        showLocalStorageMessage();
    }
}

async function storeLocally(audioBlob) {
    // TODO: Implement IndexedDB storage
    console.log('Storing locally (not yet implemented)');
}

function showResult(result) {
    document.getElementById('upload-status').classList.add('hidden');
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('recording-status-text').textContent = result.status;
}

function showLocalStorageMessage() {
    document.getElementById('upload-status').classList.add('hidden');
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('result').innerHTML = `
        <h3>Recording Saved Locally</h3>
        <p>Your recording has been saved and will upload when connection is restored.</p>
        <a href="/queue" class="btn">View Queue</a>
    `;
}

// Hidden class utility
// (add to CSS)
```

```python
# Add to pwa/backend/routes/pages.py
@router.get("/record/{patient_id}", response_class=HTMLResponse)
async def record_page(request: Request, patient_id: str):
    """Recording page for a specific patient."""
    return templates.TemplateResponse("record.html", {
        "request": request,
        "patient_id": patient_id
    })
```

**Step 2: Commit**

```bash
git add pwa/
git commit -m "feat: add recording interface with audio capture"
```

---

## Next Phases (Summary)

The detailed plan continues through:

### Phase 3: Offline Capabilities (Week 3)
- Service Worker implementation
- IndexedDB storage for audio
- Background sync
- Queue management

### Phase 4: AI Integration (Week 4)
- Whisper container setup
- LLM container setup (Llama 3.1 70B)
- Transcription pipeline
- Verification integration

### Phase 5: Authentication (Week 5)
- Keycloak integration
- JWT handling
- Login/logout flow

### Phase 6: Production Hardening (Week 6)
- Docker Compose orchestration
- Monitoring setup
- Backup procedures
- Security audit

### Phase 7: Compliance & Pilot (Week 7-8)
- Documentation
- Privacy policy
- User training materials
- Pilot with 1-2 clinicians

---

## How to Execute This Plan

**Option 1: Subagent-Driven (Recommended)**
- I dispatch fresh subagents for each task
- Review between tasks
- Iterative refinement

**Option 2: Parallel Session**
- Open new session with executing-plans skill
- Batch execution with checkpoints

**Which approach do you prefer?**

---

**Plan saved to:** `docs/plans/2026-02-23-clinical-transcription-pwa-implementation.md`
