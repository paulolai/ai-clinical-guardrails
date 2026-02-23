# Phase 2b Handoff Document

**Status:** Ready for Implementation
**Previous Phase:** Phase 2a (Offline Recording PWA) - ✅ Complete
**Next Phase:** Phase 3 (Future Enhancements)
**Date:** 2026-02-23

---

## What You're Building

**Phase 2b: AI Transcription & Extraction**

Now that the PWA can record and sync audio, we're adding the AI layer:

1. **Whisper Transcription** - Convert audio to text
2. **LLM Extraction** - Extract structured clinical data
3. **Verification Pipeline** - Check accuracy and flag issues
4. **Integration** - Replace mock transcription with real AI

**What Phase 2a Left You:**
- ✅ Audio uploads working (upload endpoint)
- ✅ Recordings stored in SQLite with metadata
- ✅ Queue UI showing upload status
- ✅ Files available at `/api/v1/recordings/{id}/audio`
- ⚠️ Transcription is MOCK (returns dummy text)

**What You're Adding:**
- Whisper Docker container for transcription
- Transcription service with progress tracking
- LLM container (pick ONE: Llama 3.1 8B or 70B)
- Extraction pipeline (FHIR resources)
- Verification layer (clinical safety checks)

---

## Critical Technical Decisions

### 1. Pick ONE LLM Model

**Don't evaluate multiple models.** Pick one based on community benchmarks and move on.

**Recommendation: Llama 3.1 8B**
- Good balance of speed/accuracy for clinical extraction
- Fits on single GPU (16GB VRAM)
- Fast enough for real-time feedback
- If you have more GPU: use 70B

**Why not evaluate?**
- Clinical extraction is subjective
- No gold standard dataset
- Speed matters more than 2-3% accuracy gain
- Build the pipeline first, optimize later

### 2. Docker-First Architecture

**Both Whisper and LLM run in Docker containers:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FastAPI    │────▶│   Whisper    │────▶│   LLM        │
│   (Host)     │     │   (Docker)   │     │   (Docker)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Why Docker?**
- Isolates heavy AI dependencies
- Easy to scale/replace models
- Consistent environment
- Can run on separate machine if needed

### 3. Async Processing Required

**Transcription is SLOW (10-30 seconds for 2-minute audio)**

**Pattern: Queue → Process → Poll for Results**
1. Recording uploaded → status = "queued"
2. Background job starts Whisper
3. Client polls `/api/v1/recordings/{id}` for status
4. When done: status = "completed", transcript available

**Don't block HTTP requests with transcription.**

### 4. Clinical Safety First

**Verification checks BEFORE showing to clinician:**
- Drug names match known medications
- Dosages in reasonable ranges
- No conflicting contraindications
- Confidence scores above threshold

**If verification fails:**
- Status = "needs_review"
- Show raw transcript
- Flag specific issues
- Let clinician manually enter data

---

## Implementation Review Notes

**Status:** ✅ Approved with architectural improvements

### Changes Made Based on Code Review:

**1. Docker Model Management (Critical)**
- **Issue:** Baking 10GB+ models into Docker images
- **Solution:** Runtime download via volume mounts
- **Benefit:** ~500MB images vs 15GB, models persist across rebuilds
- **Implementation:**
  - Whisper: `/root/.cache/whisper`
  - LLM: `/root/.cache/huggingface`

**2. Zombie Job Recovery**
- **Issue:** FastAPI BackgroundTasks die on container restart
- **Solution:** Startup recovery check for stuck jobs
- **Implementation:** `recover_zombie_jobs()` marks stuck jobs (>30 min) as ERROR
- **Note:** Documented as future enhancement in Task 2

**3. Verification Extensibility**
- **Issue:** Hardcoded medication/condition lists
- **Solution:** Class-based design supports external data sources
- **Future:** Easy swap for RxNorm, database, or file-based lookups
- **Implementation:** Constructor accepts custom sources

---

## Architecture Overview

### Data Flow

```
1. Audio Upload (from Phase 2a)
   ↓
2. Trigger Transcription Job
   ↓
3. Whisper Container → Text
   ↓
4. LLM Container → Structured Data
   ↓
5. Verification Layer → Checks
   ↓
6. Store Results
   ↓
7. HTMX Poll → UI Update
```

### New Components

| Component | Tech | Purpose |
|-----------|------|---------|
| Whisper Service | Docker + Whisper | Audio → Text |
| LLM Service | Docker + Llama 3.1 | Text → FHIR |
| Transcription Job | Celery/Background | Async processing |
| Verification Engine | Python + Rules | Clinical safety |

### Database Changes

Add to `Recording` model:
```python
# Transcription
final_transcript: str | None = None
whisper_model: str = "base"  # Which model was used
transcription_started_at: datetime | None = None
transcription_completed_at: datetime | None = None

# Extraction
fhir_bundle: dict | None = None  # Extracted FHIR resources
llm_model: str | None = None
extraction_started_at: datetime | None = None
extraction_completed_at: datetime | None = None

# Verification
verification_results: dict | None = None  # Pass/fail checks
verification_score: float | None = None  # 0.0 - 1.0
verified_at: datetime | None = None
```

---

## Implementation Guide

### The Plan

