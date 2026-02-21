# Voice Data Compliance: Privacy and Security Requirements

**For:** Compliance, Legal, Security, Engineering
**Purpose:** Ensure Privacy Act compliance and data security for voice transcription system
**Context:** Australian Healthcare System
**Classification:** CONFIDENTIAL - Contains PHI Handling Procedures

---

## Executive Summary

This document defines compliance requirements for handling personal information (including health information) in voice transcription workflows under Australian law. Our architecture minimises risk by:

1. **Not storing audio recordings** (third-party processes and deletes)
2. **Storing transcripts with medical record-grade security**
3. **Automatic identifier detection and redaction** (Medicare, DVA numbers)
4. **Comprehensive audit logging**
5. **Australian data sovereignty** (Sydney data centres)

**Key Principle:** *We collect and store only what is necessary, protect what we store, and delete what we don't need. All data stays in Australia.*

---

## Regulatory Framework

### Primary Legislation

| Act | Jurisdiction | Key Requirements |
|-----|--------------|------------------|
| **Privacy Act 1988 (Cth)** | Federal | Australian Privacy Principles (APPs) |
| **My Health Records Act 2012** | Federal | Healthcare identifier, record system |
| **State Health Records Acts** | State | Health information handling |
| **Healthcare Identifiers Act 2010** | Federal | HI Service usage |

### Australian Privacy Principles (APPs)

**Applicable APPs:**
- **APP 1:** Open and transparent management
- **APP 3:** Collection of solicited personal information
- **APP 5:** Notification of collection
- **APP 6:** Use or disclosure
- **APP 11:** Security of personal information
- **APP 12:** Access to personal information
- **APP 13:** Correction of personal information

---

## Data Classification

### Personal Information (Health Information)

**Present in Voice Transcription:**
- Patient names and demographics
- Healthcare identifiers (IHI)
- Dates of service
- Clinical information (diagnoses, medications, procedures)
- Provider names and credentials

**May Be Present (Accidental):**
- Medicare/DVA numbers
- Private health insurance membership numbers
- Phone numbers and addresses
- Drivers licence numbers

### Data Sensitivity Levels

| Level | Data | Handling |
|-------|------|----------|
| **Critical** | Medicare/DVA numbers, IHIs | Immediate redaction, alert |
| **High** | Transcripts, extractions | Encryption at rest/transit, access controls |
| **Medium** | Audit logs, confidence scores | Encryption at rest, limited access |
| **Low** | Aggregated metrics, non-PII | Standard security |

---

## Data Sovereignty

### Requirement
All patient data must remain within Australia.

### Implementation
- AWS Sydney Region (ap-southeast-2) only
- No data transfer offshore
- Third-party services must use Australian infrastructure
- No CDN that caches content overseas

### Verification
- Regular infrastructure audits
- Network traffic monitoring
- Vendor attestation letters
- Contract clauses prohibiting offshore processing

---

## Technical Safeguards (APP 11)

### 1. Access Control

**Requirements:**
- Unique user IDs for all system access
- Role-based access control (RBAC)
- Automatic logoff after inactivity
- Emergency access procedures

**Implementation:**
```
Authentication: PKI certificates (NASH) or SSO via practice systems
Authorisation: Role-based (GP, Specialist, Nurse, Admin, Auditor)
Session Timeout: 15 minutes of inactivity
Emergency Access: Break-glass procedures documented
Multi-Factor Authentication: Required for all access
```

### 2. Audit Controls

**Required Logging:**
| Event | Data Logged | Retention |
|-------|-------------|-----------|
| Transcript received | Timestamp, IHI (hashed), user ID | 7 years |
| Extraction completed | Extraction ID, confidence scores, processing time | 7 years |
| Clinician review | User ID, timestamp, fields modified | 7 years |
| Data export to EMR | Timestamp, IHI, fields exported | 7 years |
| My Health Record upload | Timestamp, document type, success/failure | 7 years |
| Access denied | Timestamp, user ID, attempted action | 7 years |

**Log Protection:**
- Append-only logs
- Encrypted at rest
- Separate from application logs
- Regular integrity checks
- Tamper-evident logging

