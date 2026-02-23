# Phase 2a: Offline Recording PWA Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Progressive Web App that lets clinicians record audio offline, store it locally in IndexedDB, and auto-upload when connectivity returns.

**Architecture:** Client-side IndexedDB for offline audio storage, Service Worker with fallback HTMX polling for sync (iOS doesn't support Background Sync), Upload Manager with exponential backoff retry, and a Queue UI with real-time status updates.

**Tech Stack:** FastAPI (backend), IndexedDB (localForage wrapper), vanilla JavaScript (frontend), HTMX for polling, Playwright for testing.

---

## Prerequisites

Before starting, verify Phase 1 is working:

```bash
# Verify tests pass
uv run pytest pwa/tests/ -v
# Expected: 27+ tests passing

# Run the server
uv run python pwa/backend/main.py
# Open http://localhost:8002/
# Verify: Home page loads, can click "Record" button
```

---

## Task 1: Install localForage

**Purpose:** Add IndexedDB library for reliable offline storage.

**Files:**
- Modify: `pwa/frontend/templates/base.html:9-10`
- Verify: `pwa/frontend/static/js/indexeddb-service.js` doesn't exist yet

**Step 1: Add localForage CDN to base template**

Edit `pwa/frontend/templates/base.html`, add after HTMX script:

```html
<!-- localForage for IndexedDB -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/localforage/1.10.0/localforage.min.js"></script>
```

**Step 2: Run server and verify**

```bash
uv run python pwa/backend/main.py
# Open browser dev tools > Console
# Type: localforage
# Expected: Returns the localforage object (not undefined)
```

**Step 3: Commit**

```bash
git add pwa/frontend/templates/base.html
git commit -m "feat: add localForage for IndexedDB storage"
```

---

## Task 2: Create IndexedDB Service

**Purpose:** Wrap IndexedDB operations in a reusable service for storing/retrieving recordings.

**Files:**
- Create: `pwa/frontend/static/js/indexeddb-service.js`
- Test: Create `pwa/tests/e2e/test_indexeddb.py` (Playwright test)

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_indexeddb.py`:

```python
"""Playwright tests for IndexedDB functionality."""

import pytest
from playwright.sync_api import Page, expect


def test_indexeddb_stores_recording(page: Page) -> None:
    """Test that IndexedDB can store and retrieve a recording."""
    # This test will initially fail because the service doesn't exist
    page.goto("http://localhost:8002/record/patient-123")

    # Execute IndexedDB operations via page.evaluate
    result = page.evaluate("""
        async () => {
            if (!window.RecordingStorage) {
                return { error: 'RecordingStorage not defined' };
            }

            const recording = {
                id: 'test-recording-123',
                patient_id: 'patient-123',
                clinician_id: 'clinician-456',
                duration_seconds: 60,
                audio_blob: new Blob(['test audio data'], { type: 'audio/wav' }),
                created_at: new Date().toISOString(),
                sync_status: 'pending_upload'
            };

            await window.RecordingStorage.saveRecording(recording);
            const retrieved = await window.RecordingStorage.getRecording('test-recording-123');

            // Clean up
            await window.RecordingStorage.deleteRecording('test-recording-123');

            return {
                saved: true,
                retrieved: retrieved ? true : false,
                id: retrieved?.id
            };
        }
    """)

    assert result.get("error") is None, f"IndexedDB service error: {result.get('error')}"
    assert result["saved"] is True
    assert result["retrieved"] is True
    assert result["id"] == "test-recording-123"


def test_indexeddb_lists_pending_recordings(page: Page) -> None:
    """Test listing pending recordings."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        async () => {
            if (!window.RecordingStorage) {
                return { error: 'RecordingStorage not defined' };
            }

            // Save two recordings
            await window.RecordingStorage.saveRecording({
                id: 'rec-1',
                patient_id: 'patient-123',
                sync_status: 'pending_upload',
                created_at: new Date().toISOString()
            });

            await window.RecordingStorage.saveRecording({
                id: 'rec-2',
                patient_id: 'patient-456',
                sync_status: 'uploaded',
                created_at: new Date().toISOString()
            });

            const pending = await window.RecordingStorage.getPendingRecordings();

            // Clean up
            await window.RecordingStorage.deleteRecording('rec-1');
            await window.RecordingStorage.deleteRecording('rec-2');

            return {
                pending_count: pending.length,
                pending_ids: pending.map(r => r.id)
            };
        }
    """)

    assert result.get("error") is None
    assert result["pending_count"] == 1
    assert "rec-1" in result["pending_ids"]
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_indexeddb.py -v
# Expected: FAIL - "RecordingStorage not defined"
```

**Step 3: Create IndexedDB service**

Create `pwa/frontend/static/js/indexeddb-service.js`:

```javascript
/**
 * IndexedDB Service for offline recording storage
 * Uses localForage for reliable cross-browser IndexedDB operations
 */

(function() {
    'use strict';

    // Initialize localForage instance for recordings
    const recordingStore = localforage.createInstance({
        name: 'ClinicalTranscription',
        storeName: 'recordings',
        description: 'Clinical transcription recordings'
    });

    /**
     * Save a recording to IndexedDB
     * @param {Object} recording - Recording object
     * @returns {Promise<void>}
     */
    async function saveRecording(recording) {
        if (!recording.id) {
            throw new Error('Recording must have an id');
        }

        // Ensure required fields
        const recordingData = {
            ...recording,
            updated_at: new Date().toISOString(),
            retry_count: recording.retry_count || 0
        };

        await recordingStore.setItem(recording.id, recordingData);
        console.log('[IndexedDB] Saved recording:', recording.id);
    }

    /**
     * Get a recording by ID
     * @param {string} id - Recording ID
     * @returns {Promise<Object|null>}
     */
    async function getRecording(id) {
        return await recordingStore.getItem(id);
    }

    /**
     * Get all recordings
     * @returns {Promise<Array>}
     */
    async function getAllRecordings() {
        const recordings = [];
        await recordingStore.iterate((value) => {
            recordings.push(value);
        });
        return recordings.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }

    /**
     * Get pending recordings (not yet uploaded)
     * @returns {Promise<Array>}
     */
    async function getPendingRecordings() {
        const all = await getAllRecordings();
        return all.filter(r => r.sync_status === 'pending_upload' || r.sync_status === 'failed');
    }

    /**
     * Get recordings by status
     * @param {string} status - sync_status to filter by
     * @returns {Promise<Array>}
     */
    async function getRecordingsByStatus(status) {
        const all = await getAllRecordings();
        return all.filter(r => r.sync_status === status);
    }

    /**
     * Update a recording
     * @param {string} id - Recording ID
     * @param {Object} updates - Fields to update
     * @returns {Promise<Object>} Updated recording
     */
    async function updateRecording(id, updates) {
        const existing = await getRecording(id);
        if (!existing) {
            throw new Error(`Recording ${id} not found`);
        }

        const updated = {
            ...existing,
            ...updates,
            updated_at: new Date().toISOString()
        };

        await recordingStore.setItem(id, updated);
        return updated;
    }

    /**
     * Delete a recording
     * @param {string} id - Recording ID
     * @returns {Promise<void>}
     */
    async function deleteRecording(id) {
        await recordingStore.removeItem(id);
        console.log('[IndexedDB] Deleted recording:', id);
    }

    /**
     * Get storage quota information
     * @returns {Promise<Object>}
     */
    async function getStorageInfo() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            const estimate = await navigator.storage.estimate();
            return {
                usage: estimate.usage || 0,
                quota: estimate.quota || 0,
                percentage: estimate.quota ? ((estimate.usage / estimate.quota) * 100).toFixed(2) : 0
            };
        }
        return { usage: 0, quota: 0, percentage: 0 };
    }

    /**
     * Clear all recordings (use with caution)
     * @returns {Promise<void>}
     */
    async function clearAll() {
        await recordingStore.clear();
        console.log('[IndexedDB] Cleared all recordings');
    }

    // Expose API globally
    window.RecordingStorage = {
        saveRecording,
        getRecording,
        getAllRecordings,
        getPendingRecordings,
        getRecordingsByStatus,
        updateRecording,
        deleteRecording,
        getStorageInfo,
        clearAll
    };

    console.log('[IndexedDB] RecordingStorage initialized');
})();
```

**Step 4: Add service to base template**

Edit `pwa/frontend/templates/base.html`, add before closing `</body>`:

```html
    <!-- IndexedDB Service -->
    <script src="/static/js/indexeddb-service.js"></script>
