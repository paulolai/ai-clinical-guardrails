# Testing Standards

**For:** All developers
**Purpose:** How to test safety-critical systems

---

## Testing Trophy (Priority Order)

1. **Component Tests** (Real APIs) ← **Primary**
2. **Integration Tests** (Workflows)
3. **Property Tests** (Invariants)
4. **Unit Tests** (Pure functions)

## Invariant-Based Verification

Unit tests are insufficient for safety-critical systems. We use **Property-Based Testing (PBT)**.

*   **Don't check:** "Does 1 + 1 = 2?"
*   **Do verify:** "For any valid Patient, the generated Summary MUST NOT contain dates outside their Admission Window."
*   **Tooling:** `Hypothesis` is mandatory for all domain logic.

## When Tests Fail

**Property test failure:** Check `docs/learnings/pbt_debugging.md`

**Component test failure:** Verify sandbox is running: `uv run python cli/fhir.py inspect 90128869`

**Type check failure:** Run `uv run mypy src/` and fix errors before committing

---

## Verification Requirements

### Component Tests
- Test against real APIs (HAPI FHIR Sandbox)
- Prove integration actually works
- Run before mocking in CI

### Property Tests
- Generate randomized inputs
- Verify invariants hold
- Use Hypothesis framework

### Integration Tests
- Test complete workflows
- Multiple components together
- Realistic scenarios

### Unit Tests
- Pure functions only
- Fast feedback
- Edge cases

## Test Coverage Requirements

### Mandatory Test Categories

For every component under test, you MUST include:

**1. Happy Path Tests**
- Verify normal operation with valid inputs
- Expected outputs for standard scenarios

**2. Negative Tests (Required)**
- Invalid inputs (null, empty, malformed)
- Out-of-range values
- Type mismatches
- Missing required fields
- Error conditions and exception handling

**3. Boundary Tests (Required)**
- Minimum/maximum values
- Empty collections
- Single element vs. multiple elements
- String length boundaries (empty, 1 char, max)
- Numeric boundaries (zero, min, max, overflow)
- Date/time boundaries (epoch, far future, DST transitions)

### Implementation Approach

**For Property-Based Tests (Preferred):**
```python
@given(st.text(min_size=0, max_size=10000))  # Includes empty and max
def test_handles_various_lengths(text):
    # Property: System should handle any text length
    result = process_text(text)
    assert isinstance(result, ProcessResult)

@given(st.one_of(st.just(""), st.just("   "), st.just(None)))
def test_rejects_empty_inputs(value):
    # Property: Empty/whitespace inputs should be rejected
    with pytest.raises(ValueError):
        validate_input(value)
```

**For Example-Based Tests (When PBT Not Applicable):**
```python
def test_empty_string_raises_error():
    """Negative: Empty string should raise ValidationError."""
    with pytest.raises(ValidationError):
        parse_patient_name("")

def test_boundary_max_length():
    """Boundary: Maximum allowed name length."""
    max_name = "A" * 255
    result = parse_patient_name(max_name)
    assert result.name == max_name

def test_boundary_overflow_length():
    """Boundary: Exceeding max length should raise error."""
    too_long = "A" * 256
    with pytest.raises(ValidationError, match="exceeds maximum"):
        parse_patient_name(too_long)
```

### Verification Checklist

Before submitting tests, verify:
- [ ] Negative cases: Invalid inputs, error conditions
- [ ] Boundary cases: Min/max values, empty states
- [ ] Edge cases: Special characters, encoding issues, null handling
- [ ] Error messages: Descriptive and actionable

### Reference Implementation

See `tests/extraction/test_llm_client.py` for examples of:
- Property-based negative tests (lines 114-125)
- Property-based boundary tests (lines 127-155)
- Example-based error handling (lines 30-36)
