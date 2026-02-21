# Risk Mitigation Strategy

**For:** Engineering, Product, Clinical Leadership
**Purpose:** How we prevent the failures identified in the pre-mortem
**Related:** [PRE_MORTEM.md](PRE_MORTEM.md) - The failure scenarios we're preventing

---

## Risk Framework

**Risk Severity Matrix:**

| Impact →<br>↓ Likelihood | Low | Medium | High | Critical |
|--------------------------|-----|--------|------|----------|
| **High** | Monitor | Plan | Act Now | Critical |
| **Medium** | Accept | Monitor | Plan | Act Now |
| **Low** | Accept | Accept | Monitor | Plan |

**Mitigation Strategies:**
- **Prevent:** Design to avoid the risk
- **Detect:** Monitor for early warning signs
- **Respond:** Plan for when it happens
- **Transfer:** Share risk (insurance, contracts)

---

## Critical Risks (Act Now)

### Risk 1: Wrong Medication Extracted → Patient Harm

**Pre-Mortem Scenario:** System extracted "Metformin" instead of "Metoprolol", auto-populated due to high confidence, clinician didn't notice, patient received wrong drug.

**Risk Level:** Critical

**Mitigation Strategy:**

**1. Prevent: Never Auto-Populate Safety-Critical Fields**
```python
# Safety-critical fields require explicit confirmation
SAFETY_CRITICAL_FIELDS = {
    'medication_changes',  # New, stopped, dose changes
    'allergies',
    'diagnoses',
}

def should_auto_populate(field_type: str, confidence: float) -> bool:
    if field_type in SAFETY_CRITICAL_FIELDS:
        return False  # Never auto-populate
    return confidence > 0.95
```

**2. Prevent: Dual Confirmation for Medication Changes**
- Require explicit checkbox: "I confirm this medication change is accurate"
- Show original transcript text alongside extraction
- Highlight medication name in bold
- Require re-authentication for medication changes

**3. Detect: Hallucination Detection**
- Cross-reference extracted medications against known PBS medication list
- Flag medications not in reference list for manual review
- Check if medication name appears verbatim in transcript
- Low confidence if medication name not found in text

**4. Detect: Confidence Calibration**
```python
class ConfidenceCalibrator:
    """Ensure confidence scores reflect actual accuracy."""

    def __init__(self):
        self.accuracy_history = []

    def calibrate(self, extraction, was_correct: bool):
        """Track whether high confidence actually means high accuracy."""
        self.accuracy_history.append({
            'confidence': extraction.confidence,
            'correct': was_correct,
            'field_type': extraction.field_type
        })

    def get_calibrated_confidence(self, raw_confidence: float) -> float:
        """Adjust confidence based on historical accuracy."""
        # If 0.9 confidence historically 70% accurate, adjust to 0.7
        # Implementation based on calibration curve
        pass
```

**5. Respond: Incident Response Plan**
- Immediate alert to clinical safety team
- Automatic flagging of note for review
- Mandatory correction workflow
- Root cause analysis within 24 hours

**Acceptance Criteria:**
- [ ] Zero auto-population of medication changes
- [ ] Hallucination detection implemented
- [ ] Confidence calibration validated with 100+ samples
- [ ] Incident response plan documented

---

### Risk 2: Clinician Refusal to Adopt

**Pre-Mortem Scenario:** <10% adoption, "faster to just type", don't trust AI, liability concerns, too many false alerts.

**Risk Level:** Critical

**Mitigation Strategy:**

**1. Prevent: Clinical Co-Design from Day One**
- Clinical Advisory Board formed before technical work
- RACGP consultation on requirements
- User research with 20+ clinicians
- Wireframes reviewed by clinicians before coding

**2. Prevent: Prove Value Before Asking for Trust**
- Start with high-confidence extractions only (reduce false alerts)
- Demonstrate time savings in pilot (>30% reduction)
- Show accuracy metrics transparently
- Optional adoption - prove value first

**3. Prevent: Address Medicolegal Concerns**
- Clear documentation: "System assists, clinician decides"
- Audit trail shows who made each decision
- Liability remains with clinician (system is tool, not agent)
- Legal review of all documentation

**4. Detect: Adoption Metrics**
```python
ADOPTION_THRESHOLDS = {
    'daily_active_users': {'target': 0.7, 'alert': 0.5},
    'voluntary_usage_rate': {'target': 0.8, 'alert': 0.6},
    'satisfaction_score': {'target': 4.0, 'alert': 3.0},
    'completion_rate': {'target': 0.9, 'alert': 0.7},
}
```

**5. Respond: Pivot Strategy**
- If adoption <50% after 3 months: Pause, investigate, fix issues
- If adoption <30%: Consider pivot to different use case or shutdown
- Regular user interviews to understand barriers

