# Pre-Mortem: Voice Transcription Extraction System

**Date:** 2026-02-21
**Purpose:** Identify failure modes before they happen
**Approach:** Imagine the project has failed spectacularly. What went wrong?

---

## The Scenario

*It's 12 months from now. The Voice Transcription Extraction system has been abandoned. Clinicians refuse to use it. The organisation has lost $X and significant reputation. The project is considered a cautionary tale. What happened?*

---

## Built-in Defences (What's Already Protected)

**Before diving into failures, we acknowledge these protections are already in place:**

### 1. Phonetic Hallucination Detection
- **Defence:** Every extraction includes `raw_text` field showing exactly what was in transcript
- **Benefit:** Clinicians can verify AI didn't invent information
- **Location:** `llm_parser.py` prompt requires raw_text for every extraction

### 2. Alert Fatigue Prevention
- **Defence:** Three-tier confidence model (>95% auto, 70-95% warning, <70% manual)
- **Benefit:** Prevents "wall of warnings" that clinicians ignore
- **Location:** Confidence scoring framework in extraction layer

### 3. Data Sovereignty Awareness
- **Defence:** Explicit "Sydney Gap" identified - US endpoints marked as research-only
- **Benefit:** Prevents accidental PII leakage to offshore servers
- **Location:** Design docs specify Azure OpenAI Sydney for production

---

## Technical Failures

### 1. Extraction Accuracy Was Terrible

**What went wrong:**
- LLM hallucinated medications that weren't mentioned
- **Vital signs extracted with wrong units** (e.g., "120" interpreted as HR instead of BP, lbs vs kg confusion)
- Temporal expressions resolved to completely wrong dates
- Medication names misheard and extracted as wrong drugs
- Dosages parsed incorrectly (e.g., "10 mg" vs "100 mg")
- **Unit conversion errors:** System showed "85 kg" when clinician said "187 lbs"
- **Ambiguous vitals:** "Pressure was 120" - systolic only or complete BP?

