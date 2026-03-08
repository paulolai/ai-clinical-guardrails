# ADR Extracts for AI Agents

This document is **GENERATED** from `docs/ARCHITECTURE_DECISIONS.md`.
DO NOT EDIT MANUALLY - Changes will be overwritten.

Last generated: 2026-03-08T17:59:52.617591

---

## Testing Strategy

🏛️ **[DECISION]** We prioritize **Sociable Tests** (Integration/Component) over **Solitary Unit Tests**.
   *ADR-1: Testing Scope: Sociable over Solitary (No "Mock Drift")* (The Decision)

🏛️ **[DECISION]** **Pure Logic (Solitary):** Tested extensively (e.g., `ComplianceEngine`). Zero mocks allowed.
   *ADR-1: Testing Scope: Sociable over Solitary (No "Mock Drift")* (The Decision)

🏛️ **[DECISION]** **Components/Services (Sociable):** Tested with real collaborators. We do *not* mock internal classes or functions.
   *ADR-1: Testing Scope: Sociable over Solitary (No "Mock Drift")* (The Decision)

✅ **[MUST]** **Mock only at the Boundaries:** External APIs, Time, and Randomness.
   *ADR-1: Testing Scope: Sociable over Solitary (No "Mock Drift")* (Rule)

✅ **[MUST]** **Never Mock Internals:** If Class A calls Class B, the test for Class A should run real Class B code.
   *ADR-1: Testing Scope: Sociable over Solitary (No "Mock Drift")* (Rule)

🏛️ **[DECISION]** We explicitly reject Gherkin/Cucumber layers.
   *ADR-2: Rejection of Gherkin (Cucumber)* (The Decision)

🏛️ **[DECISION]** We use **TypeScript as the Specification Language**.
   *ADR-2: Rejection of Gherkin (Cucumber)* (The Decision)

🏛️ **[DECISION]** We define business invariants first, prove them via Property-Based Testing (PBT), then implement the logic.
   *ADR-3: Property-Based Testing First* (The Decision)

🏛️ **[DECISION]** Example-based tests are used sparingly for documentation only.
   *ADR-3: Property-Based Testing First* (The Decision)