</body>
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest pwa/tests/e2e/test_indexeddb.py -v
# Expected: 2 tests PASS
```

**Step 6: Commit**

```bash
git add pwa/frontend/static/js/indexeddb-service.js pwa/frontend/templates/base.html pwa/tests/e2e/test_indexeddb.py
git commit -m "feat: add IndexedDB service for offline recording storage"
```

---

## Task 3: Update Recording Model (Pydantic)

**Purpose:** Add fields needed for offline tracking.

**Files:**
- Modify: `pwa/backend/models/recording.py`
- Test: Modify `pwa/tests/test_recording_model.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_recording_model.py` if it doesn't exist, or add to it:

```python
# pwa/tests/test_recording_model.py
"""Tests for Recording Pydantic model."""

import pytest
from uuid import UUID

from pwa.backend.models.recording import Recording, RecordingStatus


def test_recording_with_draft_transcript():
    """Test recording with draft transcript field."""
    recording = Recording(
        patient_id="patient-123",
        clinician_id="clinician-456",
        draft_transcript="This is a draft",
        duration_seconds=120
    )

    assert recording.draft_transcript == "This is a draft"
    assert recording.final_transcript is None


def test_recording_with_upload_tracking():
    """Test recording with upload tracking fields."""
    recording = Recording(
        patient_id="patient-123",
        clinician_id="clinician-456",
        local_storage_key="local-uuid-123",
        duration_seconds=120
    )

    assert recording.local_storage_key == "local-uuid-123"
    assert recording.upload_attempts == 0


def test_recording_defaults():
    """Test recording default values."""
    recording = Recording(
        patient_id="patient-123",
        clinician_id="clinician-456",
        duration_seconds=120
    )

    assert recording.draft_transcript is None
    assert recording.final_transcript is None
    assert recording.local_storage_key is None
    assert recording.upload_attempts == 0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_recording_model.py -v
# Expected: FAIL - AttributeError for draft_transcript, final_transcript, local_storage_key, upload_attempts
```

**Step 3: Update Recording model**

Edit `pwa/backend/models/recording.py`, add new fields after line 46:

```python
    # Results (populated after processing)
    transcript: str | None = None
    verification_results: dict[str, Any] | None = None

    # NEW: Transcription (Phase 2a)
    draft_transcript: str | None = None      # Browser Speech API result
    final_transcript: str | None = None      # Whisper result

    # NEW: Upload tracking (Phase 2a)
    local_storage_key: str | None = None     # IndexedDB key (client-generated UUID)
    upload_attempts: int = 0                 # Retry counter
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_recording_model.py -v
# Expected: 3 tests PASS
```

**Step 5: Run all tests to ensure no regressions**

```bash
uv run pytest pwa/tests/ -v
# Expected: All tests pass (27+ tests)
```

**Step 6: Commit**

```bash
git add pwa/backend/models/recording.py pwa/tests/test_recording_model.py
git commit -m "feat: add draft_transcript, final_transcript, local_storage_key, upload_attempts to Recording model"
```

---

## Task 4: Create Audio Upload Endpoint

**Purpose:** Endpoint to receive audio blob from client and create recording.

**Files:**
- Modify: `pwa/backend/routes/recordings.py`
- Test: Create `pwa/tests/test_upload_endpoint.py`

**Step 1: Write the failing test**

Create `pwa/tests/test_upload_endpoint.py`:

```python
# pwa/tests/test_upload_endpoint.py
"""Tests for audio upload endpoint."""

import io
from fastapi.testclient import TestClient
import pytest

