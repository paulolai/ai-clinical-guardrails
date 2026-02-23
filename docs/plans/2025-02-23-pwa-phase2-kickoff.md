# Clinical Transcription PWA - Phase 2 Kickoff

**Date:** 2025-02-23
**Status:** 🚀 Ready to Start
**Depends on:** Phase 1 Complete ✅
**Branch:** `main` (stable) → `phase-2-offline-capabilities` (new)

---

## Mission

Transform the Phase 1 foundation into an **offline-capable clinical transcription system** with local AI processing.

**Goal:** Clinicians can record dictations without internet, sync when connected, and get AI transcription + verification.

---

## What Phase 1 Gave Us

✅ FastAPI backend with recording API
✅ HTMX frontend with audio capture
✅ Recording model with status tracking
✅ Basic web interface

**What's Missing (Phase 2 Goals):**
⏳ Offline recording (Service Worker + IndexedDB)
⏳ Local AI transcription (Whisper)
⏳ LLM extraction and verification
⏳ Queue management UI

---

## Phase 2 Scope

### Must Have (MVP)

1. **Offline Capabilities**
   - Service Worker for PWA
   - IndexedDB for audio storage
   - Background sync when online
   - Queue management interface

2. **AI Integration**
   - Whisper container (local transcription)
   - LLM container with evaluation suite
   - Transcription pipeline
   - Integration with existing guardrails

3. **Data Persistence**
   - PostgreSQL database
   - Migration from in-memory storage
   - Audio file storage

### Should Have

4. **Enhanced UX**
   - Recording queue visualization
   - Progress indicators
   - Error recovery flows

### Won't Have (Phase 3)

- Keycloak authentication
- Docker Compose orchestration
- Production monitoring
- My Health Record integration

---

## Architecture Decisions

### LLM Selection Strategy

**User Requirement:** Don't lock in a model. Build evaluation suite first.

**Approach:**
1. Define evaluation criteria (speed, accuracy, clinical extraction quality)
2. Test 3-5 local models (Llama 3.1 70B, Qwen2.5 72B, Mixtral 8x7B, etc.)
3. Score each model against test dataset
4. Select best model based on metrics
5. Implement with model swap capability

**Evaluation Suite:**
- Test dataset: 100 synthetic clinical transcripts
- Metrics: WER (Word Error Rate), extraction accuracy, latency, RAM usage
- Judge: LLM-as-judge for extraction quality

### Offline-First Design

**Pattern:** Background sync with queue

```
Record Audio → Store in IndexedDB → Show in Queue
                                    ↓ (when online)
                              Upload to Server
                                    ↓
                              Whisper Transcribe
                                    ↓
                              LLM Extract/Verify
                                    ↓
                              Show Results
```

**Conflict Resolution:** Server wins (last-write-wins)

---

## Implementation Plan

### Sprint 1: Offline Foundation
**Week 1:**
- [ ] Service Worker registration
- [ ] IndexedDB schema for recordings
- [ ] Background sync implementation
- [ ] Offline queue UI

**Week 2:**
- [ ] Queue management page
- [ ] Retry logic for failed uploads
- [ ] Connection status indicator
- [ ] Test offline scenarios

### Sprint 2: AI Infrastructure
**Week 3:**
- [ ] Whisper container setup
- [ ] Audio transcription endpoint
- [ ] Basic transcription flow

**Week 4:**
- [ ] LLM evaluation suite design
- [ ] Test 3-5 models
- [ ] Score and select best model

### Sprint 3: Integration
**Week 5:**
- [ ] LLM extraction pipeline
- [ ] Verification integration
- [ ] PostgreSQL persistence

**Week 6:**
- [ ] End-to-end workflow
- [ ] Polish and bug fixes
- [ ] Documentation

---

## Technical Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Frontend | HTMX + vanilla JS | Service Worker for offline |
| Storage | IndexedDB | localForage library |
| Audio | MediaRecorder API | WAV format |
| Transcription | Whisper (local) | Docker container |
| LLM | TBD (evaluated) | vLLM or llama.cpp |
| Database | PostgreSQL | SQLAlchemy async |
| Queue | Background Sync API | HTMX polling fallback |

---

## Getting Started

### 1. Create Branch

```bash
git checkout main
git pull
git checkout -b phase-2-offline-capabilities
```

### 2. Verify Phase 1

```bash
# Run tests
uv run pytest pwa/tests/ -v

# Run server
uv run python pwa/backend/main.py
# Open http://localhost:8002/ and test recording
```

### 3. Start Implementation

See detailed task breakdown in:
**[2025-02-23-clinical-transcription-pwa-implementation.md](./2025-02-23-clinical-transcription-pwa-implementation.md)**

(Tasks 8+ cover Phase 2)

---

## Success Criteria

- [ ] Record audio offline ✓
- [ ] Audio persists in IndexedDB ✓
- [ ] Auto-sync when online ✓
- [ ] Whisper transcribes locally ✓
- [ ] LLM evaluation suite runs ✓
- [ ] Best model selected and integrated ✓
- [ ] Data persists in PostgreSQL ✓
- [ ] End-to-end workflow complete ✓

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Whisper too slow on Mac Studio | Use faster-whisper, quantize model |
| LLM evaluation takes too long | Start with 50 samples, parallel testing |
| IndexedDB storage limits | Implement compression, purge old recordings |
| Service Worker complexity | Use Workbox library |

---

## Resources

- **Design Doc:** [2025-02-23-clinical-transcription-pwa-design.md](./2025-02-23-clinical-transcription-pwa-design.md)
- **Phase 1 Summary:** [2025-02-23-pwa-phase1-implementation-summary.md](./2025-02-23-pwa-phase1-implementation-summary.md)
- **Implementation Plan:** [2025-02-23-clinical-transcription-pwa-implementation.md](./2025-02-23-clinical-transcription-pwa-implementation.md)

---

**Ready to start?** Create the branch and begin Sprint 1.
