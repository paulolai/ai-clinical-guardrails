# Monitoring and Alerting

**For:** Engineering, Operations
**Purpose:** Operational visibility and incident response

---

## Monitoring Stack

**Metrics:** Prometheus + Grafana
**Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
**Tracing:** Jaeger (distributed tracing)
**Alerting:** PagerDuty

## Key Metrics

### System Health

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Uptime | 99.9% | <99.5% for 5 min |
| Response Time (p95) | <10s | >15s for 5 min |
| Error Rate | <1% | >5% for 5 min |
| CPU Utilisation | <70% | >85% for 10 min |
| Memory Utilisation | <80% | >90% for 10 min |
| Disk Usage | <70% | >85% |

### Business Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Transcription Success Rate | >98% | <95% for 10 min |
| Extraction Confidence (avg) | >0.85 | <0.75 for 1 hour |
| Fallback Rate | <10% | >20% for 1 hour |
| User Satisfaction | >4.0/5 | N/A (review monthly) |
| Verification Alert Rate | <15% | >30% for 1 hour |

### Compliance Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| PII Detection | 100% | Any detection |
| Audit Log Completeness | 100% | <100% |
| Data Sovereignty | 100% | Any offshore access |
| Failed Logins | <5/day | >20/day |

## Dashboards

### Operations Dashboard
**Refresh:** Real-time
**Audience:** Operations team
**Widgets:**
- Service status (green/yellow/red)
- Request rate and latency
- Error rate by type
- Resource utilisation
- Active alerts

### Clinical Dashboard
**Refresh:** 5 minutes
**Audience:** Clinical leadership
**Widgets:**
- Usage by department/clinician
- Extraction accuracy trends
- Time savings achieved
- Verification alert patterns
- User feedback summary

### Compliance Dashboard
**Refresh:** 15 minutes
**Audience:** Privacy Officer, Security
**Widgets:**
- Access audit summary
- PII detection events
- Data sovereignty status
- Failed authentication attempts
- Retention compliance

## Alerting Rules

### Critical (Page Immediately)
- Service down >2 minutes
- Error rate >10%
- Data sovereignty violation
- PII detection in production
- Database connectivity lost

### High (Page within 15 minutes)
- Response time p95 >20 seconds
- Error rate >5% for 10 minutes
- Transcription service unavailable
- Infrastructure resource exhaustion

### Medium (Notify during business hours)
- Error rate >2% for 30 minutes
- Extraction confidence trending down
- Fallback rate >15%
- Single component degradation

### Low (Log only, review weekly)
- Performance degradation <10%
- Individual slow requests
- Non-critical component issues
- Capacity warnings

## Incident Response

### Severity Levels

**SEV-1 (Critical):**
- Complete service outage
- Data loss or corruption
- Security breach
- Response: All hands, immediate

**SEV-2 (High):**
- Major functionality impaired
- Significant performance degradation
- Compliance violation
- Response: On-call + team lead within 30 min

**SEV-3 (Medium):**
- Minor functionality impaired
- Degraded experience for subset of users
- Response: Next business day

**SEV-4 (Low):**
- Cosmetic issues
- Non-urgent improvements
- Response: Backlog

### Response Playbook

1. **Detect:** Alert fired or user report
2. **Assess:** Determine severity and impact
3. **Communicate:** Status page update, stakeholder notification
4. **Mitigate:** Apply fix or workaround
5. **Monitor:** Confirm resolution
6. **Resolve:** Close incident
7. **Review:** Post-incident analysis within 48 hours

## Log Management

### Log Levels

**ERROR:**
- Service failures
- Integration errors
- Security events
- Retention: 90 days

**WARN:**
- Degradations
- Retry events
- Configuration issues
- Retention: 30 days

**INFO:**
- Normal operations
- User actions
- Business events
- Retention: 14 days

**DEBUG:**
- Detailed diagnostics
- Disabled in production
- Retention: 7 days

### Log Aggregation

**Sources:**
- Application logs
- Infrastructure logs
- Audit logs (separate, 7-year retention)
- Security logs (SIEM integration)

**Search:**
- Full-text search capability
- Filter by time, service, level
- Trace correlation

## On-Call Rotation

**Primary:** Engineering team member
**Secondary:** Engineering manager
**Escalation:** CTO

**Schedule:**
- Week-long rotations
- Business hours: Primary only
- After hours: Primary + Secondary
- Weekend: Primary + Secondary

**Handoff:**
- Weekly meeting to review incidents
- Update runbooks
- Knowledge transfer

---

*Operations runbook maintained separately*
