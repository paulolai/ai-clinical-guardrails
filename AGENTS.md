# AI Agent Operational Protocol

This document defines the **High-Assurance Engineering Standards** for this repository.
AI Coding Assistants (Gemini, Claude, Copilot) must strictly adhere to these protocols. We do not build "scripts"; we build **Auditable Platforms**.

---

## Quick Reference

**Project:** AI Clinical Guardrails
**Domain:** Healthcare / Clinical AI Safety
**Stack:** Python 3.12+, FastAPI, FHIR, Hypothesis
**Package Manager:** `uv`

## Essential Commands

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

---

## 🏛 The Core Philosophy: "Zero-Trust Engineering"

We operate on the principle that **External Data** (User Input, EMR APIs, AI Predictions) is inherently untrusted until verified by our system.

### 1. Contract-First Lifecycle
We never "hack" an integration. We follow a strict hierarchy of truth:
1.  **The Standard:** Download the official industry spec (e.g., HL7 FHIR Schema).
2.  **The Generation:** Generate strict Pydantic models from the spec (`datamodel-codegen`).
3.  **The Wrapper:** Build a clean Domain Client that isolates our logic from the raw schema complexity.
4.  **The Logic:** Implement business rules *only* against our clean Domain Objects.

### 2. Invariant-Based Verification
Unit tests are insufficient for safety-critical systems. We use **Property-Based Testing (PBT)**.
*   **Don't check:** "Does 1 + 1 = 2?"
*   **Do verify:** "For any valid Patient, the generated Summary MUST NOT contain dates outside their Admission Window."
*   **Tooling:** `Hypothesis` is mandatory for all domain logic.

### 3. Interface-First Tooling
Every major system boundary must have a dedicated CLI handle for developer debugging.
*   **EMR Integration:** `cli/fhir.py inspect <id>`
*   **API Service:** `cli/api.py verify <id>`
*   **Why?** If you can't debug the interface in isolation, you can't trust the system integration.

---

## ⚡ Operational Workflows

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

## Critical Patterns

### Result Type
```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Success(Generic[T]): value: T

@dataclass(frozen=True)
class Failure(Generic[E]): error: E

type Result[T, E] = Success[T] | Failure[E]
```

### Domain Wrapper
```python
# Never return generated FHIR models
async def get_patient(id: str) -> Result[PatientProfile, FHIRError]:
    raw = await fetch_from_fhir(id)
    fhir_patient = FHIRPatient.model_validate(raw)
    return Success(PatientProfile.from_fhir(fhir_patient))
```

---

## Testing Trophy (Priority Order)

1. Component Tests (Real APIs) ← Primary
2. Integration Tests (Workflows)
3. Property Tests (Invariants)
4. Unit Tests (Pure functions)

---

## 🚫 Forbidden Patterns
*   **Magic Dictionaries:** Never pass untyped `dict` objects. Use Pydantic models.
*   **Mock-Only Development:** You must prove integration with a real sandbox (CLI/Component Tests) before mocking it in CI.
*   **Implicit Failure:** Never return `None` or raise generic Exceptions for compliance failures. Return a structured `Failure` result.

## 🏁 Definition of Done
A feature is only complete when:
1.  The **CLI** can inspect the real data.
2.  The **Component Test** proves the integration works.
3.  The **Property Test** proves the logic is robust.
4.  The **README** is updated with the new capabilities.

## Before Committing

1. Run unit tests: `uv run pytest tests/ -m "not component" -x`
2. Run linter: `uv run ruff check .`
3. Update relevant AGENTS.md if patterns changed
4. Document significant learnings in `docs/learnings/`

---

## 📚 Documentation

Single source of truth for all documentation.

### Getting Started
- **[QUICKSTART.md](docs/QUICKSTART.md)** - 15-minute tutorial
- **[FAQ.md](docs/FAQ.md)** - Common questions
- **[GLOSSARY.md](docs/GLOSSARY.md)** - Terminology reference

### Core Documentation
- **[PYTHON_STANDARDS.md](docs/PYTHON_STANDARDS.md)** - Code standards, patterns, integration guidelines
- **[TESTING_FRAMEWORK.md](docs/TESTING_FRAMEWORK.md)** - Testing philosophy
- **[TESTING_WORKFLOWS.md](docs/TESTING_WORKFLOWS.md)** - Command reference
- **[INTEGRATION_TESTING.md](docs/INTEGRATION_TESTING.md)** - Component testing
- **[WORKFLOW_SPEC.md](docs/WORKFLOW_SPEC.md)** - Development workflow
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design

### Reference
- **[ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md)** - ADRs
- **[DEBUGGING_GUIDE.md](docs/DEBUGGING_GUIDE.md)** - Troubleshooting
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to extend
- **[examples/](examples/)** - Runnable code samples

### Learning
- **[learnings/](docs/learnings/)** - Project learnings

### When to Update Documentation

**Always update when:**
- Adding new interfaces or CLI commands
- Changing testing patterns or fixtures
- Discovering important infrastructure fixes
- Learning new API behaviors
- Creating reusable patterns

**Follow the template:** See [`docs/learnings/AGENTS.md`](./docs/learnings/AGENTS.md) for learning capture process.

---

## 🎓 Learning & Improvement

We practice **continuous documentation**. Significant discoveries must be captured:

1. **Infrastructure fixes** → [`docs/learnings/critical_infrastructure_fixes.md`](./docs/learnings/critical_infrastructure_fixes.md)
2. **API patterns** → [`docs/learnings/api_consistency_learnings.md`](./docs/learnings/api_consistency_learnings.md)
3. **Testing insights** → [`docs/learnings/pbt_debugging.md`](./docs/learnings/pbt_debugging.md)
4. **Workflow improvements** → [`docs/learnings/github_workflow.md`](./docs/learnings/github_workflow.md)

**Critical:** Learning documentation is not optional. It's essential for project knowledge retention.

---

## Getting Help

See [Debugging Guide](docs/DEBUGGING_GUIDE.md) for systematic troubleshooting.
