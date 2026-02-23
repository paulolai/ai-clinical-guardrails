# Phase 2b Kickoff Summary

**Date:** 2026-02-23
**Status:** Ready to implement
**Estimated Duration:** 3-4 weeks at 50% capacity (25-36 hours)

---

## What Was Just Created

### 1. Handoff Document
**File:** `docs/plans/2026-02-23-phase2b-ai-transcription-handoff.md`

**Purpose:** High-level overview for the next developer
- What we're building (Whisper + LLM + Verification)
- Critical technical decisions (Docker-first, async processing)
- Architecture overview with data flow diagram
- Success criteria and common pitfalls
- Resources and links

### 2. Implementation Plan
**File:** `docs/plans/2026-02-23-phase2b-ai-transcription-implementation.md`

**Purpose:** Detailed task-by-task guide
- 8 tasks with complete code
- TDD approach (failing test → implementation)
- Exact file paths and commands
- Testing instructions per task

---

## The 8 Tasks

| # | Task | Files Created/Modified | Time Est |
|---|------|------------------------|----------|
| 1 | Whisper Docker Container | `docker/whisper/*`, `transcription_service.py` | 3-4 hrs |
| 2 | Transcription Job | `transcription_job.py`, update routes/models | 4-6 hrs |
| 3 | LLM Docker Container | `docker/llm/*`, `extraction_service.py` | 2-3 hrs |
| 4 | Extraction Pipeline | `extraction_job.py` | 3-4 hrs |
| 5 | Verification Engine | `verification_service.py` | 4-6 hrs |
| 6 | Recording Model Updates | SQL columns, Alembic migration | 2-3 hrs |
| 7 | Queue UI Integration | Update queue.js, CSS | 3-4 hrs |
| 8 | Integration Testing | E2E tests, manual validation | 4-6 hrs |

**Total:** ~25-36 hours

---

## Key Decisions Documented

### 1. Pick ONE LLM (8B recommended)
- Don't evaluate multiple models
- 8B = fast, fits on 16GB GPU
- 70B = better accuracy, needs 40GB GPU

### 2. Docker-First Architecture
```
FastAPI (host) → Whisper (docker) → LLM (docker)
```
- Isolates AI dependencies
- Easy to swap models
- Can run on separate machines

### 3. Async Processing Required
**Don't block HTTP requests!**
- Upload endpoint returns immediately
- Background job does transcription
- Client polls for status updates
- 10-30 seconds for 2-minute audio

### 4. Clinical Safety First
Verification checks before showing data:
- Known medication names
- Valid dosage formats
- Confidence threshold > 0.7
- Unknown drugs flagged for review

---

## New Components

### Docker Services
```yaml
docker-compose up
├── whisper (port 8001)    # Audio → Text
└── llm (port 8003)        # Text → FHIR
```

### Backend Services
```
pwa/backend/services/
├── transcription_service.py   # Whisper wrapper
├── extraction_service.py      # LLM wrapper
└── verification_service.py    # Safety checks
```

### Background Jobs
```
pwa/backend/jobs/
├── transcription_job.py   # Triggered on upload
└── extraction_job.py      # Triggered after transcription
```

### Database Schema Additions
```python
# Transcription
final_transcript: str
whisper_model: str = "base"
transcription_started_at: datetime
transcription_completed_at: datetime

# Extraction
fhir_bundle: dict
llm_model: str
extraction_started_at: datetime
extraction_completed_at: datetime

# Verification
verification_results: dict
verification_score: float
verified_at: datetime
```

---

## Data Flow

```
1. Audio Upload (Phase 2a)
   ↓
2. Upload Endpoint Triggers Job
   ↓
3. Transcription Job
   ├── Update status → "processing"
   ├── Call Whisper container
   └── Save transcript
   ↓
4. Extraction Job (auto-triggered)
   ├── Call LLM container
   └── Extract medications/conditions/allergies
   ↓
5. Verification
   ├── Check confidence > 0.7
   ├── Validate medication names
   └── Check dosage formats
   ↓
6. Store Results
   ├── status = "completed" (if passed)
   └── status = "error" (if failed)
   ↓
7. Client Polling
   ├── Queue UI polls every 10s
   └── Shows transcript when ready
```

---

## Review Feedback Incorporated

**Status:** ✅ Approved with architectural improvements

### Changes Made Based on Review:

**1. Docker Model Management (Task 1 & 3)**
- **Before:** Baked 10GB+ models into Docker images
- **After:** Runtime download via volume mount
- **Benefit:** ~500MB images (vs 15GB), model persists across rebuilds
- **Implementation:** Models download to `/root/.cache/*` via volume mounts

**2. Zombie Job Recovery (Task 2)**
- **Before:** FastAPI BackgroundTasks die on container restart
- **After:** Documented recovery pattern + startup check
- **Implementation:** `recover_zombie_jobs()` startup event
- **Note:** Mark jobs stuck >30 min as ERROR on startup

**3. Verification Extensibility (Task 5)**
- **Before:** Hardcoded medication/condition lists
- **After:** Class design supports external data sources
- **Future:** Easy swap for RxNorm, database, or file-based lists
- **Implementation:** Constructor accepts custom sources

---

## Success Criteria

**By end of Phase 2b:**
- [ ] Upload audio → automatic transcription (10-30s)
- [ ] LLM extracts structured FHIR data
- [ ] Verification checks pass/fail with score
- [ ] Queue UI shows transcription progress
- [ ] Failed verifications flagged for review
- [ ] All tests passing
- [ ] Docker containers running smoothly

---

## Ready to Start?

### Prerequisites Check:
```bash
# Phase 2a working?
uv run pytest pwa/tests/test_upload_endpoint.py -v

# Docker installed?
docker --version

# GPU available? (optional but recommended)
nvidia-smi
```

### Next Steps:
1. Read handoff: `docs/plans/2026-02-23-phase2b-ai-transcription-handoff.md`
2. Read implementation plan: `docs/plans/2026-02-23-phase2b-ai-transcription-implementation.md`
3. Start Task 1: Whisper Docker Container
4. Use `executing-plans` skill for task-by-task implementation

---

## Files Created

```
docs/plans/
├── 2026-02-23-phase2b-ai-transcription-handoff.md         (this summary)
├── 2026-02-23-phase2b-ai-transcription-implementation.md  (detailed tasks)
└── 2026-02-23-phase2b-kickoff-summary.md                  (overview)
```

**Total: 3 new documents, ~500 lines of planning**

---

*Phase 2b is ready to build. Start with Task 1: Whisper Docker Container.*
