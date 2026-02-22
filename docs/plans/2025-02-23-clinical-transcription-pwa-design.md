# Clinical Transcription PWA - Design Document

**Date:** 2025-02-23
**Status:** Approved for Implementation
**Scope:** Production system for 5-clinician medical practice
**Timeline:** 6 months
**Target:** Real patient data (Australian compliance)

---

## 1. Executive Summary

A Progressive Web Application (PWA) for clinical voice transcription, designed to run entirely on-premise on a Mac Studio with 128GB RAM. The system enables clinicians to dictate patient notes, transcribes audio using local AI models, verifies extracted data against patient context, and integrates with the existing guardrails verification system.

**Key Design Decisions:**
- **HTMX + FastAPI** over React/Vue/Svelte for maintainability
- **100% on-premise** - all AI models, data, and processing local to Mac Studio
- **Offline-first architecture** - clinicians can record offline, sync when connected
- **Australian compliance** - Privacy Act 1988, AHPRA requirements built-in

---

## 2. Business Requirements

### 2.1 Problem Statement

Clinicians spend 15-20% of their working hours on documentation. Current workflow requires:
- Manual typing or external transcription services
- Context-switching between EMR and documentation tools
- Manual verification of AI-extracted data against patient records

**Target Users:** 5 GPs/specialists in a single practice

### 2.2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Documentation time | 40% reduction | Time from encounter to signed note |
| Transcription accuracy | >95% | Verified against EMR context |
| System uptime | 99.5% | Excluding scheduled maintenance |
| User adoption | >80% | Clinicians using system daily |
| Data breach incidents | Zero | Security audit results |

### 2.3 Constraints

- **Single maintainer** - architecture must be supportable by one person
- **Real patient data** - Australian Privacy Act compliance required
- **No external dependencies** - must work during internet outages
- **6-month timeline** - must deliver production-ready system
- **Limited budget** - Mac Studio hardware, minimal ongoing costs

---

## 3. Architecture Overview

### 3.1 System Architecture

```
┌─────────────────────────────────────────────┐
│   CLINICIAN DEVICES (5 users)               │
│   • Browser PWA (HTMX + Service Worker)     │
│   • Internal WiFi only                      │
│   • Self-signed TLS acceptable              │
└─────────────────┬───────────────────────────┘
                  │ HTTPS (internal network)
                  ▼
┌─────────────────────────────────────────────┐
│   MAC STUDIO 128GB (Primary)                │
│                                             │
│   Docker Compose Stack:                     │
│   ┌────────────────────────────────────┐    │
│   │  Nginx (Reverse Proxy + SSL)       │    │
│   │  HTMX Frontend (Jinja2)            │    │
│   │  FastAPI Backend                   │    │
│   │  Local Whisper (transcription)     │    │
│   │  Local LLM (Llama 3.1 70B)         │    │
│   │  Keycloak (Authentication)         │    │
│   │  PostgreSQL (Encrypted)            │    │
│   │  Prometheus + Grafana (Monitoring) │    │
│   └────────────────────────────────────┘    │
│                                             │
│   Backup: Time Machine + Backblaze B2       │
└─────────────────────────────────────────────┘
```

### 3.2 Hardware Utilization (Mac Studio 128GB)

| Component | RAM | CPU | Notes |
|-----------|-----|-----|-------|
| Llama 3.1 70B | ~40GB | 8-16 cores | Primary LLM for extraction/verification |
| Whisper Large-v3 | ~10GB | 4-8 cores | Audio transcription |
| FastAPI + Python | ~2GB | 2 cores | Backend API workers |
| Keycloak | ~2GB | 1 core | Authentication service |
| PostgreSQL | ~4GB | 2 cores | With connection pooling |
| Monitoring | ~2GB | 1 core | Prometheus + Grafana |
| **Total Used** | **~60GB** | **18-30 cores** | **Headroom for concurrent users** |
| **Available** | **~68GB** | **Remaining cores** | **Room for scaling** |

### 3.3 Network Architecture

