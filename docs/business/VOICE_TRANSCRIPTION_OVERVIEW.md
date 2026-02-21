# Voice Transcription Extraction System: Overview

**For:** All Stakeholders
**Purpose:** High-level understanding of the voice-to-structured-data system
**Context:** Australian Healthcare System
**Status:** Draft

---

## What We're Building

A system that converts clinician voice dictation into structured clinical data that can be verified against the EMR before entering the medical record.

**The Human in the Loop:**
This system assists clinicians—it does not replace their clinical judgment. Every piece of extracted data is presented for physician review and approval before becoming part of the permanent medical record.

---

## The Problem

Australian clinicians spend **2+ hours daily on clinical documentation**, contributing to high rates of burnout and reducing time available for patient care.

**Current State:**
- GP sees patient → Dictates notes → Typist or self-types → Manual entry into clinical software (Best Practice, MedicalDirector)
- Time: 5-10 minutes per patient of clicking and typing
- After-hours "pajama time" spent catching up on notes
- MBS (Medicare Benefits Schedule) compliance requires detailed documentation

**Target State:**
- GP dictates → AI extracts structured data → Verification validates against patient record → GP reviews → Auto-populates clinical software
- Time: 1-3 minutes per patient
- Safer: Verification catches discrepancies before they become errors
- Compliant: MBS requirements automatically captured

**Current State:**
- Physician sees patient → Dictates notes → Transcription service converts to text → Manual EHR entry
- Time: 5-10 minutes per patient of clicking and typing
- Error-prone: Fatigue leads to mistakes

**Target State:**
- Physician dictates → AI extracts structured data → Verification validates against EMR → Physician reviews → Auto-populates EHR
- Time: 1-2 minutes per patient
- Safer: Verification catches discrepancies before they become errors

---

## Two Primary Use Cases

### 1. General Practice Consultation
**Who:** General Practitioners (GPs), practice nurses
**Volume:** 15-25 patients/day
**Pain Point:** Routine documentation consumes 2+ hours daily; MBS compliance requirements
**Solution:** Voice dictation → Extract structured data → Verify → Auto-populate Best Practice/MedicalDirector → Quick review and sign

**Key Data Extracted:**
- Medication reconciliation (changes, new prescriptions, PBS items)
- Vital signs and measurements
- Assessment and plan (MBS Level B/C/D requirements)
- Follow-up intervals
- Temporal references ("started last week", "recheck in 3 months")

**Confidence Threshold:** 98% for medication changes (safety critical)

**Compliance Note:** System suggests MBS item numbers but GP must manually select—no automated billing.

### 2. Emergency Department Documentation
**Who:** Emergency physicians, registrars
**Volume:** High acuity, frequent interruptions
**Pain Point:** Documentation delayed until shift end; critical details buried in narrative
**Solution:** Real-time extraction at bedside → Protocol alerts (sepsis, stroke, STEMI) → Auto-generate disposition → Event summary for My Health Record

**Key Data Extracted:**
- Presenting complaint
- Vital signs matching flowsheet
- Protocol triggers (sepsis, stroke, STEMI, trauma)
- Procedures and orders
- Disposition (admit/discharge/transfer)

**Confidence Threshold:** 99% for protocol triggers (compliance critical)

**Integration:** Prepares Event Summary for automatic upload to My Health Record.

---

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Clinician      │────▶│  Third-Party     │────▶│  Extraction     │
│  Dictation      │     │  Transcription   │     │  Engine         │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                    ┌─────────────────────▼─────────────────────┐
                                    │          Verification Engine               │
                                    │  ┌──────────────┐  ┌──────────────────┐   │
                                    │  │  Date Check  │  │  Protocol Check  │   │
                                    │  └──────────────┘  └──────────────────┘   │
                                    │  ┌──────────────┐  ┌──────────────────┐   │
                                    │  │  PII Check   │  │  EMR Validation  │   │
                                    │  └──────────────┘  └──────────────────┘   │
                                    └─────────────────────┬─────────────────────┘
                                                          │
                                    ┌─────────────────────▼─────────────────────┐
                                    │         Physician Review Interface         │
                                    │    (Human approval required for all data)  │
                                    └─────────────────────┬─────────────────────┘
                                                          │
                                    ┌─────────────────────▼─────────────────────┐
                                    │              EMR Integration               │
                                    │         (FHIR API or direct write)         │
                                    └───────────────────────────────────────────┘
