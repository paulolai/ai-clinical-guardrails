# Clinical Note Review System - Design Document

**Date:** 2025-02-22
**Status:** Approved for Implementation
**Author:** Design Review Session

---

## 1. Business Requirements (Step 1 - Foundation)

### The Problem
Clinicians spend 20-40% of their day reviewing and correcting AI-generated clinical notes. Current workflow requires:
- Cross-referencing AI notes against patient EMR across multiple systems
- Context-switching between 3-5 different applications
- Manual detection of hallucinations and missing information

**Result:** 15-25 minutes per patient instead of 5 minutes, contributing to clinician burnout.

### Success Metrics
- **Primary:** Reduce documentation review time from 20 min → <5 min per patient (75% reduction)
- **Secondary:** Catch >95% of AI hallucinations before doctor review
- **Tertiary:** Zero missed critical alerts (allergies, drug interactions) due to fragmented context

### Stakeholders
- **Primary Users:** Clinicians reviewing AI-generated notes
- **Compliance:** Requires immutable audit trail
- **Operations:** Must work during EMR downtime

### Constraints
- Zero patient safety risks introduced
- Immutable audit trail required
- Graceful degradation during EMR outages

---

## 2. Requirements & Source Spec (Step 2 - Truth)

### Upstream Data Sources

| System | FHIR R5 Resource | Purpose |
|--------|------------------|---------|
| **EMR (FHIR R5)** | Patient | Demographics, identifiers |
| | MedicationRequest | Active medications |
| | AllergyIntolerance | Known allergies |
| | Condition | Active diagnoses |
| | Observation | Recent vitals, labs |
| | Encounter | Visit context |
| | DocumentReference | Existing clinical notes |
| **AI Service** | Clinical Note (JSON) | Generated documentation |
| **Protocol Registry** | Safety Rules | Validation checks |

### AI Note Format (Input)
```json
{
  "patient_id": "12345",
  "encounter_id": "67890",
  "generated_at": "2025-02-22T10:30:00Z",
  "sections": {
    "chief_complaint": "string",
    "history_of_present_illness": "string",
    "assessment": "string",
    "plan": "string"
  },
  "extracted_entities": {
    "medications": [{"name": "", "dosage": ""}],
    "diagnoses": [{"code": "", "display": ""}],
    "dates": ["2025-02-22"]
  }
}
```

### Verification Rules (from existing Protocol Registry)
1. **Date Integrity:** All dates must exist in patient's EMR window
2. **Allergy Checker:** Flag medications conflicting with known allergies
3. **Drug Interaction Checker:** Flag unsafe medication combinations
4. **Required Fields:** Ensure mandatory sections present
5. **PII Scanning:** Detect unauthorized identifiers

### Latency Requirements
- Initial verification: < 2 seconds (async)
- Review page load: < 500ms
- Re-verification on stale data: < 1 second

---

## 3. Architecture Decision: Hybrid Verification with Smart Re-verification

### Selected Approach: Hybrid with Smart Re-verification (Approach 3)

**Rationale:**
- **Fast initial review** - Verified snapshot ready when doctor opens
- **Freshness guarantees** - Automatic re-verification if EMR data changed
- **Audit trail** - Immutable record of what was verified when
- **Resilient** - Works during EMR downtime with cached data + warnings

### Why Not Other Approaches?
- **Approach 1 (Snapshots Only):** Risk of stale data if doctor reviews hours later
- **Approach 2 (On-Demand):** Unacceptable latency, no audit trail, EMR rate limiting risk

---

## 4. Component Design

### 4.1 Core Components

| Component | Responsibility | Key Design Decisions |
|-----------|---------------|---------------------|
| **VerificationOrchestrator** | Async pipeline coordinating FHIR fetch + protocol checks + LLM validation | Event-driven, idempotent, retry logic |
| **SnapshotStore** | Immutable storage with versioning | Append-only, cryptographic hashes for integrity |
| **FreshnessChecker** | Detect EMR data changes since verification | Compares timestamps and version IDs |
| **UnifiedViewBuilder** | Aggregates AI note, EMR data, verification results | Denormalized for fast reads |
| **ReviewAPI** | FastAPI endpoint serving unified experience | Caching, rate limiting, auth |

### 4.2 Data Flow

```
1. AI generates note
   ↓
2. VerificationOrchestrator:
   - Fetch Patient from FHIR
   - Fetch MedicationRequest, AllergyIntolerance
   - Run protocol checks
   - Store verified snapshot
   ↓
3. Doctor opens review
   ↓
4. ReviewAPI:
   - Check freshness
   - Re-verify if needed
   - Build unified view
   ↓
5. Doctor reviews unified view with:
   - AI note (highlighted)
   - EMR context (medications, allergies)
   - Discrepancies flagged
```

### 4.3 API Design

**POST /api/v1/notes/verify**
```json
{
  "note_id": "uuid",
  "patient_id": "12345",
  "content": {...}
}
```

**GET /api/v1/notes/{note_id}/review**
```json
{
  "ai_note": {...},
  "emr_context": {
    "patient": {...},
    "medications": [...],
    "allergies": [...]
  },
  "verification_results": {
    "status": "verified|stale|error",
    "discrepancies": [...],
    "verified_at": "2025-02-22T10:30:00Z",
    "data_freshness": "fresh|stale|unavailable"
  }
}
```

---

## 5. Error Handling & Resilience

### Scenarios

| Scenario | Behavior |
|----------|----------|
| **EMR Available** | Real-time verification, fresh data |
| **EMR Down** | Serve cached data with "stale" warning |
| **EMR Slow** | Timeout after 2s, fallback to cache |
| **Verification Fails** | Store error state, notify ops |
| **Data Mismatch** | Highlight discrepancies, confidence score |

### Graceful Degradation
- Never block doctor review
- Always show data with clear freshness indicators
- Log all decisions for audit

---

## 6. Testing Strategy

### Component Tests
- Verify FHIR R5 integration against HAPI sandbox
- Test SnapshotStore immutability
- Test FreshnessChecker change detection

### Property-Based Tests
- Generate random patient data, verify invariants hold
- Prove no hallucinations slip through

### Integration Tests
- End-to-end: AI note → verification → review page
- EMR downtime scenarios

---

## 7. Success Criteria Verification

**Primary Metric (Review Time):**
- Baseline: Manual review takes 15-25 min
- Target: <5 min per patient
- Measurement: Time from opening review page to approval/submission

**Secondary Metric (Hallucination Detection):**
- Target: >95% catch rate
- Measurement: Percentage of hallucinations flagged before doctor review

**Tertiary Metric (Safety):**
- Target: 0 missed critical alerts
- Measurement: Incidents of undetected allergies/interactions

---

## 8. Non-Goals (Explicitly Out of Scope)

- Real-time AI note generation (assumed upstream)
- Direct EMR write-back (read-only for this phase)
- Mobile app (web-based review first)
- Multi-EMR aggregation (single EMR per patient)

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| False confidence in AI notes | Clear discrepancy highlighting, confidence scores |
| Performance under load | Caching, async processing, rate limiting |
| Data privacy violations | PII scanning, audit logs, access controls |
| EMR API changes | Wrapper pattern isolates changes |

---

## Approval

This design is approved for implementation. Proceed to writing-plans skill to create detailed implementation plan.

**Next Steps:**
1. Load writing-plans skill
2. Create implementation plan following 8-step lifecycle
3. Begin implementation with Step 3 (Generated Model Layer)
