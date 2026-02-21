# AI Clinical Guardrails: Voice-to-Structured-Data Verification

**Concept:** A deterministic verification layer that ensures AI voice transcription outputs are validated against EMR source of truth before entering clinical records.

See [BUSINESS_PURPOSE.md](docs/BUSINESS_PURPOSE.md) for the full business narrative and [BUSINESS_PURPOSE_THINKING.md](docs/BUSINESS_PURPOSE_THINKING.md) for decision rationale.

---

## 🎯 The Mission

**Give clinicians their time back without sacrificing safety.**

Healthcare workers spend ~2 hours on EHR documentation for every 1 hour of patient care. Voice AI can help, but only if we can trust it not to hallucinate dates, miss protocols, or leak PII.

**The Pivot:** We are building the **"AI Compliance Officer"**—an invisible safety net that validates AI-generated documentation against the EMR source of truth before it enters the record.

*   **Problem:** AI voice transcription extracts structured data from clinician dictation, but without verification, clinicians must manually review every field—defeating the purpose.
*   **Solution:** A deterministic **Process Verification Engine** that mathematically proves AI outputs match the source of truth and follow standard operating procedures.

---

## 🏗 The Architecture

### 1. The Domain: Process Verification Engine

**Inputs:**
*   `PatientContext`: Demographics, encounter dates, active medications (from EMR/FHIR)
*   `VoiceTranscription`: Raw text from clinician dictation
*   `ExtractedData`: AI-extracted structured fields (dates, medications, follow-ups)

**The Logic:**
```python
VerificationEngine.verify(patient_context, extracted_data) -> Result<Verified, ComplianceAlert[]>
```

### 2. The Invariants (Administrative Safety)

We use Property-Based Testing to prove the engine catches every sloppy mistake the AI might make.

*   **Invariant 1: Date Integrity**
    *   *Rule:* Every temporal reference MUST resolve to dates within the patient's actual EMR context window
    *   *PBT:* Generate random patient encounters. Feed "corrupted" extractions (wrong dates, impossible windows). Prove it *always* flags discrepancies.

*   **Invariant 2: Protocol Adherence**
    *   *Rule:* If clinical triggers (e.g., "suspected sepsis") appear, mandatory documentation MUST be present
    *   *PBT:* Generate cases with specific triggers. Ensure the engine *always* alerts if required fields are missing.

*   **Invariant 3: Data Safety (PII)**
    *   *Rule:* Structured data MUST NOT contain illegal patterns (e.g., SSNs, Medicare Numbers)
    *   *PBT:* Inject PII into extractions. Prove the engine *never* lets it pass without an alert.

### 3. The Workflow

1.  **Step 1: Dictation.** Clinician dictates: "Mrs. Johnson came in yesterday with chest pain. Started her on Lisinopril. Follow up in two weeks."
2.  **Step 2: Extraction.** AI extracts: `{date: "yesterday", medication: "Lisinopril", follow_up: "two weeks"}`
3.  **Step 3: Verification.** Engine validates against EMR:
    *   Does "yesterday" match an encounter date? ✓
    *   Is Lisinopril in active medications? ✓
    *   Does "two weeks" resolve to valid clinical window? ✓
4.  **Step 4: Auto-fill.** Validated data populates structured fields
5.  **Step 5: Discrepancy handling.** If any check fails, flag for manual review with specific alert
6.  **Step 6: Audit trail.** System logs verification results for compliance attestation

---

## 🚀 Why This Gets You Hired

*   **Staff+ Engineering:** Demonstrates how to scale output through AI while maintaining zero-defect quality standards
*   **Domain Expertise:** Solves the "trust" problem for AI in healthcare administration
*   **Technical Depth:** Contract-first FHIR integration, property-based testing, zero-trust verification
*   **Business Fluency:** Connects technical decisions to workflow efficiency and compliance outcomes

## 🛠 From Concept to Implementation

**Completed:**
- ✅ Business purpose documentation ([BUSINESS_PURPOSE.md](docs/BUSINESS_PURPOSE.md))
- ✅ Decision rationale ([BUSINESS_PURPOSE_THINKING.md](docs/BUSINESS_PURPOSE_THINKING.md))
- ✅ Thinking documentation standard ([THINKING_STANDARD.md](docs/THINKING_STANDARD.md))
- ✅ Updated README with new documentation index

