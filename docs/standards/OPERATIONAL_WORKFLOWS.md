# Operational Workflows

**For:** All developers
**Purpose:** Step-by-step workflows for common development tasks

---

## The 8-Step Lifecycle

**⚠️ MUST be followed IN ORDER. See [WORKFLOW_SPEC.md](../WORKFLOW_SPEC.md) for complete details.**

### Step 1: Business Requirements (The Foundation)
**Goal:** Define the "why" and "what" before the "how".
- **Action:** Document the business problem, success criteria, stakeholders, and constraints.
- **Key Questions:**
  - What clinical/operational problem does this solve?
  - What are the success metrics?
  - Who are the stakeholders?
  - What are regulatory/compliance constraints?
- **Output:** Requirements document approved before ANY technical work begins.
- **❌ NEVER skip this step.**

### Step 2: Requirements & Source Spec (The Truth)
*   **Source:** Always link to the official upstream schema (OpenAPI, JSON Schema).
*   **Action:** Extract relevant definitions to `specs/` if the full spec is unmanageable.
*   **Output:** Generated code in `src/integrations/<system>/generated.py`.

### Step 3: Generated Model Layer (The Types)
*   **Tool:** `datamodel-code-generator`
*   **Action:** Generate Pydantic models from official upstream schemas (FHIR, etc.)
*   **Output:** `src/integrations/<system>/generated.py`

### Step 4: Domain Wrapper Layer (The Firewall)
*   **Pattern:** The **Wrapper Pattern**.
*   **Rule:** Never leak generated "Raw Models" into the "Business Logic".
*   **Implementation:** `FHIRClient` consumes `generated.Patient` (Complex) and returns `PatientProfile` (Clean).

### Step 5: Interface-Specific CLI (The Handles)
*   **Goal:** Enable developer debugging of each system boundary.
*   **Standard:** Tools named after the interface they serve.
*   **Examples:** `cli/emr.py`, `cli/api.py`

### Step 6: Component Testing (The Proof)
*   **Component Tests:** Verify the `Wrapper` talks to the `Real Sandbox`.
*   **Standard:** Use `pytest-asyncio` with real test data.

### Step 7: Business Logic (The Engine)
*   **Pattern:** Functional Core, Imperative Shell.
*   **Style:** Pure functions using the **Result Pattern** (`Result[T, E]`).
*   **Forbidden:** Throwing exceptions for business rule violations. Exceptions are for system failures only.

### Step 8: System Verification (The Invariants)
*   **Tool:** Hypothesis for Property-Based Testing
*   **Action:** Prove logic holds for all valid inputs.
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

*   **EMR Integration:** `cli/emr.py inspect <id>`
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
uv run python cli/emr.py inspect 90128869
uv run python cli/api.py verify --id 90128869 --text "Seen today."
```