- **Isolated VLAN** - Mac Studio on separate network segment
- **No public internet exposure** - Internal WiFi access only
- **VPN for remote maintenance** - Tailscale or WireGuard
- **Self-signed TLS certificate** - Acceptable for internal-only access

---

## 4. Component Design

### 4.1 Frontend (HTMX PWA)

**Technology Stack:**
- HTMX for progressive enhancement
- Jinja2 templates (server-rendered)
- Vanilla JavaScript for offline-critical features
- Service Worker for offline capabilities
- IndexedDB for local storage

**Key Pages:**

1. **Login** (`/login`)
   - Keycloak integration
   - Local account authentication
   - "Remember me" functionality

2. **Patient Selection** (`/patients`)
   - Search by name/DOB/MRN
   - Recent patients list
   - My Health Record lookup (when online)

3. **Recording Interface** (`/record/{patient_id}`)
   - Real-time audio visualization
   - Pause/resume controls
   - Offline indicator
   - Recording timer

4. **Review & Verification** (`/review/{recording_id}`)
   - Transcript display with editing
   - Verification results with color coding:
     - 🟢 Verified against EMR
     - 🟡 Needs review
     - 🔴 Conflict detected
   - Structured data preview
   - Submit/Discard buttons

5. **Queue Management** (`/queue`)
   - Pending recordings
   - Processing status
   - Retry failed uploads
   - Estimated completion times

### 4.2 Backend (FastAPI)

**Endpoints:**

```python
# Authentication
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout

# Patients
GET  /api/v1/patients/search?q={query}
GET  /api/v1/patients/{patient_id}
GET  /api/v1/patients/{patient_id}/context  # EMR data for verification

# Recordings
POST /api/v1/recordings                    # Upload audio (multipart)
GET  /api/v1/recordings/{recording_id}
GET  /api/v1/recordings/{recording_id}/status
POST /api/v1/recordings/{recording_id}/process  # Trigger processing

# Transcriptions
GET  /api/v1/transcriptions/{recording_id}
POST /api/v1/transcriptions/{recording_id}/edit
POST /api/v1/transcriptions/{recording_id}/verify

# Queue
GET  /api/v1/queue                         # List pending for current user
POST /api/v1/queue/{recording_id}/retry    # Retry failed upload
DELETE /api/v1/queue/{recording_id}        # Cancel pending

# Admin (restricted)
GET  /api/v1/admin/health
GET  /api/v1/admin/metrics
GET  /api/v1/admin/audit-log
```

### 4.3 AI Services

**Whisper (Local):**
- Model: `large-v3` or `large-v3-turbo`
- Container: OpenAI Whisper or faster-whisper
- RAM: ~10GB
- GPU: Optional (Mac Studio M2 Ultra Neural Engine can accelerate)
- Output: Raw transcript with timestamps

**LLM (Local):**
- Model: Llama 3.1 70B (or 70B Q4_K_M quantized)
- Framework: llama.cpp or vLLM
- RAM: ~40GB (quantized) to ~80GB (full)
- Functions:
  1. Extract structured data (dates, medications, diagnoses)
  2. Verify against patient context (from EMR/MHR)
  3. Flag discrepancies and conflicts
- Fallback: Llama 3.1 8B if resources constrained

### 4.4 Data Storage

**PostgreSQL:**
- User accounts (Keycloak-managed)
- Patient metadata (no audio)
- Transcription records
- Verification results
- Audit logs (immutable)

**IndexedDB (Browser):**
- Audio recordings (encrypted)
- Pending upload queue
- Patient context cache
- Offline queue status

**File System (Mac Studio):**
- Temporary audio storage (during processing)
- Model files (Whisper, LLM)
- Logs and metrics

---

## 5. Data Flow

### 5.1 Happy Path (Online)

```
1. Clinician selects patient
   ↓
2. Clicks "Record", speaks naturally
   ↓
3. Clicks "Stop", audio uploaded immediately
   ↓
4. Backend: Whisper transcribes (10-30s)
   ↓
5. Backend: LLM extracts + verifies (20-60s)
   ↓
6. Clinician sees:
   - Transcript (editable)
   - Structured data
   - Verification results (green/yellow/red)
   ↓
7. Clinician edits if needed, clicks "Submit"
   ↓
8. Note sent to existing review system
   ↓
9. Audit log entry created
```

