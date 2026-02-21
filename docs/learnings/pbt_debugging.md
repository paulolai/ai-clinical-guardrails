# Property-Based Testing Learnings

Insights from using Hypothesis for clinical safety verification.

## 2025-02-21: Template Entry

**Context:** Template for future entries.

**Problem:** Example problem.

**Solution:** Example solution.

**Root Cause:** Example root cause.

**Prevention:** Example prevention.

**Related:** N/A

---

## Common Hypothesis Patterns

### Strategy Composition
```python
@st.composite
def emr_contexts(draw):
    """Generate valid EMR contexts."""
    start = draw(st.dates())
    duration = draw(st.integers(1, 30))
    return EMRContext(
        admission_date=start,
        discharge_date=start + timedelta(days=duration)
    )
```

### Deadline Management
```python
@settings(deadline=None)  # For slow operations
@given(...)
def test_slow(...):
    pass
```

### Shrinking Control
```python
@settings(max_examples=100, derandomize=True)
@given(...)
def test_deterministic(...):
    pass
```

## Template

**Context:**

**Problem:**

**Solution:**

**Root Cause:**

**Prevention:**

**Related:**