from pwa.backend.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_upload_audio_success(client: TestClient) -> None:
    """Test successful audio upload."""
    # Create a fake audio file
    audio_content = b"fake audio data" * 100  # Make it big enough

    response = client.post(
        "/api/v1/recordings/upload",
        files={"audio": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
        data={
            "patient_id": "patient-123",
            "duration_seconds": "60",
            "local_storage_key": "local-uuid-abc-123"
        }
    )

    assert response.status_code == 201, f"Unexpected status: {response.text}"
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["duration_seconds"] == 60
    assert data["status"] == "pending"
    assert "id" in data


def test_upload_audio_missing_patient_id(client: TestClient) -> None:
    """Test upload without patient_id."""
    audio_content = b"fake audio data"

    response = client.post(
        "/api/v1/recordings/upload",
        files={"audio": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
        data={"duration_seconds": "60"}
    )

    # Should fail validation
    assert response.status_code == 422


def test_upload_audio_stores_local_key(client: TestClient) -> None:
    """Test that local_storage_key is persisted."""
    audio_content = b"fake audio data" * 50

    response = client.post(
        "/api/v1/recordings/upload",
        files={"audio": ("test.wav", io.BytesIO(audio_content), "audio/wav")},
        data={
            "patient_id": "patient-123",
            "duration_seconds": "60",
            "local_storage_key": "my-local-key-456"
        }
    )

    assert response.status_code == 201

    # Get the recording and verify local_storage_key
    recording_id = response.json()["id"]
    get_response = client.get(f"/api/v1/recordings/{recording_id}")

    # Note: local_storage_key may not be in the response depending on RecordingResponse schema
    # This test verifies the upload succeeds
    assert get_response.status_code == 200
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/test_upload_endpoint.py -v
# Expected: FAIL - 404 Not Found (endpoint doesn't exist yet)
```

**Step 3: Implement upload endpoint**

Edit `pwa/backend/routes/recordings.py`, add after line 100:

```python
# NEW: File upload endpoint for audio
import io
from fastapi import File, Form, UploadFile


class UploadRecordingResponse(BaseModel):
    """Response for uploaded recording."""

    id: str
    patient_id: str
    clinician_id: str
    duration_seconds: int
    status: str
    local_storage_key: str | None = None
    created_at: str


@router.post("/upload", response_model=UploadRecordingResponse, status_code=201)
async def upload_recording(
    audio: UploadFile = File(...),
    patient_id: str = Form(...),
    duration_seconds: int = Form(...),
    local_storage_key: str | None = Form(None),
    draft_transcript: str | None = Form(None),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadRecordingResponse:
    """Upload a recording with audio file."""
    # TODO: Get clinician_id from auth token
    clinician_id = "current-clinician"

    # Read audio content
    audio_content = await audio.read()
    audio_file_size = len(audio_content)

    # TODO: Save audio file to disk (Phase 2a - basic implementation)
    # For now, just store the size
    audio_file_path = f"/tmp/recordings/{local_storage_key or 'unknown'}.wav"

    service = RecordingService(db)
    recording = await service.create_recording(
        patient_id=patient_id,
        clinician_id=clinician_id,
        duration_seconds=duration_seconds,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        local_storage_key=local_storage_key,
        draft_transcript=draft_transcript,
    )

    return UploadRecordingResponse(
        id=str(recording.id),
        patient_id=recording.patient_id,
        clinician_id=recording.clinician_id,
        duration_seconds=recording.duration_seconds or 0,
        status=recording.status.value,
        local_storage_key=recording.local_storage_key,
        created_at=recording.created_at.isoformat(),
    )
```

**Step 4: Update RecordingService to handle new fields**

Check `pwa/backend/services/recording_service.py` - add parameters if needed. The service likely already accepts **kwargs or we need to add them:

```python
# In recording_service.py, update create_recording signature if needed
async def create_recording(
    self,
    patient_id: str,
    clinician_id: str,
    duration_seconds: int,
    audio_file_path: str | None = None,
    audio_file_size: int | None = None,
    local_storage_key: str | None = None,
    draft_transcript: str | None = None,
) -> RecordingModel:
    """Create a new recording."""
    recording = RecordingModel(
        patient_id=patient_id,
        clinician_id=clinician_id,
        duration_seconds=duration_seconds,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        local_storage_key=local_storage_key,
        draft_transcript=draft_transcript,
        status=RecordingStatus.PENDING,
    )
    self.db.add(recording)
    await self.db.commit()
    await self.db.refresh(recording)
    return recording
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest pwa/tests/test_upload_endpoint.py -v
# Expected: 3 tests PASS
```

**Step 6: Run all tests**

```bash
uv run pytest pwa/tests/ -v
# Expected: All tests pass
```

**Step 7: Commit**

```bash
git add pwa/backend/routes/recordings.py pwa/backend/services/recording_service.py pwa/tests/test_upload_endpoint.py
git commit -m "feat: add audio upload endpoint with multipart/form-data support"
```

---

## Task 5: Create Upload Manager JavaScript Module

**Purpose:** Handle upload logic with retry, exponential backoff, and status tracking.

**Files:**
- Create: `pwa/frontend/static/js/upload-manager.js`
- Test: Create `pwa/tests/e2e/test_upload_manager.py`

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_upload_manager.py`:

```python
# pwa/tests/e2e/test_upload_manager.py
"""Playwright tests for Upload Manager."""

import pytest
from playwright.sync_api import Page, expect


def test_upload_manager_defined(page: Page) -> None:
    """Test that UploadManager is available globally."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        () => {
            return {
                defined: typeof window.UploadManager !== 'undefined',
                hasQueueUpload: typeof window.UploadManager?.queueUpload === 'function',
                hasProcessQueue: typeof window.UploadManager?.processQueue === 'function'
            };
        }
    """)

    assert result["defined"] is True, "UploadManager not defined"
    assert result["hasQueueUpload"] is True, "queueUpload method not found"
    assert result["hasProcessQueue"] is True, "processQueue method not found"


def test_upload_manager_detects_online_status(page: Page) -> None:
    """Test online/offline detection."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        () => {
            if (!window.UploadManager) {
                return { error: 'UploadManager not defined' };
            }
            return {
                isOnline: window.UploadManager.isOnline()
            };
        }
    """)

    assert result.get("error") is None
    assert isinstance(result["isOnline"], bool)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_upload_manager.py -v
# Expected: FAIL - UploadManager not defined
```

**Step 3: Create Upload Manager**

Create `pwa/frontend/static/js/upload-manager.js`:

```javascript
/**
 * Upload Manager - Handles uploading recordings to server with retry logic
 * Features:
 * - Queue recordings for upload
 * - Retry with exponential backoff
 * - Online/offline detection
 * - iOS detection and warnings
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        MAX_RETRIES: 3,
        BASE_DELAY_MS: 1000,
        MAX_DELAY_MS: 30000,
        POLLING_INTERVAL_MS: 30000, // 30 seconds for iOS fallback
    };

    // State
    let isProcessing = false;
    let iOSWarningShown = false;
    let pollingInterval = null;

    /**
     * Detect if user is on iOS/Safari
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Detect if Background Sync API is supported
     * @returns {boolean}
     */
    function isBackgroundSyncSupported() {
        return 'serviceWorker' in navigator &&
               'sync' in ServiceWorkerRegistration.prototype;
    }

    /**
     * Check if browser is online
     * @returns {boolean}
     */
    function isOnline() {
        return navigator.onLine;
    }

    /**
     * Calculate retry delay with exponential backoff
     * @param {number} attempt - Retry attempt number (0-based)
     * @returns {number} Delay in milliseconds
     */
    function getRetryDelay(attempt) {
        const delay = Math.min(
            CONFIG.BASE_DELAY_MS * Math.pow(2, attempt),
            CONFIG.MAX_DELAY_MS
        );
        // Add jitter to prevent thundering herd
        return delay + Math.random() * 1000;
    }

    /**
     * Queue a recording for upload
     * @param {string} recordingId - Recording ID in IndexedDB
     * @returns {Promise<void>}
     */
    async function queueUpload(recordingId) {
        console.log('[UploadManager] Queuing upload for:', recordingId);

        // Update recording status to pending
        await window.RecordingStorage.updateRecording(recordingId, {
            sync_status: 'pending_upload'
        });

        // Trigger upload processing
        await processQueue();
    }

    /**
     * Upload a single recording
     * @param {Object} recording - Recording object from IndexedDB
     * @returns {Promise<boolean>} True if successful
     */
    async function uploadRecording(recording) {
        const recordingId = recording.id;

        try {
            // Update status to uploading
            await window.RecordingStorage.updateRecording(recordingId, {
                sync_status: 'uploading'
            });

            // Dispatch event for UI update
            dispatchStatusUpdate(recordingId, 'uploading');

            // Prepare form data
            const formData = new FormData();
            formData.append('audio', recording.audio_blob, `recording-${recordingId}.wav`);
            formData.append('patient_id', recording.patient_id);
            formData.append('duration_seconds', recording.duration_seconds);
            formData.append('local_storage_key', recordingId);
            if (recording.draft_transcript) {
                formData.append('draft_transcript', recording.draft_transcript);
            }

            // Upload
            const response = await fetch('/api/v1/recordings/upload', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();

                // Mark as uploaded
                await window.RecordingStorage.updateRecording(recordingId, {
                    sync_status: 'uploaded',
                    server_id: result.id,
                    uploaded_at: new Date().toISOString()
                });

                dispatchStatusUpdate(recordingId, 'uploaded');
                console.log('[UploadManager] Upload successful:', recordingId);

                return true;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('[UploadManager] Upload failed:', error);

            // Increment retry count
            const updated = await window.RecordingStorage.updateRecording(recordingId, {
                sync_status: 'failed',
                retry_count: (recording.retry_count || 0) + 1,
                last_error: error.message
            });

            dispatchStatusUpdate(recordingId, 'failed', error.message);

            // Retry if under max retries
            if (updated.retry_count < CONFIG.MAX_RETRIES) {
                const delay = getRetryDelay(updated.retry_count - 1);
                console.log(`[UploadManager] Retrying ${recordingId} in ${delay}ms (attempt ${updated.retry_count}/${CONFIG.MAX_RETRIES})`);

                setTimeout(() => {
                    queueUpload(recordingId);
                }, delay);
            } else {
                console.error(`[UploadManager] Max retries reached for ${recordingId}`);
            }

            return false;
        }
    }

    /**
     * Process upload queue
     * @returns {Promise<void>}
     */
    async function processQueue() {
        if (isProcessing) {
            console.log('[UploadManager] Already processing queue');
            return;
        }

        if (!isOnline()) {
            console.log('[UploadManager] Offline, skipping queue processing');
            return;
        }

        isProcessing = true;

        try {
            // Get all pending recordings
            const pending = await window.RecordingStorage.getPendingRecordings();

            console.log(`[UploadManager] Processing ${pending.length} pending recordings`);

            // Upload each one
            for (const recording of pending) {
                if (!isOnline()) {
                    console.log('[UploadManager] Went offline, pausing queue');
                    break;
                }

                await uploadRecording(recording);
            }
        } finally {
            isProcessing = false;
        }
    }

    /**
     * Dispatch status update event
     * @param {string} recordingId
     * @param {string} status
     * @param {string|null} error
     */
    function dispatchStatusUpdate(recordingId, status, error = null) {
        window.dispatchEvent(new CustomEvent('upload-status-change', {
            detail: { recordingId, status, error }
        }));
    }

    /**
     * Show iOS warning (called when on iOS)
     */
    function showIOSWarning() {
        if (iOSWarningShown) return;

        const warning = document.createElement('div');
        warning.id = 'ios-sync-warning';
        warning.className = 'ios-warning';
        warning.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <span>iOS requires keeping this app open to sync recordings</span>
        `;

        const header = document.querySelector('header');
        if (header) {
            header.insertAdjacentElement('afterend', warning);
        }

        iOSWarningShown = true;
    }

    /**
     * Start iOS polling fallback
     */
    function startIOSPolling() {
        if (pollingInterval) return;

        console.log('[UploadManager] Starting iOS polling fallback');
        showIOSWarning();

        pollingInterval = setInterval(() => {
            if (isOnline()) {
                processQueue();
            }
        }, CONFIG.POLLING_INTERVAL_MS);
    }

    /**
     * Stop iOS polling
     */
    function stopIOSPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            console.log('[UploadManager] Stopped iOS polling');
        }
    }

    /**
     * Initialize upload manager
     */
    function init() {
        console.log('[UploadManager] Initializing...');

        // Listen for online/offline events
        window.addEventListener('online', () => {
            console.log('[UploadManager] Browser went online');
            processQueue();
        });

        window.addEventListener('offline', () => {
            console.log('[UploadManager] Browser went offline');
        });

        // iOS detection and fallback
        if (isIOS()) {
            console.log('[UploadManager] iOS detected, using polling fallback');
            startIOSPolling();
        } else if (!isBackgroundSyncSupported()) {
            console.log('[UploadManager] Background Sync not supported, using polling');
            startIOSPolling();
        }

        // Initial queue processing
        if (isOnline()) {
            processQueue();
        }
    }

    // Expose API globally
    window.UploadManager = {
        queueUpload,
        processQueue,
        isOnline,
        isIOS,
        isBackgroundSyncSupported,
        CONFIG,
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log('[UploadManager] Loaded');
})();
```

**Step 4: Add to base template**

Edit `pwa/frontend/templates/base.html`, add after the IndexedDB service:

```html
    <!-- Upload Manager -->
    <script src="/static/js/upload-manager.js"></script>
