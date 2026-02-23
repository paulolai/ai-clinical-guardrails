# Phase 2a: Offline Recording Implementation Plan (REVISED)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**⚠️ REVISED SCOPE:** Phase 2 has been split:
- **Phase 2a (This Plan)**: Offline recording and sync ONLY. AI backend is mocked.
- **Phase 2b (Next Sprint)**: Add Whisper + LLM integration.

**Why split?** Offline PWA state management and AI R&D are two massive unrelated engineering hurdles. Attempting both risks a buggy PWA and half-baked AI pipeline.

**Goal:** Add offline recording capabilities with IndexedDB storage, Service Worker with iOS fallback, and foreground sync. Mock transcription for Phase 2a.

**Architecture:** Service Worker (Workbox) intercepts upload requests and queues them in IndexedDB. When online, background sync triggers automatic upload to FastAPI server (Chrome/Android). iOS/Safari uses HTMX polling for foreground sync. Web Speech API provides draft transcription (ONLINE ONLY) for immediate feedback.

**Tech Stack:** Python 3.12, FastAPI, HTMX, IndexedDB (localForage), Workbox, Web Speech API (online only), Playwright for testing

**Reference Design:** [2025-02-23-phase2-offline-recording-design.md](./2025-02-23-phase2-offline-recording-design.md) (Revision 1.1)

---

## Prerequisites

Before starting Phase 2 implementation:

```bash
# 1. Verify Phase 1 is working
uv run pytest pwa/tests/ -v

# 2. Run the server and test recording
uv run python pwa/backend/main.py
# Open http://localhost:8002/ and verify recording works
```

---

## Sprint 1: IndexedDB Storage Foundation

### Task 1: Install localForage for IndexedDB

**Files:**
- Modify: `pwa/frontend/templates/base.html`

**Step 1: Add localForage CDN to base template**

```html
<!-- Add before closing </body> tag in base.html -->
<script src="https://cdn.jsdelivr.net/npm/localforage@1.10.0/dist/localforage.min.js"></script>
```

**Step 2: Create IndexedDB service file**

```javascript
// pwa/frontend/static/js/indexeddb-service.js
/**
 * IndexedDB service for offline audio storage
 * Uses localForage for simplified IndexedDB API
 */

const RecordingStore = {
    // Initialize the store
    async init() {
        await localforage.config({
            name: 'ClinicalTranscriptionPWA',
            storeName: 'recordings',
            description: 'Offline audio recordings'
        });
    },

    // Save a recording
    async saveRecording(recording) {
        const recordingData = {
            id: recording.id || crypto.randomUUID(),
            patient_id: recording.patient_id,
            clinician_id: recording.clinician_id,
            audio_blob: recording.audio_blob,
            draft_transcript: recording.draft_transcript || null,
            duration_seconds: recording.duration_seconds,
            created_at: recording.created_at || new Date().toISOString(),
            sync_status: 'pending_upload',
            retry_count: 0,
            last_error: null
        };

        await localforage.setItem(recordingData.id, recordingData);
        return recordingData;
    },

    // Get a recording by ID
    async getRecording(id) {
        return await localforage.getItem(id);
    },

    // Get all recordings
    async getAllRecordings() {
        const recordings = [];
        await localforage.iterate((value) => {
            recordings.push(value);
        });
        return recordings.sort((a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
        );
    },

    // Get pending uploads
    async getPendingUploads() {
        const recordings = await this.getAllRecordings();
        return recordings.filter(r => r.sync_status === 'pending_upload');
    },

    // Update recording status
    async updateStatus(id, status, error = null) {
        const recording = await this.getRecording(id);
        if (recording) {
            recording.sync_status = status;
            if (error) {
                recording.last_error = error;
            }
            if (status === 'failed') {
                recording.retry_count += 1;
            }
            await localforage.setItem(id, recording);
        }
        return recording;
    },

    // Mark as uploaded (clean up local storage)
    async markUploaded(id) {
        await localforage.removeItem(id);
    },

    // Delete a recording
    async deleteRecording(id) {
        await localforage.removeItem(id);
    },

    // Get storage stats
    async getStorageStats() {
        const recordings = await this.getAllRecordings();
        const totalSize = recordings.reduce((sum, r) => {
            return sum + (r.audio_blob?.size || 0);
        }, 0);

        return {
            count: recordings.length,
            totalSize: totalSize,
            pendingCount: recordings.filter(r => r.sync_status === 'pending_upload').length
        };
    }
};

// Initialize on load
RecordingStore.init().catch(console.error);
```