**In Progress:**
- 🔄 FHIR client with contract-first integration
- 🔄 Domain wrapper pattern implementation
- 🔄 Property-based testing for invariants
- 🔄 CLI tooling for interface debugging

**Next Actions (Prioritized):**

### Phase 0: Test Data Generation (Start here)

**Prerequisite for all extraction work** - Need realistic clinical dictation samples to validate extraction.

**Task 0.1: Create manual sample transcript fixtures**
- **File:** `tests/fixtures/sample_transcripts.json`
- **Goal:** 5-10 realistic clinical dictation examples covering:
  - Different visit types (follow-up, acute complaint, routine check)
  - Various temporal expressions ("yesterday", "last week", "in two days")
  - Medication mentions with dosages
  - Protocol triggers (sepsis, chest pain, etc.)
  - PII edge cases (accidental SSN mentions)
- **Definition of Done:** File exists with varied, realistic examples
- **Format:** JSON with fields: `id`, `text`, `expected_extractions`, `metadata`

**Task 0.2: Build synthetic transcript generator (Optional)**
- **File:** `scripts/generate_transcripts.py`
- **Goal:** Generate unlimited synthetic transcripts with controlled parameters
- **Definition of Done:** Script can generate 100+ varied transcripts on demand
- **Value:** Demonstrates testing-at-scale capability

---

### Phase 1: Voice Transcription Extraction Layer (Ready to start)

**Task 1.1: Create extraction module structure**
- **File:** `src/extraction/__init__.py`, `src/extraction/parser.py`
- **Goal:** Parse clinician dictation into structured fields
- **Definition of Done:** Can extract dates, medications, diagnoses from sample text
- **Example:** "Started her on Lisinopril" → `{medication: "Lisinopril", confidence: 0.95}`

**Task 1.2: Temporal expression resolution**
- **File:** `src/extraction/temporal.py`
- **Goal:** Convert relative dates ("yesterday", "two weeks") to absolute dates
- **Definition of Done:** Given an encounter date, resolves temporal expressions correctly
- **Test:** Property-based test with random encounter dates

**Task 1.3: Extraction confidence scoring**
- **File:** `src/models.py` (add ExtractionResult with confidence)
- **Goal:** Each extraction has confidence score for downstream filtering
- **Definition of Done:** Low confidence extractions flagged for review

### Phase 2: Integration Workflow (Blocked by 1.x)

**Task 2.1: Wire FHIR client to verification engine**
- **File:** `src/integrations/fhir/workflow.py`
- **Goal:** Fetch PatientProfile + EMRContext from FHIR, run verification
- **Definition of Done:** `verify_patient_documentation(patient_id, ai_output)` returns Result

**Task 2.2: Build end-to-end example**
- **File:** `examples/complete_workflow.py`
- **Goal:** Demonstrate full flow: Dictation → Extract → Verify → Result
- **Definition of Done:** Runnable example with sample clinical encounter

### Phase 3: Demonstration & Polish (Blocked by 2.x)

**Task 3.1: Add FastAPI endpoints**
- **File:** `src/api.py` (expand existing)
- **Goal:** POST `/verify` endpoint accepts transcription, returns verification
- **Definition of Done:** Can curl the endpoint with sample data

**Task 3.2: Performance benchmarking**
- **File:** `tests/benchmarks/`, `scripts/benchmark.py`
- **Goal:** Measure latency for verification workflow
- **Definition of Done:** Documented p50/p95/p99 latencies

**Current Status:** Ready to start Phase 1.1
**Next Immediate Action:** Create extraction module

## 📝 Documentation Map

| Document | Purpose |
|----------|---------|
| **[RATIONALE](RATIONALE.md)** | High-level architectural reasoning |
| **[BUSINESS_PURPOSE](docs/BUSINESS_PURPOSE.md)** | Business problem and solution narrative |
| **[BUSINESS_PURPOSE_THINKING](docs/BUSINESS_PURPOSE_THINKING.md)** | Why voice transcription, why clinical focus |
| **[THINKING_STANDARD](docs/THINKING_STANDARD.md)** | When and how to document decisions |
| **[AGENTS](AGENTS.md)** | Engineering principles and standards |
| **[ARCHITECTURE](docs/ARCHITECTURE.md)** | System design details |

---

*See [AGENTS.md](AGENTS.md) for engineering standards and [docs/THINKING_STANDARD.md](docs/THINKING_STANDARD.md) for decision documentation patterns.*