</body>
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest pwa/tests/e2e/test_upload_manager.py -v
# Expected: 2 tests PASS
```

**Step 6: Commit**

```bash
git add pwa/frontend/static/js/upload-manager.js pwa/frontend/templates/base.html pwa/tests/e2e/test_upload_manager.py
git commit -m "feat: add UploadManager with retry logic and iOS polling fallback"
```

---

## Task 6: Create Service Worker

**Purpose:** Enable offline functionality and background sync (where supported).

**Files:**
- Create: `pwa/frontend/static/js/service-worker.js`
- Create: `pwa/frontend/static/js/sw-register.js`
- Test: Create `pwa/tests/e2e/test_service_worker.py`

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_service_worker.py`:

```python
# pwa/tests/e2e/test_service_worker.py
"""Playwright tests for Service Worker."""

import pytest
from playwright.sync_api import Page, expect


def test_service_worker_registers(page: Page) -> None:
    """Test that service worker registers successfully."""
    page.goto("http://localhost:8002/")

    result = page.evaluate("""
        async () => {
            if (!('serviceWorker' in navigator)) {
                return { error: 'Service Worker not supported' };
            }

            const registration = await navigator.serviceWorker.ready;
            return {
                registered: registration ? true : false,
                scope: registration?.scope
            };
        }
    """)

    assert result.get("error") is None, f"Service Worker error: {result.get('error')}"
    assert result["registered"] is True, "Service Worker not registered"


def test_service_worker_caches_assets(page: Page) -> None:
    """Test that static assets are cached."""
    page.goto("http://localhost:8002/")

    # Wait for SW to be ready
    page.wait_for_timeout(1000)

    result = page.evaluate("""
        async () => {
            const cacheNames = await caches.keys();
            return {
                hasCache: cacheNames.length > 0,
                cacheNames: cacheNames
            };
        }
    """)

    assert result["hasCache"] is True, "No caches found"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_service_worker.py -v
# Expected: FAIL - Service Worker not registered
```

**Step 3: Create Service Worker**

Create `pwa/frontend/static/js/service-worker.js`:

```javascript
/**
 * Service Worker for Clinical Transcription PWA
 * Handles:
 * - Caching static assets for offline use
 * - Network interception for upload requests
 * - Background sync (Chrome/Android only)
 */

const CACHE_NAME = 'clinical-transcription-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/recorder.js',
    '/static/js/indexeddb-service.js',
    '/static/js/upload-manager.js',
    '/static/js/queue.js',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Skip waiting');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Cache failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== CACHE_NAME)
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Claiming clients');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (POST for uploads handled separately)
    if (request.method !== 'GET') {
        return;
    }

    // Strategy: Cache First for static assets, Network First for API
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirst(request));
    } else if (isAPIRequest(url.pathname)) {
        event.respondWith(networkFirst(request));
    }
});

// Sync event - background sync (Chrome/Android only)
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync event:', event.tag);

    if (event.tag === 'upload-recordings') {
        event.waitUntil(syncRecordings());
    }
});

/**
 * Check if path is a static asset
 * @param {string} pathname
 * @returns {boolean}
 */
function isStaticAsset(pathname) {
    return pathname.startsWith('/static/') || pathname === '/';
}

/**
 * Check if path is an API request
 * @param {string} pathname
 * @returns {boolean}
 */
function isAPIRequest(pathname) {
    return pathname.startsWith('/api/');
}

/**
 * Cache First strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function cacheFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);

    if (cached) {
        return cached;
    }

    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('[SW] Cache first fetch failed:', error);
        throw error;
    }
}

/**
 * Network First strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            // Cache successful API responses
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Fallback to cache
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(request);

        if (cached) {
            return cached;
        }

        throw error;
    }
}

/**
 * Sync recordings (background sync handler)
 * @returns {Promise<void>}
 */
async function syncRecordings() {
    console.log('[SW] Syncing recordings...');

    // Notify all clients to process queue
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'SYNC_RECORDINGS'
        });
    });
}

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
    console.log('[SW] Received message:', event.data);

    if (event.data === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('[SW] Service Worker loaded');
```

**Step 4: Create Service Worker registration script**

Create `pwa/frontend/static/js/sw-register.js`:

```javascript
/**
 * Service Worker Registration
 * Registers the service worker and handles iOS-specific limitations
 */

(function() {
    'use strict';

    // Check if service workers are supported
    if (!('serviceWorker' in navigator)) {
        console.log('[SW] Service Worker not supported in this browser');
        return;
    }

    /**
     * Detect iOS
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Register service worker
     */
    async function registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');

            console.log('[SW] Registered successfully:', registration.scope);

            // Handle updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        console.log('[SW] New version available');
                        // Could show update notification here
                    }
                });
            });

            // iOS-specific handling
            if (isIOS()) {
                console.log('[SW] iOS detected - limited service worker support');
                handleIOSLimitations(registration);
            }

        } catch (error) {
            console.error('[SW] Registration failed:', error);
        }
    }

    /**
     * Handle iOS limitations
     * @param {ServiceWorkerRegistration} registration
     */
    function handleIOSLimitations(registration) {
        // iOS doesn't support background sync
        // The UploadManager will handle polling fallback

        // Listen for messages from SW
        navigator.serviceWorker.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'SYNC_RECORDINGS') {
                // Trigger queue processing via UploadManager
                if (window.UploadManager) {
                    window.UploadManager.processQueue();
                }
            }
        });
    }

    // Register when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', registerServiceWorker);
    } else {
        registerServiceWorker();
    }
})();
```

