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

### How This Plan Works

**Phases** = *What* we build (features in priority order)
**8-Step Workflow** = *How* we build each component (contract-first engineering standard)

**See:** [WORKFLOW_SPEC.md](docs/WORKFLOW_SPEC.md) for the complete 8-step lifecycle

**Mapping:**

| PLAN Phase | 8-Step Workflow Applied | Purpose |
|:-----------|:------------------------|:--------|
| **Phase 0** | Steps 1-4: Business reqs → Source spec → Generated models | Create test fixtures |
| **Phase 1** | Steps 1-8: Complete extraction layer | Voice → structured data |
| **Phase 2** | Steps 4-6: Wrapper → CLI → Component tests | Wire extraction to FHIR |
| **Phase 3** | Steps 7-8: Business logic → PBT verification | FastAPI + end-to-end |

**Each phase follows:** Business Requirements → Spec → Models → Wrapper → CLI → Tests → Logic → Verification

---

**Current Status:**

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | ✅ COMPLETE | Sample transcripts created (10 examples) |
| Phase 1.1 | ✅ COMPLETE | Extraction module structure (llm_parser.py, models.py, temporal.py) |
| Phase 1.2 | ✅ COMPLETE | Temporal resolution working |
| Phase 1.3 | ✅ COMPLETE | Confidence scoring framework in place |
| Phase 1.4 | ✅ COMPLETE | LLM client with multi-provider support and automatic retry |
| Phase 2 | ✅ COMPLETE | Integration workflow complete (extraction → FHIR → verification) |
| Phase 3 | ✅ COMPLETE | FastAPI `/extract` endpoint + performance benchmarking |

---

**Completed:**
- ✅ Business purpose documentation ([BUSINESS_PURPOSE.md](docs/BUSINESS_PURPOSE.md))
- ✅ Comprehensive requirements (15+ business/clinical/compliance docs)
- ✅ Pre-mortem analysis (20 failure scenarios identified)
- ✅ Risk mitigation strategies documented
- ✅ Sample transcripts ([tests/fixtures/sample_transcripts.json](tests/fixtures/sample_transcripts.json))
- ✅ Extraction module scaffold ([src/extraction/](src/extraction/))
- ✅ AGENTS.md restructured with standards split out

---

**Next Actions (Prioritized):**

### Phase 3: Demonstration & Polish ✅ COMPLETE
**8-Step:** Steps 7-8 (Pure-Functional Business Logic → System Verification/PBT)

**Task 3.1: Add FastAPI endpoints** ✅
- **File:** `src/api.py` (expand existing)
- **Status:** POST `/extract` endpoint accepts patient_id + transcript, returns extraction + verification
- **Acceptance:** Can curl the endpoint with sample data
- **API:** Returns `ExtractionResponse` with extraction details and verification result

**Task 3.2: Performance benchmarking** ✅
- **Files:** `tests/benchmarks/test_performance.py`, `scripts/benchmark.py`
- **Status:** Benchmarks for `/health`, `/verify`, `/verify/fhir/{id}`, `/extract` endpoints
- **Acceptance:** Documented p50/p95/p99 latencies via pytest-benchmark

### Phase 2: Integration Workflow ✅ COMPLETE
**8-Step:** Steps 4-6 (Domain Wrapper → CLI Tooling → Component Tests)

**Task 2.1: Wire FHIR client to verification engine** ✅
- **File:** `src/integrations/fhir/workflow.py`
- **Status:** `VerificationWorkflow` class orchestrates complete pipeline
- **Acceptance:** `verify_patient_documentation(patient_id, transcript)` returns Result

**Task 2.2: Build end-to-end example** ✅
- **File:** `examples/complete_workflow.py`
- **Status:** Runnable example showing Dictation → Extract → Verify → Result
- **Acceptance:** Demonstrates real-world clinical encounter with HAPI FHIR sandbox

### Phase 1.4: LLM Client Integration ✅ COMPLETE
**8-Step:** Steps 5-6 (CLI Tooling → Component Tests)

**Task 1.4.1: Implement LLM client** ✅
- **File:** `src/extraction/llm_client.py`
- **Status:** Abstract LLM provider with OpenAI, Azure, and Synthetic support
- **Features:** Automatic retry with exponential backoff, centralized configuration
- **Acceptance:** Works with Synthetic API (tested with real calls)

**Task 1.4.2: Wire LLM to parser** ✅
- **File:** `src/extraction/llm_parser.py`
- **Status:** Integrated LLM client with extraction logic
- **Test:** 11/11 extraction tests passing

