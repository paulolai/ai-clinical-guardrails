# Clinical Workflow Integration

**For:** Clinical Staff, Product, Engineering
**Purpose:** End-to-end workflow from dictation to clinical software documentation
**Context:** Australian Healthcare System

---

## The Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLINICAL WORKFLOW OVERVIEW                           │
└─────────────────────────────────────────────────────────────────────────────┘

PHYSICIAN                                    SYSTEM
─────────                                    ──────
    │                                           │
    │  1. INITIATE                              │
    │  Click "Voice Document" in EHR           │
    │──────────────────────────────────────────▶│
    │                                           │
    │  2. DICTATE                               │
    │  "Mrs. Johnson came in yesterday..."      │
    │──────────────────────────────────────────▶│
    │                                           │
    │                              3. TRANSCRIBE│
    │                              (3rd party)  │
    │                              Confidence   │
    │                              per word     │
    │                                           │
    │                              4. EXTRACT   │
    │                              • Medications│
    │                              • Diagnoses  │
    │                              • Dates      │
    │                              • Vitals     │
    │                                           │
    │                              5. VERIFY    │
    │                              • Date check │
    │                              • Protocol   │
    │                              • PII scan   │
    │                                           │
    │  6. REVIEW                                │
    │◀──────────────────────────────────────────│
    │  See structured data + alerts             │
    │                                           │
    │  7. APPROVE/EDIT                          │
    │  Review, make corrections, sign          │
    │──────────────────────────────────────────▶│
    │                                           │
    │                              8. EXPORT    │
    │                              to EMR       │
    │                                           │
    │  9. COMPLETE                              │
    │◀──────────────────────────────────────────│
    │  Note in EHR, ready for billing          │
    │                                           │