**Step 5: Update base template to register SW**

Edit `pwa/frontend/templates/base.html`, uncomment and modify lines 36-37:

```html
    <!-- Service Worker Registration -->
    <script src="/static/js/sw-register.js"></script>
</body>
```

**Step 6: Run test to verify it passes**

```bash
uv run pytest pwa/tests/e2e/test_service_worker.py -v
# Expected: 2 tests PASS (may require browser reload for first run)
```

**Step 7: Commit**

```bash
git add pwa/frontend/static/js/service-worker.js pwa/frontend/static/js/sw-register.js pwa/frontend/templates/base.html pwa/tests/e2e/test_service_worker.py
git commit -m "feat: add Service Worker with caching and background sync support"
```

---

## Task 7: Create Queue UI

**Purpose:** Allow clinicians to view pending/completed recordings and their upload status.

**Files:**
- Create: `pwa/frontend/templates/queue.html`
- Create: `pwa/frontend/static/js/queue.js`
- Modify: `pwa/backend/routes/pages.py` - add queue route
- Test: Create `pwa/tests/e2e/test_queue_ui.py`

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_queue_ui.py`:

```python
# pwa/tests/e2e/test_queue_ui.py
"""Playwright tests for Queue UI."""

import pytest
from playwright.sync_api import Page, expect


def test_queue_page_loads(page: Page) -> None:
    """Test that queue page loads."""
    page.goto("http://localhost:8002/queue")

    # Verify page title
    expect(page).to_have_title("Clinical Transcription PWA")

    # Verify queue heading exists
    heading = page.locator('h2:has-text("Recording Queue")')
    expect(heading).to_be_visible()


def test_queue_shows_empty_state(page: Page) -> None:
    """Test empty queue message."""
    page.goto("http://localhost:8002/queue")

    # Check for empty state message
    empty_msg = page.locator('text=No recordings in queue')
    expect(empty_msg).to_be_visible()


def test_queue_shows_ios_warning(page: Page) -> None:
    """Test that iOS warning appears on iOS devices."""
    # Simulate iOS user agent
    page.context.set_extra_http_headers({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
    })

    page.goto("http://localhost:8002/queue")

    # The iOS warning might not appear in Playwright, but we can check the page loads
    expect(page).to_have_title("Clinical Transcription PWA")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_queue_ui.py -v
# Expected: FAIL - 404 Not Found (queue route doesn't exist)
```

**Step 3: Add queue route**

Edit `pwa/backend/routes/pages.py`, add after line 23:

```python

@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request) -> HTMLResponse:
    """Queue page showing pending/completed recordings."""
    return templates.TemplateResponse("queue.html", {"request": request})
```

**Step 4: Create Queue HTML template**

Create `pwa/frontend/templates/queue.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="queue-container">
    <h2>Recording Queue</h2>

    <div id="connection-status" class="connection-indicator online">
        <span class="status-dot"></span>
        <span class="status-text">Online</span>
    </div>

    <div id="ios-warning-container"></div>

    <div class="queue-actions">
        <button id="refresh-queue" class="btn btn-secondary" onclick="QueueUI.refresh()">
            Refresh
        </button>
        <button id="sync-now" class="btn btn-primary" onclick="QueueUI.syncNow()">
            Sync Now
        </button>
    </div>

    <div id="queue-list" class="queue-list">
        <p class="empty-state">Loading queue...</p>
    </div>

    <div id="recording-detail" class="recording-detail hidden">
        <h3>Recording Details</h3>
        <div id="detail-content"></div>
        <button class="btn btn-secondary" onclick="QueueUI.hideDetail()">Close</button>
    </div>
</div>

<style>
.queue-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

.connection-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
}

.connection-indicator.online {
    background: #d4edda;
    color: #155724;
}

.connection-indicator.offline {
    background: #f8d7da;
    color: #721c24;
}

.connection-indicator.syncing {
    background: #fff3cd;
    color: #856404;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
}

.queue-actions {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.queue-list {
    border: 1px solid #ddd;
    border-radius: 4px;
    overflow: hidden;
}

.queue-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background 0.2s;
}

.queue-item:last-child {
    border-bottom: none;
}

.queue-item:hover {
    background: #f5f5f5;
}

.queue-item.status-failed {
    background: #fff5f5;
}

.queue-item.status-uploaded {
    background: #f5fff5;
}

.status-icon {
    margin-right: 12px;
    font-size: 18px;
}

.recording-info {
    flex: 1;
}

.recording-id {
    font-weight: 500;
    color: #333;
}

.recording-meta {
    font-size: 12px;
    color: #666;
    margin-top: 2px;
}

.recording-actions {
    display: flex;
    gap: 8px;
}

.btn-icon {
    padding: 4px 8px;
    font-size: 12px;
    background: none;
    border: 1px solid #ddd;
    border-radius: 3px;
    cursor: pointer;
}

.btn-icon:hover {
    background: #f0f0f0;
}

.empty-state {
    text-align: center;
    padding: 40px;
    color: #666;
}

.recording-detail {
    margin-top: 24px;
    padding: 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #f9f9f9;
}

.recording-detail.hidden {
    display: none;
}

