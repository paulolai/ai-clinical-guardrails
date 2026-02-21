# Performance and SLA Requirements

**For:** Engineering, Infrastructure
**Purpose:** Performance targets and capacity planning

---

## Response Time Requirements

### Transcription

| Metric | Target | Maximum |
|--------|--------|---------|
| p50 latency | <3 seconds | <5 seconds |
| p95 latency | <5 seconds | <10 seconds |
| p99 latency | <10 seconds | <15 seconds |

**Measurement:** Time from audio submission to transcript return

### Extraction

| Metric | Target | Maximum |
|--------|--------|---------|
| p50 latency | <2 seconds | <3 seconds |
| p95 latency | <3 seconds | <5 seconds |
| p99 latency | <5 seconds | <8 seconds |

**Measurement:** Time from transcript to structured extraction

### Verification

| Metric | Target | Maximum |
|--------|--------|---------|
| p50 latency | <1 second | <2 seconds |
| p95 latency | <2 seconds | <3 seconds |

**Measurement:** Time from extraction to verification complete

### End-to-End

| Metric | Target | Maximum |
|--------|--------|---------|
| p50 latency | <6 seconds | <10 seconds |
| p95 latency | <10 seconds | <18 seconds |

**Measurement:** Audio submission to extraction ready for review

## Throughput Requirements

### Concurrent Users

**Target:** 500 concurrent clinicians
**Peak:** 1,000 concurrent clinicians
**Growth:** Support 2,000 within 2 years

### Request Rate

**Average:** 100 requests/minute
**Peak:** 500 requests/minute
**Burst:** 1,000 requests/minute (brief spikes)

### Data Volume

**Per Transcript:**
- Audio: 1-5MB
- Transcript: 1-10KB
- Extraction: 5-50KB

**Daily:**
- Audio processed: 100GB
- Storage (transcripts): 100MB/day
- Growth: 20% year-over-year

## Availability Requirements

### Uptime SLA

**Target:** 99.9% uptime (8.76 hours downtime/year)
**Minimum:** 99.5% uptime (43.8 hours downtime/year)

**Measurement:** Service available and responding within SLA latency

### Maintenance Windows

**Scheduled:** <4 hours/month, announced 7 days in advance
**Emergency:** As needed, minimise impact
**Timezone:** Outside AU business hours (8pm-6am AEDT)

### Degradation Modes

| Degradation | Response |
|-------------|----------|
| Transcription slow | Continue with delay, notify user |
| Extraction unavailable | Manual template fallback |
| Verification slow | Skip verification, flag for review |
| EMR sync delayed | Queue and retry, notify user |

## Capacity Planning

### Infrastructure

**Compute:**
- Application servers: Auto-scaling 2-10 instances
- Extraction workers: Auto-scaling 3-15 workers
- Database: Primary + read replica

**Storage:**
- Database: 100GB initial, 500GB 2-year projection
- Object storage: 1TB initial, 5TB 2-year projection
- Backup: 30-day retention, geo-redundant

**Network:**
- Bandwidth: 1Gbps minimum
- CDN: Not applicable (Australian only)
- DDoS protection: Enabled

### Scaling Triggers

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU utilisation | >70% for 5 min | <30% for 10 min |
| Memory utilisation | >80% for 5 min | <40% for 10 min |
| Request queue | >100 queued | <10 queued |
| Latency p95 | >10 seconds | <5 seconds |

## Testing and Validation

### Load Testing

**Before Release:**
- Simulate 500 concurrent users
- 1-hour sustained load test
- Burst test to 1,000 users

**Ongoing:**
- Monthly load test
- Quarterly capacity review
- Annual disaster recovery test

### Performance Monitoring

**Real-time:**
- Request latency histograms
- Error rates by endpoint
- Resource utilisation
- Queue depths

**Reporting:**
- Daily: Key metrics dashboard
- Weekly: Performance trends
- Monthly: SLA compliance report
- Quarterly: Capacity planning review

## Cost Considerations

### Infrastructure

**Compute:** $X/month (scales with usage)
**Storage:** $X/month (grows over time)
**Network:** $X/month (varies with volume)
**Transcription Service:** $X/month (usage-based)

**Total:** $X,XXX/month estimated at launch

### Optimisation Targets

- Reduce transcription costs by 20% via caching
- Optimise extraction algorithms for speed
- Right-size infrastructure based on actual usage
- Review monthly and adjust

---

*Implementation details in infrastructure configuration*