```

---

## Step-by-Step Process

### Step 1: Initiate (Physician)

**Trigger:** Physician decides to document via voice

**Actions:**
- Click "Voice Document" button in EHR
- Select note type (H&P, Progress Note, Procedure Note)
- Confirm patient context (auto-populated from EHR)

**System Response:**
- Launch voice capture interface
- Display patient banner (name, DOB, MRN)
- Show dictation timer

**Error Handling:**
- If patient mismatch → Alert and require correction
- If no microphone → Prompt for manual entry

### Step 2: Dictate (Physician)

**What Physician Does:**
- Speaks naturally about the encounter
- No special formatting required
- Can pause, resume, restart

**Example Dictation (Ambulatory):**
> "Mrs. Sarah Johnson came in yesterday for her follow-up visit. She's been taking Lisinopril 10 milligrams daily and her blood pressure has improved significantly. Started two weeks ago. Next appointment scheduled for in two weeks to check her progress."

**System Response:**
- Stream audio to transcription service
- Display real-time transcript (if available)
- Show recording indicator

### Step 3: Transcribe (Third-Party Service)

**Process:**
- Audio → Text conversion
- Medical vocabulary optimization
- Automatic punctuation
- Confidence scoring per word

**Timing:**
- <2 min dictation: <5 seconds processing
- >2 min dictation: Asynchronous with progress indicator

**Error Handling:**
- Timeout >10 seconds → Fallback to manual template
- Low transcription confidence → Flag for careful review

### Step 4: Extract (Extraction Engine)

**Entities Extracted:**

| Category | Examples | Output |
|----------|----------|--------|
| **Medications** | Lisinopril 10mg daily | Name, dosage, frequency, status |
| **Temporal** | yesterday, two weeks | Resolved dates, confidence |
| **Vitals** | BP 128/82 | Type, value, unit |
| **Diagnoses** | hypertension | Text, ICD-10 if identifiable |
| **Procedures** | knee replacement | Name, date if mentioned |

**Example Extraction:**
```json
{
  "patient_name": "Mrs. Sarah Johnson",
  "medications": [
    {
      "name": "Lisinopril",
      "dosage": "10 mg",
      "frequency": "daily",
      "status": "active",
      "confidence": 0.95
    }
  ],
  "temporal_expressions": [
    {
      "text": "yesterday",
      "resolved_date": "2026-02-20",
      "confidence": 1.0
    }
  ]
}
```

### Step 5: Verify (Verification Engine)

**Checks Performed:**

1. **Date Integrity**
   - Do extracted dates match encounter dates?
   - Are dates within plausible ranges?

2. **Protocol Adherence**
   - Sepsis mentioned? → Antibiotic documented?
   - Chest pain? → EKG/MI protocol followed?

3. **PII Detection**
   - SSN patterns detected?
   - Medicare numbers found?

4. **EMR Validation**
   - Medications match active list?
   - Vital signs match flowsheet?

**Alert Generation:**
| Severity | Condition | Action Required |
|----------|-----------|-----------------|
| **Critical** | Medication mismatch | Must resolve before sign |
| **High** | Date discrepancy | Review and confirm |
| **Medium** | Low confidence extraction | Acknowledge |
| **Low** | Missing optional field | Optional completion |

### Step 6: Review (Physician Interface)

**Screen Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│ Patient: Sarah Johnson | DOB: 01/15/1955 | MRN: 12345678     │
│ Encounter: 02/21/2026 | Provider: Dr. Smith                   │
├────────────────────────────────────────────────────────────────┤
│ 🎤 ORIGINAL TRANSCRIPT                                         │
│ Mrs. Sarah Johnson came in yesterday for her follow-up visit...│
├────────────────────────────────────────────────────────────────┤
│ 📋 EXTRACTED DATA                                              │
│                                                                │
│ Medications:                                                   │
│ ✅ Lisinopril 10 mg daily (Active) [Confidence: 95%]          │
│                                                                │
│ Dates:                                                         │
│ ✅ Yesterday → 02/20/2026 [Confidence: 100%]                  │
│ ⚠️  "Two weeks ago" → 02/07/2026 [Confidence: 80%]          │
│                                                                │
│ Vitals:                                                        │
│ — None extracted                                               │
├────────────────────────────────────────────────────────────────┤
│ ⚠️ ALERTS (2)                                                  │
│ • Date "two weeks ago" is ambiguous - please verify           │
│ • No vital signs mentioned - extract from flowsheet?          │
├────────────────────────────────────────────────────────────────┤
│ [Edit Field] [Reject Extraction] [Sign & Export to EMR]       │
└────────────────────────────────────────────────────────────────┘
```

**Physician Actions:**
1. Review original transcript
2. Verify extracted fields
3. Edit any incorrect extractions
4. Resolve all critical alerts
5. Add missing information
6. Sign and export

### Step 7: Approve/Edit (Physician)

**Editing Capabilities:**
- Click any field to edit
- Add new fields
- Delete incorrect extractions
- Mark extraction as "incorrect" (feedback)

**Override Workflow:**
- System suggests X, physician enters Y
- Capture reason (optional dropdown): "Patient clarified", "Extraction error", "Transcription error"
- Log for quality improvement

**Sign-Off Requirements:**
- All critical alerts resolved
- Patient identity confirmed
- Physician identity verified (re-authentication)

### Step 8: Export to EMR (System)

**Data Flow:**
```
Extraction System → FHIR API → EMR
```

**Fields Populated:**
- Medication list
- Diagnosis codes
- Vital signs
- Chief complaint
- Plan/follow-up
- Full narrative (transcript as note text)

**Error Handling:**
- EMR API failure → Queue for retry, notify operations
- Partial success → Log which fields succeeded
- Conflict detection → Flag for manual resolution

### Step 9: Complete (EMR)

**Final State:**
- Note visible in EMR
- Structured data queryable
- Billing codes available
- Signed and locked

**Audit Trail:**
- Who dictated
- When extraction occurred
- Confidence scores
- What was edited
- When signed

---

## Use Case Workflows

### Ambulatory Follow-Up (Happy Path)

**Scenario:** Routine diabetes follow-up

