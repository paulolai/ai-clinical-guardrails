# Extraction Layer Design

**For:** Engineering
**Purpose:** Technical architecture for voice-to-structured-data extraction

---

## Architecture Overview

```
Raw Transcript → LLM Parser → Temporal Resolver → Structured Output
                     ↓
              Confidence Scoring
                     ↓
              Verification Engine
```

## Why LLM-Based?

Clinical dictation is messy, conversational, and highly variable. Unlike rule-based approaches that require rigid patterns, LLMs can:

- Understand context and nuance
- Handle spelling variations and abbreviations
- Extract meaning from conversational speech
- Adapt to different clinician styles
- Process incomplete or ambiguous statements

**Trade-offs:**
- Higher latency (API call required)
- Ongoing cost per extraction
- Need for confidence calibration
- Potential for hallucination (mitigated by human review)

## Components

### 1. LLMTranscriptParser

**Responsibility:** Extract structured data from unstructured clinical text using LLM

**Input:**
- Raw transcript text (messy, conversational)
- Reference date (for temporal resolution)
- LLM client (configured for API calls)

**Output:** StructuredExtraction object

**Pipeline:**
1. Build prompt with transcript and reference context
2. Call LLM API with structured extraction prompt
3. Parse JSON response
4. Convert to domain models
5. Merge with rule-based temporal resolution
6. Return structured result

**Prompt Design:**
- System: "You are a clinical data extraction assistant"
- User: Transcript + JSON schema + extraction guidelines
- Temperature: 0.0 (deterministic)
- Max tokens: 2000

### 2. Prompt Engineering

**Key Elements:**
- Clear extraction instructions
- JSON schema definition
- Australian context (PBS medications, MBS terms)
- Confidence scoring guidance
- Ambiguity handling instructions

**Example Output Format:**
```json
{
  "patient_name": "...",
  "medications": [
    {
      "name": "...",
      "dosage": "...",
      "status": "started|stopped|continued",
      "confidence": 0.9
    }
  ],
  "diagnoses": [...],
  "temporal_expressions": [...],
  "confidence": 0.85
}
```

### 3. TemporalResolver

**Responsibility:** Convert relative dates to absolute dates using rule-based approach

**Why keep rule-based?**
- More reliable for standard patterns ("yesterday", "last week")
- Deterministic and explainable
- Faster than LLM for known patterns

**Integration:**
- Run regex-based resolver first
- Merge with LLM temporal insights
- Use LLM for ambiguous expressions
- Combine confidence scores

### 4. Confidence Scoring & Safety Controls

**Prevention of Critical Failures:**

**Safety-Critical Fields (Never Auto-Populate):**
```python
SAFETY_CRITICAL_FIELDS = {
    'medication_changes',  # New, stopped, dose adjustments
    'allergies',
    'protocol_triggers',
}

# These always require explicit clinician confirmation
def should_auto_populate(field_type: str, confidence: float) -> bool:
    if field_type in SAFETY_CRITICAL_FIELDS:
        return False  # Never auto-populate, regardless of confidence
    return confidence > 0.95
```

**Two-Layer Confidence Approach:**

**Layer 1: LLM Confidence**
- Extracted by LLM for each entity (0.0-1.0)
- Based on clarity of mention in transcript
- Overall confidence for entire extraction

**Layer 2: System Confidence (Calibrated)**
```python
class ConfidenceCalibrator:
    """Ensure confidence scores reflect actual accuracy.

    Based on pre-mortem Risk #1: Wrong medication extracted.
    We must ensure high confidence actually means high accuracy.
    """

    def __init__(self):
        self.calibration_data = []

    def record_outcome(self, extraction: ExtractionResult, was_correct: bool):
        """Track actual accuracy vs predicted confidence."""
        self.calibration_data.append({
            'predicted_confidence': extraction.confidence,
            'actual_correct': was_correct,
            'field_type': extraction.field_type
        })

    def get_calibrated_confidence(self, raw_confidence: float, field_type: str) -> float:
        """Adjust confidence based on historical accuracy.

        Example: If 0.9 confidence historically 75% accurate,
        calibrate to 0.75 to avoid false confidence.
        """
        # Implementation: Calculate calibration curve per field type
        # Use isotonic regression or similar
        pass
```