**Special Case - Vital Signs Unit Confusion (Critical Gap):**
The system stored vitals as unstructured strings (`"BP 120/80"`, `"Weight 85"`) without separating numeric values from units. This led to:
- Display errors in EMR (showing lbs as kg)
- Pediatric dosing errors from weight confusion
- Trend analysis failures (can't compare 85 kg vs 187 lbs)

**Impact:**
- Clinicians lost trust immediately
- Safety incidents from wrong medication extractions
- More time spent correcting errors than saved
- System abandoned after 2 months

**Root Causes:**
- Insufficient training data from real Australian clinical dictation
- LLM not fine-tuned for medical terminology
- Didn't validate extraction accuracy before clinical deployment
- Relied too heavily on LLM without proper verification layer

**Prevention:**
- Extensive testing with real (de-identified) clinical notes before launch
- Confidence thresholds too aggressive - need clinical validation
- Implement "uncertainty detection" - flag ambiguous mentions
- Start with high-confidence extractions only, expand gradually

### 2. Latency Killed User Experience

**What went wrong:**
- LLM API calls took [X] seconds per extraction (unacceptable delay)
- Clinicians had to wait too long for results
- Interface felt sluggish and unresponsive
- Peak times caused queue backups ([X] second waits)

**Impact:**
- Clinicians gave up and went back to manual entry
- "Faster to just type it myself"
- Negative word-of-mouth spread quickly

**Root Causes:**
- Didn't test under realistic load
- No caching strategy
- Didn't optimise prompts for token efficiency
- Chose wrong LLM provider (too slow)

**Prevention:**
- Set strict SLAs (<5 seconds p95) and test rigorously
- Implement smart caching (similar dictations → similar extractions)
- Progressive loading (show partial results as they arrive)
- Consider async processing for non-critical fields

### 3. Integration Was a Nightmare

**What went wrong:**
- Best Practice API kept changing
- MedicalDirector integration broke every update
- My Health Record HI Service authentication was flaky
- Data sync issues corrupted patient records
- Version mismatches between systems

**Impact:**
- Constant firefighting
- Clinicians blamed our system for EMR problems
- Support overwhelmed with integration issues
- Had to hire 3 full-time integration engineers

**Root Causes:**
- Underestimated EMR integration complexity
- Didn't build abstraction layer for EMR differences
- No automated testing of integrations
- Didn't establish vendor relationships early

**Prevention:**
- Build robust abstraction layer (Domain Wrapper pattern)
- Extensive integration testing with sandbox environments
- Vendor partnership agreements with change notification
- Graceful degradation when EMR unavailable

### 4. LLM Costs Spiralled Out of Control

**What went wrong:**
- LLM extraction cost $[X] per note (more than budgeted)
- [X] notes/day = $[X]/day = $[X]/year for one practice (unsustainable)
- Didn't account for retry costs on failures
- No cost monitoring or limits
- Bills shocked finance team

**Impact:**
- Project deemed too expensive
- Had to switch to cheaper (worse) model mid-flight
- Extraction quality dropped
- Lost clinical credibility

**Root Causes:**
- Didn't model costs at scale
- No cost optimization strategy
- Didn't consider Australian LLM providers
- Prompts were token-inefficient

**Prevention:**
- Cost modeling before launch (extractions × cost × practices)
- Implement token-efficient prompts
- Cache common patterns aggressively
- Budget alerts and hard limits
- Evaluate Australian providers early

---

## Clinical Safety Failures

### 5. Wrong Medication Extracted → Patient Harm

**What went wrong:**
- System extracted "Metformin" when clinician said "Metoprolol"
- High confidence score (0.95) so auto-populated
- Clinician didn't notice in review (too many extractions)
- Wrong medication entered into record
- Patient received wrong drug

**Impact:**
- Sentinel event investigation
- AHPRA notification required
- Media coverage: "AI Medical System Causes Patient Harm"
- Regulatory scrutiny
- Project halted pending investigation
- Organisation reputation damaged
- Clinicians refuse to use any AI tools

**Root Causes:**
- Over-reliance on confidence scores
- Alert fatigue - too many warnings ignored
- UI made it too easy to approve without review
- Didn't implement "safety-critical" override requirements
- No independent verification for medication changes

**Prevention:**
- Never auto-populate medication changes without explicit confirmation
- Separate workflow for high-risk extractions
- Require re-authentication for medication changes
- Independent pharmacist review layer (optional but recommended)
- "Do not harm" principle: When in doubt, require manual entry

### 6. Missed Protocol Trigger → Compliance Violation

**What went wrong:**
- ED physician mentioned "suspected sepsis" in dictation
- System didn't recognise it as protocol trigger (low confidence)
- No sepsis bundle alert generated
- Hospital missed sepsis protocol compliance
- Accreditation audit found violation

**Impact:**
- Hospital lost accreditation points
- Public report of non-compliance
- Clinical governance investigation
- System blamed for oversight
- Mandatory removal of AI assistance in ED

**Root Causes:**
- Protocol trigger detection not sensitive enough
- Didn't weight recall over precision for safety-critical items
- Didn't test with real sepsis cases
- Didn't integrate with hospital's existing protocol systems

**Prevention:**
- High sensitivity (not specificity) for protocol triggers
- Mandatory checklist for high-risk presentations
- Integration with existing hospital protocols
- Regular validation against real cases
- Alert escalation when protocol triggers missed

### 7. PII Leaked Through System

**What went wrong:**
- Clinician accidentally included Medicare number in dictation
- System didn't detect it (regex missed format variation)
- Extracted and stored in database
- Medicare number appeared in audit logs
- Privacy breach discovered during security audit

**Impact:**
- Notifiable Data Breach (NDB) to OAIC
- Mandatory patient notification
- Media coverage of privacy breach
- Fines under Privacy Act
- Loss of trust in digital health initiatives
- My Health Record participation questioned

**Root Causes:**
- PII detection not robust enough
- Didn't use multiple detection methods
- Insufficient testing with PII-containing transcripts
- Logs weren't redacted properly
- Didn't implement defence in depth

**Prevention:**
- Multiple PII detection layers (regex + ML + manual review)
- Automatic redaction in all storage
- No PII in logs (use hashes only)
- Regular PII scanning of database
- Privacy by design from day one

---

## Adoption & User Experience Failures

### 8. Clinicians Refused to Adopt

**What went wrong:**
- "It's faster to just type"
- Don't trust AI with clinical decisions
- Worried about liability if system makes mistakes
- Too many false alerts
- Interface felt clunky and medical-software-ish
- No perceived benefit

**Impact:**
- <10% adoption rate after 6 months
- Project deemed failure
- ROI never achieved
- Investment written off

**Root Causes:**
- Didn't involve clinicians in design
- Built what engineers thought was cool, not what clinicians needed
- Didn't demonstrate time savings convincingly
- Didn't address liability concerns
- Change management was afterthought
- No clinical champions engaged early

**Prevention:**
- Clinical co-design from day one
- RACGP/College consultation
- Start with clinical champions
- Demonstrate value with pilot data
- Address medicolegal concerns upfront
- Make it optional, prove value, let adoption happen organically

### 9. Alert Fatigue Made System Dangerous

**What went wrong:**
- Too many alerts for minor issues
- Clinicians started ignoring all alerts
- Critical safety alerts buried in noise
- "Click through without reading" culture developed
- Verification layer became meaningless

**Impact:**
- Safety incidents from ignored alerts
- Clinicians turned off safety features
- System became liability rather than asset
- Compliance team shut it down

**Root Causes:**
- Didn't prioritise alerts by severity
- Alert thresholds too sensitive
- Didn't differentiate critical vs informational
- No alert fatigue monitoring

**Prevention:**
- Tiered alerting (Critical/High/Medium/Low)
- Suppress informational alerts after initial learning period
- Monitor alert response rates
- Regular review of alert effectiveness
- Make critical alerts blocking, informational collapsible

### 10. Workflow Integration Was Awkward

**What went wrong:**
- Had to switch between EMR and our system
- Context switching killed flow
- Dictation button buried in menu
- Results appeared in separate window
- "Feels like two different systems"

**Impact:**
- Workflow friction exceeded time savings
- Clinicians abandoned after trial period
- "Adds more friction than it removes"

**Root Causes:**
- Didn't embed deeply enough in EMR
- iframe integration was clunky
- Didn't match existing workflow patterns
- No single sign-on

**Prevention:**
- Deep EMR integration (same window, same login)
- Embedded UI components, not separate application
- Match existing dictation workflows
- Minimise context switching
- Pilot with workflow observation studies

---

## Compliance & Legal Failures

### 11. My Health Record Compliance Violation (The "Consent Bypass")

**What went wrong:**
- System automatically prepared Event Summary for upload after clinician signed note
- "Upload to My Health Record" checkbox was pre-checked by default
- Clinician didn't notice the checkbox (buried in UI)
- Patient had previously opted out of specific information sharing
- System uploaded information patient had requested NOT be included in My Health Record
- Patient complained to System Operator
- Investigation revealed systematic consent bypass

**Impact:**
- Civil penalties: Up to $1.575M
- Criminal investigation for My Health Record Act violations
- Hospital/Practice de-registered from My Health Record
- Mandatory removal of all uploaded documents
- Systematic review of all digital health projects organisation-wide
- Reputational damage - "Hospital violated patient privacy with AI system"

**Root Causes:**
- **Critical Design Flaw:** Pre-checked consent checkbox (opt-out vs opt-in)
- Didn't understand My Health Record legislation requires explicit consent
- Automated preparation without verification step
- Consent UI element too small/obscure
- Didn't check patient's existing My Health Record preferences
- Lack of legal review of consent workflow
- No "consent state" validation in upload pipeline

**Prevention:**
- **EXPLICIT CONSENT REQUIRED:** Upload checkbox MUST be unchecked by default
- **CONSENT STATE VALIDATION:** Hard-coded check - block transmission unless `consent=True` explicitly set
- **PATIENT PREFERENCE CHECK:** Query My Health Record for patient's existing restrictions before upload
- **SEPARATE WORKFLOW:** Upload preparation as distinct step from clinical documentation
- **AUDIT TRAIL:** Log every consent decision with timestamp and user
- **LEGAL REVIEW:** My Health Record Act compliance audit before launch
- **NEVER AUTOMATE:** Even after consent, require explicit "Upload Now" action

### 12. Medicare Billing Automation Breach (The "Billing Trap")

**What went wrong:**
- System suggested MBS items based on extraction and displayed them prominently
- Auto-populated billing codes in the same interface as clinical documentation
- Clinician just clicked "approve all" without reviewing billing separately
- Pattern of upcoding detected: Level D items (44) suggested for simple Level B (23) consults
- Services Australia investigation revealed systematic over-billing
- Allegations of automated billing fraud and Medicare abuse

**Impact:**
- Medicare audit of all claims from practices using the system
- Potential clawback of $500K+ in rebates
- Criminal investigation for fraud
- AHPRA referral for participating clinicians
- Practice accreditation suspended
- System shut down immediately, all billing flagged for manual review

**Root Causes:**
- **Critical Design Flaw:** Billing suggestions presented alongside clinical verification, creating implicit endorsement
- System made billing suggestions too easy to accept
- Didn't enforce physical and logical separation of clinical vs billing workflows
- "Approve" button applied to both clinical data AND billing codes
- Didn't educate clinicians that suggestions are not billable time determiners

**Prevention:**
- **PHYSICAL SEPARATION:** Billing suggestions in entirely different UI section or screen
- **TEMPORAL SEPARATION:** Clinical note must be signed BEFORE billing interface accessible
- **EXPLICIT DISCLAIMERS:** "System suggestions are NOT billable time determinations"
- **MANUAL BILLING WORKFLOW:** Clinician must actively select MBS item from dropdown
- **AUDIT TRAIL:** Log all billing decisions separately from clinical decisions
- **UPCODING DETECTION:** Alert if billing complexity doesn't match extracted complexity
- **COMPLIANCE TRAINING:** Mandatory module on MBS requirements before system use

### 13. Data Sovereignty Breach

**What went wrong:**
- Using AWS US region for some processing
- CDN cached content overseas
- Third-party analytics sent data offshore
- Privacy Commissioner investigation
- Breach of patient trust

**Impact:**
- Notifiable data breach
- Fines under Privacy Act
- Requirement to destroy all offshore data
- Expensive data migration
- Project delay 6+ months

**Root Causes:**
- Didn't verify all data flows
- Assumed "AWS" meant Australian region
- Third-party services not vetted
- Didn't implement data flow monitoring

**Prevention:**
- Explicit data sovereignty requirements in all contracts
- Network traffic monitoring
- Regular infrastructure audits
- Vendor attestation letters
- "Australia-only" architecture review

---

## Operational Failures

### 14. Support Was Overwhelmed

**What went wrong:**
- Support tickets flooded in after launch
- No dedicated clinical support team
- Engineers doing support
- Response times >48 hours
- Clinicians frustrated, abandoned system

**Impact:**
- Poor user experience
- Negative reviews spread
- Support costs exceeded budget
- Engineering team diverted from development

**Root Causes:**
- Didn't plan for support scale
- Underestimated clinical IT support needs
- No self-service resources
- No tiered support model

**Prevention:**
- Dedicated clinical support team (hire before launch)
- Comprehensive knowledge base
- In-app help and tooltips
- Tier 1: Self-service, Tier 2: Email, Tier 3: Phone
- Proactive monitoring to prevent issues

### 15. Training Was Insufficient

**What went wrong:**
- One-hour training session not enough
- Clinicians didn't understand confidence scores
- Didn't know when to trust vs verify
- Workflow confusion
- "I wasn't trained properly" complaints

**Impact:**
- Low adoption
- High error rates
- Support burden
- Safety incidents from misuse

**Root Causes:**
- Underestimated training needs
- Didn't create role-specific training
- No ongoing education
- Didn't assess competency

**Prevention:**
- Multiple training modalities (video, live, documentation)
- Role-based training paths
- Competency assessment before go-live
- Refresher training quarterly
- Super-user program for peer support

---

## Business & Strategic Failures

### 16. Competitor Launched Better Solution

**What went wrong:**
- Nuance/Microsoft launched integrated solution
- Already integrated with major EMRs
- Better accuracy from day one
- Cheaper due to scale
- Our solution became redundant

**Impact:**
- Lost first-mover advantage
- Couldn't compete on price or features
- Investment stranded
- Had to pivot or shut down

**Root Causes:**
- Didn't monitor competitive landscape
- Took too long to market
- Didn't establish moat (proprietary data, integrations)
- Underestimated big tech competition

**Prevention:**
- Regular competitive analysis
- Speed to market prioritised
- Focus on unique value (Australian compliance, verification layer)
- Partnerships to create barriers to entry

### 17. Business Case Was Wrong

**What went wrong:**
- Time savings never materialised
- Clinicians spent more time reviewing than typing
- Integration costs exceeded projections
- Support costs not factored
- ROI negative after 12 months

**Impact:**
- Project defunded
- Team disbanded
- Reputational damage to digital health initiatives

**Root Causes:**
- Optimistic assumptions
- Didn't pilot long enough
- Didn't measure actual vs projected benefits
- Hidden costs not identified

**Prevention:**
- Conservative assumptions in business case
- Pilot with rigorous measurement
- Track actual time savings
- Full cost accounting (integration, support, training)
- Go/No-Go decision gates with real data

---

## External Dependency Failures

### 18. Transcription Service Shut Down

**What went wrong:**
- AWS Transcribe Medical discontinued service
- No migration plan
- Sudden loss of transcription capability
- System completely broken

**Impact:**
- Emergency migration to alternative
- 2-week outage
- Data loss during migration
- Clinicians lost trust

**Root Causes:**
- Single vendor dependency
- No contract continuity requirements
- Didn't monitor vendor health
- No abstraction layer for transcription

**Prevention:**
- Multi-vendor strategy
- Abstraction layer for transcription services
- Contract with migration assistance clause
- Regular vendor risk assessment
- Local backup transcription option

### 19. LLM Provider Changed Terms

**What went wrong:**
- OpenAI changed API pricing 300%
- New terms prohibited healthcare use
- Forced to migrate to different provider
- Extraction quality degraded with new model

**Impact:**
- Costs unsustainable
- Legal risk under new terms
- Quality regression
- User complaints about accuracy

**Root Causes:**
- Single LLM provider
- Didn't negotiate healthcare-specific terms
- No fallback provider qualified
- Didn't monitor terms of service changes

**Prevention:**
- Multi-provider strategy
- Healthcare-specific agreements
- Local model fallback (even if lower quality)
- Regular legal review of provider terms
- Portable prompt engineering

### 20. Regulatory Changes Banned AI in Clinical Notes

**What went wrong:**
- New AHPRA guidance prohibited AI-generated clinical content
- System deemed non-compliant
- Had to shut down immediately
- Existing notes required review

**Impact:**
- Immediate shutdown
- Cost of compliance review
- Potential legal exposure for existing notes
- Project failure

**Root Causes:**
- Didn't engage with regulator early
- Didn't establish human-in-the-loop clearly
- No regulatory monitoring
- Didn't contribute to standards development

**Prevention:**
- Engage AHPRA early in development
- Clear documentation of human oversight
- Conservative interpretation of regulations
- Contribute to industry standards
- Flexible architecture to adapt to regulation changes

---

## Summary: Top 5 Critical Risks

| Rank | Risk | Likelihood | Impact | Prevention Priority |
|------|------|-----------|--------|-------------------|
| 1 | Wrong medication extraction → patient harm | Medium | Critical | Safety-critical workflow, never auto-populate meds |
| 2 | Clinician refusal to adopt | High | Critical | Clinical co-design, prove value, optional adoption |
| 3 | LLM cost/quality unsustainable | Medium | High | Cost modeling, Australian provider evaluation |
| 4 | PII/privacy breach | Low | Critical | Defence in depth, privacy by design |
| 5 | Integration complexity | High | High | Abstraction layer, vendor partnerships |

---

## Mitigation Strategies Summary

### Technical
- Extensive accuracy testing before clinical use
- Strict SLAs with performance monitoring
- Abstraction layers for all integrations
- Cost controls and optimisation

### Safety
- Never auto-populate safety-critical fields
- Blocking alerts for high-risk items
- Independent verification layer
- Conservative confidence thresholds

### Adoption
- Clinical co-design from start
- Optional adoption, prove value
- Change management investment
- Address medicolegal concerns

### Compliance
- Privacy by design
- Legal review of all processes
- Data sovereignty enforcement
- Regular compliance audits

### Operational
- Dedicated clinical support team
- Comprehensive training program
- Self-service resources
- Proactive monitoring

---

*Remember: This document imagines failure to prevent it. Every item here is preventable with proper planning, testing, and risk management.*