**Step 3: Commit**

```bash
git add pwa/
git commit -m "feat: add IndexedDB service with localForage"
```

---

### Task 2: Update Recording Model for Offline Support

**Files:**
- Modify: `pwa/backend/models/recording.py`
- Test: `pwa/tests/test_recording_model.py`

**Step 1: Write failing test for new fields**

```python
# pwa/tests/test_recording_model.py
import pytest
from datetime import datetime
from uuid import UUID, uuid4
from pwa.backend.models.recording import Recording, RecordingStatus

def test_recording_with_draft_transcript():
    """Test that Recording model supports draft transcript."""
    recording = Recording(
        id=uuid4(),
        patient_id="test-patient-123",
        clinician_id="test-clinician-456",
        audio_file_path="/tmp/test.wav",
        duration_seconds=120,
        status=RecordingStatus.PENDING,
        draft_transcript="This is a draft transcription from browser"
    )

    assert recording.draft_transcript == "This is a draft transcription from browser"
    assert recording.final_transcript is None

def test_recording_with_upload_tracking():
    """Test that Recording model supports upload tracking."""
    recording = Recording(
        id=uuid4(),
        patient_id="test-patient-123",
        clinician_id="test-clinician-456",
        local_storage_key="indexed-db-key-123",
        upload_attempts=2
    )

    assert recording.local_storage_key == "indexed-db-key-123"
    assert recording.upload_attempts == 2
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_model.py::test_recording_with_draft_transcript -v
uv run pytest pwa/tests/test_recording_model.py::test_recording_with_upload_tracking -v
```

Expected: FAIL with "unexpected keyword argument"

**Step 3: Add new fields to Recording model**

```python
# pwa/backend/models/recording.py
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class RecordingStatus(str, Enum):
    """Status of a recording."""
    PENDING = "pending"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class Recording(BaseModel):
    """Model representing a clinical recording."""
    id: UUID = Field(default_factory=uuid4)
    patient_id: str = Field(..., description="Patient identifier")
    clinician_id: str = Field(..., description="Clinician who recorded")

    # Audio
    audio_file_path: Optional[str] = None
    audio_file_size: Optional[int] = None
    duration_seconds: Optional[int] = None

    # Transcription (NEW FIELDS)
    draft_transcript: Optional[str] = Field(
        default=None,
        description="Draft transcription from browser Speech API"
    )
    final_transcript: Optional[str] = Field(
        default=None,
        description="Final transcription from Whisper"
    )

    # Status
    status: RecordingStatus = RecordingStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0

    # Upload tracking (NEW FIELDS)
    local_storage_key: Optional[str] = Field(
        default=None,
        description="IndexedDB key for pending uploads"
    )
    upload_attempts: int = Field(
        default=0,
        description="Number of upload retry attempts"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    # Results
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

**Step 4: Run tests to verify they pass**

```bash
uv run pytest pwa/tests/test_recording_model.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add draft_transcript, final_transcript, and upload tracking fields"
```

---

### Task 3: Create Upload API Endpoint

**Files:**
- Modify: `pwa/backend/routes/recordings.py`
- Test: `pwa/tests/test_recording_routes.py`

**Step 1: Write failing test for upload endpoint**

```python
# pwa/tests/test_recording_routes.py
import pytest
from fastapi.testclient import TestClient
from pwa.backend.main import app

client = TestClient(app)