```

---

## Human-in-the-Loop Design

**Core Principle:** The physician owns all clinical decisions. The system assists but never decides.

### Extraction Confidence Tiers

| Confidence | Action | Physician Involvement |
|------------|--------|----------------------|
| **>95%** | Auto-populate with highlight | Review and approve |
| **70-95%** | Populate with warning flag | Review and correct if needed |
| **<70%** | Do not populate; suggest options | Manual selection or entry |

### Physician Review Screen

**What They See:**
- Original transcript (full text)
- Extracted structured data (organized by category)
- Confidence scores for each field
- Verification alerts (discrepancies with EMR)
- One-click accept or edit capability

**What They Must Do:**
- Review all extracted data
- Resolve any verification alerts
- Explicitly sign/approve before data enters EMR

---

## Data Privacy and Compliance

**Australian Regulatory Framework:**
- Privacy Act 1988 (Australian Privacy Principles)
- My Health Records Act 2012
- Healthcare Identifiers Act 2010
- State Health Records Acts

**Data Sovereignty:**
- All processing in Australia (AWS Sydney region)
- No offshore data transfer
- Audio processed and deleted; only transcripts retained

**Third-Party Service:**
- AWS Transcribe Medical (Sydney region) or equivalent Australian-hosted service
- Data processing agreement under Australian law
- Audio not stored by our system (only transcripts)

**What We Store:**
- ✅ Transcript text (personal information under Privacy Act)
- ✅ Structured extractions
- ✅ Verification results
- ✅ Audit trail (who, when, what was reviewed)

**What We Do NOT Store:**
- ❌ Audio recordings
- ❌ Extracted identifiers in logs (Medicare, DVA numbers redacted)

**Retention:** Match medical record policy (7+ years per state requirements)

---

## Success Metrics

*Note: All metrics to be established during pilot. Replace [X] with actual data.*

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Documentation time | [Current: ___ min] | [Target: ___ min] | Time study |
| Same-day note closure | [Current: ___%] | [Target: ___%] | Clinical software metrics |
| Medication reconciliation errors | [Current: ___%] | [Target: ___%] | Chart audit |
| Extraction accuracy | N/A | [Target: ___%] | Golden set comparison |
| Clinician satisfaction | [Current: ___/5] | [Target: ___/5] | Survey |
| Protocol compliance (ED) | 85% | 98% |

---

## Documentation Structure

**Core Documents (for Engineers):**
1. [VOICE_TRANSCRIPTION_REQUIREMENTS.md](VOICE_TRANSCRIPTION_REQUIREMENTS.md) - Detailed functional requirements (Australian context)
2. [EXTRACTION_LAYER_DESIGN.md](../technical/EXTRACTION_LAYER_DESIGN.md) - Technical architecture
3. [VOICE_DATA_COMPLIANCE.md](../compliance/VOICE_DATA_COMPLIANCE.md) - Privacy Act and My Health Record compliance
4. [CLINICAL_WORKFLOW_INTEGRATION.md](../clinical/CLINICAL_WORKFLOW_INTEGRATION.md) - End-to-end workflow

**Technical Documents:**
5. [TRANSCRIPTION_SERVICE_INTEGRATION_SPEC.md](../technical/TRANSCRIPTION_SERVICE_INTEGRATION_SPEC.md) - API specs
6. [EXTRACTION_TESTING_STRATEGY.md](../technical/EXTRACTION_TESTING_STRATEGY.md) - Testing approach
7. [ERROR_HANDLING_AND_FALLBACKS.md](../technical/ERROR_HANDLING_AND_FALLBACKS.md) - Failure modes
8. [PERFORMANCE_AND_SLA_REQUIREMENTS.md](../technical/PERFORMANCE_AND_SLA_REQUIREMENTS.md) - Performance specs
9. [MONITORING_AND_ALERTING.md](../technical/MONITORING_AND_ALERTING.md) - Operations

**Implementation Documents:**
10. [CLINICAL_ROLLOUT_PLAN.md](../clinical/CLINICAL_ROLLOUT_PLAN.md) - Deployment strategy

**Strategic Documents:**
- [PRODUCT_CASE.md](PRODUCT_CASE.md) - Strategic justification and product vision
- [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) - C-suite briefing
- [CLINICAL_STAKEHOLDER_GUIDE.md](../clinical/CLINICAL_STAKEHOLDER_GUIDE.md) - For clinicians and clinical leadership
- [COMPLIANCE_CHECKLIST.md](../compliance/COMPLIANCE_CHECKLIST.md) - For audit and legal review

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Third-party transcription | Faster time-to-market, proven medical accuracy |
| No audio storage | Reduces HIPAA liability; transcripts sufficient |
| Variable confidence thresholds | Field importance varies; safety-critical needs higher bar |
| Human-in-the-loop required | Physician owns clinical decisions; system assists only |
| Two initial use cases | Ambulatory and ED represent high-volume, different complexity |

---

## Next Steps

1. **Review:** Clinical leadership reviews requirements
2. **Vendor Selection:** Evaluate transcription services
3. **Design Approval:** Technical design review
4. **Pilot Planning:** Define scope and success criteria

---

*For questions or feedback, contact the Health IT Product Team.*