**Location:** `docs/plans/2026-02-23-phase2b-ai-transcription-implementation.md`

This file will have:
- 8 detailed tasks
- Complete code for each step
- Docker compose setup
- Testing strategy

### Task Breakdown

| Task | What | Time Est |
|------|------|----------|
| 1 | Whisper Docker container | 3-4 hrs |
| 2 | Transcription endpoint + job | 4-6 hrs |
| 3 | LLM Docker container (pick one) | 2-3 hrs |
| 4 | Extraction service | 3-4 hrs |
| 5 | Verification engine | 4-6 hrs |
| 6 | Update Recording model | 2-3 hrs |
| 7 | Integrate with Queue UI | 3-4 hrs |
| 8 | E2E tests + validation | 4-6 hrs |

**Total: ~25-36 hours (3-4 weeks at 50% capacity)**

---

## Where to Start

### Prerequisites

```bash
# Verify Phase 2a works
uv run pytest pwa/tests/test_upload_endpoint.py -v

# Check Docker is installed
docker --version

# Run server
uv run python pwa/backend/main.py
```

### Step-by-Step

1. **Read the full plan:** `docs/plans/2026-02-23-phase2b-ai-transcription-implementation.md`

2. **Start with Task 1** (Whisper Docker) - it's the foundation

3. **Pick your LLM first** (8B or 70B) - affects Task 3-5

4. **Use `executing-plans` skill** - invoke it to implement task-by-task

5. **Test constantly** - run `uv run pytest pwa/tests/ -v` after each commit

---

## Key Files You'll Create/Modify

### New Files:
- `docker/whisper/Dockerfile` - Whisper container
- `docker/llm/Dockerfile` - LLM container
- `docker/docker-compose.yml` - Orchestration
- `pwa/backend/services/transcription_service.py` - Whisper integration
- `pwa/backend/services/extraction_service.py` - LLM integration
- `pwa/backend/services/verification_service.py` - Clinical checks
- `pwa/backend/jobs/transcription_job.py` - Background processing
- `pwa/tests/e2e/test_transcription.py` - E2E tests

### Modified Files:
- `pwa/backend/models/recording.py` - Add transcription/extraction fields
- `pwa/backend/models/recording_sql.py` - Add SQL columns
- `pwa/backend/routes/recordings.py` - Add status polling
- `pwa/frontend/static/js/queue.js` - Show transcription progress
- `pwa/frontend/templates/queue.html` - Display transcript
- `.env` - API keys and model paths

---

## Testing Strategy

### Unit Tests

```python
# Test transcription service
def test_whisper_transcribes_audio():
    audio_path = "test_data/sample.wav"
    result = transcription_service.transcribe(audio_path)
    assert result.text is not None
    assert result.confidence > 0.5

# Test extraction service
def test_llm_extracts_medication():
    transcript = "Patient takes Metformin 500mg twice daily"
    fhir = extraction_service.extract(transcript)
    assert fhir["resourceType"] == "MedicationStatement"
```

### Integration Tests

```python
# Full pipeline test
def test_end_to_end_transcription():
    # Upload audio
    recording = upload_audio("test.wav")

    # Wait for transcription (poll)
    result = wait_for_transcription(recording.id)

    # Verify
    assert result.final_transcript is not None
    assert result.verification_score > 0.7
```

### Manual Testing

- [ ] Upload audio, verify transcription appears
- [ ] Check Whisper logs for errors
- [ ] Verify LLM extraction produces valid FHIR
- [ ] Test verification flags bad data
- [ ] Check queue UI shows progress
- [ ] Test error handling (corrupt audio, etc.)

---

## Common Pitfalls

### 1. Blocking HTTP Requests

**Mistake:** Calling Whisper in the upload endpoint
**Fix:** Always use background jobs for transcription

### 2. Model Too Big for Hardware

**Mistake:** Using 70B model on 8GB GPU
**Fix:** Check VRAM requirements, start with 8B

### 3. No Progress Updates

**Mistake:** Client waits 30 seconds with no feedback
**Fix:** Update recording.status frequently, client polls

### 4. Ignoring Verification Failures

**Mistake:** Showing unverified data to clinicians
**Fix:** Block on verification_score < 0.7

### 5. No Error Recovery

**Mistake:** If Whisper fails, recording stuck in "processing"
**Fix:** Catch errors, set status = "error", allow retry

---

## Success Criteria

At the end of Phase 2b, you should be able to:

- Upload audio file
- Automatic transcription (10-30 seconds)
- LLM extracts structured data
- Verification checks pass/fail
- Queue shows transcription progress
- Failed verifications flagged for review
- All tests passing
- Docker containers running smoothly

---

## Resources

### Whisper
- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- Recommended: Use `base` or `small` model for speed

### LLM Options
- [Llama 3.1 8B](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) - Fast, good accuracy
- [Llama 3.1 70B](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) - Slower, best accuracy

### FHIR
- [FHIR MedicationStatement](https://www.hl7.org/fhir/medicationstatement.html)
- [FHIR Condition](https://www.hl7.org/fhir/condition.html)

### Docker
- [Docker Compose Guide](https://docs.docker.com/compose/)

---

**Ready to build the AI layer? Start with Task 1.**