### 5.2 Offline Path

```
1. Clinician selects patient (cached locally)
   ↓
2. Clicks "Record", speaks naturally
   ↓
3. Clicks "Stop", audio stored in IndexedDB
   ↓
4. Service Worker queues for sync
   ↓
5. Clinician sees: "3 recordings queued for upload"
   ↓
6. Can continue with next patient
   ↓
7. When connection restored:
   ↓
8. Background sync uploads in FIFO order
   ↓
9. Processing happens server-side
   ↓
10. Clinician receives notification when ready for review
```

### 5.3 Error Handling

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| Network fails during upload | Retry 3x with exponential backoff, then queue locally | "Connection lost - saved locally, will retry automatically" |
| Whisper fails | Retry once, then queue for manual review | "Transcription unavailable - recording saved for manual processing" |
| LLM OOM | Fall back to smaller model (8B) or skip extraction | "Processing with alternate model - may take longer" |
| Disk full on Mac | Reject new uploads | "Storage limit reached - contact administrator" |
| Auth token expires | Redirect to login | "Session expired - please log in again" |
| Patient context stale | Re-fetch from MHR (if online) or show warning | "Patient data may be outdated - verify with EMR" |

---

## 6. Security Architecture

### 6.1 Authentication & Authorization

**Keycloak Configuration:**
- Local user accounts (no external identity providers for production)
- OAuth 2.0 + OpenID Connect
- JWT tokens with 15-minute expiry
- Refresh tokens with 7-day expiry
- Role-based access control:
  - `clinician`: Can record, review own transcriptions
  - `admin`: Can manage users, view all transcriptions
  - `auditor`: Read-only access to audit logs

**Password Policy:**
- Minimum 12 characters
- Complexity requirements
- 90-day rotation (configurable)
- Account lockout after 5 failed attempts

### 6.2 Data Protection

**In Transit:**
- TLS 1.3 for all communications
- Certificate pinning for internal services
- No HTTP fallback allowed

**At Rest:**
- FileVault full-disk encryption (Mac Studio)
- PostgreSQL transparent data encryption
- IndexedDB audio encryption using Web Crypto API
- Backup encryption (AES-256 before offsite upload)

**In Processing:**
- Audio processed in-memory when possible
- Temporary files encrypted and wiped securely
- Memory cleared after processing
- No audio logging (transcripts only)

### 6.3 Compliance (Australian)

**Privacy Act 1988 + APPs:**

| Requirement | Implementation |
|-------------|----------------|
| APP 1 - Open & transparent | Privacy policy displayed at first login |
| APP 3 - Collection of solicited personal info | Only collect what's necessary for clinical documentation |
| APP 6 - Use or disclosure | Audio and transcripts used only for creating clinical notes |
| APP 11 - Security | Encryption, access controls, audit logging |
| APP 12 - Access | Patients can request their data via practice |

**AHPRA Requirements:**
- All transcriptions attributable to clinician
- Immutable audit trail
- 7-year retention (adults), 25 years (children)
- Tamper-evident records

**Data Breach Notification:**
- Automated breach detection (unusual access patterns)
- 72-hour OAIC notification process
- Patient notification procedures
- Incident response runbook

### 6.4 Audit Logging

**Logged Events:**
- User login/logout
- Patient record access
- Recording created/deleted
- Transcription viewed/edited/submitted
- Verification results
- System errors and failures

**Log Format:**
```json
{
  "timestamp": "2025-02-23T10:30:00Z",
  "event": "TRANSCRIPTION_SUBMITTED",
  "user_id": "uuid",
  "patient_id": "hashed_id",
  "recording_id": "uuid",
  "ip_address": "10.0.1.x",
  "user_agent": "...",
  "success": true
}
```

**Log Storage:**
- PostgreSQL append-only table
- Daily export to immutable storage
- 7-year retention
- Access restricted to auditors

---

## 7. Offline Capabilities

