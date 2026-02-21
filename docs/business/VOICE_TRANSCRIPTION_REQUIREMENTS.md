# Voice Transcription Extraction: Business Requirements

**For:** Product, Engineering, Clinical Leadership
**Purpose:** Functional requirements and business rules
**Context:** Australian Healthcare System

---

## Two Primary Use Cases

### Use Case 1: General Practice Consultation

**Context:** GP completes consultation for chronic disease management (e.g., diabetes, hypertension)

**Workflow:**
```
1. GP dictates during/after consultation (2-3 min)
2. AI transcribes and extracts structured data (30 sec)
3. Verification validates against patient record (10 sec)
4. Structured fields auto-populate clinical software
5. My Health Record data prepared for upload
6. GP reviews and signs (1 min)
7. MBS billing item auto-suggested based on complexity

Total: 3-4 minutes vs 7-10 minutes current state
```

**Required Data Extraction:**

| Field | Required | Business Rule | Confidence Threshold | Failure Action |
|-------|----------|---------------|---------------------|----------------|
| Patient Name | Yes | Must match appointment | 95% | Block if mismatch |
| Consult Type | Yes | MBS item classification (Level B/C/D) | 85% | Manual selection |
| Vital Signs | Conditional | Extract if mentioned | 90% | Flag for review |
| Current Medications | Yes | For reconciliation vs PBS | 90% | Suggest alternatives |
| **Medication Changes** | **Critical** | New, stopped, adjusted | **98%** | **Block auto-pop** |
| Reason for Visit | Yes | MBS requirement | 85% | Present options |
| Clinical Assessment | Yes | MBS requirement | 80% | Flag incomplete |
| Plan/Management | Yes | MBS requirement | 85% | Suggest alternatives |
| Follow-up | Conditional | Care planning | 85% | Suggest alternatives |
| PBS Scripts | Yes | Prescription details | 95% | Verify separately |

### Use Case 2: Emergency Department Documentation

**Context:** Emergency physician evaluates patient with chest pain in Australian public hospital

**Workflow:**
```
1. Physician dictates at bedside during evaluation (3-5 min)
2. Real-time extraction populates structured fields
3. Protocol triggers auto-activate (sepsis, stroke, STEMI)
4. Verification validates against state EMR
5. Disposition documentation auto-generates
6. My Health Record event summary prepared

Safety Value: Protocol alerts + reduced cognitive load
```

**Required Data Extraction:**

| Field | Required | Business Rule | Confidence Threshold | Failure Action |
|-------|----------|---------------|---------------------|----------------|
| Presenting Complaint | Critical | ED documentation requirement | 90% | Mandatory entry |
| Vital Signs | Critical | Must match EMR flowsheet | 95% | Alert on mismatch |
| Allergies | Critical | Extract or verify "NKDA" | 95% | Mandatory verification |
| **Protocol Triggers** | **Critical** | Sepsis, stroke, STEMI, trauma | **99%** | **Auto-activate protocol** |
| Diagnoses | Critical | ED diagnoses | 95% | Manual entry required |
| Procedures | Yes | What was done | 90% | Flag for review |
| **Disposition** | **Critical** | Admit/discharge/transfer | **98%** | **Verify against bed management** |
| My Health Record | Yes | Event summary data | 85% | Flag for manual review |

---

## Australian System Integration Requirements

### Medical Practice Software

**Must Integrate With:**
- Best Practice Software
- MedicalDirector
- Genie Solutions
- Zedmed
- Stat Health

**Integration Method:**
- APIs where available
- HL7 v2 messaging
- Direct database integration (with appropriate security)
- My Health Record integration via HI Service

### My Health Record Integration

**Data Upload Requirements:**
| Document Type | Trigger | Data Extracted |
|--------------|---------|----------------|
| Shared Health Summary | Annual/update | Medications, allergies, conditions |
| Event Summary | ED visit | Diagnoses, procedures, medications |
| Specialist Letter | Consultation | Assessment, plan, recommendations |

**Technical Requirements:**
- HI Service authentication
- NASH (National Authentication Service for Health) certificates
- Compliance with My Health Record legislation
- Patient consent verification

### Medicare/MBS Integration