**Acceptance Criteria:**
- [ ] Clinical Advisory Board meeting minutes documented
- [ ] Pilot shows >30% time savings
- [ ] Legal opinion on liability obtained
- [ ] Adoption dashboard operational

---

## High Risks (Plan)

### Risk 3: Vital Signs Unit Confusion

**Pre-Mortem Scenario:** System stored vitals as unstructured strings ("BP 120/80", "Weight 85") without separating values and units. Led to display errors, dosing errors from weight confusion (lbs vs kg), and inability to trend data.

**Risk Level:** High

**Mitigation Strategy:**

**1. Prevent: Structured Vital Signs Schema**
```python
@dataclass(frozen=True)
class ExtractedVitalSign:
    """Vital sign with separated value and unit for safety."""
    type: VitalSignType  # Enum: BLOOD_PRESSURE, WEIGHT, TEMPERATURE, etc.
    value_numeric: float | tuple[float, float]  # 120.0 or (120.0, 80.0) for BP
    unit: VitalSignUnit  # Enum: MMHG, KG, CELSIUS, BPM, etc.
    value_display: str  # Original text: "120/80 mmHg"
    confidence: float
```

**2. Prevent: Unit Standardisation**
```python
class VitalSignStandardizer:
    """Convert all vitals to standard units for comparison and display."""

    def standardize(self, vital: ExtractedVitalSign) -> ExtractedVitalSign:
        if vital.type == VitalSignType.WEIGHT:
            if vital.unit == VitalSignUnit.POUNDS:
                # Convert lbs to kg
                kg_value = vital.value_numeric * 0.453592
                return replace(vital, value_numeric=kg_value, unit=VitalSignUnit.KG)
        # ... handle other conversions
```

**3. Detect: Plausibility Checking**
- Weight: Flag if <2kg or >300kg
- BP: Flag if systolic <70 or >250
- Temperature: Flag if <30°C or >45°C
- Age-appropriate ranges for pediatrics

**4. Respond: Ambiguous Vital Handling**
- If unit unclear ("Pressure was 120"), flag as ambiguous
- Require clinician clarification
- Don't assume (e.g., don't assume BP if only one number)

**Acceptance Criteria:**
- [ ] All vitals stored with separate value and unit fields
- [ ] Automatic unit conversion to standard units
- [ ] Plausibility checks implemented
- [ ] Ambiguous vitals flagged for review

---

### Risk 4: Medicare Billing "Trap"

**Pre-Mortem Scenario:** Billing suggestions presented alongside clinical verification created implicit endorsement. Clinicians clicked "approve all" without reviewing billing separately. Pattern of upcoding detected - Level D suggested for Level B consults.

**Risk Level:** Critical

**Mitigation Strategy:**

**1. Prevent: Physical and Logical Separation**
```
Clinical Note Tab          Billing Tab (separate)
├─ Extraction Results      ├─ MBS Item Selection
├─ Verification Alerts     ├─ Time Assessment
└─ Sign Note Button        └─ Bill Separately Button

Rule: Cannot access Billing tab until Clinical Note signed
```

**2. Prevent: Explicit Disclaimers**
```python
BILLING_DISCLAIMER = """
⚠️ IMPORTANT: System suggestions are NOT billable time determinations.
You must manually assess consultation complexity and select appropriate MBS item.
Time alone does not determine billing level.
"""
```

**3. Detect: Upcoding Detection**
```python
def detect_upcoding(extracted_complexity: str, selected_mbs_item: str) -> bool:
    """Alert if billing level significantly exceeds extracted complexity."""
    complexity_to_mbs = {
        'low': ['23', '36'],      # Level B or C
        'medium': ['36', '44'],   # Level C or D
        'high': ['44'],           # Level D only
    }

    appropriate_items = complexity_to_mbs.get(extracted_complexity, [])
    if selected_mbs_item not in appropriate_items:
        return True  # Potential upcoding
    return False
```

**4. Respond: Separate Audit Trail**
- Clinical decisions logged separately from billing decisions
- Billing audit trail includes explicit confirmation of manual selection
- Monthly review of billing patterns

**Acceptance Criteria:**
- [ ] Billing interface physically separate from clinical interface
- [ ] Clinical note must be signed before billing accessible
- [ ] Upcoding detection alerts implemented
- [ ] Separate audit trail for billing decisions
- [ ] Mandatory compliance training before billing feature use

---

### Risk 5: LLM Cost/Quality Unsustainable

**Pre-Mortem Scenario:** GPT-4 costs $0.05/note × 1000/day = $18K/year per practice. Quality degrades when switching to cheaper model.