**Task 1.4.3: Test extraction accuracy** ✅
- **Files:** `tests/test_extraction_accuracy.py`, `cli/test_extraction.py`
- **Status:** Comprehensive test suite with mock and real API validation
- **CLI Tool:** Interactive extraction testing with accuracy reporting

---

### Phase 1: Voice Transcription Extraction Layer (Reference)
**8-Step:** Steps 1-8 complete (Full lifecycle for extraction module)

**Task 1.1: Create extraction module structure** ✅ DONE
- **Files:** `src/extraction/__init__.py`, `src/extraction/llm_parser.py`
- **Status:** Module scaffolded with LLM-based approach

**Task 1.2: Temporal expression resolution** ✅ DONE
- **File:** `src/extraction/temporal.py`
- **Status:** Rule-based temporal resolver implemented
- **Next:** Integration testing

**Task 1.3: Extraction confidence scoring** ✅ DONE
- **File:** `src/extraction/models.py`
- **Status:** Confidence framework in place
- **Next:** Calibration with real data

### Phase 2: Integration Workflow ✅ COMPLETE
**8-Step:** Steps 4-6 (Domain Wrapper → CLI Tooling → Component Tests)

**Task 2.1: Wire FHIR client to verification engine** ✅
- **File:** `src/integrations/fhir/workflow.py`
- **Status:** `VerificationWorkflow` class orchestrates complete pipeline
- **Acceptance:** `verify_patient_documentation(patient_id, transcript)` returns Result

**Task 2.2: Build end-to-end example** ✅
- **File:** `examples/complete_workflow.py`
- **Status:** Runnable example showing Dictation → Extract → Verify → Result
- **Acceptance:** Demonstrates real-world clinical encounter with HAPI FHIR sandbox

### Phase 3: Demonstration & Polish ✅ COMPLETE
**8-Step:** Steps 7-8 (Pure-Functional Business Logic → System Verification/PBT)

**Task 3.1: Add FastAPI endpoints** ✅
- **File:** `src/api.py` (expand existing)
- **Status:** POST `/extract` endpoint accepts patient_id + transcript, returns extraction + verification
- **Acceptance:** Can curl the endpoint with sample data

**Task 3.2: Performance benchmarking** ✅
- **File:** `tests/benchmarks/`, `scripts/benchmark.py`
- **Status:** Benchmarks for `/health`, `/verify`, `/verify/fhir/{id}`, `/extract` endpoints
- **Acceptance:** Documented p50/p95/p99 latencies via pytest-benchmark

**Current Status:** All Phases Complete ✅ | Project Ready for Production
**Next Phase:** Medical Protocols Compliance Layer (see docs/plans/2026-02-22-medical-protocols-design.md)

## 📝 Documentation Map

### Core Documentation
| Document | Purpose |
|----------|---------|
| **[RATIONALE](RATIONALE.md)** | High-level architectural reasoning |
| **[AGENTS](AGENTS.md)** | Quick reference and entry point |
| **[CONSOLIDATED_PLAN](CONSOLIDATED_PLAN.md)** | Current implementation status |

### Standards (How We Work)
| Document | Purpose |
|----------|---------|
| **[OPERATIONAL_WORKFLOWS](docs/standards/OPERATIONAL_WORKFLOWS.md)** | How to build features (8-step lifecycle) |
| **[CRITICAL_PATTERNS](docs/standards/CRITICAL_PATTERNS.md)** | Code patterns to use |
| **[TESTING_STANDARDS](docs/standards/TESTING_STANDARDS.md)** | How to test safely |
| **[COMMIT_STANDARDS](docs/standards/COMMIT_STANDARDS.md)** | How to commit code |

### Business & Clinical
| Document | Purpose |
|----------|---------|
| **[PRODUCT_CASE](docs/business/PRODUCT_CASE.md)** | Strategic justification |
| **[REQUIREMENTS](docs/business/VOICE_TRANSCRIPTION_REQUIREMENTS.md)** | Functional requirements |
| **[COMPLIANCE](docs/compliance/VOICE_DATA_COMPLIANCE.md)** | Privacy & My Health Record |
| **[PRE_MORTEM](docs/PRE_MORTEM.md)** | Failure scenarios |
| **[RISK_MITIGATION](docs/RISK_MITIGATION.md)** | Mitigation strategies |

---

*See [AGENTS.md](AGENTS.md) for quick start and [docs/standards/OPERATIONAL_WORKFLOWS.md](docs/standards/OPERATIONAL_WORKFLOWS.md) for how to build.*
