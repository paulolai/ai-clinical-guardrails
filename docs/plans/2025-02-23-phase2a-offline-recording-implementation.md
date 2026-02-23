# Phase 2a: Offline Recording Implementation Plan (HANDOFF READY)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Status:** Ready for implementation
> **Estimated Time:** 2-3 weeks (revised from 1 week based on complexity)

---

## ⚠️ CRITICAL CONTEXT FOR NEXT AGENT

**Phase 2 has been SPLIT:**
- **Phase 2a (This Plan)**: Offline recording and sync ONLY. AI backend is mocked.
- **Phase 2b (Next Sprint)**: Add Whisper + LLM integration.

**Why split?** Offline PWA state management and AI R&D are two massive unrelated engineering hurdles. Attempting both simultaneously risks a buggy PWA and half-baked AI pipeline.

### Key Technical Constraints (DO NOT SKIP):

1. **Draft Transcription is ONLINE ONLY** - Web Speech API requires internet (streams to Google/Apple servers). It will NOT work offline on most browsers.

2. **iOS/Safari has NO Background Sync** - Safari doesn't support the Background Sync API. Must implement foreground sync with HTMX polling and clear UI messaging.

3. **Timeline is Optimistic** - The original "Week 1" estimate is unrealistic. Robust offline sync usually takes 2-3x longer due to browser quirks (storage quotas, eviction, iOS limitations).

4. **LLM Evaluation Suite is CANCELLED** - Pick ONE model (Llama 3.1 8B or 70B) and move on. Optimization is Phase 3.

**Reference:** See `2025-02-23-phase2-offline-recording-design.md` (Revision 1.1) for full design.

---

## Goal

Build offline-capable clinical recording with IndexedDB storage, Service Worker (with iOS fallback), and foreground sync. Mock transcription for Phase 2a.

**Architecture:**
- Chrome/Android: Service Worker (Workbox) + Background Sync
- iOS/Safari: HTMX polling fallback + foreground sync requirement
- Web Speech API: ONLINE ONLY (catches mic issues when connected)

---

## Prerequisites

Before starting:

```bash
# 1. Verify Phase 1 is working (9 tests should pass)
uv run pytest pwa/tests/ -v

# 2. Run the server and test recording works
uv run python pwa/backend/main.py
# Open http://localhost:8002/ and verify recording works

# 3. Check git status is clean
git status
```

---

## Sprint 1: IndexedDB Storage Foundation (Week 1)

### Task 1: Install localForage for IndexedDB

**Files:**
- Modify: `pwa/frontend/templates/base.html`
- Create: `pwa/frontend/static/js/indexeddb-service.js`

**Step 1: Add localForage CDN**

```html
<!-- Add before closing </body> tag in base.html -->
<script src="https://cdn.jsdelivr.net/npm/localforage@1.10.0/dist/localforage.min.js"></script>
<script src="/static/js/indexeddb-service.js"></script>
```

**Step 2: Create IndexedDB service**

```javascript
// pwa/frontend/static/js/indexeddb-service.js
/**
 * IndexedDB service for offline audio storage
 * Uses localForage for simplified IndexedDB API
 */

const RecordingStore = {
    async init() {
        await localforage.config({
            name: 'ClinicalTranscriptionPWA',
            storeName: 'recordings',
            description: 'Offline audio recordings'
        });
    },

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

    async getRecording(id) {
        return await localforage.getItem(id);
    },

    async getAllRecordings() {
        const recordings = [];
        await localforage.iterate((value) => {
            recordings.push(value);
        });
        return recordings.sort((a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
        );
    },

    async getPendingUploads() {
        const recordings = await this.getAllRecordings();
        return recordings.filter(r => r.sync_status === 'pending_upload');
    },

    async updateStatus(id, status, error = null) {
        const recording = await this.getRecording(id);
        if (recording) {
            recording.sync_status = status;
            if (error) recording.last_error = error;
            if (status === 'failed') recording.retry_count += 1;
            await localforage.setItem(id, recording);
        }
        return recording;
    },

    async markUploaded(id) {
        await localforage.removeItem(id);
    },

    async deleteRecording(id) {
        await localforage.removeItem(id);
    },

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
window.RecordingStore = RecordingStore;
```

