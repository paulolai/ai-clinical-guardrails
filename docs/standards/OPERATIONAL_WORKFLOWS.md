# Operational Workflows

**For:** All developers
**Purpose:** Step-by-step workflows for common development tasks

---

## The 8-Step Lifecycle

See [WORKFLOW_SPEC.md](../WORKFLOW_SPEC.md) for the complete canonical implementation guide.

### Phase 1: Specifications (The Truth)
*   **Source:** Always link to the official upstream schema (OpenAPI, JSON Schema).
*   **Action:** Extract relevant definitions to `specs/` if the full spec is unmanageable.
*   **Output:** Generated code in `src/integrations/<system>/generated.py`.

### Phase 2: The Integration Layer (The Firewall)
*   **Pattern:** The **Wrapper Pattern**.
*   **Rule:** Never leak generated "Raw Models" into the "Business Logic".
*   **Implementation:** `FHIRClient` consumes `generated.Patient` (Complex) and returns `PatientProfile` (Clean).

### Phase 3: The Engine (The Governor)
*   **Pattern:** Functional Core, Imperative Shell.
*   **Style:** Pure functions using the **Result Pattern** (`Result[T, E]`).
*   **Forbidden:** Throwing exceptions for business rule violations. Exceptions are for system failures only.

### Phase 4: Verification (The Proof)
*   **Component Tests:** Verify the `Wrapper` talks to the `Real Sandbox`.
*   **Property Tests:** Verify the `Engine` handles `Randomized Inputs`.
*   **Attestation:** Every run must produce an audit trail (`Trace` or `Report`).

---

## Pre-Mortem Analysis

**Required for:** Any new major component or feature (especially safety-critical)

**What:** Before implementation, imagine the project has failed spectacularly. What went wrong?

**Why:** Shifts focus from "how it works" to "how it fails" - essential for safety-critical systems

**Process:**
1. Imagine it's 12 months from now and the system was abandoned
2. Write out all the ways it failed (technical, clinical, compliance, adoption)
3. Identify root causes for each failure
4. Design mitigations into the architecture from day one

**Template:** See [PRE_MORTEM.md](../PRE_MORTEM.md) for example

**Output:** Update [RISK_MITIGATION.md](../RISK_MITIGATION.md) with specific mitigations

---

## Interface-First Tooling

Every major system boundary must have a dedicated CLI handle for developer debugging.

*   **EMR Integration:** `cli/fhir.py inspect <id>`
*   **API Service:** `cli/api.py verify <id>`
*   **Why?** If you can't debug the interface in isolation, you can't trust the system integration.

---

## Quick Reference Commands

```bash
# Run tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_compliance.py -v

# Check code
uv run ruff check .

# Type check
uv run mypy src/

# Run API
uv run python main.py

# CLI tools
uv run python cli/fhir.py inspect 90128869
uv run python cli/api.py verify --id 90128869 --text "Seen today."
```