**Timeline:**
1. Dictate (2 min) → 2. Review (1 min) → 3. Sign (30 sec) → **Total: 3.5 min**

**Outcome:** All fields high confidence, minor edit to follow-up date, exported successfully.

### Emergency Department (Complex Path)

**Scenario:** Chest pain with protocol triggers

**Timeline:**
1. Dictate (4 min) → 2. Review (2 min, resolve alerts) → 3. Sign (1 min) → **Total: 7 min**

**Alerts Generated:**
- ⚠️ Chest pain mentioned → MI protocol checklist displayed
- ⚠️ Medication (nitroglycerin) not in EMR active list → Physician confirms PRN
- ✅ Vitals match flowsheet

**Outcome:** Protocol documented, all alerts resolved, disposition note auto-populated.

### Ambulatory (Low Confidence Path)

**Scenario:** Ambiguous temporal references

**Timeline:**
1. Dictate (3 min) → 2. Review (3 min, manual corrections) → 3. Sign (1 min) → **Total: 7 min**

**Alerts Generated:**
- ⚠️ "Recently" started medication (confidence: 30%) → Physician enters actual date
- ⚠️ Unrecognized medication name → Manual entry
- ⚠️ Visit type unclear → Physician selects from dropdown

**Outcome:** System assisted but required significant physician input. Feedback logged for algorithm improvement.

---

## Exception Workflows

### Service Unavailable

**Trigger:** Transcription service timeout

**Response:**
1. Display error message: "Voice service temporarily unavailable"
2. Offer: "Try Again" or "Use Manual Template"
3. If retry fails, default to template-based entry
4. Log incident for operations

### Critical Alert Cannot Resolve

**Trigger:** Medication mismatch that physician cannot reconcile

**Response:**
1. Physician selects "Cannot Resolve - Manual Entry"
2. System exports transcript text only (no structured data)
3. Physician completes note manually
4. Incident logged for quality review

### PII Detected

**Trigger:** SSN or Medicare number found in transcript

**Response:**
1. Redact value in display: "[REDACTED-SSN]"
2. Alert: "Potential PII detected - do not include in clinical record"
3. Physician must confirm removal before signing
4. Compliance team notified

---

## Success Metrics by Step

| Step | Metric | Target |
|------|--------|--------|
| 1. Initiate | Time to start dictation | <5 seconds |
| 2. Dictate | Dictation completion rate | >95% |
| 3. Transcribe | Transcription success rate | >98% |
| 4. Extract | Extraction success rate | >95% |
| 5. Verify | Alert generation rate | <20% of notes |
| 6. Review | Time in review screen | <2 minutes |
| 7. Approve | Physician edit rate | <30% of fields |
| 8. Export | EMR export success rate | >99% |
| 9. Complete | End-to-end time | <5 minutes (avg) |

---

## Integration Points

### EHR Integration

**Launch:**
- Embedded iframe or separate window
- Context passed: Patient ID, Encounter ID, User ID

**Return:**
- Note ID created
- Structured data available for queries
- Billing interface updated

### Scheduling Integration

**Trigger:** Extracted "follow-up in 2 weeks"

**Action:**
- Pre-populate scheduling request
- Suggest appointment slots
- Provider reviews and confirms

### Order Entry Integration

**Trigger:** Extracted medication start

**Action:**
- Suggest order in CPOE
- Provider reviews and signs order separately
- No automatic ordering (safety)

---

## User Experience Principles

### Speed
- No click deeper than 2 levels
- Keyboard shortcuts for common actions
- Progressive disclosure (expand only if needed)

### Trust
- Show original transcript prominently
- Confidence scores visible
- Clear indicators of what system did vs. physician did

### Safety
- Critical alerts block sign-off
- Easy override with reason capture
- Audit trail of all decisions

### Flexibility
- Easy switch to manual entry
- Save and resume later
- Multiple input methods (voice, keyboard, template)

---

*For technical implementation details, see [EXTRACTION_LAYER_DESIGN.md](../technical/EXTRACTION_LAYER_DESIGN.md)*
