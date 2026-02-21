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
