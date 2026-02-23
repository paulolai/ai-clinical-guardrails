# Phase 2a Handoff Document

**Status:** Ready for Implementation
**Previous Agent:** Completed design phase
**Next Agent:** Implementation
**Date:** 2026-02-23

---

## What You're Building

**Phase 2a: Offline Recording PWA** (NOT the AI part yet)

A Progressive Web App that lets clinicians:
1. Record audio WITHOUT internet
2. Store it locally in the browser (IndexedDB)
3. Auto-upload when they get connectivity back
4. View a queue of pending/completed recordings

**Out of Scope for Phase 2a:**
- Whisper transcription (mock only)
- LLM extraction (not started)
- PostgreSQL persistence (SQLite persistence is now available from Phase 1.5)

---

## Critical Technical Constraints

### 1. Draft Transcription = ONLINE ONLY

**The Web Speech API requires internet.** It streams audio to Google/Apple servers.

**What this means:**
- When online: Show draft transcription (catches mic issues)
- When offline: DON'T try to transcribe - just show "Recording saved locally"

**Don't waste time trying to make it work offline.** It won't.

### 2. iOS/Safari Has NO Background Sync

Safari (iOS) doesn't support the Background Sync API.

**What this means:**
- Chrome/Android: Background sync works automatically
- iOS/Safari: User must keep the app/tab OPEN for sync to happen

**Implementation:**
- Use HTMX polling as fallback (check every 30 seconds)
- Show clear warning: "Keep app open to sync (iOS limitation)"
- Don't promise background sync on iOS

### 3. Timeline Reality Check

Original estimate: "Week 1"
**Realistic estimate: 3-4 weeks**

Why? Offline PWA state management is hard. Browser quirks, storage quotas, iOS limitations.

---

## Your Implementation Guide

### The Plan

**Location:** `docs/plans/2026-02-23-phase2a-offline-recording-implementation.md`

This file has:
- 9 detailed tasks
- Complete code for each step
- Testing instructions
- Known issues

### Task Breakdown

| Task | What | Time Est |
|------|------|----------|
| 1 | Install localForage + IndexedDB service | 1-2 hrs |
| 2 | Update Recording model | 2-3 hrs |
| 3 | Create upload endpoint | 3-4 hrs |
| 4 | Service Worker + iOS detection | 4-6 hrs |
| 5 | Upload Manager with retry | 3-4 hrs |
| 6 | Queue UI with iOS warnings | 4-6 hrs |
| 7 | Update recorder.js | 3-4 hrs |
| 8 | Playwright tests | 2-3 hrs |
| 9 | Integration testing | 4-6 hrs |

**Total: ~25-38 hours (3-4 weeks at 50% capacity)**

---

## Where to Start

### Prerequisites

```bash
# Verify Phase 1 works (27 tests passing)
uv run pytest pwa/tests/ -v

# Run server
uv run python pwa/backend/main.py
# Open http://localhost:8002/
```

### Step-by-Step

1. **Read the full plan:** `docs/plans/2026-02-23-phase2a-offline-recording-implementation.md`

2. **Start with Task 1** (IndexedDB) - it's the foundation

3. **Use `executing-plans` skill** - invoke it to implement task-by-task

4. **Test constantly** - run `uv run pytest pwa/tests/ -v` after each commit

---

## Key Files You'll Create/Modify

### New Files:
- `pwa/frontend/static/js/indexeddb-service.js` - IndexedDB wrapper
- `pwa/frontend/static/js/service-worker.js` - Service Worker
- `pwa/frontend/static/js/sw-register.js` - SW registration + iOS detection
- `pwa/frontend/static/js/upload-manager.js` - Upload logic
- `pwa/frontend/static/js/queue.js` - Queue UI
- `pwa/frontend/templates/queue.html` - Queue page
- `pwa/tests/e2e/test_offline.py` - Playwright tests

### Modified Files:
- `pwa/backend/models/recording.py` - Add new fields
- `pwa/backend/routes/recordings.py` - Add upload endpoint
- `pwa/backend/routes/pages.py` - Add queue route
- `pwa/frontend/static/js/recorder.js` - Integrate IndexedDB
- `pwa/frontend/templates/base.html` - Add SW registration
- `pwa/frontend/static/css/style.css` - Queue styles

---

## Testing Strategy

### Automated Tests

```bash
# Unit tests
uv run pytest pwa/tests/ -v

# E2E tests (after Task 8)
uv run pytest pwa/tests/e2e/ -v
```

### Manual Testing Checklist

- [ ] Record audio offline (airplane mode)
- [ ] Verify stored in IndexedDB (check browser DevTools > Application > IndexedDB)
- [ ] Go online, verify auto-upload starts
- [ ] Test on iOS Safari - confirm "Keep app open" warning appears
- [ ] Test on Chrome Android - confirm background sync works
- [ ] Test retry after upload failure
- [ ] Test export functionality
- [ ] Verify queue UI updates in real-time

---

## Common Pitfalls

### 1. Don't Forget iOS

**Mistake:** Only test on Chrome desktop
**Fix:** Test on iOS Simulator or real iPhone

### 2. Storage Quotas

**Mistake:** Store unlimited recordings
**Fix:** Implement quota checking and old recording cleanup

### 3. Draft Transcription Confusion

**Mistake:** Expect Web Speech API to work offline
**Fix:** Only enable when `navigator.onLine === true`

### 4. Async/Await Hell

**Mistake:** Mix promises and async/await inconsistently
**Fix:** Use async/await consistently throughout

---

## Success Criteria

At the end of Phase 2a, you should be able to:

- Record audio without internet
- Audio persists across browser restarts
- Auto-sync when online (Chrome/Android)
- Foreground sync on iOS (with clear messaging)
- Queue shows upload status
- Retry logic handles failures
- Export audio for clinical safety
- All tests passing

---

## Questions?

### Design Questions
See: `docs/plans/2026-02-23-phase2-offline-recording-design.md` (Revision 1.1)

### Implementation Questions
See: `docs/plans/2026-02-23-phase2a-offline-recording-implementation.md`

### Phase 1 Context
See: `docs/plans/2026-02-23-pwa-phase1-implementation-summary.md`

---

## Next Phase (Phase 2b)

After Phase 2a is complete:

1. Set up Whisper Docker container
2. Add transcription endpoint
3. Pick ONE LLM model (Llama 3.1 8B or 70B)
4. Add extraction/verification pipeline
5. Replace mock transcription with real Whisper

**Note:** Skip the evaluation suite. Pick one model and move on.

---

**Good luck! The plan is solid, just take it one task at a time.**
