# Phase 2: Offline Recording Design

**Date:** 2026-02-23
**Status:** ✅ Approved
**Revision:** 1.1 (Critical feedback incorporated)

---

## 1. Overview & Goals

**⚠️ REVISED SCOPE - Phase 2a (PWA Only)**

Phase 2 has been split into two parts to manage complexity:
- **Phase 2a (This Sprint)**: Offline recording and sync ONLY. AI backend is mocked.
- **Phase 2b (Next Sprint)**: Add Whisper + LLM integration.

**Why split?** Offline PWA state management and AI R&D are two massive unrelated engineering hurdles. Attempting both simultaneously risks ending with a buggy PWA and a half-baked AI pipeline.

**Scope for Phase 2a**: Enable offline audio recording with automatic sync when connectivity returns. Server provides mock transcription for now.

**Key Behaviors**:
- Clinician records → Audio stored in IndexedDB immediately
- If online: Auto-upload starts with progress indicator
- If offline: Recording queued with subtle "pending upload" badge
- When connectivity returns: **Foreground sync required** (background sync unavailable on iOS Safari)
- Server: Mock transcription response (Phase 2b adds real Whisper)

**Success Criteria**:
- [ ] Record audio without internet
- [ ] Audio persists across browser sessions
- [ ] Foreground sync when online (user must keep app open)
- [ ] Queue shows upload/processing status
- [ ] Retry logic for failed uploads
- [ ] iOS/Safari compatibility with clear sync instructions
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

1. **RECORD**: User clicks "Record" → MediaRecorder captures audio → Store in IndexedDB
2. **SYNC CHECK**: Service Worker detects connectivity → Queue upload tasks (background sync where supported)
3. **UPLOAD**: Read from IndexedDB → POST to server → Mark as uploaded → Clear local storage
4. **PROCESS** (Server): Mock transcription (Phase 2b adds Whisper) → Store results
5. **POLL FOR RESULTS**: HTMX polls for status → Show transcript

**iOS/Safari Note**: Background Sync API not supported. Sync requires:
- User keeps app/tab open
- HTMX polling detects connectivity
- Visual indicator: "Keep app open to sync"

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
    created_at: "2026-02-23T10:30:00Z",
    sync_status: "pending_upload", // pending_upload | uploading | uploaded | failed
    retry_count: 0
}
```

---

## 4. Service Worker Strategy

**⚠️ iOS LIMITATION**: Safari (iOS) does not support the Background Sync API. A significant portion of mobile clinicians use iPhones/iPads.

**Why Service Worker**: Intercepts network requests, queues when offline, enables background sync where supported.

**Responsibilities**:
1. Cache static assets for offline viewing
2. Intercept upload requests → Queue in IndexedDB if offline
3. Trigger background sync when connectivity returns (Chrome/Android only)
4. Fallback to HTMX polling for iOS/Safari

**iOS Sync Strategy**:
- Background sync unavailable on Safari
- **Foreground sync required**: User must keep app open
- HTMX polling every 30 seconds when online
- Visual warning: "⚠️ Keep app open to sync (iOS limitation)"
- Poll while tab is active, pause when backgrounded

**Implementation**: Workbox library for Chrome/Android, HTMX polling fallback for iOS/Safari.

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

## 6. Draft Transcription (ONLINE ONLY ⚠️)

**⚠️ CRITICAL**: Web Speech API requires internet connection on most browsers (streams audio to Google/Apple servers). It will NOT work offline.

**Purpose**: Immediate feedback to catch mic/audio issues **when online**

**Implementation**:
- Web Speech API (streams to cloud)
- Display as light gray "Draft..." text **only when online**
- **When offline**: No draft transcription, show "Recording saved locally" only
- Read-only, not editable
- Replaced by Whisper transcript when ready

**Why ONLINE ONLY**:
- Web Speech API requires active internet on Chrome, Safari Desktop, Firefox
- Only Pixel phones with on-device dictation work offline
- Client-side WASM model is Phase 3 scope

**UI Behavior**:
```
Online:  Recording... + "Draft: [live transcription]"
Offline: Recording... + "Recording saved locally"
```

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

| Component | Technology | Notes |
|-----------|-----------|-------|
| Offline Storage | IndexedDB (localForage) | Client-side audio persistence |
| Service Worker | Workbox | Chrome/Android background sync |
| Sync Fallback | HTMX polling | iOS/Safari foreground sync |
| Draft Transcription | Web Speech API | ONLINE ONLY - catches mic issues |
| Testing | Playwright + pytest | Automated E2E |
| Sync Detection | Network Information API + polling | iOS requires polling |
| Audio Format | WAV | Phase 3: Opus/FLAC compression |

---

## 11. Out of Scope (Phase 3)

### Phase 2a (Current) - PWA Only
- AI/Transcription is **mocked** - server returns dummy transcripts
- Focus: Reliable offline recording and sync

### Phase 2b (Next Sprint) - AI Integration
- Whisper container for transcription
- **Simplified LLM**: Pick ONE model (Llama 3.1 8B or 70B)
- **NO evaluation suite** - pick based on community benchmarks, test locally
- LLM extraction and verification

### Phase 3 (Future)
- Client-side Whisper (WebAssembly)
- Offline LLM processing
- Audio compression (Opus/FLAC) for bandwidth
- Real-time sync across devices
- End-to-end encryption of local storage

---

## 12. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial design |
| 1.1 | 2026-02-23 | Critical feedback incorporated: Split Phase 2, mark draft transcription ONLINE ONLY, add iOS foreground sync requirements, simplify LLM approach |

---

**Design approved for implementation.**
