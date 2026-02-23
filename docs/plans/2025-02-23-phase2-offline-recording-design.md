# Phase 2: Offline Recording Design

**Date:** 2025-02-23
**Status:** ✅ Approved
**Depends on:** Phase 1 Complete

---

## 1. Overview & Goals

**Scope**: Enable offline audio recording with automatic sync when connectivity returns. Server handles all transcription and LLM processing.

**Key Behaviors**:
- Clinician records → Audio stored in IndexedDB immediately
- Web Speech API provides draft transcription for immediate feedback
- If online: Auto-upload starts with progress indicator
- If offline: Recording queued with subtle "pending upload" badge
- When connectivity returns: Background sync triggers automatically
- Server: Whisper transcribes → LLM extracts/verifies → Results returned

**Success Criteria**:
- [ ] Record audio without internet
- [ ] Audio persists across browser sessions
- [ ] Auto-sync when online (no user action)
- [ ] Queue shows upload/processing status
- [ ] Retry logic for failed uploads
- [ ] Draft transcription for immediate feedback
- [ ] Export audio for clinical safety

---

## 2. Architecture & Data Flow

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                           BROWSER                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   recorder.js│───▶│  IndexedDB   │    │ Service      │       │
│  │   (existing) │    │   (audio)    │    │   Worker     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                    │                │
│         │                   │                    │                │
│         ▼                   ▼                    ▼                │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                    Queue Manager (new)                  │     │
│  │         - Track upload status                          │     │
│  │         - Trigger background sync                      │     │
│  │         - Retry failed uploads                         │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────┬─────────────────────────────────────┘
                              │ (when online)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           SERVER                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  FastAPI     │───▶│ PostgreSQL   │    │   Whisper    │     │
│  │  (existing)  │    │   (metadata) │    │  (Docker)    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                                         │            │
│         │                                         ▼            │
│         │                              ┌──────────────┐       │
│         └─────────────────────────────▶│     LLM      │       │
│                                        │  (Docker)    │       │
│                                        └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **RECORD**: User clicks "Record" → MediaRecorder captures audio + Web Speech API transcribes → Store in IndexedDB
2. **SYNC CHECK**: Service Worker detects connectivity → Queue upload tasks
3. **UPLOAD**: Read from IndexedDB → POST to server → Mark as uploaded → Clear local storage
4. **PROCESS** (Server): Whisper transcribes → LLM extracts/verifies → Store results
5. **POLL FOR RESULTS**: HTMX polls for status → Show final transcript

---

## 3. Data Model Updates

### Recording Model (server-side additions)

```python
class Recording(BaseModel):
    # ... existing fields ...

    # NEW: Transcription
    draft_transcript: Optional[str] = None      # Browser Speech API result
    final_transcript: Optional[str] = None      # Whisper result

    # NEW: Upload tracking
    local_storage_key: Optional[str] = None     # IndexedDB key
    upload_attempts: int = 0                     # Retry counter
```

### IndexedDB Schema (client-side)

```javascript
// Object Store: "recordings"
{
    id: "uuid-generated-client-side",
    patient_id: "patient-123",
    clinician_id: "clinician-456",
    audio_blob: Blob,              // The actual audio
    draft_transcript: "...",       // Browser transcription
    duration_seconds: 120,
    created_at: "2025-02-23T10:30:00Z",
    sync_status: "pending_upload", // pending_upload | uploading | uploaded | failed
    retry_count: 0
}
```

---

## 4. Service Worker Strategy

**Why Service Worker**: Intercepts network requests, queues when offline, background sync when online.

**Responsibilities**:
1. Cache static assets for offline viewing
2. Intercept upload requests → Queue in IndexedDB if offline
3. Trigger background sync when connectivity returns
4. Optional: Notify when processing complete

**Implementation**: Workbox library for reliability, fallback to HTMX polling for unsupported browsers.

---

## 5. UI/UX Flow

### Subtle Design Philosophy

**Recording**:
- Red circular button (single tap start/stop)
- Light gray draft transcription below (1-2 lines)
- Toast: "Recording saved"

**Queue** (Collapsible, default hidden):
| Patient | Duration | Status |
|---------|----------|--------|
| Patient-123 | 2m 15s | ⏳ Pending |
| Patient-456 | 0m 45s | ✓ Ready |

**Status Icons**:
- ⏳ Pending (yellow dot)
- 🔄 Uploading (animated spinner)
- 🔵 Processing (blue dot)
- ✓ Ready (green dot)
- ⚠️ Failed (red dot + retry)

**Troubleshooting** (On-Demand):
- Click recording → slide-out panel
- Full draft transcript
- Upload attempts: "2/3"
- Last error message
- Retry / Export buttons

**Connection Indicator**:
- Small header dot: Green (online) / Yellow (syncing) / Red (offline)

---

## 6. Draft Transcription

**Purpose**: Immediate feedback to catch mic/audio issues

**Implementation**:
- Web Speech API (built-in browser capability)
- Display as light gray "Draft..." text
- Read-only, not editable
- Replaced by Whisper transcript when ready
- Clear visual distinction between draft and final

**Why not editable**: Avoids confusion when final (accurate) Whisper transcript arrives.

---

## 7. Error Handling

| Error | Handling |
|-------|----------|
| IndexedDB quota exceeded | Alert user, offer to delete old recordings |
| Upload network timeout | Retry with exponential backoff (1s, 2s, 4s) |
| Server 5xx | Retry 3x, then mark "server error" |
| Server 4xx | Don't retry, mark "needs attention" |
| Auth failure | Preserve queue, redirect to login |
| SW registration failed | Fallback to HTMX polling |

---

## 8. Export Capability

**Why**: Clinical safety, data portability, compliance

**Safeguards**:
- Confirmation: "This contains patient data. Store securely."
- Audit log: Track all exports
- Audio only: No patient metadata in export
- Format: WAV (original quality)

**Location**: Export button in troubleshooting slide-out panel

---

## 9. Testing Strategy

**Unit Tests** (pytest):
- Model validation, upload endpoint, retry logic

**Integration Tests** (Playwright):
- IndexedDB read/write/verify
- Service Worker registration
- Upload flow: offline → online → sync
- Draft transcription: verify appears, mute → warning

**E2E Tests** (Playwright):
- Full journey: Record → Stop → Upload → Results
- Offline journey: Record offline → Online → Sync complete

**Tools**: Playwright, pytest-xdist, coverage

---

## 10. Technical Stack

| Component | Technology |
|-----------|-----------|
| Offline Storage | IndexedDB (localForage library) |
| Service Worker | Workbox |
| Draft Transcription | Web Speech API |
| Testing | Playwright + pytest |
| Sync Detection | Network Information API + polling fallback |

---

## 11. Out of Scope (Phase 3)

- Client-side Whisper (WebAssembly)
- Offline LLM processing
- Real-time sync across devices
- End-to-end encryption of local storage

---

**Design approved for implementation.**
