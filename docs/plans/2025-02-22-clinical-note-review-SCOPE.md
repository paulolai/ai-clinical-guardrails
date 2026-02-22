# Clinical Note Review - Revised Implementation Scope

**Date:** 2025-02-22
**Status:** Streamlined for Staff+ Demo
**Rationale:** Focus on demonstrating integration depth over breadth

---

## Executive Summary

**Original Plan:** 11 tasks, ~100 steps, full verification pipeline
**Revised Scope:** 4 tasks, ~25 steps, integration-focused demonstration

**Why Scale Back:**
- Existing system already has verification engine (ComplianceEngine)
- Existing system already has FHIR R5 client
- Existing system already has protocol checkers
- **Gap is:** Connecting these pieces for the "review" workflow

**What's Different:** Instead of building a parallel system, we **extend** the existing one.

---

## What Already Exists (Leverage These)

| Component | Location | What It Does |
|-----------|----------|--------------|
| **FHIRClient** | `src/integrations/fhir/client.py` | Fetch Patient, Encounter from FHIR R5 |
| **ComplianceEngine** | `src/engine.py` | Verify AI output against EMR (dates, PII, protocols) |
| **ProtocolRegistry** | `src/protocols/registry.py` | Allergy, drug interaction checks |
| **Extraction Models** | `src/extraction/models.py` | StructuredExtractions with medications, diagnoses |
| **API** | `src/api.py` | `/verify`, `/extract` endpoints |
| **CLI** | `cli/emr.py`, `cli/api.py` | Debugging tools |

---

## Revised Scope: 4 Tasks

### Task 1: Extend Domain Models (30 min)
**Purpose:** Add clinical note structure to existing models

**Files:**
- Modify: `src/models.py` (add ClinicalNote, UnifiedReview)

**What to add:**
```python
class ClinicalNote(BaseModel):
    """AI-generated clinical note for review."""
    note_id: str
    patient_id: str
    encounter_id: str
    generated_at: datetime
    sections: dict[str, str]  # chief_complaint, assessment, plan, etc.
    extraction: StructuredExtraction  # Reuse existing!

class UnifiedReview(BaseModel):
    """Combined view for clinician review."""
    note: ClinicalNote
    emr_context: EMRContext  # Existing!
    verification: VerificationResult  # Existing!
    review_url: str
```

**Why minimal:** Reuse `StructuredExtraction` instead of building new entity extraction. Reuse `VerificationResult` instead of building new verification.

---

### Task 2: Create Review Service (45 min)
**Purpose:** Service that orchestrates fetch → verify → present

**Files:**
- Create: `src/review/service.py`
- Create: `src/review/__init__.py`

**What it does:**
```python
class ReviewService:
    """Orchestrates the review workflow."""

    async def create_review(
        self,
        note: ClinicalNote
    ) -> UnifiedReview:
        # 1. Fetch EMR (existing FHIRClient)
        patient = await self.fhir_client.get_patient_profile(note.patient_id)
        context = await self.fhir_client.get_latest_encounter(note.patient_id)

        # 2. Convert to AIGeneratedOutput (existing model)
        ai_output = self._note_to_ai_output(note)

        # 3. Verify (existing ComplianceEngine)
        result = ComplianceEngine.verify(patient, context, ai_output)

        # 4. Build unified view
        return UnifiedReview(
            note=note,
            emr_context=context,
            verification=result.value if result.is_success else None,
            review_url=f"/review/{note.note_id}"
        )
```

**Key insight:** We're **composing** existing components, not building new ones.

---

### Task 3: Add Review API Endpoint (30 min)
**Purpose:** HTTP endpoint for getting review view

**Files:**
- Modify: `src/api.py` (add endpoints)

**Endpoints:**
```python
@app.post("/review/create")
async def create_review(request: CreateReviewRequest) -> UnifiedReview:
    """Create a unified review for an AI-generated note."""
    service = ReviewService(fhir_client=emr_client)
    return await service.create_review(request.to_clinical_note())

@app.get("/review/{note_id}")
async def get_review(note_id: str) -> UnifiedReview:
    """Get existing review (with freshness check)."""
    # Simple: regenerate each time for demo
    # Production: would cache and check freshness
```

**Why simple:** For demo, regenerate on each request. Shows the flow works.

---

### Task 4: Add CLI for Review Testing (20 min)
**Purpose:** Developer tool to test review flow

**Files:**
- Create: `cli/review.py`

**Commands:**
```bash
# Create a review
uv run python cli/review.py create \
  --patient-id 90128869 \
  --transcript "Patient has hypertension, started on lisinopril"

# View review
uv run python cli/review.py view --note-id <id>
```

**Output:**
```
Review for Patient: John Doe (ID: 90128869)

AI Note:
  Assessment: Hypertension
  Medications: Lisinopril

EMR Context:
  Current Medications: [Lisinopril 10mg, Metformin 500mg]
  Allergies: [Penicillin]

Verification:
  Status: VERIFIED
  Score: 0.95
  Alerts: None

Review URL: /review/note-123
```

---

## Testing Strategy

**Component Tests:**
- Test ReviewService against HAPI FHIR sandbox
- Use VCR for HTTP recording

**Integration Tests:**
- End-to-end: CLI → API → FHIR → Response

**Property Tests:**
- Minimal - focus on component tests for demo

---

## What We're NOT Building (YAGNI)

| Original Plan | Why Skip | Alternative |
|---------------|----------|-------------|
| Snapshot Store | Complexity | Regenerate each time for demo |
| FreshnessChecker | Complex change detection | Simple timestamp compare |
| VerificationOrchestrator | Duplicate of existing | Extend ComplianceEngine |
| UnifiedViewBuilder | Over-engineering | Simple dataclass composition |
| Full test suite | Time constraint | Component tests only |

---

## Success Criteria

**Must Have:**
- [ ] CLI can create review for test patient
- [ ] Review shows AI note + EMR context + verification
- [ ] API endpoint works
- [ ] Component tests pass against HAPI sandbox

**Nice to Have:**
- [ ] Discrepancy highlighting in output
- [ ] Freshness warning displayed

**Out of Scope:**
- [ ] Web UI
- [ ] Caching/persistence
- [ ] Async job queue
- [ ] Full test coverage

---

## Estimated Effort

**Total:** ~2-3 hours focused work

**Breakdown:**
- Task 1: 30 min
- Task 2: 45 min
- Task 3: 30 min
- Task 4: 20 min
- Testing: 30 min

**What This Demonstrates:**
1. **Integration Architecture** - Composing existing systems
2. **FHIR R5 Proficiency** - Real EMR data
3. **Safety-Critical Thinking** - Verification at every step
4. **Production Patterns** - Service layer, Result types
5. **CLI Tooling** - Developer experience focus

---

## Next Steps

1. **Approve this scope** - Confirm 4 tasks are right focus
2. **Create implementation plan** - Detailed steps for each task
3. **Execute** - Build incrementally with TDD

**Alternative:** If this scope is still too broad, we could further reduce to just Task 2 + Task 4 (Service + CLI) as a proof of concept.