### 7.1 Service Worker Strategy

**Caching:**
- Static assets (HTML, CSS, JS) - Cache First
- API responses - Network First with timeout
- Audio uploads - Queue for background sync

**Background Sync:**
```javascript
// Service Worker
self.addEventListener('sync', event => {
  if (event.tag === 'upload-recordings') {
    event.waitUntil(
      getPendingRecordings()
        .then(recordings => Promise.all(
          recordings.map(r => uploadWithRetry(r))
        ))
    );
  }
});
```

### 7.2 IndexedDB Schema

```javascript
// Database: ClinicalTranscription
// Version: 1

// Store: recordings
{
  id: "uuid",
  patient_id: "hashed_id",
  audio_blob: Blob, // Encrypted
  duration_seconds: 120,
  recorded_at: "2025-02-23T10:30:00Z",
  status: "pending|uploading|processing|completed|failed",
  retry_count: 0,
  last_error: null
}

// Store: patient_cache
{
  id: "hashed_id",
  name: "J. Smith",
  dob: "1980-01-01",
  mrn: "...",
  cached_at: "2025-02-23T09:00:00Z",
  ttl: 3600 // 1 hour
}
```

### 7.3 Offline UX

**Visual Indicators:**
- Green dot: Online
- Yellow dot: Degraded (slow connection)
- Red dot: Offline

**Functional Degradation:**

| Feature | Online | Offline |
|---------|--------|---------|
| Record audio | ✅ | ✅ |
| Store locally | ✅ | ✅ |
| Search patients | ✅ | ✅ (cached only) |
| Upload recording | ✅ | ⏳ Queued |
| View processing | ✅ | ❌ N/A |
| Review transcription | ✅ | ❌ N/A |
| Submit note | ✅ | ⏳ Queued |
| My Health Record lookup | ✅ | ❌ Unavailable |

---

## 8. Error Handling & Resilience

### 8.1 Graceful Degradation

**Model Failover Chain:**
1. Llama 3.1 70B (primary)
2. Llama 3.1 8B (if OOM on 70B)
3. Raw transcript only (if both fail)

**Storage Failover:**
1. PostgreSQL (primary)
2. Local JSON files (if DB unavailable)
3. Alert admin for manual intervention

### 8.2 Recovery Procedures

**Mac Studio Hardware Failure:**
1. Activate hot spare (if configured)
2. Restore from latest backup
3. RTO: 4 hours, RPO: 1 hour

**Disk Full:**
1. Alert via monitoring
2. Auto-delete temp files > 7 days old
3. If still full, reject new uploads
4. Manual cleanup required

**Network Partition:**
1. Continue operating offline mode
2. Queue all operations
3. Sync when connection restored
4. Conflict resolution: Server wins for simultaneous edits

### 8.3 Monitoring & Alerting

**Critical Alerts (Immediate SMS/Email):**
- Service down > 5 minutes
- Disk > 80% full
- Backup failures
- Failed login attempts > 10/hour
- Error rate > 5%

**Warning Alerts (Email):**
- Disk > 70% full
- Memory usage > 80%
- Queue depth > 20 items
- API latency > 2 seconds

**Dashboard Metrics:**
- Active users
- Recordings per hour
- Processing queue depth
- Average transcription time
- Error rates by endpoint
- System resources (CPU, RAM, disk)

---

## 9. Testing Strategy

### 9.1 Test Categories

| Type | Scope | Tools | Coverage Target |
|------|-------|-------|-----------------|
| Unit | Python functions, HTMX handlers | pytest | 80%+ |
| Integration | API endpoints, database | pytest + TestClient | Critical paths |
| E2E | Full user workflows | Playwright | 5 core flows |
| Property-based | Verification invariants | Hypothesis | All safety checks |
| Load | Concurrent users | k6 or Locust | 5-10 concurrent |
| Security | Auth, injection, XSS | OWASP ZAP | High-risk areas |

### 9.2 Critical Test Scenarios

**Offline Workflow:**
1. Record 3 patients offline
2. Verify IndexedDB storage
3. Restore connection
4. Verify background sync
5. Verify processing completes