**Confidence Thresholds:**
| Confidence | Action | UI Treatment |
|------------|--------|--------------|
| >0.95 | Auto-populate (non-safety-critical only) | Green highlight |
| 0.70-0.95 | Populate with warning | Yellow warning icon |
| <0.70 | Do not populate | Red flag, manual entry |

**Hallucination Detection:**
```python
class HallucinationDetector:
    """Detect extractions not supported by transcript text.

    Pre-mortem Risk #1: LLM hallucinated medications.
    """

    def __init__(self):
        self.pbs_medication_list = load_pbs_medications()

    def check_medication(self, medication: ExtractedMedication, transcript: str) -> bool:
        """Return True if medication appears to be hallucinated."""
        # Check 1: Is medication name in PBS list?
        if medication.name not in self.pbs_medication_list:
            return True  # Unknown medication, flag for review

        # Check 2: Does medication name appear in transcript?
        if medication.name.lower() not in transcript.lower():
            return True  # Not in original text, possible hallucination

        return False
```

## Data Models

See `src/extraction/models.py` for implementation:
- `StructuredExtraction` - Top-level result
- `ExtractedMedication` - Medication details with confidence
- `ExtractedDiagnosis` - Diagnosis details with confidence
- `ExtractedTemporalExpression` - Temporal data with resolution

## LLM Provider Options

### Option 1: OpenAI GPT-4
- **Pros:** High accuracy, fast, JSON mode
- **Cons:** US-based (data sovereignty concerns)
- **Mitigation:** Use only for processing, not storage

### Option 2: Australian-Hosted LLM
- **Pros:** Data sovereignty compliance
- **Cons:** May have lower accuracy, higher latency
- **Examples:** Local Azure OpenAI, Australian AI providers

### Option 3: Hybrid Approach
- Use rule-based for high-confidence patterns
- Use LLM for ambiguous or complex cases
- Fallback to LLM when rule-based fails

**Recommendation:** Start with Option 1 (OpenAI) for accuracy, migrate to Option 2 (Australian) for production.

## Integration Points

**Incoming:**
- Transcription service (raw text)
- Reference date (from encounter context)
- LLM client (configured API connection)

**Outgoing:**
- Verification engine (for validation)
- Review interface (for clinician presentation)

## Error Handling

**LLM API Failure:**
- Retry with exponential backoff (max 3 attempts)
- If still failing: Return low-confidence extraction
- Log error for monitoring
- Fallback to manual template

**Invalid JSON Response:**
- Attempt to clean response (remove markdown)
- If still invalid: Return fallback extraction
- Log for prompt improvement

**Low Confidence Extraction:**
- Return with low confidence flag
- Do not auto-populate fields
- Present to clinician for manual review

## Performance Considerations

**Latency:**
- LLM API call: 1-5 seconds
- Total extraction: 2-6 seconds
- Target: <5 seconds p95

**Optimization:**
- Cache common extraction patterns
- Batch multiple extractions
- Async processing for non-critical paths
- Progressive enhancement (show results as they arrive)

**Cost:**
- ~$0.01-0.05 per extraction (GPT-4)
- 1000 extractions/day = ~$15-75/day
- Monitor and optimise prompts for token efficiency

## Testing Strategy

See [EXTRACTION_TESTING_STRATEGY.md](EXTRACTION_TESTING_STRATEGY.md)

**LLM-Specific Testing:**
- Prompt robustness (variations in input)
- Confidence calibration (does 0.9 actually mean 90% accuracy?)
- Edge cases (ambiguous, incomplete, contradictory)
- Hallucination detection (extracting things not in text)

## Future Enhancements

**Fine-tuned Model:**
- Train on Australian clinical dictation corpus
- Specialised for PBS medications, MBS terminology
- Improved accuracy for local context

**Multi-Model Ensemble:**
- Use multiple LLMs and combine results
- Weight by historical accuracy
- Reduce hallucination risk

**Caching:**
- Cache extraction results for similar transcripts
- Hash-based lookup
- Invalidate on model updates

---

*Implementation:* `src/extraction/llm_parser.py`