**Cannot Automate Billing (Legal Requirement):**
- System can **suggest** MBS item numbers
- GP must **manually select and confirm** billing
- No automated Medicare claims submission

**Suggestion Criteria:**
| Item Number | Time Required | Complexity | System Suggestion |
|------------|---------------|------------|-------------------|
| Level B (23) | <20 min | Straightforward | If <3 extractions |
| Level C (36) | ≥20 min | Moderate | If 3-5 extractions |
| Level D (44) | ≥40 min | Complex | If >5 extractions |

---

## Third-Party Service Requirements

**Selected Approach:** AWS Transcribe Medical (Sydney region) or equivalent Australian-hosted service

**Data Sovereignty Requirement:**
- Audio processing must occur in Australia
- Transcription service must have Australian data centres
- No offshore data transfer without patient consent

| Requirement | Specification | Why |
|-------------|---------------|-----|
| Medical Vocabulary | Australian clinical terminology | Drug names (PBS), diagnoses |
| Australian Spelling | Localised spelling recognition | Behaviour, colour, centre |
| Punctuation | Automatic sentence segmentation | Extraction accuracy |
| Custom Vocabulary | Practice-specific terms | Provider names, locations |
| Privacy Compliance | Privacy Act 1988 compliant | Legal requirement |
| Data Location | AWS Sydney (ap-southeast-2) | Data sovereignty |
| Retention | Audio deleted after transcription | Minimise liability |
| Latency | <5 seconds for <2 min dictation | User experience |
| Error Rate | <2% transcription failures | Reliability |

**What We Send:**
- Audio stream or file (encrypted)
- Medical specialty (for vocabulary optimization)
- NO patient identifiers in metadata

**What We Receive:**
- Transcript text (PHI)
- Confidence scores per word
- Timestamp information

---

## Confidence Threshold Framework

### Tier 1: Safety Critical (95-99%)

**Fields:**
- Medication changes (new, stopped, dose adjustments)
- Allergies
- Protocol triggers (sepsis, stroke, STEMI)
- Disposition decisions

**Why High Threshold:**
- Patient harm if wrong
- AHPRA compliance requirements
- Legal liability
- MBS audit risk

**Below Threshold Action:**
- Block auto-population
- Flag for mandatory clinician review
- Show original text prominently
- Provide structured entry alternative

### Tier 2: Important (85-95%)

**Fields:**
- Patient names, vitals, current meds
- Visit types, presenting complaints
- Diagnoses

**Why Medium-High Threshold:**
- Important for continuity
- MBS documentation requirements
- My Health Record accuracy

**Below Threshold Action:**
- Populate with warning indicator
- Highlight in review interface
- Suggest top 3 alternatives

### Tier 3: Informational (70-85%)

**Fields:**
- Social history
- Family history
- Preventive care reminders

**Why Lower Threshold:**
- Useful context but not critical
- Easy to correct
- Low risk if wrong

**Below Threshold Action:**
- Populate with review flag
- Collapse in UI (expandable)

---

## Human-in-the-Loop Requirements

### Clinician Review Interface

**Must Display:**
1. Original transcript (full text, read-only)
2. Extracted structured data (organised by category)
3. Confidence scores per field
4. Verification alerts (EMR discrepancies)
5. PII warnings (if detected)
6. Protocol alerts (if triggered)
7. **MBS item suggestions** (with manual selection required)

**Required Actions:**
1. Review all extracted data
2. Resolve verification alerts
3. Explicitly approve with signature
4. **Manually select MBS item** (system cannot bill)
5. Option to edit any field
6. Option to reject extraction and manual entry

**Workflow Rules:**
- Cannot sign until all critical alerts resolved
- Low confidence fields (<70%) must be acknowledged
- Audit trail records review time and changes
- My Health Record upload requires explicit consent check

### Override Capabilities

**Clinician Can:**
- Edit any extracted field
- Delete extracted data
- Add missing data manually
- Mark extraction as incorrect (feedback)
- Switch to template-based entry
- **Override MBS suggestion** (legal requirement)

**System Must:**
- Capture override reason (optional but encouraged)
- Log all changes for quality improvement
- Not allow signature until all safety checks pass
- Never submit Medicare claims automatically

