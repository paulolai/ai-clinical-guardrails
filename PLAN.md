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

**Next Steps:**
- 📋 Component tests against real FHIR sandbox
- 📋 Complete verification engine with all three invariants
- 📋 Integration workflow demonstration
- 📋 Performance benchmarking and optimization

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