**Step 3: Verify IndexedDB works**

```bash
# Run tests (none yet, just verify no errors)
uv run python pwa/backend/main.py
# Open browser, check console for "RecordingStore initialized"
```

**Step 4: Commit**

```bash
git add pwa/
git commit -m "feat: add IndexedDB service with localForage"
```

---

### Task 2: Update Recording Model for Offline Support

**Files:**
- Modify: `pwa/backend/models/recording.py`
- Test: `pwa/tests/test_recording_model.py`

**Step 1: Write failing test**

```python
# pwa/tests/test_recording_model.py
import pytest
from uuid import uuid4
from pwa.backend.models.recording import Recording, RecordingStatus

def test_recording_with_draft_transcript():
    """Test that Recording model supports draft transcript."""
    recording = Recording(
        id=uuid4(),
        patient_id="patient-123",
        clinician_id="clinician-456",
        audio_file_path="/tmp/test.wav",
        duration_seconds=120,
        status=RecordingStatus.PENDING,
        draft_transcript="Draft text"
    )
    assert recording.draft_transcript == "Draft text"

def test_recording_with_upload_tracking():
    """Test upload tracking fields."""
    recording = Recording(
        id=uuid4(),
        patient_id="patient-123",
        local_storage_key="key-123",
        upload_attempts=2
    )
    assert recording.local_storage_key == "key-123"
    assert recording.upload_attempts == 2
```

**Step 2: Run test (expect fail)**

```bash
uv run pytest pwa/tests/test_recording_model.py::test_recording_with_draft_transcript -v
# Expected: FAIL
```

**Step 3: Add fields to model**

```python
# Modify pwa/backend/models/recording.py
# Add these fields to the Recording class:

    # NEW: Transcription fields
    draft_transcript: Optional[str] = Field(default=None)
    final_transcript: Optional[str] = Field(default=None)

    # NEW: Upload tracking
    local_storage_key: Optional[str] = Field(default=None)
    upload_attempts: int = Field(default=0)
```

**Step 4: Run test (expect pass)**

```bash
uv run pytest pwa/tests/test_recording_model.py -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add draft_transcript and upload tracking fields"
```

---

### Task 3: Create Upload API Endpoint

**Files:**
- Modify: `pwa/backend/routes/recordings.py`
- Test: `pwa/tests/test_recording_routes.py`

**Step 1: Write failing test**

```python
# pwa/tests/test_recording_routes.py
import io

def test_upload_recording_with_audio():
    """Test uploading a recording with audio file."""
    audio_content = b"fake audio data"

    response = client.post(
        "/api/v1/recordings/upload",
        data={
            "patient_id": "patient-123",
            "duration_seconds": "120",
            "draft_transcript": "Draft"
        },
        files={
            "audio": ("recording.wav", io.BytesIO(audio_content), "audio/wav")
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-123"
```

**Step 2: Run test (expect fail)**

```bash
uv run pytest pwa/tests/test_recording_routes.py::test_upload_recording_with_audio -v
# Expected: FAIL (404)
```

**Step 3: Add upload endpoint**

```python
# Modify pwa/backend/routes/recordings.py
# Add after existing routes:

@router.post("/upload", status_code=201)
async def upload_recording(
    patient_id: str = Form(...),
    duration_seconds: int = Form(...),
    draft_transcript: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    service: RecordingService = Depends(get_recording_service)
):
    """Upload a recording with audio file."""
    import shutil
    from pathlib import Path
    from uuid import uuid4

    # Save audio file
    upload_dir = Path("uploads/recordings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{uuid4()}.wav"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Create recording
    recording = service.create_recording(
        patient_id=patient_id,
        clinician_id="current-clinician",  # TODO: Get from auth
        duration_seconds=duration_seconds,
        audio_file_path=str(file_path),
        draft_transcript=draft_transcript
    )

    return {
        "id": str(recording.id),
        "patient_id": recording.patient_id,
        "duration_seconds": recording.duration_seconds,
        "status": recording.status.value,
        "created_at": recording.created_at.isoformat()
    }
```

