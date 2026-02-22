# Architecture Decision Records (ADR)

This repository demonstrates the **Invariant-Based Verification Pattern** for AI safety in regulated domains. We have made specific, non-standard choices to optimize for **Regulatory Compliance** and **Mathematical Rigor**.

This document explains the *Why* behind these decisions, and what alternatives were rejected.

<!-- toc -->

- [I. Testing Strategy](#i-testing-strategy)
  * [1. Testing Scope: Sociable over Solitary (No "Mock Drift")](#1-testing-scope-sociable-over-solitary-no-mock-drift)
  * [2. Rejection of Gherkin (Cucumber)](#2-rejection-of-gherkin-cucumber)
  * [3. Property-Based Testing First](#3-property-based-testing-first)
- [II. Architecture & Implementation](#ii-architecture--implementation)
  * [4. Result Pattern for Error Handling](#4-result-pattern-for-error-handling)
  * [5. Shared Core Pattern](#5-shared-core-pattern)
- [III. Compliance & Reporting](#iii-compliance--reporting)
  * [6. Dual-View Reporting](#6-dual-view-reporting)
  * [7. Deep Observability (Mandatory Tracing)](#7-deep-observability-mandatory-tracing)
  * [8. Dual-Coverage Strategy (Business vs. Code)](#8-dual-coverage-strategy-business-vs-code)
- [IV. CLI & Developer Experience](#iv-cli--developer-experience)
  * [9. Typer and Rich for CLI Tools](#9-typer-and-rich-for-cli-tools)
  * [10. Modular FHIR Models (Granular Imports)](#10-modular-fhir-models-granular-imports)

<!-- tocstop -->

---

## I. Testing Strategy

### 1. Testing Scope: Sociable over Solitary (No "Mock Drift")
**Status:** Accepted

#### The Decision
We prioritize **Sociable Tests** (Integration/Component) over **Solitary Unit Tests**.
-   **Pure Logic (Solitary):** Tested extensively (e.g., `ComplianceEngine`). Zero mocks allowed.
-   **Components/Services (Sociable):** Tested with real collaborators. We do *not* mock internal classes or functions.

#### Why?
*   **The "Mock Drift" Danger:** A mock represents your *assumption* of how a dependency works. When the real dependency changes but the mock doesn't, tests pass but production fails (The "Lying Test").
*   **Refactoring Resistance:** Mocks often couple tests to implementation details. Refactoring the internal flow breaks the test even if the behavior is correct.
*   **Maintenance Tax:** Keeping mocks synchronized with their real counterparts is low-value toil.

#### Rule
*   **Mock only at the Boundaries:** External APIs, Time, and Randomness.
*   **Never Mock Internals:** If Class A calls Class B, the test for Class A should run real Class B code.

---

### 2. Rejection of Gherkin (Cucumber)
**Status:** Accepted

#### The Decision
We explicitly reject Gherkin/Cucumber layers.
We use **TypeScript as the Specification Language**.

#### Why?
*   **The "Translation Tax":** Gherkin requires maintaining a regex mapping layer (`steps.ts`) between English and Code. This layer is expensive, brittle, and rarely read by stakeholders.
*   **Type Safety:** Gherkin text has no type safety. `Given I have 5 items` passes a string "5" to code that expects a number.
*   **Refactoring:** Renaming a business concept in TypeScript is one `F2` keypress. In Gherkin, it's a grep/sed nightmare.

#### The Alternative
We use **Attestation Reporting** to generate the "English" view from the code metadata, rather than writing English to generate code execution.

#### When to Revisit: Non-Technical Stakeholders
This decision assumes that business stakeholders primarily read generated reports, not raw tests. Consider Gherkin if you have:
- Active, technical product owners who write scenarios directly
- Regulatory requirements requiring natural-language artifacts stored alongside code

---

### 3. Property-Based Testing First
**Status:** Accepted

#### The Decision
We define business invariants first, prove them via Property-Based Testing (PBT), then implement the logic.
Example-based tests are used sparingly for documentation only.

#### Why?
*   **The "Happy Path" Trap:** Manual examples (e.g., "1 patient with Sepsis") only verify the obvious. Humans forget edge cases (leap years, empty strings, boundary conditions).
*   **Infinite Examples:** PBT generates hundreds of random, valid test cases automatically. The machine proves the rule holds for *all* inputs, not just the ones you thought of.
*   **Refactoring Safety:** When code changes, you don't need to manually add new examples. The invariant is re-verified against fresh random inputs.

#### Alternative Rejected: High-Coverage BDD Tables
**Rejected:** BDD "Scenario Outline" tables (e.g., 20 rows of test data) are brittle and create a false sense of completeness. They only verify the cases you explicitly write, not the infinite edge cases that PBT discovers automatically.

#### Rule
*   **Invariants over Examples:** Use `fast-check` to prove business rules.
*   **Examples are Documentation:** Only use `it('Example: ...')` to illustrate specific scenarios mentioned in the business spec.

**Example:**
```typescript
// This single test verifies the rule across 100 random patient records
it('Admission Date cannot be after Discharge Date', () => {
  verifyInvariant({
    ruleReference: 'PLAN.md §2.1',
    rule: 'Temporal consistency check'
  }, (patient, summary, result) => {
    expect(result.dischargeDate >= result.admissionDate).toBe(true);
  });
});
```

---

## II. Architecture & Implementation

### 4. Result Pattern for Error Handling
**Status:** Accepted

#### The Decision
We use the `Result<T, E>` discriminated union type for explicit error handling instead of throwing exceptions for business logic errors.

#### Why?
*   **Forces Error Handling:** With exceptions, it's easy to silently ignore errors (empty catch block). With `Result`, the compiler forces callers to handle both success and failure paths.
*   **Explicit Control Flow:** try/catch blocks can nest deeply and create complex control jumps. `Result` composes linearly with `map` and `chain` utilities.
*   **Type Safety:** Exceptions break type safety—any function can throw anything at runtime. `Result<T, E>` makes the error type `E` explicit in the function signature.
*   **Testability:** Testing functions that return `Result` is simpler—just assert on the return value. Testing exception-throwing functions requires mocking or try/catch wrapping.

#### Alternative Rejected: Exceptions for Business Logic
**Rejected:** Using exceptions for normal business flows (validation failures, "not found" errors) conflates truly exceptional errors with expected failure modes. This makes it harder to reason about what errors a function can actually produce.

#### The Pattern
```typescript
// Type definition
type Result<T, E> = Success<T> | Failure<E>;

interface Success<T> {
  success: true;
  value: T;
}

interface Failure<E> {
  success: false;
  error: E;
}

// Example usage
function verifyCompliance(context: PatientContext, summary: AISummary): Result<Verified, ComplianceAlert[]> {
  const alerts = runAllChecks(context, summary);
  if (alerts.length > 0) {
    return failure(alerts);
  }
  return success({ status: 'VERIFIED', timestamp: Date.now() });
}

// Compose operations safely
const result = verifyCompliance(patientContext, generatedSummary);

if (isSuccess(result)) {
  console.log('Compliance verified:', result.value.status);
} else {
  console.error('Compliance violations:', result.error);
}
```

#### Available Utilities
*   `success(value)` / `failure(error)` - Create Results
*   `isSuccess()` / `isFailure()` - Type guards
*   `map()` - Transform success values, propagate failures
*   `chain()` - Compose operations that return Results
*   `unwrap()` / `unwrapOr()` / `unwrapOrElse()` - Extract values
*   `match()` - Pattern matching for side effects
*   `all()` - Combine multiple Results
*   `tryCatch()` / `tryCatchAsync()` - Convert exceptions to Results
*   `fromNullable()` - Handle null/undefined values
*   `fromZod()` - Convert Zod validation results

#### Rule
*   **Use Result for Business Logic Failures:** Validation errors, compliance violations, expected failures.
*   **Keep Exceptions for True Exceptions:** Only throw for truly exceptional conditions (system corruption, programmer errors, things that should crash).
*   **Prefer `chain()` Over Nested `if isSuccess`:** The `chain` utility composes linearly and stops at the first failure.

---

### 5. Shared Core Pattern
**Status:** Accepted

#### The Decision
All test data generation lives in a monorepo-style `packages/shared` directory, consumed by test suites.

#### Why?
*   **Single Source of Truth:** The `CartBuilder` used in tests is identical across all test files.
*   **Semantic Integrity:** Types and schemas are defined once and shared across layers. A schema change instantly breaks all tests (a good thing).
*   **Cost Savings:** Avoids duplicate maintenance of test utilities.

#### Alternative Rejected: Separate Test Utilities
**Rejected:** Putting helpers in each implementation's `test/` directory creates duplication and drift. When a test changes in one file, the other files' helpers don't get updated, breaking the "Single Source of Truth."

#### Structure
```
packages/shared/
├── fixtures/
│   ├── cart-builder.ts      # Fluent API for creating carts (legacy e-commerce reference)
│   └── arbitraries.ts       # fast-check generators for PBT
└── src/
    ├── types.ts             # Zod schemas shared by all code and tests
    └── result.ts            # Result<T,E> pattern utilities
```

#### Rule
*   **Never Duplicate Builders:** If you need a helper for test data, it belongs in `packages/shared/fixtures`.
*   **No Magic Objects:** Tests must never use raw `{ name: "item", price: 100 }` literals. Always use `CartBuilder.new()` or future `PatientRecordBuilder.new()`.

---

## III. Compliance & Reporting

### 6. Dual-View Reporting
**Status:** Accepted

#### The Decision
We generate a custom HTML report that pivots the same test results into two views: **Technical** (Architecture) and **Business** (Goals).

#### Why?
*   **Audience Gap:** Developers care about *Components* (ComplianceEngine, Validators). Stakeholders care about *Goals* (Patient Safety, HIPAA Compliance).
*   **Single Source of Truth:** We don't want separate reports. One execution should satisfy both Engineering (Debuggability) and Compliance (Audit Trail).

---

### 7. Deep Observability (Mandatory Tracing)
**Status:** Accepted

#### The Decision
All tests **must** capture their inputs and outputs to a `tracer`. A test without a trace is considered **incomplete**.

#### Why?
*   **Audit Trail:** Regulated environments require evidence that tests actually ran with meaningful data, not just "PASS."
*   **Debuggability:** When a test fails, the trace shows exactly what inputs triggered the failure (critical for PBT counterexamples).
*   **Attestation Evidence:** The generated HTML report uses these traces to prove compliance to auditors.

#### Alternative Rejected: Basic Pass/Fail
**Rejected:** A green checkmark proves code ran, not that it verified meaningful business rules. Without trace data, regulators have no evidence of *what* was tested.

#### The Pattern
```typescript
// API Tests - Manual tracing
it('Invariant: Critical Protocol Check', () => {
  verifyInvariant({
    ruleReference: 'PLAN.md §2.2',
    rule: 'Sepsis requires antibiotic timing documentation'
  }, (patient, summary, result) => {
    tracer.log(testName, { patient, summary }, result);
    expect(result.hasAntibioticTiming).toBe(true);
  });
});
```

#### Verification Rule
After running tests, open `reports/{latest}/attestation-full.html`. If a test is listed but has no "Input/Output" trace, it is incomplete.

---

### 8. Dual-Coverage Strategy (Business vs. Code)
**Status:** Accepted

#### The Decision
We verify quality using two distinct coverage metrics that must **both** pass quality gates.
1.  **Code Coverage (Technical):** Do tests execute the lines of code?
2.  **Domain Coverage (Business):** Do tests verify the rules in the requirements document (PLAN.md)?

#### Why?
*   **The "Testing the Wrong Thing" Problem:** You can have 100% code coverage without testing a single business rule (e.g., executing a function but asserting nothing).
*   **The "Dead Requirements" Problem:** Features are often specified in Markdown but never implemented or tested. Domain Coverage highlights these gaps.
*   **Stakeholder Communication:** Compliance auditors don't care about `branches covered`. They care about `rules verified`.

#### Implementation
*   **Tooling:** We use a custom `DomainCoverageParser` that reads `PLAN.md` and maps it to test metadata (`ruleReference`).
*   **Reporting:** The final Attestation Report displays both metrics side-by-side.

#### Rule
*   **All new features need 2 layers of tests:** One to execute the code (Code Coverage) and one to verify the invariant (Domain Coverage).

#### Quality Gates
| Metric | Tool | Minimum Threshold | CI Gate |
|--------|------|-------------------|---------|
| Code Coverage (Lines) | vitest/v8 | 90% | Yes |
| Domain Coverage (Rules Verified) | DomainCoverageParser | 80% for critical features | Warning at 60%, Fail at 50% |

**Rationale for thresholds:**
- **90% code coverage**: Ensures dead code detection while allowing some unreachable error branches.
- **80% domain coverage**: Core safety rules must be verified. Lower rules may be documentation-only or pending implementation.

---

## IV. CLI & Developer Experience

### 9. Typer and Rich for CLI Tools
**Status:** Accepted

#### The Decision
We use **Typer** for building CLI utilities and **Rich** for terminal formatting.

#### Why?
*   **Consistency with FastAPI:** Typer is the CLI equivalent of FastAPI (built by the same author). It uses standard Python type hints to define arguments and options, creating a unified developer experience across the API and CLI.
*   **Type Safety as Documentation:** By using type hints, the CLI's interface is self-documenting and verifiable by static analysis tools (Ruff/Mypy).
*   **High-Visibility Safety Status:** In a clinical context, "Safe to File" vs. "Blocked" status must be unmistakable. Rich allows us to use bold colors and stylized banners to ensure the user cannot misinterpret the engine's verdict.
*   **Automatic Help Generation:** Typer generates beautiful, color-coded --help menus from docstrings and type hints without manual effort.

#### Alternative Rejected: Click
**Rejected:** While Click is mature, it relies on decorators for type definition rather than native Python type hints. This leads to duplication of type information and less effective IDE support compared to Typer.

#### Rule
*   **Use Rich for Status Verdicts:** All CLI outputs indicating safety status must use Rich's `console.print` with appropriate semantic colors (Green for Safe, Red for Blocked).
*   **Define Types Explicitly:** Use `typer.Option` and `typer.Argument` with explicit type hints and help text.
# ADR 010: Modular FHIR Model Generation

**Status:** Proposed
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)

## The Problem
The current FHIR integration uses a single, monolithic `generated.py` file containing the full HL7 FHIR R4 specification (~50,000 lines, 3MB).

Even with lazy loading in `FHIRClient`, any import of this module (e.g., `from .generated import Patient`) causes Python to parse and execute the entire file. This results in a **16-20 second bottleneck** during the first interaction with the EMR layer, severely impacting CLI responsiveness and test suite execution time.

## The Decision
We will transition from a single-file model to a **Modular Package** generation strategy.

1.  **Regenerate Models:** Use `datamodel-codegen` to output a package (directory) instead of a single file.
2.  **Granular Imports:** Refactor `FHIRClient` to import specific resource models from their respective modules (e.g., `from .models.patient import Patient`).
3.  **Maintain Full Spec:** We continue to generate the *entire* FHIR R4 spec to ensure contract-first integrity, but we leverage Python's filesystem-based module system to only load what is used.

## Why?
*   **Performance (20s -> 20ms):** Python only parses the specific files required for the requested resource (e.g., `patient.py` and its direct dependencies like `human_name.py`), rather than the entire 50,000-line universe.
*   **Zero-Trust Integrity:** We maintain the "Full Official Spec" requirement. We are not "cherry-picking" or manually writing models, which would introduce "Contract Drift" risk.
*   **Developer Experience:** CLI tools (`cli/emr.py`) become "instant-on," which is critical for clinical workflows where sub-second latency is expected.
*   **Test Suite Efficiency:** Component tests can run in parallel without each process incurring a 20s startup tax.

## Alternatives Rejected

### 1. Manual Subset Models
**Rejected:** Hand-writing a `Patient` model would be fast but violates our **Contract-First** principle. It introduces the risk that our internal model deviates from the official HL7 standard, leading to silent failures in production EMR integrations.

### 2. Standard Lazy-Import Wrappers
**Rejected:** Tools like `lazy_import` still eventually trigger the full parse of the monolithic file upon the first attribute access. The bottleneck is the physical size of the single `.py` file.

### 3. External Libraries (e.g., fhir.resources)
**Rejected:** While comprehensive, external libraries often have their own large dependency trees and may not align with our specific Pydantic v2 / Python 3.12 performance targets. Generating our own modular code gives us full control over the Pydantic configuration (e.g., `extra='forbid'`).

## Implementation Plan
1. Update `docs/WORKFLOW_SPEC.md` with the new modular command.
2. Run the generator to create `src/integrations/fhir/models/`.
3. Update `src/integrations/fhir/client.py` to use granular imports.
4. Remove the obsolete `src/integrations/fhir/generated.py`.
5. Verify performance via `tests/component/test_fhir_client.py`.
# ADR 011: Use fhir.resources Package

**Status:** Proposed
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)
**Supersedes:** ADR 010 (Modular FHIR Models)

## The Problem
The `generated.py` file from ADR 010 was intended to be modular, but `datamodel-code-generator` produces a heavy `_internal.py` file (1.2MB) to handle circular dependencies, resulting in imports taking **29 seconds**—slower than the original monolithic file.

We need a solution that provides instant (<1s) import times for the `FHIRClient` while maintaining type safety and spec compliance.

## The Decision
We will replace our custom-generated FHIR models with the community-standard **`fhir.resources`** package.

1.  **Dependency:** Add `fhir.resources` (Pydantic v2 compatible).
2.  **Removal:** Delete `src/integrations/fhir/generated.py` and the `datamodel-codegen` step.
3.  **Refactor:** Update `FHIRClient` to use `fhir.resources.patient.Patient` and `fhir.resources.encounter.Encounter`.

## Why?
*   **Performance (29s -> 0.2s):** `fhir.resources` is highly optimized for modular loading, achieving **100x faster import times**.
*   **Standardization:** It is the de-facto Python library for FHIR resources, maintained by the community and tested against the spec.
*   **Maintenance:** We offload the complexity of generating correct Pydantic models from the massive FHIR JSON schema to the `fhir.resources` maintainers.
*   **Simplicity:** `fhir.resources` uses standard Python types (e.g., `str` for `id`) instead of `RootModel` wrappers, simplifying our code (no more `.root` access).

## Alternatives Considered

### 1. Modular Generation (ADR 010)
**Rejected:** Attempted in `src/integrations/fhir/models_test/`. Resulted in 29s import times due to `_internal.py` overhead.

### 2. Manual Schema Splitting
**Rejected:** Writing a custom script to split `fhir.r4.schema.json` into 1000 individual schema files is complex, error-prone, and high maintenance.

### 3. Lazy Imports (Current State)
**Rejected:** Still requires full parsing of the 3MB file on first use, causing unacceptable UI lag.

## Implementation Plan
1.  Add `fhir.resources` to `pyproject.toml`.
2.  Update `src/integrations/fhir/client.py` to import from `fhir.resources`.
3.  Remove `src/integrations/fhir/generated.py`.
4.  Verify tests pass.
# ADR 012: Use fhir.resources Package (FHIR R5)

**Status:** Accepted
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)
**Supersedes:** ADR 010 (Modular Generation), ADR 011 (Subset Generation)

## The Problem
Maintaining custom-generated Pydantic models for FHIR is proving complex and slow.
- **Monolithic Generation:** 20s import time.
- **Modular Generation:** Circular dependency hell (`_internal.py` is 1.2MB).
- **Subset Generation:** Requires complex custom scripting and strict manual dependency management.

## The Decision
We will adopt the community-standard **`fhir.resources`** library (version 8.x+), which supports **FHIR R5** and **Pydantic v2**.

1.  **Dependency:** `fhir.resources>=8.0.0`
2.  **FHIR Version:** Upgrade project from R4 to **R5** to match the library's support.
3.  **Endpoint:** Switch HAPI Sandbox to `http://hapi.fhir.org/baseR5`.
4.  **Refactor:** Update `FHIRClient` to use standard library imports.

## Why?
*   **Performance:** Instant imports (<1s) due to optimized package structure.
*   **Maintenance:** Offload model correctness and updates to the library maintainers.
*   **Standardization:** Aligns with the broader Python FHIR ecosystem.
*   **Future-Proofing:** Moving to FHIR R5 ensures compatibility with modern healthcare standards.

## Alternatives Rejected
*   **Sticking with R4:** The only Pydantic v2-compatible version of `fhir.resources` (8.x) requires R5. Downgrading Pydantic to v1 is not an option as our entire codebase uses v2.
*   **Custom Generation:** Too much maintenance overhead for zero business value.

## Implementation Plan
1.  `uv add fhir.resources>=8.0.0`
2.  Delete `src/integrations/fhir/generated.py` and generation scripts.
3.  Update `FHIRClient` to import from `fhir.resources` and point to R5 sandbox.
4.  Update tests and snapshots.