### 3. Integrity

**Measures:**
- Checksums for all stored transcripts
- Immutable audit logs
- Version control for extraction algorithms
- Data validation on EMR write
- Blockchain or Merkle tree for critical records (optional)

### 4. Transmission Security

**Requirements:**
- TLS 1.3 for all data in transit
- Certificate pinning for third-party APIs
- VPN or private connectivity where possible
- No unencrypted transmission over public networks

**Data Flows:**
```
Clinician Device → Load Balancer [TLS] → Application Server [TLS] → Third-Party API
Application Server → Database [TLS/encrypted connection]
Application Server → Medical Software API [TLS + PKI]
Application Server → HI Service [TLS + NASH certificate]
```

---

## Third-Party Compliance

### Vendor Requirements

**Required from All Vendors:**
- Privacy Act compliance attestation
- Data processing agreement (Australian law)
- Data sovereignty guarantee
- Breach notification within 24 hours
- No subprocessors without approval

### AWS Transcribe Medical (or equivalent)

**Specific Requirements:**
| Requirement | Verification |
|-------------|--------------|
| Australian data centres only | Contract terms |
| ISO 27001 certification | Annual report review |
| IRAP (Information Security Registered Assessors Program) | Certification |
| Encryption at rest | Architecture review |
| Encryption in transit | Certificate validation |
| Data retention/deletion | Contract terms |

### Medical Practice Software Vendors

**Integration Partners:**
- Best Practice Software
- MedicalDirector
- Genie Solutions
- Others as needed

**Requirements:**
- Secure API access
- Audit logging of data exchange
- Privacy compliance attestation
- Data minimisation in integration

---

## Identifier Detection and Redaction

### Automatic Detection

**Patterns Detected:**
| Pattern | Regex | Action |
|---------|-------|--------|
| Medicare Number | `\b\d{10}\b` or `\d{4}\s?\d{5}\s?\d` | Redact + Alert |
| DVA Number | `\b[NX]\d{7}\b` or `\bQX\d{6}\b` | Redact + Alert |
| IHI (Individual Healthcare Identifier) | `\b8\d{15}\b` | Redact + Alert |
| Phone (Australian) | `\b\(?(0[2-9]\d{1}\)?[ \-]?\d{4}[ \-]?\d{4})\b` | Redact |
| DOB | Context-dependent | Flag for review |

**Detection Implementation:**
```
1. Real-time scanning during extraction
2. Replace match with [REDACTED-MEDICARE], [REDACTED-DVA], etc.
3. Log detection (without exposing value)
4. Alert clinician in review interface
5. Include in compliance dashboard
6. Never store unredacted identifiers
```

### Alert Thresholds

| Detection | Alert To | Response Time |
|-----------|----------|---------------|
| Medicare/DVA number | Privacy Officer + Clinician | Immediate |
| IHI in unexpected location | Privacy Officer + Clinician | Immediate |
| Other identifiers | Clinician only | Before sign-off |

---

## My Health Record Compliance

### Healthcare Provider Organisation (HPO) Obligations

**Under My Health Records Act 2012:**

1. **Registration**
   - HPI-O (Healthcare Provider Identifier - Organisation)
   - Seed organisation registered with HI Service
   - Individual practitioners linked to HPO

2. **Access Controls**
   - Only authorised representatives access My Health Record
   - Access limited to "need to know" for treatment
   - Emergency access procedures documented

3. **Data Quality**
   - Accurate and up-to-date information
   - Correction procedures for errors
   - Regular data quality audits

4. **Security**
   - Comply with My Health Record Security Requirements
   - Report security breaches to System Operator
   - Regular security assessments

### Prohibited Conduct

**Never:**
- Access records without patient consent (except emergency)
- Upload information patient has requested not be included
- Delete information without authorisation
- Use information for non-healthcare purposes
- Disclose information to unauthorised parties

**Penalties:**
- Civil penalties: Up to $315,000 for individuals, $1.575M for bodies corporate
- Criminal penalties for intentional misuse

---

## Data Retention and Disposal

### Retention Schedule