**Step 4: Run test (expect pass)**

```bash
uv run pytest pwa/tests/test_recording_routes.py::test_upload_recording_with_audio -v
# Expected: PASS
```

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add upload endpoint with audio file handling"
```

---

## Sprint 2: Service Worker & iOS Fallback (Week 2)

### Task 4: Create Service Worker with iOS Detection

**Files:**
- Create: `pwa/frontend/static/js/service-worker.js`
- Create: `pwa/frontend/static/js/sw-register.js`
- Modify: `pwa/frontend/templates/base.html`

**Step 1: Create Service Worker**

```javascript
// pwa/frontend/static/js/service-worker.js
/**
 * Service Worker for offline capabilities
 * Uses Workbox with iOS fallback
 */

importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js');

// Cache static assets
workbox.routing.registerRoute(
    ({request}) => request.destination === 'image' ||
                   request.destination === 'script' ||
                   request.destination === 'style',
    new workbox.strategies.StaleWhileRevalidate({
        cacheName: 'static-assets'
    })
);

// Cache the app shell
workbox.routing.registerRoute(
    '/',
    new workbox.strategies.NetworkFirst({
        cacheName: 'app-shell'
    })
);

// Background sync for uploads (Chrome/Android only)
if ('sync' in self.registration) {
    workbox.routing.registerRoute(
        '/api/v1/recordings/upload',
        new workbox.backgroundSync.BackgroundSyncPlugin('upload-queue', {
            maxRetentionTime: 24 * 60 // 24 hours
        }),
        'POST'
    );
}

// Listen for sync events
self.addEventListener('sync', (event) => {
    if (event.tag === 'upload-recordings') {
        event.waitUntil(syncPendingUploads());
    }
});

async function syncPendingUploads() {
    // Handled by UploadManager polling
    console.log('Background sync triggered');
}

console.log('Service Worker registered');
```

**Step 2: Create SW registration with iOS detection**

```javascript
// pwa/frontend/static/js/sw-register.js
/**
 * Service Worker registration with iOS detection
 */

const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

window.SyncCapabilities = {
    backgroundSync: false,
    isIOS: isIOS,
    isSafari: isSafari,
    serviceWorker: false
};

if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');
            console.log('SW registered:', registration.scope);
            window.SyncCapabilities.serviceWorker = true;

            // Check for background sync support
            if ('sync' in registration) {
                window.SyncCapabilities.backgroundSync = true;
                console.log('Background sync supported');
            } else {
                console.log('Background sync NOT supported (iOS/Safari)');
                setupPollingFallback();
            }

            // Listen for online/offline
            window.addEventListener('online', () => {
                console.log('Online - requesting sync');
                if (window.SyncCapabilities.backgroundSync) {
                    registration.sync.register('upload-recordings');
                }
                if (window.UploadManager) {
                    window.UploadManager.syncAll();
                }
            });

        } catch (error) {
            console.log('SW registration failed:', error);
            setupPollingFallback();
        }
    });
} else {
    console.log('Service Worker not supported');
    setupPollingFallback();
}

function setupPollingFallback() {
    console.log('Using polling fallback for sync detection');

    // Poll every 30 seconds when online
    setInterval(() => {
        if (navigator.onLine && window.UploadManager) {
            window.UploadManager.syncAll();
        }
    }, 30000);
}
```

**Step 3: Add SW registration to base template**

```html
<!-- Add to base.html before </body> -->
<script src="/static/js/sw-register.js"></script>
```

**Step 4: Commit**

```bash
git add pwa/
git commit -m "feat: add Service Worker with Workbox and iOS detection"
```

---

### Task 5: Create Upload Manager with Retry Logic

**Files:**
- Create: `pwa/frontend/static/js/upload-manager.js`

**Step 1: Create upload manager**

```javascript
// pwa/frontend/static/js/upload-manager.js
/**
 * Upload Manager with retry logic and iOS support
 */