**Risk Level:** High

**Mitigation Strategy:**

**1. Prevent: Cost Modeling Before Launch**
```
Cost Model:
- Extraction cost: $0.01-0.05 per note
- Daily volume: 1000 notes
- Annual cost: $3,650 - $18,250 per practice
- Target: < $5,000/year per practice

Optimization:
- Cache common patterns: 30% reduction
- Token-efficient prompts: 20% reduction
- Australian provider (potentially cheaper): TBD
```

**2. Prevent: Multi-Provider Strategy**
- Primary: GPT-4 (highest quality)
- Fallback: Azure OpenAI (Australian, potentially cheaper)
- Emergency: Rule-based extraction (lower quality but free)

**3. Detect: Cost Monitoring**
- Daily cost dashboard
- Alert at 150% of budget
- Hard stop at 200% of budget
- Per-practice cost tracking

**4. Respond: Cost Reduction Plan**
- Aggressive caching implementation
- Prompt optimization
- Negotiate enterprise rates
- Switch to cheaper model for low-risk fields

**Acceptance Criteria:**
- [ ] Cost model validated with pilot data
- [ ] Fallback provider tested and ready
- [ ] Cost monitoring dashboard live
- [ ] Cost reduction plan documented

---

### Risk 4: Integration Complexity

**Pre-Mortem Scenario:** Best Practice API changes break integration, MedicalDirector updates incompatible, constant firefighting.

**Risk Level:** High

**Mitigation Strategy:**

**1. Prevent: Abstraction Layer**
```python
class EMRAdapter(ABC):
    """Abstract EMR integration."""

    @abstractmethod
    def get_patient(self, patient_id: str) -> PatientProfile:
        pass

    @abstractmethod
    def create_clinical_note(self, note: ClinicalNote) -> str:
        pass

class BestPracticeAdapter(EMRAdapter):
    """Best Practice specific implementation."""
    pass

class MedicalDirectorAdapter(EMRAdapter):
    """MedicalDirector specific implementation."""
    pass
```

**2. Prevent: Vendor Partnerships**
- Formal partnership agreements with Best Practice, MedicalDirector
- Change notification clauses in contracts
- Beta testing program for updates
- Dedicated liaison at each vendor

**3. Detect: Integration Health Monitoring**
- Automated integration tests run every hour
- Alert on API failures or schema changes
- Version compatibility matrix
- Sandbox environment testing

**4. Respond: Graceful Degradation**
- If EMR integration fails: Queue for retry, notify user
- Manual export option (CSV, PDF)
- Fallback to copy-paste workflow
- Emergency offline mode

**Acceptance Criteria:**
- [ ] Abstraction layer implemented
- [ ] Partnership agreements signed
- [ ] Integration health monitoring operational
- [ ] Graceful degradation tested

---

### Risk 5: PII/Privacy Breach

**Pre-Mortem Scenario:** Medicare number in dictation not detected, stored in database, appears in logs, privacy breach discovered.

**Risk Level:** Critical

**Mitigation Strategy:**

**1. Prevent: Defence in Depth**
```
Layer 1: Input validation - Scan transcript before processing
Layer 2: Extraction time - LLM instructed to redact PII
Layer 3: Storage - Automatic redaction before database write
Layer 4: Logs - Never log PII (use hashes)
Layer 5: Access controls - Strict need-to-know
```

**2. Prevent: Multiple Detection Methods**
- Regex patterns for common formats
- ML-based PII detection
- Heuristic detection (e.g., "Medicare" + 10 digits)
- Manual review queue for uncertain cases

**3. Detect: Continuous PII Scanning**
- Weekly automated scan of database for PII
- Alert on any detection
- Quarterly manual audit
- Penetration testing includes PII detection

**4. Respond: Breach Response Plan**
- 24-hour containment target
- OAIC notification within 72 hours
- Patient notification plan
- Post-incident review within 1 week

**Acceptance Criteria:**
- [ ] All 5 defence layers implemented
- [ ] PII detection validated with test data
- [ ] Continuous scanning operational
- [ ] Breach response plan tested

---

## Medium Risks (Monitor)

### Risk 6: Alert Fatigue

**Pre-Mortem Scenario:** Too many alerts, clinicians ignore all, critical safety alerts missed.

**Mitigation Strategy:**

**1. Prevent: Tiered Alerting**
```python
ALERT_LEVELS = {
    'CRITICAL': {
        'action': 'BLOCK_SIGN_OFF',
        'notification': 'PROMINENT',
        'sound': True,
    },
    'HIGH': {
        'action': 'REQUIRE_ACKNOWLEDGMENT',
        'notification': 'HIGHLIGHT',
        'sound': False,
    },
    'MEDIUM': {
        'action': 'FLAG_FOR_REVIEW',
        'notification': 'WARNING_ICON',
        'sound': False,
    },
    'LOW': {
        'action': 'INFORMATIONAL',
        'notification': 'COLLAPSIBLE',
        'sound': False,
    },
}
```