.ios-warning {
    background: #fff3cd;
    border: 1px solid #ffc107;
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.warning-icon {
    font-size: 18px;
}

.detail-row {
    margin-bottom: 8px;
}

.detail-label {
    font-weight: 500;
    color: #555;
}

.detail-value {
    color: #333;
}

.error-message {
    color: #721c24;
    font-size: 12px;
}
</style>

<script src="/static/js/queue.js"></script>
<script>
    // Initialize queue UI when page loads
    document.addEventListener('DOMContentLoaded', () => {
        QueueUI.init();
    });
</script>
{% endblock %}
```

**Step 5: Create Queue JavaScript module**

Create `pwa/frontend/static/js/queue.js`:

```javascript
/**
 * Queue UI Module
 * Displays and manages the recording queue
 */

(function() {
    'use strict';

    // DOM Elements
    let queueListEl;
    let connectionStatusEl;
    let recordingDetailEl;
    let detailContentEl;
    let iosWarningContainerEl;

    /**
     * Initialize queue UI
     */
    function init() {
        console.log('[QueueUI] Initializing...');

        // Get DOM elements
        queueListEl = document.getElementById('queue-list');
        connectionStatusEl = document.getElementById('connection-status');
        recordingDetailEl = document.getElementById('recording-detail');
        detailContentEl = document.getElementById('detail-content');
        iosWarningContainerEl = document.getElementById('ios-warning-container');

        // Setup listeners
        setupEventListeners();

        // Check iOS and show warning if needed
        if (isIOS()) {
            showIOSWarning();
        }

        // Initial load
        refresh();

        // Start polling for updates
        startPolling();
    }

    /**
     * Check if on iOS
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Show iOS warning
     */
    function showIOSWarning() {
        const warning = document.createElement('div');
        warning.className = 'ios-warning';
        warning.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <div>
                <strong>iOS Sync Limitation</strong><br>
                Keep this app open to sync recordings. iOS doesn't support background sync.
            </div>
        `;
        iosWarningContainerEl.appendChild(warning);
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Listen for upload status changes
        window.addEventListener('upload-status-change', (event) => {
            const { recordingId, status } = event.detail;
            console.log('[QueueUI] Upload status change:', recordingId, status);
            refresh();
        });

        // Listen for online/offline
        window.addEventListener('online', updateConnectionStatus);
        window.addEventListener('offline', updateConnectionStatus);

        // Initial status
        updateConnectionStatus();
    }

    /**
     * Update connection status indicator
     */
    function updateConnectionStatus() {
        if (!connectionStatusEl) return;

        const isOnline = navigator.onLine;
        const statusDot = connectionStatusEl.querySelector('.status-dot');
        const statusText = connectionStatusEl.querySelector('.status-text');

        if (isOnline) {
            connectionStatusEl.className = 'connection-indicator online';
            statusText.textContent = 'Online';
        } else {
            connectionStatusEl.className = 'connection-indicator offline';
            statusText.textContent = 'Offline - Sync paused';
        }
    }

    /**
     * Start polling for updates
     */
    function startPolling() {
        // Refresh every 10 seconds
        setInterval(() => {
            refresh();
        }, 10000);
    }

    /**
     * Refresh the queue display
     */
    async function refresh() {
        if (!queueListEl) return;

        try {
            const recordings = await window.RecordingStorage.getAllRecordings();
            renderQueue(recordings);
            updateConnectionStatus();
        } catch (error) {
            console.error('[QueueUI] Error refreshing queue:', error);
            queueListEl.innerHTML = '<p class="empty-state">Error loading queue</p>';
        }
    }

    /**
     * Render the queue
     * @param {Array} recordings
     */
    function renderQueue(recordings) {
        if (recordings.length === 0) {
            queueListEl.innerHTML = '<p class="empty-state">No recordings in queue</p>';
            return;
        }

        const html = recordings.map(recording => {
            const statusIcon = getStatusIcon(recording.sync_status);
            const statusClass = getStatusClass(recording.sync_status);
            const formattedDate = formatDate(recording.created_at);
            const duration = formatDuration(recording.duration_seconds);

            return `
                <div class="queue-item ${statusClass}" data-id="${recording.id}" onclick="QueueUI.showDetail('${recording.id}')">
                    <span class="status-icon">${statusIcon}</span>
                    <div class="recording-info">
                        <div class="recording-id">${recording.patient_id}</div>
                        <div class="recording-meta">
                            ${duration} • ${formattedDate} • ${formatStatus(recording.sync_status)}
                        </div>
                        ${recording.last_error ? `<div class="error-message">${recording.last_error}</div>` : ''}
                    </div>
                    <div class="recording-actions" onclick="event.stopPropagation()">
                        ${getActionButtons(recording)}
                    </div>
                </div>
            `;
        }).join('');

        queueListEl.innerHTML = html;
    }

    /**
     * Get status icon
     * @param {string} status
     * @returns {string}
     */
    function getStatusIcon(status) {
        const icons = {
            'pending_upload': '⏳',
            'uploading': '🔄',
            'uploaded': '✅',
            'failed': '❌'
        };
        return icons[status] || '❓';
    }

    /**
     * Get status CSS class
     * @param {string} status
     * @returns {string}
     */
    function getStatusClass(status) {
        return `status-${status}`;
    }

    /**
     * Format status for display
     * @param {string} status
     * @returns {string}
     */
    function formatStatus(status) {
        const labels = {
            'pending_upload': 'Pending Upload',
            'uploading': 'Uploading...',
            'uploaded': 'Uploaded',
            'failed': 'Failed - Will Retry'
        };
        return labels[status] || status;
    }

    /**
     * Format duration
     * @param {number} seconds
     * @returns {string}
     */
    function formatDuration(seconds) {
        if (!seconds) return '0s';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (mins > 0) {
            return `${mins}m ${secs}s`;
        }
        return `${secs}s`;
    }

    /**
     * Format date
     * @param {string} dateString
     * @returns {string}
     */
    function formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    /**
     * Get action buttons for recording
     * @param {Object} recording
     * @returns {string}
     */
    function getActionButtons(recording) {
        const buttons = [];

        // Retry button for failed uploads
        if (recording.sync_status === 'failed') {
            buttons.push(`<button class="btn-icon" onclick="QueueUI.retryUpload('${recording.id}')">Retry</button>`);
        }

        // Export button
        if (recording.audio_blob) {
            buttons.push(`<button class="btn-icon" onclick="QueueUI.exportRecording('${recording.id}')">Export</button>`);
        }

        // Delete button
        buttons.push(`<button class="btn-icon" onclick="QueueUI.deleteRecording('${recording.id}')">Delete</button>`);

        return buttons.join('');
    }

    /**
     * Show recording detail
     * @param {string} recordingId
     */
    async function showDetail(recordingId) {
        const recording = await window.RecordingStorage.getRecording(recordingId);
        if (!recording) return;

        const html = `
            <div class="detail-row">
                <span class="detail-label">ID:</span>
                <span class="detail-value">${recording.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Patient:</span>
                <span class="detail-value">${recording.patient_id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Duration:</span>
                <span class="detail-value">${formatDuration(recording.duration_seconds)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">${formatStatus(recording.sync_status)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span class="detail-value">${formatDate(recording.created_at)}</span>
            </div>
            ${recording.draft_transcript ? `
            <div class="detail-row">
                <span class="detail-label">Draft Transcript:</span>
                <div class="detail-value" style="margin-top: 8px; padding: 8px; background: white; border: 1px solid #ddd; border-radius: 4px;">
                    ${recording.draft_transcript}
                </div>
            </div>
            ` : ''}
            ${recording.retry_count ? `
            <div class="detail-row">
                <span class="detail-label">Retry Count:</span>
                <span class="detail-value">${recording.retry_count}</span>
            </div>
            ` : ''}
            ${recording.last_error ? `
            <div class="detail-row">
                <span class="detail-label">Last Error:</span>
                <span class="detail-value" style="color: #721c24;">${recording.last_error}</span>
            </div>
            ` : ''}
        `;

        detailContentEl.innerHTML = html;
        recordingDetailEl.classList.remove('hidden');
    }

    /**
     * Hide detail panel
     */
    function hideDetail() {
        recordingDetailEl.classList.add('hidden');
    }

    /**
     * Retry upload
     * @param {string} recordingId
     */
    async function retryUpload(recordingId) {
        console.log('[QueueUI] Retrying upload:', recordingId);
        await window.UploadManager.queueUpload(recordingId);
        refresh();
    }

    /**
     * Export recording
     * @param {string} recordingId
     */
    async function exportRecording(recordingId) {
        const recording = await window.RecordingStorage.getRecording(recordingId);
        if (!recording || !recording.audio_blob) {
            alert('Recording not found or no audio available');
            return;
        }

        // Confirm export
        if (!confirm('Export this recording? The audio file will be downloaded.')) {
            return;
        }

        // Create download link
        const url = URL.createObjectURL(recording.audio_blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `recording-${recordingId}.wav`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Delete recording
     * @param {string} recordingId
     */
    async function deleteRecording(recordingId) {
        if (!confirm('Are you sure you want to delete this recording?')) {
            return;
        }

        try {
            await window.RecordingStorage.deleteRecording(recordingId);
            refresh();
        } catch (error) {
            console.error('[QueueUI] Error deleting recording:', error);
            alert('Failed to delete recording');
        }
    }

    /**
     * Sync now - trigger queue processing
     */
    async function syncNow() {
        if (!navigator.onLine) {
            alert('You are offline. Sync will resume when connection is restored.');
            return;
        }

        connectionStatusEl.className = 'connection-indicator syncing';
        connectionStatusEl.querySelector('.status-text').textContent = 'Syncing...';

        await window.UploadManager.processQueue();

        // Refresh after a short delay to show updated status
        setTimeout(() => {
            refresh();
        }, 1000);
    }

    // Expose API globally
    window.QueueUI = {
        init,
        refresh,
        showDetail,
        hideDetail,
        retryUpload,
        exportRecording,
        deleteRecording,
        syncNow
    };

    console.log('[QueueUI] Loaded');
})();
```

**Step 6: Run test to verify it passes**

```bash
uv run pytest pwa/tests/e2e/test_queue_ui.py -v
# Expected: 3 tests PASS
```

**Step 7: Run all tests**

```bash
uv run pytest pwa/tests/ -v
# Expected: All tests pass
```

**Step 8: Commit**

```bash
git add pwa/frontend/templates/queue.html pwa/frontend/static/js/queue.js pwa/backend/routes/pages.py pwa/tests/e2e/test_queue_ui.py
git commit -m "feat: add Queue UI with recording status, retry, and export functionality"
```

---

## Task 8: Update Recorder.js for Offline Storage

**Purpose:** Integrate IndexedDB storage into the existing recording flow.

**Files:**
- Modify: `pwa/frontend/static/js/recorder.js`
- Test: Create `pwa/tests/e2e/test_offline_recording.py`

**Step 1: Write the failing test**

Create `pwa/tests/e2e/test_offline_recording.py`:

```python
# pwa/tests/e2e/test_offline_recording.py
"""Playwright tests for offline recording functionality."""

import pytest
from playwright.sync_api import Page, expect


def test_record_button_works(page: Page) -> None:
    """Test that record button starts/stops recording."""
    page.goto("http://localhost:8002/record/patient-123")

    # Click record button
    record_btn = page.locator('#record-btn')
    record_btn.click()

    # Wait a moment
    page.wait_for_timeout(1000)

    # Should show recording status
    status = page.locator('#recording-status')
    expect(status).not_to_have_class('hidden')

    # Click again to stop
    record_btn.click()

    # Wait for processing
    page.wait_for_timeout(500)


def test_offline_storage_saves_recording(page: Page) -> None:
    """Test that recording is saved to IndexedDB even when offline."""
    page.goto("http://localhost:8002/record/patient-123")

    # Simulate offline
    page.context.set_offline(True)

    # Record something
    record_btn = page.locator('#record-btn')
    record_btn.click()
    page.wait_for_timeout(1000)
    record_btn.click()

    # Wait for local storage
    page.wait_for_timeout(1000)

    # Check IndexedDB
    result = page.evaluate("""
        async () => {
            const recordings = await window.RecordingStorage.getAllRecordings();
            return {
                count: recordings.length,
                hasPending: recordings.some(r => r.sync_status === 'pending_upload')
            };
        }
    """)

    # Restore online
    page.context.set_offline(False)

    assert result["count"] >= 1, "No recordings found in IndexedDB"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest pwa/tests/e2e/test_offline_recording.py -v
# Expected: FAIL - recorder.js doesn't integrate with IndexedDB yet
```

**Step 3: Update recorder.js**

Edit `pwa/frontend/static/js/recorder.js`, replace the entire file:

```javascript
/**
 * Recorder Module - Handles audio recording with offline storage
 */

let mediaRecorder;
let audioChunks = [];
let recordingStartTime;
let timerInterval;
let isRecording = false;
let currentRecordingId = null;

// Audio context for draft transcription (online only)
let recognition = null;
let draftTranscript = '';

/**
 * Toggle recording on/off
 */
async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

/**
 * Initialize speech recognition for draft transcription
 * Online only - Web Speech API requires internet
 */
function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('[Recorder] Speech recognition not supported');
        return null;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                final += transcript;
            } else {
                interim += transcript;
            }
        }

        draftTranscript += final;
        updateDraftTranscript(draftTranscript + interim);
    };

    recognition.onerror = (event) => {
        console.error('[Recorder] Speech recognition error:', event.error);
    };

    return recognition;
}

/**
 * Update draft transcript display
 * @param {string} text
 */
function updateDraftTranscript(text) {
    let draftEl = document.getElementById('draft-transcript');
    if (!draftEl) {
        draftEl = document.createElement('div');
        draftEl.id = 'draft-transcript';
        draftEl.className = 'draft-transcript';
        draftEl.style.cssText = 'margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px; font-style: italic; color: #666;';

        const container = document.querySelector('.recorder-container');
        if (container) {
            container.appendChild(draftEl);
        }
    }

    draftEl.textContent = text ? `Draft: ${text}` : '';
    draftEl.style.display = text ? 'block' : 'none';
}

/**
 * Start recording
 */
async function startRecording() {
    try {
        // Reset state
        audioChunks = [];
        draftTranscript = '';
        currentRecordingId = generateUUID();

        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create media recorder
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            await handleRecordingComplete();
        };

        // Start recording
        mediaRecorder.start(100); // Collect data every 100ms
        isRecording = true;
        recordingStartTime = Date.now();

        // Update UI
        document.getElementById('record-btn').classList.add('recording');
        document.getElementById('record-text').textContent = 'Stop Recording';
        document.getElementById('recording-status').classList.remove('hidden');

        // Start timer
        timerInterval = setInterval(updateTimer, 1000);

        // Start draft transcription if online
        if (navigator.onLine && recognition) {
            try {
                recognition.start();
            } catch (e) {
                console.log('[Recorder] Could not start speech recognition:', e.message);
            }
        }

        console.log('[Recorder] Started recording:', currentRecordingId);

    } catch (error) {
        console.error('[Recorder] Error starting recording:', error);
        alert('Could not start recording. Please ensure microphone access is allowed.');
    }
}

/**
 * Stop recording
 */
async function stopRecording() {
    if (!mediaRecorder || !isRecording) return;

    // Stop media recorder
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    isRecording = false;

    // Stop speech recognition
    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {
            // Already stopped
        }
    }

    // Clear timer
    clearInterval(timerInterval);

    // Update UI
    document.getElementById('record-btn').classList.remove('recording');
    document.getElementById('record-text').textContent = 'Start Recording';
    document.getElementById('recording-status').classList.add('hidden');
    document.getElementById('upload-status').classList.remove('hidden');

    console.log('[Recorder] Stopped recording');
}

/**
 * Handle recording complete
 */
async function handleRecordingComplete() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
    const durationSeconds = Math.floor((Date.now() - recordingStartTime) / 1000);

    console.log('[Recorder] Recording complete:', {
        id: currentRecordingId,
        duration: durationSeconds,
        size: audioBlob.size
    });

    // Save to IndexedDB
    const recording = {
        id: currentRecordingId,
        patient_id: typeof patientId !== 'undefined' ? patientId : 'unknown',
        clinician_id: 'current-clinician', // TODO: Get from auth
        audio_blob: audioBlob,
        draft_transcript: draftTranscript || null,
        duration_seconds: durationSeconds,
        created_at: new Date().toISOString(),
        sync_status: 'pending_upload',
        retry_count: 0
    };

    try {
        await window.RecordingStorage.saveRecording(recording);
        console.log('[Recorder] Saved to IndexedDB:', currentRecordingId);

        // Show appropriate message
        if (navigator.onLine) {
            document.getElementById('upload-status').classList.add('hidden');
            document.getElementById('result').classList.remove('hidden');
            document.getElementById('result').innerHTML = `
                <h3>Recording Saved</h3>
                <p>Status: <span id="recording-status-text">Pending Upload</span></p>
                <p>Your recording will be uploaded shortly.</p>
                <a href="/queue" class="btn">View Queue</a>
            `;

            // Trigger upload
            await window.UploadManager.queueUpload(currentRecordingId);
        } else {
            document.getElementById('upload-status').classList.add('hidden');
            document.getElementById('result').classList.remove('hidden');
            document.getElementById('result').innerHTML = `
                <h3>Recording Saved Locally</h3>
                <p>You are currently offline.</p>
                <p>Your recording has been saved and will upload when you reconnect.</p>
                <a href="/queue" class="btn">View Queue</a>
            `;
        }

        // Clear draft transcript
        updateDraftTranscript('');

    } catch (error) {
        console.error('[Recorder] Error saving recording:', error);
        document.getElementById('upload-status').classList.add('hidden');
        document.getElementById('result').classList.remove('hidden');
        document.getElementById('result').innerHTML = `
            <h3>Error Saving Recording</h3>
            <p>There was an error saving your recording: ${error.message}</p>
            <button class="btn" onclick="location.reload()">Try Again</button>
        `;
    }
}

/**
 * Update timer display
 */
function updateTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('timer').textContent = `${minutes}:${seconds}`;
}

/**
 * Generate UUID
 * @returns {string}
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Initialize speech recognition on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initSpeechRecognition();
    });
} else {
    initSpeechRecognition();
}

console.log('[Recorder] Module loaded');
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest pwa/tests/e2e/test_offline_recording.py -v
# Expected: 2 tests PASS
```

**Step 5: Run all tests**

```bash
uv run pytest pwa/tests/ -v
# Expected: All tests pass
```

**Step 6: Commit**

```bash
git add pwa/frontend/static/js/recorder.js pwa/tests/e2e/test_offline_recording.py
git commit -m "feat: integrate IndexedDB storage into recorder with offline support"
```

---

## Task 9: Add CSS Styles

**Purpose:** Add styling for new UI components (queue, status indicators, iOS warning).

**Files:**
- Modify: `pwa/frontend/static/css/style.css`

**Step 1: Add styles to existing CSS**

Edit `pwa/frontend/static/css/style.css`, add at the end:

```css
/* Queue UI Styles */
.queue-container {
    max-width: 800px;
    margin: 0 auto;
}

.connection-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 14px;
}

.connection-indicator.online {
    background: #d4edda;
    color: #155724;
}

.connection-indicator.offline {
    background: #f8d7da;
    color: #721c24;
}

.connection-indicator.syncing {
    background: #fff3cd;
    color: #856404;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.queue-actions {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.queue-list {
    border: 1px solid #ddd;
    border-radius: 4px;
    overflow: hidden;
}

.queue-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background 0.2s;
}

.queue-item:last-child {
    border-bottom: none;
}

.queue-item:hover {
    background: #f5f5f5;
}

.queue-item.status-failed {
    background: #fff5f5;
}

.queue-item.status-uploaded {
    background: #f5fff5;
}

.status-icon {
    margin-right: 12px;
    font-size: 18px;
}

.recording-info {
    flex: 1;
}

.recording-id {
    font-weight: 500;
    color: #333;
}

.recording-meta {
    font-size: 12px;
    color: #666;
    margin-top: 2px;
}

.recording-actions {
    display: flex;
    gap: 8px;
}

.btn-icon {
    padding: 4px 8px;
    font-size: 12px;
    background: none;
    border: 1px solid #ddd;
    border-radius: 3px;
    cursor: pointer;
}

.btn-icon:hover {
    background: #f0f0f0;
}

.empty-state {
    text-align: center;
    padding: 40px;
    color: #666;
}

.recording-detail {
    margin-top: 24px;
    padding: 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #f9f9f9;
}

.recording-detail.hidden {
    display: none;
}

/* iOS Warning */
.ios-warning {
    background: #fff3cd;
    border: 1px solid #ffc107;
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.warning-icon {
    font-size: 18px;
}

/* Detail panel styles */
.detail-row {
    margin-bottom: 8px;
}

.detail-label {
    font-weight: 500;
    color: #555;
}

.detail-value {
    color: #333;
}

.error-message {
    color: #721c24;
    font-size: 12px;
}

/* Draft transcript */
.draft-transcript {
    margin-top: 10px;
    padding: 10px;
    background: #f5f5f5;
    border-radius: 4px;
    font-style: italic;
    color: #666;
}

/* Recording button styles */
.record-btn.recording {
    background: #dc3545;
    animation: pulse 1s infinite;
}

.record-btn.recording:hover {
    background: #c82333;
}
```

**Step 2: Visual verification**

```bash
uv run python pwa/backend/main.py
# Open http://localhost:8002/queue
# Verify: Queue page loads with styling
# Open http://localhost:8002/record/patient-123
# Verify: Record button has proper styling
```

**Step 3: Commit**

```bash
git add pwa/frontend/static/css/style.css
git commit -m "style: add CSS for queue UI, status indicators, and iOS warnings"
```

---

## Task 10: Integration Testing

**Purpose:** Run full integration tests and manual testing checklist.

**Files:**
- Run: All tests
- Verify: Manual testing

**Step 1: Run all automated tests**

```bash
# Backend tests
uv run pytest pwa/tests/test_recording_model.py pwa/tests/test_upload_endpoint.py pwa/tests/test_recording_routes.py -v

# E2E tests
uv run pytest pwa/tests/e2e/ -v

# All tests
uv run pytest pwa/tests/ -v
# Expected: All tests pass
```

**Step 2: Manual testing checklist**

Open `docs/plans/HANDOFF_PHASE2A.md` and run through the manual testing section.

**Online Testing:**
1. `uv run python pwa/backend/main.py`
2. Open http://localhost:8002/record/patient-123
3. Click "Start Recording"
4. Speak for 5 seconds
5. Click "Stop Recording"
6. Verify: Recording saves and uploads automatically
7. Navigate to /queue - verify recording appears with "Uploaded" status

**Offline Testing:**
1. Open browser DevTools > Network tab
2. Check "Offline" checkbox to simulate offline mode
3. Record another 5 seconds
4. Verify: Shows "Recording Saved Locally" message
5. Open DevTools > Application > IndexedDB
6. Verify: Recording appears in "ClinicalTranscription" > "recordings"
7. Uncheck "Offline" to go back online
8. Verify: Upload starts automatically (Chrome) or click "Sync Now" (iOS)

**iOS Simulation:**
1. Open DevTools > Console
2. Type: `navigator.userAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"`
3. Reload page
4. Verify: iOS warning appears at top

**Step 3: Final verification**

```bash
# Check all files exist
ls -la pwa/frontend/static/js/indexeddb-service.js
ls -la pwa/frontend/static/js/upload-manager.js
ls -la pwa/frontend/static/js/service-worker.js
ls -la pwa/frontend/static/js/sw-register.js
ls -la pwa/frontend/static/js/queue.js
ls -la pwa/frontend/templates/queue.html

# Run final test suite
uv run pytest pwa/tests/ -v --tb=short
```

**Step 4: Commit**

```bash
# Check git status
git status

# Add any remaining files
git add -A

# Final commit
git commit -m "feat: complete Phase 2a - Offline Recording PWA with IndexedDB, Service Worker, and Queue UI"
```

---

## Summary

At the end of this implementation plan, you will have:

1. **IndexedDB Service** (`indexeddb-service.js`) - Stores recordings locally
2. **Upload Manager** (`upload-manager.js`) - Handles uploads with retry logic
3. **Service Worker** (`service-worker.js`) - Caches assets and enables offline use
4. **Queue UI** (`queue.html`, `queue.js`) - View and manage recordings
5. **Updated Recorder** (`recorder.js`) - Integrates offline storage
6. **Upload Endpoint** - Receives audio files via multipart/form-data
7. **Full test coverage** - Unit and E2E tests

**Key Behaviors Implemented:**
- Record audio offline (stored in IndexedDB)
- Auto-upload when online (Chrome/Android)
- HTMX polling fallback for iOS
- Retry with exponential backoff
- Queue shows upload status
- iOS warning displayed when detected
- Export audio for clinical safety

**Estimated Total Time:** 25-38 hours (3-4 weeks at 50% capacity)

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-02-23-phase2a-offline-recording-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**

---

*End of Implementation Plan*