def test_upload_recording_with_audio():
    """Test uploading a recording with audio file."""
    # Create a dummy audio file
    import io
    audio_content = b"fake audio data"

    response = client.post(
        "/api/v1/recordings/upload",
        data={
            "patient_id": "patient-123",
            "duration_seconds": "120",
            "draft_transcript": "Draft text here"
        },
        files={
            "audio": ("recording.wav", io.BytesIO(audio_content), "audio/wav")
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["duration_seconds"] == 120
    assert data["draft_transcript"] == "Draft text here"
    assert "id" in data
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_routes.py::test_upload_recording_with_audio -v
```

Expected: FAIL with 404 or "upload" not found

**Step 3: Add upload endpoint**

```python
# Modify pwa/backend/routes/recordings.py
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import shutil
from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.services.recording_service import RecordingService

router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])

# ... existing CreateRecordingRequest, RecordingResponse ...

class UploadRecordingRequest(BaseModel):
    patient_id: str
    duration_seconds: int
    draft_transcript: Optional[str] = None
    clinician_id: str = "current-clinician"

@router.post("/upload", status_code=201)
async def upload_recording(
    patient_id: str = Form(...),
    duration_seconds: int = Form(...),
    draft_transcript: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    service: RecordingService = Depends(get_recording_service)
):
    """Upload a recording with audio file."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    # Save audio file
    upload_dir = Path("uploads/recordings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{uuid4()}.wav"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Create recording
    recording = Recording(
        patient_id=patient_id,
        clinician_id=clinician_id,
        audio_file_path=str(file_path),
        audio_file_size=file_path.stat().st_size,
        duration_seconds=duration_seconds,
        draft_transcript=draft_transcript,
        status=RecordingStatus.QUEUED
    )

    # Save to service
    service._recordings[recording.id] = recording

    return {
        "id": str(recording.id),
        "patient_id": recording.patient_id,
        "clinician_id": recording.clinician_id,
        "duration_seconds": recording.duration_seconds,
        "draft_transcript": recording.draft_transcript,
        "status": recording.status.value,
        "created_at": recording.created_at.isoformat()
    }
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_recording_routes.py::test_upload_recording_with_audio -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add upload endpoint with audio file handling"
```

---

## Sprint 2: Service Worker & Background Sync

### Task 4: Set Up Workbox

**Files:**
- Create: `pwa/frontend/static/js/service-worker.js`
- Create: `pwa/frontend/static/js/sw-register.js`
- Modify: `pwa/frontend/templates/base.html`

**Step 1: Create Service Worker with Workbox**

```javascript
// pwa/frontend/static/js/service-worker.js
/**
 * Service Worker for offline capabilities
 * Uses Workbox for reliable background sync
 */

importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js');

const { strategies, routing, backgroundSync } = workbox;

// Cache static assets
workbox.routing.registerRoute(
    ({request}) => request.destination === 'image' ||
                   request.destination === 'script' ||
                   request.destination === 'style',
    new strategies.StaleWhileRevalidate({
        cacheName: 'static-assets'
    })
);

// Cache the app shell
workbox.routing.registerRoute(
    '/',
    new strategies.NetworkFirst({
        cacheName: 'app-shell'
    })
);

// Background sync for uploads
workbox.routing.registerRoute(
    '/api/v1/recordings/upload',
    new workbox.backgroundSync.BackgroundSyncPlugin('upload-queue', {
        maxRetentionTime: 24 * 60 // 24 hours in minutes
    }),
    'POST'
);

// Intercept upload requests and queue if offline
self.addEventListener('fetch', (event) => {
    if (event.request.url.includes('/api/v1/recordings/upload')) {
        event.respondWith(
            fetch(event.request.clone())
                .catch(async (error) => {
                    // Store request for later retry
                    await storeFailedRequest(event.request);
                    return new Response(JSON.stringify({
                        status: 'queued',
                        message: 'Upload queued for retry'
                    }), {
                        status: 202,
                        headers: { 'Content-Type': 'application/json' }
                    });
                })
        );
    }
});

// Listen for sync events
self.addEventListener('sync', (event) => {
    if (event.tag === 'upload-recordings') {
        event.waitUntil(syncPendingUploads());
    }
});

// Background sync function
async function syncPendingUploads() {
    const db = await openDB('failed-requests', 1);
    const requests = await db.getAll('requests');

    for (const request of requests) {
        try {
            await fetch(request.url, {
                method: request.method,
                headers: request.headers,
                body: request.body
            });
            await db.delete('requests', request.id);
        } catch (error) {
            console.error('Sync failed for request:', error);
        }
    }
}

// Store failed requests
async function storeFailedRequest(request) {
    const db = await openDB('failed-requests', 1, {
        upgrade(db) {
            db.createObjectStore('requests', { keyPath: 'id' });
        }
    });

    const body = await request.blob();
    await db.add('requests', {
        id: Date.now(),
        url: request.url,
        method: request.method,
        headers: Array.from(request.headers),
        body: body
    });
}

// Open IndexedDB helper
function openDB(name, version, upgradeCallback) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(name, version);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        if (upgradeCallback) {
            request.onupgradeneeded = (event) => {
                upgradeCallback(event.target.result);
            };
        }
    });
}

console.log('Service Worker registered');
```

**Step 2: Create Service Worker registration script**

```javascript
// pwa/frontend/static/js/sw-register.js
/**
 * Service Worker registration
 */

if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');
            console.log('SW registered:', registration.scope);

            // Listen for online/offline events
            window.addEventListener('online', () => {
                console.log('Browser is online');
                requestBackgroundSync();
            });

            window.addEventListener('offline', () => {
                console.log('Browser is offline');
            });

        } catch (error) {
            console.log('SW registration failed:', error);
            // Fallback to polling
            setupPollingFallback();
        }
    });
} else {
    console.log('Service Worker not supported');
    setupPollingFallback();
}

// Request background sync
async function requestBackgroundSync() {
    if ('sync' in registration) {
        try {
            await registration.sync.register('upload-recordings');
        } catch (error) {
            console.error('Background sync registration failed:', error);
        }
    }
}

// Polling fallback for browsers without SW support
function setupPollingFallback() {
    console.log('Using polling fallback for sync detection');
    setInterval(() => {
        if (navigator.onLine) {
            syncPendingUploads();
        }
    }, 30000); // Check every 30 seconds
}

// Global sync function for fallback
async function syncPendingUploads() {
    // This will be implemented in Task 5
    if (window.RecordingStore) {
        const pending = await window.RecordingStore.getPendingUploads();
        for (const recording of pending) {
            await uploadRecording(recording);
        }
    }
}
```

**Step 3: Add SW registration to base template**

```html
<!-- Add to pwa/frontend/templates/base.html before </body> -->
<script src="/static/js/sw-register.js"></script>
```

**Step 4: Commit**

```bash
git add pwa/
git commit -m "feat: add Service Worker with Workbox for background sync"
```

---

### Task 5: Create Upload Manager

**Files:**
- Create: `pwa/frontend/static/js/upload-manager.js`
- Test: `pwa/tests/test_upload_manager.py` (Playwright test)

**Step 1: Create upload manager**

```javascript
// pwa/frontend/static/js/upload-manager.js
/**
 * Upload Manager
 * Handles uploading recordings from IndexedDB to server
 * with retry logic and status tracking
 */

const UploadManager = {
    // Upload a single recording
    async uploadRecording(recording) {
        const formData = new FormData();
        formData.append('patient_id', recording.patient_id);
        formData.append('duration_seconds', recording.duration_seconds);
        formData.append('draft_transcript', recording.draft_transcript || '');
        formData.append('audio', recording.audio_blob, 'recording.wav');

        try {
            // Update status
            await RecordingStore.updateStatus(recording.id, 'uploading');

            const response = await fetch('/api/v1/recordings/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Success - clean up local storage
                await RecordingStore.markUploaded(recording.id);
                return { success: true };
            } else if (response.status >= 500) {
                // Server error - can retry
                throw new Error(`Server error: ${response.status}`);
            } else {
                // Client error - don't retry
                throw new Error(`Client error: ${response.status}`);
            }
        } catch (error) {
            // Network error - can retry
            await RecordingStore.updateStatus(recording.id, 'failed', error.message);
            return { success: false, error: error.message };
        }
    },

    // Sync all pending uploads
    async syncAll() {
        const pending = await RecordingStore.getPendingUploads();

        for (const recording of pending) {
            if (recording.retry_count >= 3) {
                console.log(`Skipping recording ${recording.id} - max retries reached`);
                continue;
            }

            // Exponential backoff delay
            const delay = Math.pow(2, recording.retry_count) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));

            const result = await this.uploadRecording(recording);

            if (!result.success) {
                console.error(`Failed to upload ${recording.id}:`, result.error);
            }
        }

        return pending.length;
    },

    // Check connection status
    isOnline() {
        return navigator.onLine;
    },

    // Get upload stats
    async getStats() {
        const stats = await RecordingStore.getStorageStats();
        return {
            ...stats,
            isOnline: this.isOnline()
        };
    }
};

// Auto-sync when coming online
window.addEventListener('online', () => {
    console.log('Online - starting sync');
    UploadManager.syncAll();
});

// Expose to global scope
window.UploadManager = UploadManager;
```

**Step 2: Commit**

```bash
git add pwa/
git commit -m "feat: add UploadManager with retry logic and exponential backoff"
```

---

## Sprint 3: Draft Transcription & UI

### Task 6: Add Draft Transcription to Recorder

**Files:**
- Modify: `pwa/frontend/static/js/recorder.js`
- Modify: `pwa/frontend/templates/record.html`

**Step 1: Update recorder.js with Speech API**

```javascript
// Modify pwa/frontend/static/js/recorder.js
// Add at the top of the file

let recognition = null;
let draftTranscript = '';

// Initialize speech recognition
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-AU'; // Australian English for clinical context

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            draftTranscript = finalTranscript + interimTranscript;
            updateDraftDisplay(draftTranscript, interimTranscript);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'not-allowed') {
                showMicError('Microphone access denied. Please allow microphone access.');
            } else if (event.error === 'no-speech') {
                showMicError('No speech detected. Please check your microphone.');
            }
        };

        return true;
    } else {
        console.log('Speech recognition not supported');
        return false;
    }
}

// Update draft display
function updateDraftDisplay(final, interim) {
    const draftEl = document.getElementById('draft-transcript');
    if (draftEl) {
        draftEl.innerHTML = `
            <span class="final">${final}</span>
            <span class="interim">${interim}</span>
        `;
    }
}

// Show mic error
function showMicError(message) {
    const errorEl = document.getElementById('recording-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
    }
}

// Modify startRecording function
async function startRecording() {
    // ... existing code ...

    // Start speech recognition
    if (recognition) {
        draftTranscript = '';
        recognition.start();
    }

    // ... rest of existing code ...
}

// Modify stopRecording function
async function stopRecording() {
    // ... existing code ...

    // Stop speech recognition
    if (recognition) {
        recognition.stop();
    }

    // ... existing code ...
}

// Modify uploadRecording function to include draft
async function uploadRecording(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('patient_id', patientId || 'unknown');
    formData.append('duration_seconds', Math.floor((Date.now() - recordingStartTime) / 1000));
    formData.append('draft_transcript', draftTranscript); // Include draft

    // Store locally first
    const recording = await RecordingStore.saveRecording({
        patient_id: patientId,
        clinician_id: 'current-clinician', // TODO: Get from auth
        audio_blob: audioBlob,
        draft_transcript: draftTranscript,
        duration_seconds: Math.floor((Date.now() - recordingStartTime) / 1000)
    });

    // Try to upload immediately if online
    if (UploadManager.isOnline()) {
        UploadManager.uploadRecording(recording);
    }

    showResult({ status: 'pending', recording_id: recording.id });
}

// Initialize speech recognition on load
initSpeechRecognition();
```

**Step 2: Update record.html template**

```html
<!-- Modify pwa/frontend/templates/record.html -->
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

        <!-- NEW: Draft Transcript Display -->
        <div id="draft-transcript-container" class="draft-container hidden">
            <label>Draft:</label>
            <div id="draft-transcript" class="draft-text"></div>
        </div>

        <div id="recording-error" class="error-message hidden"></div>

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
```

**Step 3: Add CSS for draft transcript**

```css
/* Add to pwa/frontend/static/css/style.css */

.draft-container {
    margin-top: 1rem;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
}

.draft-container label {
    display: block;
    font-size: 0.85rem;
    color: #6c757d;
    margin-bottom: 0.5rem;
}

.draft-text {
    font-size: 0.95rem;
    line-height: 1.5;
    color: #495057;
    min-height: 3em;
}

.draft-text .interim {
    color: #adb5bd;
    font-style: italic;
}

.draft-text .final {
    color: #495057;
}

.error-message {
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    background: #f8d7da;
    color: #721c24;
    border-radius: 4px;
    font-size: 0.9rem;
}

.hidden {
    display: none;
}
```

**Step 4: Commit**

```bash
git add pwa/
git commit -m "feat: add draft transcription with Web Speech API"
```

---

### Task 7: Create Queue Management UI

**Files:**
- Create: `pwa/frontend/templates/queue.html`
- Create: `pwa/frontend/static/js/queue.js`
- Modify: `pwa/backend/routes/pages.py`
- Test: `pwa/tests/test_queue.py`

**Step 1: Write failing test for queue page**

```python
# pwa/tests/test_queue.py
from fastapi.testclient import TestClient
from pwa.backend.main import app

client = TestClient(app)

def test_queue_page():
    """Test that the queue page loads."""
    response = client.get("/queue")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Recording Queue" in response.text
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_queue.py::test_queue_page -v
```

Expected: FAIL with 404

**Step 3: Add queue page route**

```python
# Add to pwa/backend/routes/pages.py
@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    """Queue management page."""
    return templates.TemplateResponse("queue.html", {"request": request})
```

**Step 4: Create queue template**

```html
<!-- pwa/frontend/templates/queue.html -->
{% extends "base.html" %}

{% block content %}
<div class="queue-page">
    <h2>Recording Queue</h2>

    <!-- Connection Status -->
    <div id="connection-status" class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text">Checking...</span>
    </div>

    <!-- Stats -->
    <div id="queue-stats" class="stats-bar">
        <span id="pending-count">0 pending</span>
        <span id="storage-used">0 MB</span>
    </div>

    <!-- Queue List -->
    <div id="queue-list" class="queue-list">
        <p class="empty-state">No recordings in queue</p>
    </div>

    <!-- Troubleshooting Panel (hidden by default) -->
    <div id="troubleshoot-panel" class="troubleshoot-panel hidden">
        <h3>Recording Details</h3>
        <div id="troubleshoot-content"></div>
    </div>
</div>

<script src="/static/js/queue.js"></script>
{% endblock %}
```

**Step 5: Create queue.js**

```javascript
// pwa/frontend/static/js/queue.js
/**
 * Queue Management UI
 */

async function updateQueue() {
    const recordings = await RecordingStore.getAllRecordings();
    const stats = await UploadManager.getStats();

    // Update stats
    document.getElementById('pending-count').textContent =
        `${stats.pendingCount} pending`;
    document.getElementById('storage-used').textContent =
        `${(stats.totalSize / 1024 / 1024).toFixed(1)} MB`;

    // Update connection status
    const statusDot = document.querySelector('#connection-status .status-dot');
    const statusText = document.querySelector('#connection-status .status-text');

    if (stats.isOnline) {
        statusDot.className = 'status-dot online';
        statusText.textContent = 'Online';
    } else {
        statusDot.className = 'status-dot offline';
        statusText.textContent = 'Offline';
    }

    // Update list
    const listEl = document.getElementById('queue-list');
    if (recordings.length === 0) {
        listEl.innerHTML = '<p class="empty-state">No recordings in queue</p>';
    } else {
        listEl.innerHTML = recordings.map(r => `
            <div class="queue-item" data-id="${r.id}">
                <div class="queue-item-info">
                    <span class="patient">${r.patient_id}</span>
                    <span class="duration">${formatDuration(r.duration_seconds)}</span>
                </div>
                <div class="queue-item-status">
                    ${getStatusIcon(r.sync_status)}
                </div>
                <div class="queue-item-actions">
                    <button onclick="showDetails('${r.id}')">Details</button>
                    ${r.sync_status === 'failed' ? `<button onclick="retryUpload('${r.id}')">Retry</button>` : ''}
                </div>
            </div>
        `).join('');
    }
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
}

function getStatusIcon(status) {
    const icons = {
        'pending_upload': '⏳ Pending',
        'uploading': '🔄 Uploading',
        'uploaded': '✓ Ready',
        'failed': '⚠️ Failed'
    };
    return icons[status] || status;
}

async function showDetails(id) {
    const recording = await RecordingStore.getRecording(id);
    const panel = document.getElementById('troubleshoot-panel');
    const content = document.getElementById('troubleshoot-content');

    content.innerHTML = `
        <dl>
            <dt>ID</dt><dd>${recording.id}</dd>
            <dt>Patient</dt><dd>${recording.patient_id}</dd>
            <dt>Duration</dt><dd>${formatDuration(recording.duration_seconds)}</dd>
            <dt>Status</dt><dd>${recording.sync_status}</dd>
            <dt>Upload Attempts</dt><dd>${recording.retry_count}</dd>
            ${recording.last_error ? `<dt>Last Error</dt><dd>${recording.last_error}</dd>` : ''}
        </dl>
        ${recording.draft_transcript ? `
            <h4>Draft Transcript</h4>
            <p class="draft-preview">${recording.draft_transcript}</p>
        ` : ''}
        <div class="actions">
            <button onclick="exportRecording('${id}')">Export Audio</button>
            <button onclick="deleteRecording('${id}')" class="danger">Delete</button>
        </div>
    `;

    panel.classList.remove('hidden');
}

async function retryUpload(id) {
    const recording = await RecordingStore.getRecording(id);
    if (recording) {
        await RecordingStore.updateStatus(id, 'pending_upload');
        await UploadManager.uploadRecording(recording);
        updateQueue();
    }
}

async function exportRecording(id) {
    const recording = await RecordingStore.getRecording(id);
    if (recording && recording.audio_blob) {
        const confirmed = confirm(
            'This will download an audio file containing patient information. ' +
            'Store this file securely according to your privacy policy.'
        );

        if (confirmed) {
            const url = URL.createObjectURL(recording.audio_blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `recording-${recording.patient_id}-${Date.now()}.wav`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }
}

async function deleteRecording(id) {
    const confirmed = confirm('Delete this recording permanently?');
    if (confirmed) {
        await RecordingStore.deleteRecording(id);
        document.getElementById('troubleshoot-panel').classList.add('hidden');
        updateQueue();
    }
}

// Poll for updates
setInterval(updateQueue, 5000);

// Initial load
document.addEventListener('DOMContentLoaded', updateQueue);
```

**Step 6: Add CSS for queue page**

```css
/* Add to pwa/frontend/static/css/style.css */

.queue-page {
    max-width: 800px;
    margin: 0 auto;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1rem 0;
}

.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ccc;
}

.status-dot.online {
    background: #28a745;
}

.status-dot.offline {
    background: #dc3545;
}

.stats-bar {
    display: flex;
    gap: 2rem;
    padding: 0.75rem 1rem;
    background: #f8f9fa;
    border-radius: 4px;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: #6c757d;
}

.queue-list {
    margin: 1rem 0;
}

.empty-state {
    text-align: center;
    padding: 3rem;
    color: #6c757d;
}

.queue-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    margin-bottom: 0.5rem;
}

.queue-item-info {
    display: flex;
    gap: 1rem;
}

.queue-item-info .patient {
    font-weight: 500;
}

.queue-item-info .duration {
    color: #6c757d;
    font-size: 0.9rem;
}

.queue-item-status {
    font-size: 0.9rem;
}

.queue-item-actions {
    display: flex;
    gap: 0.5rem;
}

.troubleshoot-panel {
    position: fixed;
    right: 0;
    top: 0;
    width: 400px;
    height: 100%;
    background: white;
    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
    padding: 2rem;
    overflow-y: auto;
}

.troubleshoot-panel h3 {
    margin-bottom: 1rem;
}

.troubleshoot-panel dl {
    margin-bottom: 1.5rem;
}

.troubleshoot-panel dt {
    font-weight: 500;
    margin-top: 0.75rem;
}

.troubleshoot-panel dd {
    margin-left: 0;
    color: #6c757d;
}

.draft-preview {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    font-size: 0.95rem;
    line-height: 1.5;
    max-height: 200px;
    overflow-y: auto;
}

button.danger {
    background: #dc3545;
}

button.danger:hover {
    background: #c82333;
}
```

**Step 7: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_queue.py::test_queue_page -v
```

Expected: PASS

**Step 8: Commit**

```bash
git add pwa/
git commit -m "feat: add queue management UI with export functionality"
```

---

## Sprint 4: Testing & Polish

### Task 8: Add Playwright Tests

**Files:**
- Create: `pwa/tests/e2e/test_offline_recording.py`
- Create: `pyproject.toml` (add Playwright config)

**Step 1: Install Playwright**

```bash
uv add --dev playwright
uv run playwright install chromium
```

**Step 2: Create Playwright test**

```python
# pwa/tests/e2e/test_offline_recording.py
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture
def page(page: Page):
    """Navigate to the app."""
    page.goto("http://localhost:8002/")
    return page

def test_record_button_exists(page: Page):
    """Test that record button is present."""
    record_btn = page.locator("#record-btn")
    expect(record_btn).to_be_visible()
    expect(record_btn).to_contain_text("Start Recording")

def test_queue_page_loads(page: Page):
    """Test that queue page loads."""
    page.goto("http://localhost:8002/queue")
    expect(page).to_have_title("Clinical Transcription PWA")
    expect(page.locator("h2")).to_contain_text("Recording Queue")

def test_connection_status_indicator(page: Page):
    """Test that connection status is shown."""
    page.goto("http://localhost:8002/queue")
    status = page.locator("#connection-status")
    expect(status).to_be_visible()
```

**Step 3: Commit**

```bash
git add pyproject.toml pwa/
git commit -m "test: add Playwright E2E tests for offline recording"
```

---

### Task 9: Add PostgreSQL Migration

**Files:**
- Create: `pwa/backend/database.py`
- Modify: `pwa/backend/models/recording.py`
- Modify: `pwa/backend/services/recording_service.py`

**Step 1: Install SQLAlchemy**

```bash
uv add sqlalchemy asyncpg
```

**Step 2: Create database module**

```python
# pwa/backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON
from uuid import uuid4

DATABASE_URL = "postgresql+asyncpg://localhost/pwa"

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class RecordingDB(Base):
    __tablename__ = "recordings"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    patient_id = Column(String, nullable=False)
    clinician_id = Column(String, nullable=False)
    audio_file_path = Column(String)
    audio_file_size = Column(Integer)
    duration_seconds = Column(Integer)
    draft_transcript = Column(Text)
    final_transcript = Column(Text)
    status = Column(String, default="pending")
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    local_storage_key = Column(String)
    upload_attempts = Column(Integer, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    uploaded_at = Column(DateTime)
    processed_at = Column(DateTime)
    verification_results = Column(JSON)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 3: Update RecordingService to use database**

```python
# Modify pwa/backend/services/recording_service.py
from pwa.backend.database import async_session, RecordingDB
from sqlalchemy import select

class RecordingService:
    """Service for managing recordings with PostgreSQL persistence."""

    async def create_recording(self, patient_id: str, clinician_id: str,
                               duration_seconds: int, audio_file_path: str = None,
                               draft_transcript: str = None) -> Recording:
        """Create a new recording in the database."""
        recording = Recording(
            patient_id=patient_id,
            clinician_id=clinician_id,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
            draft_transcript=draft_transcript,
            status=RecordingStatus.PENDING
        )

        async with async_session() as session:
            db_recording = RecordingDB(
                id=str(recording.id),
                patient_id=recording.patient_id,
                clinician_id=recording.clinician_id,
                audio_file_path=recording.audio_file_path,
                duration_seconds=recording.duration_seconds,
                draft_transcript=recording.draft_transcript,
                status=recording.status.value,
                created_at=recording.created_at
            )
            session.add(db_recording)
            await session.commit()

        return recording
```

**Step 4: Commit**

```bash
git add pwa/ pyproject.toml
```