✅ **[MUST]** **Invariants over Examples:** Use `fast-check` to prove business rules.
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** **Examples are Documentation:** Only use `it('Example: ...')` to illustrate specific scenarios mentioned in the business spec.
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** *Example:**
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** // This single test verifies the rule across 100 random patient records
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** it('Admission Date cannot be after Discharge Date', () => {
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** verifyInvariant({
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** ruleReference: 'PLAN.md §2.1',
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** rule: 'Temporal consistency check'
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** }, (patient, summary, result) => {
   *ADR-3: Property-Based Testing First* (Rule)

✅ **[MUST]** expect(result.dischargeDate >= result.admissionDate).toBe(true);
   *ADR-3: Property-Based Testing First* (Rule)

---

## Architecture & Implementation

🏛️ **[DECISION]** We use the `Result<T, E>` discriminated union type for explicit error handling instead of throwing exceptions for business logic errors.
   *ADR-4: Result Pattern for Error Handling* (The Decision)

ℹ️ **[INFO]** // Type definition
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** type Result<T, E> = Success<T> | Failure<E>;
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** interface Success<T> {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** success: true;
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** value: T;
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** interface Failure<E> {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** success: false;
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** error: E;
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** // Example usage
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** function verifyCompliance(context: PatientContext, summary: AISummary): Result<Verified, ComplianceAlert[]> {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** const alerts = runAllChecks(context, summary);
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** if (alerts.length > 0) {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** return failure(alerts);
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** return success({ status: 'VERIFIED', timestamp: Date.now() });
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** // Compose operations safely
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** const result = verifyCompliance(patientContext, generatedSummary);
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** if (isSuccess(result)) {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** console.log('Compliance verified:', result.value.status);
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** } else {
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

ℹ️ **[INFO]** console.error('Compliance violations:', result.error);
   *ADR-4: Result Pattern for Error Handling* (The Pattern)

✅ **[MUST]** **Use Result for Business Logic Failures:** Validation errors, compliance violations, expected failures.
   *ADR-4: Result Pattern for Error Handling* (Rule)

✅ **[MUST]** **Keep Exceptions for True Exceptions:** Only throw for truly exceptional conditions (system corruption, programmer errors, things that should crash).
   *ADR-4: Result Pattern for Error Handling* (Rule)

✅ **[MUST]** **Prefer `chain()` Over Nested `if isSuccess`:** The `chain` utility composes linearly and stops at the first failure.
   *ADR-4: Result Pattern for Error Handling* (Rule)

🏛️ **[DECISION]** All test data generation lives in a monorepo-style `packages/shared` directory, consumed by test suites.
   *ADR-5: Shared Core Pattern* (The Decision)

✅ **[MUST]** **Never Duplicate Builders:** If you need a helper for test data, it belongs in `packages/shared/fixtures`.
   *ADR-5: Shared Core Pattern* (Rule)

✅ **[MUST]** **No Magic Objects:** Tests must never use raw `{ name: "item", price: 100 }` literals. Always use `CartBuilder.new()` or future `PatientRecordBuilder.new()`.
   *ADR-5: Shared Core Pattern* (Rule)

---

## Compliance & Reporting

🏛️ **[DECISION]** We generate a custom HTML report that pivots the same test results into two views: **Technical** (Architecture) and **Business** (Goals).
   *ADR-6: Dual-View Reporting* (The Decision)

🏛️ **[DECISION]** All tests **must** capture their inputs and outputs to a `tracer`. A test without a trace is considered **incomplete**.
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Decision)

ℹ️ **[INFO]** // API Tests - Manual tracing
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** it('Invariant: Critical Protocol Check', () => {
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** verifyInvariant({
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** ruleReference: 'PLAN.md §2.2',
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** rule: 'Sepsis requires antibiotic timing documentation'
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** }, (patient, summary, result) => {
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** tracer.log(testName, { patient, summary }, result);
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

ℹ️ **[INFO]** expect(result.hasAntibioticTiming).toBe(true);
   *ADR-7: Deep Observability (Mandatory Tracing)* (The Pattern)

✅ **[MUST]** After running tests, open `reports/{latest}/attestation-full.html`. If a test is listed but has no "Input/Output" trace, it is incomplete.
   *ADR-7: Deep Observability (Mandatory Tracing)* (Verification Rule)

🏛️ **[DECISION]** We verify quality using two distinct coverage metrics that must **both** pass quality gates.
   *ADR-8: Dual-Coverage Strategy (Business vs. Code)* (The Decision)

🏛️ **[DECISION]** 1.  **Code Coverage (Technical):** Do tests execute the lines of code?
   *ADR-8: Dual-Coverage Strategy (Business vs. Code)* (The Decision)

🏛️ **[DECISION]** 2.  **Domain Coverage (Business):** Do tests verify the rules in the requirements document (PLAN.md)?
   *ADR-8: Dual-Coverage Strategy (Business vs. Code)* (The Decision)

✅ **[MUST]** **All new features need 2 layers of tests:** One to execute the code (Code Coverage) and one to verify the invariant (Domain Coverage).
   *ADR-8: Dual-Coverage Strategy (Business vs. Code)* (Rule)

---

## CLI & Developer Experience

🏛️ **[DECISION]** We use **Typer** for building CLI utilities and **Rich** for terminal formatting.
   *ADR-9: Typer and Rich for CLI Tools* (The Decision)

✅ **[MUST]** **Use Rich for Status Verdicts:** All CLI outputs indicating safety status must use Rich's `console.print` with appropriate semantic colors (Green for Safe, Red for Blocked).
   *ADR-9: Typer and Rich for CLI Tools* (Rule)

✅ **[MUST]** **Define Types Explicitly:** Use `typer.Option` and `typer.Argument` with explicit type hints and help text.
   *ADR-9: Typer and Rich for CLI Tools* (Rule)

---

## Infrastructure & Persistence

🏛️ **[DECISION]** We will transition from a single-file model to a **Modular Package** generation strategy.
   *ADR-10: Modular FHIR Models (Granular Imports)* (The Decision)

🏛️ **[DECISION]** 1.  **Regenerate Models:** Use `datamodel-codegen` to output a package (directory) instead of a single file.
   *ADR-10: Modular FHIR Models (Granular Imports)* (The Decision)

🏛️ **[DECISION]** 2.  **Granular Imports:** Refactor `FHIRClient` to import specific resource models from their respective modules (e.g., `from .models.patient import Patient`).
   *ADR-10: Modular FHIR Models (Granular Imports)* (The Decision)

🏛️ **[DECISION]** 3.  **Maintain Full Spec:** We continue to generate the *entire* FHIR R4 spec to ensure contract-first integrity, but we leverage Python's filesystem-based module system to only load what is used.
   *ADR-10: Modular FHIR Models (Granular Imports)* (The Decision)

🏛️ **[DECISION]** We will replace our custom-generated FHIR models with the community-standard **`fhir.resources`** package.
   *ADR-11: Use fhir.resources Package* (The Decision)

🏛️ **[DECISION]** 1.  **Dependency:** Add `fhir.resources` (Pydantic v2 compatible).
   *ADR-11: Use fhir.resources Package* (The Decision)

🏛️ **[DECISION]** 2.  **Removal:** Delete `src/integrations/fhir/generated.py` and the `datamodel-codegen` step.
   *ADR-11: Use fhir.resources Package* (The Decision)

🏛️ **[DECISION]** 3.  **Refactor:** Update `FHIRClient` to use `fhir.resources.patient.Patient` and `fhir.resources.encounter.Encounter`.
   *ADR-11: Use fhir.resources Package* (The Decision)

🏛️ **[DECISION]** We will adopt the community-standard **`fhir.resources`** library (version 8.x+), which supports **FHIR R5** and **Pydantic v2**.
   *ADR-12: Use fhir.resources Package (FHIR R5)* (The Decision)

🏛️ **[DECISION]** 1.  **Dependency:** `fhir.resources>=8.0.0`
   *ADR-12: Use fhir.resources Package (FHIR R5)* (The Decision)

🏛️ **[DECISION]** 2.  **FHIR Version:** Upgrade project from R4 to **R5** to match the library's support.
   *ADR-12: Use fhir.resources Package (FHIR R5)* (The Decision)

🏛️ **[DECISION]** 3.  **Endpoint:** Switch HAPI Sandbox to `http://hapi.fhir.org/baseR5`.
   *ADR-12: Use fhir.resources Package (FHIR R5)* (The Decision)

🏛️ **[DECISION]** 4.  **Refactor:** Update `FHIRClient` to use standard library imports.
   *ADR-12: Use fhir.resources Package (FHIR R5)* (The Decision)

🏛️ **[DECISION]** We use **SQLite (with WAL Mode)** as the primary persistence layer for local clinic deployments, instead of PostgreSQL.
   *ADR-13: Use SQLite for Local Clinic Deployments* (The Decision)

⚙️ **[CONFIG]** **Driver:** `aiosqlite` (Async)
   *ADR-13: Use SQLite for Local Clinic Deployments* (Configuration)

⚙️ **[CONFIG]** **Mode:** `PRAGMA journal_mode=WAL` (Critical for concurrency)
   *ADR-13: Use SQLite for Local Clinic Deployments* (Configuration)

⚙️ **[CONFIG]** **Safety:** `PRAGMA synchronous=NORMAL`
   *ADR-13: Use SQLite for Local Clinic Deployments* (Configuration)

✅ **[MUST]** **Always Enable WAL:** The application must explicitly configure `journal_mode=WAL` on startup.
   *ADR-13: Use SQLite for Local Clinic Deployments* (Rule)

✅ **[MUST]** **Use Batch Migrations:** Alembic must use `render_as_batch=True` to handle SQLite's limited schema alteration support.
   *ADR-13: Use SQLite for Local Clinic Deployments* (Rule)

---