const UploadManager = {
    async uploadRecording(recording) {
        const formData = new FormData();
        formData.append('patient_id', recording.patient_id);
        formData.append('duration_seconds', recording.duration_seconds);
        formData.append('draft_transcript', recording.draft_transcript || '');
        formData.append('audio', recording.audio_blob, 'recording.wav');

        try {
            await RecordingStore.updateStatus(recording.id, 'uploading');

            const response = await fetch('/api/v1/recordings/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                await RecordingStore.markUploaded(recording.id);
                return { success: true };
            } else if (response.status >= 500) {
                throw new Error(`Server error: ${response.status}`);
            } else {
                throw new Error(`Client error: ${response.status}`);
            }
        } catch (error) {
            await RecordingStore.updateStatus(recording.id, 'failed', error.message);
            return { success: false, error: error.message };
        }
    },

    async syncAll() {
        const pending = await RecordingStore.getPendingUploads();

        for (const recording of pending) {
            if (recording.retry_count >= 3) {
                console.log(`Skipping ${recording.id} - max retries`);
                continue;
            }

            // Exponential backoff
            const delay = Math.pow(2, recording.retry_count) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));

            const result = await this.uploadRecording(recording);

            if (!result.success) {
                console.error(`Failed upload ${recording.id}:`, result.error);
            }
        }

        return pending.length;
    },

    isOnline() {
        return navigator.onLine;
    },

    async getStats() {
        const stats = await RecordingStore.getStorageStats();
        return {
            ...stats,
            isOnline: this.isOnline(),
            backgroundSync: window.SyncCapabilities?.backgroundSync || false
        };
    }
};

window.UploadManager = UploadManager;
```

**Step 2: Commit**

```bash
git add pwa/
git commit -m "feat: add UploadManager with retry and iOS support"
```

---

## Sprint 3: Queue UI & iOS Messaging (Week 3)

### Task 6: Create Queue Management Page

**Files:**
- Create: `pwa/frontend/templates/queue.html`
- Create: `pwa/frontend/static/js/queue.js`
- Modify: `pwa/backend/routes/pages.py`

**Step 1: Add queue page route**

```python
# Add to pwa/backend/routes/pages.py
@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    """Queue management page."""
    return templates.TemplateResponse("queue.html", {"request": request})
```

**Step 2: Create queue template with iOS warning**

```html
<!-- pwa/frontend/templates/queue.html -->
{% extends "base.html" %}

{% block content %}
<div class="queue-page">
    <h2>Recording Queue</h2>

    <!-- iOS Warning (shown via JS if iOS detected) -->
    <div id="ios-warning" class="ios-warning hidden">
        <span class="warning-icon">⚠️</span>
        <span>Keep app open to sync recordings (iOS limitation)</span>
    </div>

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

    <!-- Troubleshooting Panel -->
    <div id="troubleshoot-panel" class="troubleshoot-panel hidden">
        <h3>Recording Details</h3>
        <div id="troubleshoot-content"></div>
    </div>
</div>

<script src="/static/js/queue.js"></script>
{% endblock %}
```

**Step 3: Create queue.js with iOS detection**

```javascript
// pwa/frontend/static/js/queue.js
/**
 * Queue Management UI with iOS support
 */

