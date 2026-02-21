# Transcription Service Integration Specification

**For:** Engineering
**Purpose:** API contract with third-party transcription service
**Service:** AWS Transcribe Medical (Sydney region) or equivalent

---

## Service Requirements

**Data Sovereignty:**
- Must use AWS Sydney region (ap-southeast-2)
- No data transfer outside Australia
- IRAP-certified or equivalent

**Compliance:**
- Privacy Act 1988 compliant
- Encryption at rest and in transit
- No audio retention post-transcription

## API Contract

### Request

**Endpoint:** `POST /medical-transcription` (or equivalent)

**Headers:**
```
Content-Type: audio/wav
Authorization: Bearer <token>
X-Specialty: general-practice|emergency|cardiology
```

**Body:**
- Audio file (WAV, MP3, or stream)
- Max duration: 10 minutes
- Max file size: 50MB

### Response

**Success (200):**
```json
{
  "transcript": "Patient came in yesterday with chest pain...",
  "confidence": 0.94,
  "word_level_confidence": [
    {"word": "Patient", "confidence": 0.99},
    {"word": "came", "confidence": 0.95}
  ],
  "duration_seconds": 145,
  "language": "en-AU"
}
```

**Error Responses:**
- 400: Invalid audio format
- 413: File too large
- 429: Rate limit exceeded
- 500: Transcription service error
- 503: Service temporarily unavailable

## Error Handling

**Timeout (>10 seconds):**
- Retry once after 2 seconds
- If still failing: Fallback to manual template

**Low Confidence (<0.7):**
- Flag transcript for careful review
- Do not auto-extract entities
- Alert clinician

**Service Unavailable:**
- Queue request for retry
- Notify operations team
- Provide manual entry option to clinician

## Retry Strategy

| Error | Retry Count | Backoff |
|-------|-------------|---------|
| 429 (Rate limit) | 3 | Exponential: 1s, 2s, 4s |
| 500/503 | 2 | Fixed: 5s between |
| Timeout | 2 | Fixed: 2s between |

## Monitoring

**Metrics:**
- Request latency (p50, p95, p99)
- Error rate by type
- Retry count
- Confidence score distribution

**Alerts:**
- Error rate >5% for 5 minutes
- Latency p95 >10 seconds
- Service unavailable for >1 minute

---

*Implementation:* Integration layer in `src/integrations/transcription/`