**Security:**
1. JWT expiry handling
2. Role-based access control
3. SQL injection attempts
4. XSS in transcript editing
5. Audio upload without auth

**Failover:**
1. Kill LLM container mid-processing
2. Verify fallback to smaller model
3. Verify user notification
4. Verify partial results returned

**Compliance:**
1. Audit log completeness
2. Data retention policies
3. Right to deletion (anonymization)
4. Encryption at rest verification

### 9.3 Test Data

- Use synthetic patient data (FHIR Synthea)
- Never use real patient data in tests
- Audio: Synthetic speech or test recordings with consent

---

## 10. Deployment & Operations

### 10.1 Docker Compose Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
      - web

  web:
    build: ./frontend
    volumes:
      - ./frontend/templates:/app/templates
    environment:
      - API_URL=http://api:8000

  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - KEYCLOAK_URL=http://keycloak:8080
      - WHISPER_URL=http://whisper:9000
      - LLM_URL=http://llm:8000
    depends_on:
      - db
      - keycloak

  whisper:
    image: faster-whisper:latest
    volumes:
      - ./models/whisper:/models
    environment:
      - MODEL_SIZE=large-v3

  llm:
    image: vllm/vllm-openai:latest
    volumes:
      - ./models/llama-3.1-70b:/models
    command: --model /models/llama-3.1-70b --tensor-parallel-size 1
    deploy:
      resources:
        limits:
          memory: 80G

  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://db:5432/keycloak
    command: start-dev  # Production: use 'start' with proper config

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards

volumes:
  postgres_data:
  prometheus_data:
  grafana_data:
