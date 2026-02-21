# Thinking Documentation Gaps

This document tracks major design decisions that need `_THINKING.md` companion files per `docs/THINKING_STANDARD.md`.

## Instructions for Other Sessions

When you encounter a significant design decision that lacks a thinking document:
1. Add it to this file under the appropriate priority section
2. Create the corresponding `_THINKING.md` file following the pattern in `docs/THINKING_STANDARD.md`
3. Update this file to mark it complete

## Critical Gaps (High Priority)

### 1. PYTHON_STANDARDS_THINKING.md
**Location:** `docs/PYTHON_STANDARDS_THINKING.md`
**Status:** ❌ Not started

**Decisions to capture:**
- **Strict typing**: Why `mypy --strict` vs gradual typing? What problems has it caught?
- **Result pattern**: Why `Result[T,E]` instead of exceptions for business logic? How does this improve safety?
- **Property-Based Testing**: Why Hypothesis over traditional TDD? What bugs has it found that examples missed?
- **Tooling choices**: Why ruff (over flake8/black/isort)? Why uv (over pip/poetry/pdm)?
- **Pydantic v2**: Why BaseModel over dataclasses/dicts? Performance vs ergonomics trade-off?
- **Generic syntax**: Why `Generic[T,E]` instead of PEP 695 `class Result[T,E]`? (mypy compatibility)

### 2. TESTING_FRAMEWORK_THINKING.md
**Location:** `docs/TESTING_FRAMEWORK_THINKING.md`
**Status:** ❌ Not started

**Decisions to capture:**
- **Testing pyramid inversion**: Why Component tests (real APIs) as PRIMARY over unit tests?
- **Sociable vs Solitary**: Why no mocks for internal classes? "Mock drift" experiences?
- **PBT as default**: Why prove invariants vs test examples? What edge cases were discovered?
- **FHIR sandbox testing**: Why test against real HAPI FHIR server vs mocking?

### 3. PRE_COMMIT_THINKING.md
**Location:** `docs/PRE_COMMIT_THINKING.md` (or thinking in `.pre-commit-config.yaml` comments)
**Status:** ❌ Not started

**Decisions to capture:**
- **Why pre-commit**: Why hooks vs CI-only? Friction vs early error detection trade-off?
- **Exclusions**: Why exclude `tests/` and `cli/` from mypy in pre-commit but not in CI?
- **Type checker version**: Why mypy 1.11.0 (not latest)? Compatibility concerns?

## Medium Priority Gaps

### 4. INTEGRATION_TESTING_THINKING.md
**Location:** `docs/INTEGRATION_TESTING_THINKING.md`
**Status:** ❌ Not started

**Decisions to capture:**
- **Wrapper pattern**: Why isolate business logic from FHIR complexity?
- **Real vs mock**: When is mocking acceptable (external APIs only)?
- **HAPI FHIR choice**: Why this specific sandbox server?

### 5. ARCHITECTURE_THINKING.md (verify if needed)
**Location:** `docs/ARCHITECTURE_THINKING.md` (only if needed)
**Status:** ❌ Not started

**Note:** Currently uses `ARCHITECTURE_DECISIONS.md` - verify if this covers all thinking or if a separate _THINKING file needed for:
- FastAPI choice over Flask/Django
- Async/await throughout vs sync
- The specific Result pattern implementation

## Reference Pattern

See `docs/BUSINESS_PURPOSE_THINKING.md` for exemplar structure including:
- Goals and Non-Goals
- Alternatives Considered
- Decision Criteria
- Trade-offs
- Risks and Mitigations
- Revisit Conditions

## When to Create Thinking Docs

Per `docs/THINKING_STANDARD.md`, create thinking docs when:
- Multiple approaches were evaluated
- Decision spans more than a single line
- Choice isn't obviously "best" and might be revisited
- Something significant was intentionally left out
- Trade-offs exist that future maintainers should understand