async function updateQueue() {
    const recordings = await RecordingStore.getAllRecordings();
    const stats = await UploadManager.getStats();

    // Show iOS warning
    if (window.SyncCapabilities?.isIOS) {
        document.getElementById('ios-warning').classList.remove('hidden');
    }

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
        statusText.textContent = window.SyncCapabilities?.isIOS
            ? 'Online (foreground sync only)'
            : 'Online';
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
            <dt>Patient</dt><dd>${recording.patient_id}</dd>
            <dt>Duration</dt><dd>${formatDuration(recording.duration_seconds)}</dd>
            <dt>Status</dt><dd>${recording.sync_status}</dd>
            <dt>Attempts</dt><dd>${recording.retry_count}</dd>
            ${recording.last_error ? `<dt>Error</dt><dd>${recording.last_error}</dd>` : ''}
        </dl>
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
    if (recording?.audio_blob) {
        const confirmed = confirm(
            'This audio file contains patient information. Store securely.'
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
    if (confirm('Delete this recording?')) {
        await RecordingStore.deleteRecording(id);
        document.getElementById('troubleshoot-panel').classList.add('hidden');
        updateQueue();
    }
}

// Poll for updates (critical for iOS)
setInterval(updateQueue, 5000);
document.addEventListener('DOMContentLoaded', updateQueue);
```

**Step 4: Add CSS for iOS warning**

```css
/* Add to pwa/frontend/static/css/style.css */

.ios-warning {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 0.75rem 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
}

.ios-warning .warning-icon {
    font-size: 1.2rem;
}

/* Add other queue styles from previous plan */
```

**Step 5: Commit**

```bash
git add pwa/
git commit -m "feat: add queue management UI with iOS warnings"
```

---

## Sprint 4: Testing & Polish (Week 3-4)

### Task 7: Update Recorder.js for IndexedDB

**Files:**
- Modify: `pwa/frontend/static/js/recorder.js`

**Key changes:**
- Store audio in IndexedDB immediately
- Upload if online, queue if offline
- Handle draft transcription (online only)

See implementation in original plan for full code.

**Step 1: Commit**

```bash
git add pwa/
git commit -m "feat: integrate recorder with IndexedDB and upload manager"
```

---

### Task 8: Add Playwright Tests

**Files:**
- Create: `pwa/tests/e2e/test_offline.py`
- Modify: `pyproject.toml`

**Step 1: Install Playwright**

```bash
uv add --dev playwright
uv run playwright install chromium
```

**Step 2: Create E2E test**

```python
# pwa/tests/e2e/test_offline.py
from playwright.sync_api import Page, expect

def test_queue_page_loads(page: Page):
    """Test that queue page loads."""
    page.goto("http://localhost:8002/queue")
    expect(page.locator("h2")).to_contain_text("Recording Queue")

def test_connection_status_shown(page: Page):
    """Test connection status indicator."""
    page.goto("http://localhost:8002/queue")
    expect(page.locator("#connection-status")).to_be_visible()
```

**Step 3: Commit**

```bash
git add pwa/ pyproject.toml
git commit -m "test: add Playwright E2E tests"
```

---

### Task 9: Final Integration & Testing

**Files:**
- All modified files

**Step 1: Run all tests**

```bash
uv run pytest pwa/tests/ -v
```

**Step 2: Manual testing checklist**

- [ ] Record audio offline (airplane mode)
- [ ] Verify stored in IndexedDB
- [ ] Go online, verify auto-upload
- [ ] Test iOS warning shows on Safari
- [ ] Test retry after failure
- [ ] Test export functionality
- [ ] Test queue UI updates

**Step 3: Commit**

```bash
git add pwa/
git commit -m "feat: Phase 2a complete - offline recording with iOS support"
```

---

## Handoff Notes for Next Agent

### What's Implemented (Phase 2a):
1. ✅ IndexedDB storage with localForage
2. ✅ Service Worker with Workbox
3. ✅ iOS/Safari fallback (HTMX polling)
4. ✅ Upload Manager with retry logic
5. ✅ Queue management UI with iOS warnings
6. ✅ Export functionality
7. ✅ Playwright tests

### What's NOT Implemented (Phase 2b):
- Whisper transcription (mocked only)
- LLM extraction (not started)
- PostgreSQL persistence (in-memory only)
- Real authentication

### Critical Files:
- `pwa/frontend/static/js/indexeddb-service.js` - IndexedDB layer
- `pwa/frontend/static/js/upload-manager.js` - Upload logic
- `pwa/frontend/static/js/sw-register.js` - iOS detection
- `pwa/frontend/templates/queue.html` - Queue UI

### Testing:
```bash
uv run pytest pwa/tests/ -v
uv run python pwa/backend/main.py
# Open http://localhost:8002/
```

### Known Issues:
- iOS requires foreground sync (keep app open)
- Draft transcription only works when online
- Storage quotas may limit recordings on mobile

### Next Phase (Phase 2b):
1. Set up Whisper Docker container
2. Add transcription endpoint
3. Pick ONE LLM model (Llama 3.1 8B or 70B)
4. Add extraction/verification pipeline

---

**Plan Complete** - Ready for another agent to implement.