```

### 10.2 Backup Strategy

**Hourly (Time Machine):**
- Full system backup
- Retention: 30 days
- Destination: External SSD

**Daily (Automated Script):**
- PostgreSQL dump
- Configuration files
- SSL certificates
- Encrypted and uploaded to Backblaze B2
- Retention: 90 days

**Monthly:**
- Full system image
- Stored offsite
- Retention: 2 years

### 10.3 Maintenance Windows

**Scheduled:**
- Sundays 2-4 AM (lowest clinic activity)
- Model updates (quarterly)
- Security patches (monthly)

**Emergency:**
- Hot fixes can be applied during clinic hours if critical
- Zero-downtime deployments using blue/green (if needed)

### 10.4 Runbook (For Your Friend/Backup)

**Common Issues:**
1. **System won't start:** Check Docker logs: `docker-compose logs`
2. **No disk space:** Clear temp files: `./scripts/cleanup.sh`
3. **Slow transcription:** Check LLM resource usage in Grafana
4. **Can't login:** Verify Keycloak is running: `docker-compose ps`

**Emergency Contacts:**
- You: [phone/email]
- Backup Python contractor: [contact]

---

## 11. Non-Goals (Out of Scope for v1)

- **Direct EMR integration** - Read-only from MHR only
- **Multi-practice support** - Single practice only
- **Mobile native apps** - PWA is sufficient
- **Real-time collaboration** - Single clinician per patient
- **Advanced analytics** - Basic metrics only
- **Patient portal** - Practice handles patient access
- **Billing integration** - Practice handles separately
- **Multi-language support** - English only initially

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Single maintainer unavailable | Medium | Critical | Documentation, runbook, backup contractor contact |
| Mac Studio hardware failure | Low | Critical | Hot spare + automated backups + 4-hour RTO |
| LLM hallucinations | Medium | High | Verification layer + human review required |
| Data breach | Low | Critical | Encryption, access controls, audit logging, incident response plan |
| Clinician resistance | Medium | Medium | Training, gradual rollout, feedback loop |
| Compliance violations | Low | Critical | Built-in compliance, legal review, audit logging |
| Whisper accuracy issues | Medium | Medium | Medical vocabulary fine-tuning, user feedback, manual correction |
| Network instability | Medium | Medium | Offline-first design, queue management |
| Disk space exhaustion | Medium | High | Monitoring, auto-cleanup, alerting |

---

## 13. Timeline (6 Months)

### Month 1: Foundation
- [ ] Week 1-2: Project setup, Docker compose, basic FastAPI
- [ ] Week 3-4: Keycloak auth, user management

### Month 2: Core Recording
- [ ] Week 1-2: HTMX frontend, patient selection
- [ ] Week 3-4: Audio recording, upload, storage

### Month 3: AI Integration
- [ ] Week 1-2: Whisper integration, transcription
- [ ] Week 3-4: LLM integration, extraction, verification

### Month 4: Offline & Polish
- [ ] Week 1-2: Service Worker, IndexedDB, background sync
- [ ] Week 3-4: Queue management, error handling, UI polish

### Month 5: Production Hardening
- [ ] Week 1-2: Security audit, penetration testing
- [ ] Week 3-4: Monitoring, alerting, backup procedures

### Month 6: Compliance & Pilot
- [ ] Week 1-2: Documentation, privacy policy, runbook
- [ ] Week 3-4: Pilot with 1-2 clinicians, feedback, iteration

**Go-live:** End of Month 6 (all 5 clinicians)

---

## 14. Success Criteria

**Technical:**
- [ ] 99.5% uptime over 30-day period
- [ ] <2 second API response time (p95)
- [ ] Zero security vulnerabilities (high/critical)
- [ ] Backup recovery tested monthly

**User:**
- [ ] >80% daily active users (4 of 5 clinicians)
- [ ] 40% reduction in documentation time (measured)
- [ ] <5% manual correction rate
- [ ] Net Promoter Score >50

**Compliance:**
- [ ] Privacy policy published
- [ ] Audit logs complete and accessible
- [ ] Security documentation complete
- [ ] Incident response tested

---

## 15. Approval

This design is approved for implementation.

**Next Steps:**
1. Create implementation plan using writing-plans skill
2. Follow 8-step lifecycle from AGENTS.md
3. Begin with Step 1 (Business Requirements) - already complete in this doc
4. Proceed to Step 2 (Requirements & Source Spec)

**Sign-off:**

| Role | Name | Date | Approved |
|------|------|------|----------|
| Architect | [You] | 2025-02-23 | ✅ |
| Product Owner | [Your Friend] | TBD | ⏳ |
| Compliance Review | TBD | TBD | ⏳ |

---

## Appendix A: Compliance Checklist

**Pre-Deployment:**
- [ ] Privacy policy drafted and reviewed
- [ ] Data breach response plan documented
- [ ] Access control matrix defined
- [ ] User training materials created
- [ ] Incident response runbook tested
- [ ] Backup and recovery tested
- [ ] Security audit completed
- [ ] Legal review (if required)

**Post-Deployment:**
- [ ] Staff training completed
- [ ] Privacy policy acknowledged by all users
- [ ] Monitoring dashboards reviewed
- [ ] First backup verified
- [ ] Audit log review process established

---

## Appendix B: Hardware Specifications

**Minimum (Demo):**
- Mac Studio (M2 Max, 64GB RAM)
- 1TB SSD
- 1Gbps internal network

**Recommended (Production):**
- Mac Studio (M2 Ultra, 128GB RAM) ✅ Selected
- 2TB SSD
- 1Gbps internal network
- 4TB external SSD (Time Machine)
- UPS (battery backup)

**Optional (High Availability):**
- Second Mac Studio (hot spare)
- Network-attached storage (Synology)
- Automated failover scripting

---

## Appendix C: Open Source Licenses

All components are open source with permissive licenses:

| Component | License | Commercial Use |
|-----------|---------|----------------|
| FastAPI | MIT | ✅ |
| HTMX | BSD 2-Clause | ✅ |
| Keycloak | Apache 2.0 | ✅ |
| PostgreSQL | PostgreSQL | ✅ |
| Prometheus | Apache 2.0 | ✅ |
| Grafana | AGPL v3 | ✅ (internal use) |
| Whisper | MIT | ✅ |
| Llama 3.1 | Llama 3.1 Community | ✅ |

**Note:** Llama 3.1 requires compliance with Meta's acceptable use policy (no illegal activities, no military use, etc.)