**2. Detect: Alert Response Metrics**
- Track time to acknowledge by severity
- Alert if critical alerts ignored >5 minutes
- Monthly review of alert effectiveness
- User feedback on alert usefulness

**3. Respond: Alert Tuning**
- Monthly alert review meeting
- Adjust thresholds based on feedback
- Remove ineffective alerts
- Consolidate related alerts

---

### Risk 7: Workflow Friction

**Pre-Mortem Scenario:** Context switching kills flow, separate window, buried menu item, feels like two systems.

**Mitigation Strategy:**

**1. Prevent: Deep Integration**
- Embed in EMR window (iframe or native component)
- Single sign-on (no separate login)
- Dictation button prominently placed
- Keyboard shortcuts

**2. Detect: Workflow Metrics**
- Time from dictate to review completion
- Number of clicks per extraction
- Context switches required
- User flow analysis (hotjar/mixpanel)

**3. Respond: UX Improvement Sprints**
- Monthly usability testing
- Clinician shadowing sessions
- Rapid iteration on friction points
- A/B testing for critical flows

---

### Risk 8: Support Overwhelm

**Pre-Mortem Scenario:** Tickets flood in, no dedicated team, engineers doing support, >48hr response times.

**Mitigation Strategy:**

**1. Prevent: Self-Service Resources**
- Comprehensive knowledge base
- In-app help and tooltips
- Video tutorials
- FAQ based on pilot questions

**2. Prevent: Proactive Support**
- Monitor for common errors
- Reach out before users complain
- Weekly tips email
- Office hours for Q&A

**3. Detect: Support Load Metrics**
- Tickets per day per 100 users
- Time to resolution
- Escalation rate
- User satisfaction with support

**4. Respond: Support Scaling**
- Tier 1: Documentation + chatbot
- Tier 2: Email support (24hr SLA)
- Tier 3: Phone support (business hours)
- Tier 4: Engineering escalation

---

## Risk Monitoring Dashboard

### Key Risk Indicators (KRIs)

| Risk | KRI | Yellow Threshold | Red Threshold |
|------|-----|------------------|---------------|
| Patient Harm | Medication errors/week | >0 | >1 |
| Adoption | Daily active users | <50% | <30% |
| Cost | Monthly spend | >150% budget | >200% budget |
| Privacy | PII detection events | >0 | >1 |
| Performance | Latency p95 | >10s | >15s |
| Quality | Extraction accuracy | <85% | <80% |

### Review Cadence

**Weekly:**
- Technical metrics (latency, errors, costs)
- Support ticket trends
- Adoption metrics

**Monthly:**
- Risk mitigation effectiveness
- New risks identification
- Mitigation plan updates

**Quarterly:**
- Full risk register review
- External risk assessment
- Board risk reporting

---

## Decision Gates

### Go/No-Go Criteria

**Alpha Gate (Month 3):**
- [ ] Extraction accuracy >85% on test set
- [ ] Zero safety-critical auto-populations
- [ ] Latency p95 <10 seconds
- [ ] Clinical Advisory Board approval

**Beta Gate (Month 6):**
- [ ] Extraction accuracy >90%
- [ ] User satisfaction >3.5/5
- [ ] Adoption >50% in pilot practices
- [ ] Zero critical incidents

**GA Gate (Month 12):**
- [ ] Extraction accuracy >95%
- [ ] User satisfaction >4.0/5
- [ ] Adoption >70% target market
- [ ] Sustainable unit economics

### Emergency Stop Criteria

**Immediate Halt:**
- Patient safety incident
- Privacy breach
- Regulatory violation
- System compromise

**Pause and Fix:**
- Extraction accuracy drops >10%
- Adoption drops below 30%
- Cost exceeds 200% budget
- Critical vendor failure

---

## Summary

**Critical Controls (Must Have):**
1. Never auto-populate medication changes
2. Hallucination detection for medications
3. Clinical co-design process
4. Defence in depth for PII
5. Abstraction layer for EMR integration

**Monitoring (Watch Closely):**
- Medication extraction accuracy
- User adoption rates
- Cost per extraction
- PII detection events
- Alert response rates

**Response Plans (Be Ready):**
- Patient safety incident response
- Privacy breach notification
- Cost overrun mitigation
- Adoption recovery plan

---

*Remember: Risk management is continuous. Review this document monthly and update as we learn.*