| Data Type | Retention Period | Rationale |
|-----------|------------------|-----------|
| Transcripts | 7+ years | Match medical record retention (state laws) |
| Extractions | 7+ years | Clinical record completeness |
| Audit logs | 7 years | Privacy Act / My Health Record requirements |
| Failed extractions | 90 days | Quality improvement |
| System logs | 90 days | Debugging (identifiers redacted) |
| Identifier detection alerts | 7 years | Compliance audit trail |
| My Health Record access logs | 7 years | Legislative requirement |

### Disposal Procedures

**Secure Deletion:**
- Cryptographic erasure for encrypted data
- Overwriting for unencrypted storage (DoD 5220.22-M standard)
- Certificate of destruction for hardware
- Witnessed destruction for high-sensitivity data

**Disposal Triggers:**
- Retention period expired
- Patient request (per Privacy Act)
- System decommissioning
- Change of practice ownership

---

## Breach Response Plan

### Privacy Act Notifiable Data Breaches (NDB) Scheme

**Notification Required When:**
1. Unauthorised access or disclosure occurs
2. Likely to result in serious harm
3. Not remedied by notification time

**Timeline:**
| Timeframe | Action | Responsible Party |
|-----------|--------|-------------------|
| Immediate | Contain breach, assess scope | Security Team |
| Within 30 days | Determine if serious harm likely | Privacy Officer |
| If NDB triggered | Notify OAIC and individuals | Privacy Officer |
| Ongoing | Document all actions | Privacy Officer |

### Serious Harm Assessment

**Factors:**
- Sensitivity of information
- Security measures protecting data
- Likelihood of misuse
- Nature of potential harm (financial, physical, psychological, reputational)

### My Health Record Breach

**Additional Requirements:**
- Notify System Operator within 24 hours
- Follow My Health Record breach protocol
- Potential de-registration for serious breaches

---

## Patient Rights (Privacy Act)

### Access (APP 12)

**Implementation:**
- Transcripts accessible via existing patient access processes
- 30-day response time (Privacy Act requirement)
- Electronic or physical format provided
- Fee may be charged (reasonable cost of retrieval)

### Correction (APP 13)

**Process:**
1. Patient requests correction
2. Assess accuracy within 30 days
3. If accurate: No change, provide statement of disagreement
4. If inaccurate: Correct and notify
5. Notify third parties who received information

### Complaints

**Process:**
1. Internal complaint to Privacy Officer
2. 30 days to respond
3. If unresolved: Patient may complain to OAIC (Office of Australian Information Commissioner)
4. OAIC investigation and determination

---

## Compliance Monitoring

### Automated Checks

| Check | Frequency | Owner |
|-------|-----------|-------|
| Encryption status | Continuous | Infrastructure |
| Access log review | Daily | Security |
| Failed authentication | Daily | Security |
| Identifier detection alerts | Real-time | Compliance |
| Data sovereignty | Weekly | Infrastructure |
| Retention compliance | Monthly | Data Governance |

### Audit Program

**Annual Activities:**
- Comprehensive privacy risk assessment
- Vendor security reviews
- Policy and procedure review
- Workforce training verification
- Penetration testing (IRAP or equivalent)
- Tabletop breach exercise

**Quarterly Activities:**
- Access certification reviews
- Log analysis reports
- Incident trend analysis
- My Health Record compliance review

---

## Training Requirements

### Workforce Training

**Required:**
- Privacy Act and APPs (annual)
- My Health Record obligations (annual)
- Voice transcription system (initial + updates)
- Identifier handling procedures
- Breach reporting

**Documentation:**
- Training completion records
- Competency assessments
- Remedial training for violations

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-21 | Compliance Team | Initial draft - Australian context |

**Review Cycle:** Annual
**Next Review:** 2027-02-21
**Approved By:** Chief Privacy Officer, Chief Information Security Officer
**Legislative Context:** Privacy Act 1988, My Health Records Act 2012

---

## Appendix

- [COMPLIANCE_CHECKLIST.md](COMPLIANCE_CHECKLIST.md) - Implementation checklist
- Privacy Impact Assessment (PIA) - Separate document
- Data Breach Response Plan - Separate document
- My Health Record Policies - Reference existing HPO policies
