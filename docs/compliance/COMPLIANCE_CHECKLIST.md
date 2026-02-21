# Compliance Checklist

**For:** Privacy Officers, Legal, Compliance Auditors
**Purpose:** Track compliance requirements and implementation status

---

## Privacy Act 1988 Compliance

### APP 1: Open and Transparent Management
- [ ] Privacy policy updated to cover voice transcription
- [ ] Collection notice drafted for clinicians
- [ ] Privacy policy published on website
- [ ] Plain language summary available

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 3: Collection of Solicited Personal Information
- [ ] Collection is reasonably necessary for healthcare functions
- [ ] Audio not stored (only transcripts)
- [ ] Direct collection from clinicians (not third parties)
- [ ] No collection of sensitive information beyond health info

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 5: Notification of Collection
- [ ] Clinicians notified at first use
- [ ] Patients informed via standard privacy notices
- [ ] Purpose of collection clearly stated
- [ ] Access/correction procedures explained

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 6: Use or Disclosure
- [ ] Primary purpose: Healthcare documentation
- [ ] Secondary uses identified and justified
- [ ] No disclosure to third parties without consent
- [ ] Disclosure to transcription service covered by contract

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 11: Security of Personal Information
- [ ] Encryption at rest implemented
- [ ] Encryption in transit (TLS 1.3)
- [ ] Access controls and authentication
- [ ] Regular security assessments scheduled
- [ ] Incident response plan documented

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 12: Access to Personal Information
- [ ] Process defined for patient access requests
- [ ] 30-day response timeframe achievable
- [ ] Format options available (electronic/physical)
- [ ] Fee structure defined

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### APP 13: Correction of Personal Information
- [ ] Process defined for correction requests
- [ ] Mechanism to update extracted data
- [ ] Notification to third parties who received information
- [ ] Documentation of disagreements

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## My Health Records Act 2012 Compliance

### Registration and Participation
- [ ] HPI-O obtained
- [ ] Seed organisation registered
- [ ] Individual practitioners linked to HPO
- [ ] Participation agreement signed

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### System Security
- [ ] Complies with My Health Record Security Requirements
- [ ] Access controls implemented
- [ ] Audit logging enabled
- [ ] Regular security assessments

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Data Quality
- [ ] Accurate information upload procedures
- [ ] Correction processes defined
- [ ] Data validation rules implemented
- [ ] Quality monitoring dashboard

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Prohibited Conduct
- [ ] Training on prohibited conduct delivered
- [ ] Access only for treatment purposes (or authorised purposes)
- [ ] No deletion without authorisation
- [ ] No unauthorised disclosure

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Data Sovereignty

### Infrastructure
- [ ] All data storage in Australia
- [ ] AWS Sydney region (ap-southeast-2) confirmed
- [ ] No CDN that caches overseas
- [ ] Third-party vendors use Australian infrastructure

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Verification
- [ ] Network traffic monitoring implemented
- [ ] Vendor attestation letters obtained
- [ ] Contract clauses prohibiting offshore processing
- [ ] Quarterly infrastructure audits scheduled

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Vendor Compliance

### Transcription Service (AWS Transcribe Medical or equivalent)
- [ ] Data processing agreement signed
- [ ] BAA or equivalent under Australian law
- [ ] Data sovereignty guarantee
- [ ] Security certifications verified (ISO 27001, IRAP)
- [ ] Breach notification procedures defined
- [ ] Subprocessor restrictions in contract

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Clinical Software Vendors
- [ ] Secure API agreements in place
- [ ] Data sharing agreements signed
- [ ] Privacy compliance confirmed

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Security Controls

### Access Control
- [ ] Unique user IDs for all access
- [ ] Role-based access control (RBAC) implemented
- [ ] Multi-factor authentication required
- [ ] Automatic session timeout configured
- [ ] Emergency access procedures documented

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Audit Logging
- [ ] All access logged
- [ ] All extractions logged
- [ ] All modifications logged
- [ ] Logs protected from tampering
- [ ] 7-year retention configured
- [ ] Regular log review process

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Data Protection
- [ ] Encryption at rest (AES-256)
- [ ] Encryption in transit (TLS 1.3)
- [ ] Key management procedures
- [ ] Secure deletion procedures
- [ ] Backup encryption

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## PII/Identifier Detection

### Automatic Detection
- [ ] Medicare number pattern detection
- [ ] DVA number pattern detection
- [ ] IHI pattern detection
- [ ] Phone number detection
- [ ] DOB flagging

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Redaction
- [ ] Automatic redaction in logs
- [ ] Redaction in audit trails
- [ ] Redaction in error messages
- [ ] Alert on detection

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Data Retention

### Retention Schedule
- [ ] Transcripts: 7+ years
- [ ] Audit logs: 7 years
- [ ] Failed extractions: 90 days
- [ ] System logs: 90 days

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Disposal
- [ ] Secure deletion procedures defined
- [ ] Cryptographic erasure for encrypted data
- [ ] Overwriting standards defined (DoD 5220.22-M)
- [ ] Destruction certificates

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Breach Response

### Detection
- [ ] Automated monitoring for breaches
- [ ] Anomaly detection configured
- [ ] User reporting mechanism
- [ ] 24/7 monitoring coverage

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Response Procedures
- [ ] Breach response plan documented
- [ ] Response team identified
- [ ] OAIC notification procedures
- [ ] Individual notification procedures
- [ ] My Health Record notification procedures

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Testing
- [ ] Tabletop exercise conducted
- [ ] Response time targets defined
- [ ] Documentation templates ready

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Documentation

### Policies
- [ ] Privacy policy updated
- [ ] Data retention policy documented
- [ ] Access control policy documented
- [ ] Incident response policy documented
- [ ] Vendor management policy documented

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Procedures
- [ ] Privacy Impact Assessment (PIA) completed
- [ ] Security risk assessment completed
- [ ] Business continuity plan documented
- [ ] Disaster recovery plan documented

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Training

### Workforce Training
- [ ] Privacy Act training delivered
- [ ] My Health Record obligations training
- [ ] System-specific training
- [ ] Security awareness training
- [ ] Completion tracking

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Pre-Launch Checklist

### Technical
- [ ] All security controls implemented
- [ ] Penetration testing completed
- [ ] Vulnerability scan clean
- [ ] Performance testing completed
- [ ] Disaster recovery tested

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Compliance
- [ ] PIA approved
- [ ] Legal review completed
- [ ] Privacy Officer sign-off
- [ ] Security Officer sign-off
- [ ] Clinical governance approval

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

### Documentation
- [ ] All policies approved
- [ ] Procedures documented
- [ ] User guides completed
- [ ] Training materials ready

**Status:** ⬜ Not Started / ⬜ In Progress / ⬜ Complete

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Chief Privacy Officer | | | |
| Chief Information Security Officer | | | |
| Clinical Governance Lead | | | |
| Legal Counsel | | | |
| Product Owner | | | |

---

**Review Cycle:** Quarterly during development, annually post-launch
**Next Review Date:** [Date]
**Document Owner:** Compliance Team
