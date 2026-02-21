# Extraction Testing Strategy

**For:** Engineering, QA
**Purpose:** Ensure extraction accuracy and reliability

---

## Testing Levels

### 1. Unit Tests
**Scope:** Individual extractors in isolation

**Examples:**
- MedicationExtractor correctly identifies "Lisinopril 10mg"
- TemporalResolver correctly resolves "yesterday" to date
- ConfidenceScorer returns expected values

**Framework:** pytest
**Location:** `tests/unit/extraction/`

### 2. Property-Based Tests
**Scope:** Invariants that must always hold

**Examples:**
- "All resolved dates must be within ±1 year of reference date"
- "Medication confidence must be 0.0-1.0"
- "Extracted patient name must appear in transcript"

**Framework:** Hypothesis
**Location:** `tests/property/`

### 3. Golden Standard Tests
**Scope:** Comparison against manually annotated transcripts

**Approach:**
- Create dataset of 100+ de-identified clinical notes
- Manual annotation by clinical expert
- Automated comparison of extraction vs. annotation
- Track precision, recall, F1 by entity type

**Location:** `tests/fixtures/golden_standard.json`

### 4. Integration Tests
**Scope:** Full pipeline from transcript to extraction

**Examples:**
- End-to-end extraction of sample transcripts
- Verification engine integration
- Clinical software API integration

**Location:** `tests/integration/`

## Test Data

**Sample Transcripts:**
- 10-20 diverse examples in `tests/fixtures/sample_transcripts.json`
- Cover different visit types, specialties, complexity levels
- Include edge cases (ambiguous dates, PII)

**De-identified Clinical Notes:**
- Sourced from practice partners (with consent)
- PHI removed according to Australian guidelines
- Annotated by clinical experts

## Success Criteria

| Entity Type | Precision Target | Recall Target |
|-------------|-----------------|---------------|
| Medications | >90% | >85% |
| Diagnoses | >85% | >80% |
| Temporal | >95% | >90% |
| Vitals | >90% | >90% |

## Regression Testing

**On Each Change:**
- Run full unit test suite
- Run property-based tests (100 examples)
- Run golden standard comparison
- Flag any degradation >2%

**Before Release:**
- Full integration test suite
- Performance benchmarking
- Clinical review of sample extractions

## Continuous Improvement

**Feedback Loop:**
1. Clinician marks extraction as incorrect
2. Log error type and context
3. Add to test corpus
4. Retrain/improve extractors
5. Validate improvement

**Monthly:**
- Review error patterns
- Update test data with new examples
- Re-evaluate success criteria

---

*See also:* [TESTING_FRAMEWORK.md](../TESTING_FRAMEWORK.md) (general testing approach)