---

## Privacy Act Compliance

### Australian Privacy Principles (APP)

**APP 1 - Open and Transparent Management:**
- Privacy policy covers voice transcription
- Collection notification includes voice data

**APP 3 - Collection of Solicited Personal Information:**
- Only collect information necessary for healthcare
- Audio processed and deleted; only transcript retained

**APP 11 - Security of Personal Information:**
- Encryption at rest and in transit
- Access controls and audit logging
- Regular security assessments

### Data Retention Policy

**What We Store:**
- ✅ Original transcript text (personal information)
- ✅ Structured extraction results
- ✅ Confidence scores
- ✅ Verification results
- ✅ Audit trail (who, when, what)

**What We Do NOT Store:**
- ❌ Audio recordings
- ❌ Extracted identifiers in logs (Medicare numbers, DVA numbers redacted)

**Retention Periods:**
- Transcripts: 7+ years (match medical record retention)
- Audit logs: 7 years (compliance)
- Failed extractions: 90 days (quality improvement)
- My Health Record audit logs: 7 years (legislative requirement)

---

## Error Handling Requirements

### Service Failure Scenarios

| Failure | Detection | Response |
|---------|-----------|----------|
| Transcription service down | Timeout >10 sec | Fallback to manual entry template |
| Extraction timeout | >5 sec processing | Return partial results + warning |
| Low overall confidence | <50% | Reject extraction, manual entry |
| Medical software integration failure | API error | Queue for retry, alert operations |
| My Health Record unavailable | HI Service error | Queue for later upload |

### User Communication

**Error Messages Must:**
- Explain what happened in plain language
- Provide clear next steps
- Not blame the user
- Include support contact if needed

**Examples:**
- "Voice service temporarily unavailable. Please use manual entry or try again in 1 minute."
- "Low confidence in medication extraction. Please review carefully before saving."
- "My Health Record upload failed. Clinical note saved locally; will retry upload automatically."

---

## Success Metrics

### Quantitative

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Documentation time | 7 min/consult | 3 min/consult | Time study |
| Same-day note closure | 60% | 90% | Clinical software metrics |
| Med reconciliation errors | 5% | <1% | Chart audit |
| Extraction accuracy | N/A | >90% | Golden set comparison |
| Clinician satisfaction | 3.2/5 | 4.2/5 | Survey |
| MBS audit queries | 50/year | <10/year | Practice management system |

### Qualitative

- Clinician feedback (monthly)
- Support ticket volume
- Feature requests
- Voluntary adoption rate
- RACGP feedback

---

## Australian Regulatory Alignment

### AHPRA Documentation Standards
- Must meet practitioner registration requirements
- Documentation must support clinical reasoning
- Audit trail demonstrates decision-making process

### My Health Record Legislation
- Healthcare provider organisation obligations
- System operator requirements
- Penalty framework for non-compliance

### State Health Systems
- NSW Health: Integration with eMR/eMeds
- Vic Health: Integration with EPAS
- Qld Health: Integration with ieMR
- Other states: Compatible with local systems

---

## Out of Scope (Phase 1)

**Not Included:**
- Real-time speech-to-text (we use third-party batch)
- AI-generated clinical content (only extraction)
- Automated MBS billing (clinician must select)
- Multi-language support (English only initially)
- Indigenous language support (future consideration)
- Mobile dictation app (integrate with existing)

**Future Considerations:**
- Aboriginal and Torres Strait Islander health templates
- Telehealth consultation documentation
- Aged care facility integration
- Specialist college-specific templates
- Medicare Benefits Schedule updates

---

## Open Questions

1. **Medicare Number Detection:** How do we handle accidental mention of Medicare/DVA numbers in dictation?
2. **Indigenous Health:** Do we need specific extraction models for Aboriginal health contexts?
3. **Telehealth:** How does extraction work for phone/video consultations?
4. **Rural/Remote:** What are connectivity requirements for regional practices?
5. **State Variations:** How do we handle differences between NSW, VIC, QLD, etc.?

*Document Owner:* Product Team
*Review Cycle:* Quarterly
*Approval Required:* Clinical Leadership, RACGP Consultation, Privacy Officer
