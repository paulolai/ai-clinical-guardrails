# Error Handling and Fallbacks

**For:** Engineering, Operations
**Purpose:** Graceful degradation strategies

---

## Failure Modes

### 1. Transcription Service Failure

**Symptoms:**
- Timeout >10 seconds
- HTTP 500/503 errors
- Network connectivity issues

**Response:**
1. Retry once after 2 seconds
2. If still failing: Display error to clinician
3. Offer manual template entry
4. Queue for background retry
5. Alert operations team

**User Message:**
> "Voice service temporarily unavailable. Please use manual entry or try again in 1 minute."

### 2. Low Extraction Confidence

**Symptoms:**
- Overall confidence <50%
- Critical field confidence <95%
- Multiple ambiguous extractions

**Response:**
1. Do not auto-populate fields
2. Present transcript for manual review
3. Suggest structured entry template
4. Log for quality improvement

**User Message:**
> "Unable to extract structured data with sufficient confidence. Please enter information manually."

### 3. Verification Alert - Critical

**Symptoms:**
- Medication mismatch with patient record
- Missing protocol element
- Date outside plausible range

**Response:**
1. Block sign-off
2. Highlight alert prominently
3. Require clinician resolution
4. Provide context (what was expected vs. extracted)

**User Message:**
> "⚠️ Alert: Extracted medication 'Lisinopril' not in patient's active medication list. Please verify."

### 4. EMR Integration Failure

**Symptoms:**
- API timeout
- Authentication failure
- Data validation error

**Response:**
1. Save extraction locally
2. Queue for retry
3. Notify clinician of delay
4. Alert operations team

**User Message:**
> "Clinical software temporarily unavailable. Your documentation is saved and will sync automatically."

### 5. My Health Record Upload Failure

**Symptoms:**
- HI Service error
- NASH certificate issue
- Patient consent error

**Response:**
1. Save for retry
2. Log error with retry count
3. If >3 failures: Alert operations
4. Document note saved locally

**User Message:**
> "My Health Record upload pending. Document saved locally; will retry automatically."

## Fallback Procedures

### Manual Template Entry

**Trigger:** Any extraction failure

**Available Templates:**
- GP consultation (Level B/C/D)
- Progress note
- Procedure note
- Discharge summary
- ED documentation

**Pre-population:**
- Patient demographics from context
- Date/time
- Clinician name
- Other known context

### Partial Extraction

**Trigger:** Some fields extracted successfully, others failed

**Response:**
1. Populate successful fields
2. Flag failed fields for manual entry
3. Allow clinician to complete note
4. Log partial success for improvement

### Offline Mode (Future)

**Trigger:** Complete connectivity loss

**Response:**
1. Store audio locally (encrypted)
2. Queue for processing when online
3. Provide offline template entry
4. Sync when connection restored

## Monitoring and Alerting

**Error Metrics:**
- Error rate by type
- Fallback usage rate
- Retry success rate
- Time to recovery

**Alert Thresholds:**
- Error rate >5% for 5 minutes
- Fallback rate >20%
- Service unavailable >10 minutes

## Recovery Procedures

**Operations Playbook:**
1. Identify error type from logs
2. Check service status dashboards
3. If third-party issue: Check vendor status page
4. If internal issue: Check infrastructure
5. Communicate with users via status page
6. Apply fix or escalate
7. Post-incident review

---

*See also:* [MONITORING_AND_ALERTING.md](MONITORING_AND_ALERTING.md)
