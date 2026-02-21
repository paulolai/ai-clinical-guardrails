# Testing Framework Thinking

This document captures the rationale behind our testing strategy, specifically the decision to invert the traditional testing pyramid and prioritize property-based testing.

## Context

We are building a high-assurance clinical guardrail system. The cost of failure is high (patient safety), and the system integrates with complex, variable external standards (FHIR).

## core Decisions

### 1. Inverting the Testing Pyramid

**Decision:**
Prioritize **Component Tests** (testing against real/containerized dependencies) over **Unit Tests** (testing with mocks).

**Rationale:**
- **Mock Drift:** In integration-heavy systems, mocks often represent the developer's *understanding* of an API, not its *reality*. Mocks drift from the real implementation, leading to false positives (tests pass, production fails).
- **Behavioral Verification:** We care that the system works with a real FHIR server, not that it calls a specific method on a mock object.
- **Refactoring Safety:** "Sociable" tests (using real collaborators) allow internal refactoring without breaking tests. "Solitary" tests (using mocks) couple tests to implementation details.

**Trade-offs:**
- **Speed:** Component tests are slower than unit tests. We mitigate this by using fast containerized dependencies (e.g., HAPI FHIR in Docker) and efficient test runners (`uv`, `pytest-xdist`).
- **Complexity:** Setup is harder (requires Docker/services). We mitigate this with a unified `TestDataManager`.

### 2. Property-Based Testing (PBT) as Default

**Decision:**
Use **Hypothesis** to test invariants (properties that always hold true) rather than just example-based testing.

**Rationale:**
- **The "Infinite" Input Space:** Clinical data is messy and unpredictable. Human-written examples cover the "happy path" and known edge cases but miss the "unknown unknowns."
- **Machine-Generated Discovery:** PBT generates thousands of test cases, including minimal examples of failure (shrinking), uncovering edge cases we wouldn't think to write.
- **Specification-Driven:** Writing properties forces us to clearly define the *rules* of the domain (e.g., "End date must always be >= start date") rather than just checking specific values.

**Trade-offs:**
- **Learning Curve:** Writing properties requires a different mindset than writing examples.
- **Performance:** Running 100 examples per test is slower. We mitigate this with profile configuration (dev vs. CI settings).

### 3. Real FHIR Sandbox (HAPI)

**Decision:**
Test against a real, running HAPI FHIR server instance in CI and local dev, rather than mocking HTTP responses.

**Rationale:**
- **Spec Complexity:** The FHIR spec is massive and has subtle validation rules. Re-implementing this validation in mocks is error-prone and redundant.
- **Vendor Variances:** Real servers exhibit behaviors (pagination, search sorting, error formats) that mocks miss.
- **Zero-Trust Integration:** We treat the external world as untrusted. Testing against a real server proves our "Wrapper" layer correctly isolates us from these complexities.

**Alternatives Considered:**
- **VCR/Betamax:** Recording real interactions. Rejected because it makes tests brittle to minor data changes and doesn't test the *logic* against new data, only replays old data.
- **In-memory FHIR mocks:** Rejected due to "Mock Drift" and lack of full spec compliance.

### 4. Sociable vs. Solitary Unit Tests

**Decision:**
When writing unit tests (for pure logic), prefer "Sociable" tests that use real domain objects over "Solitary" tests that mock internal classes.

**Rationale:**
- **Value:** We want to verify the *outcome* of business logic, not the *collaboration* between internal classes.
- **Resilience:** Internal refactoring (extracting a class, merging methods) shouldn't break tests if the behavior is unchanged. Mocks make tests rigid.

## Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **Slow Test Suite** | Parallel execution (`pytest-xdist`), distinct profiles for Dev vs. CI (fewer PBT examples in Dev). |
| **Flaky Tests** | PBT `deadline` settings, deterministic seeding for randomized data generators. |
| **Complex Setup** | Invest heavily in `TestDataManager` and `docker-compose` to make "spinning up the world" a single command. |

## Revisit Conditions

- **If test times exceed 10 minutes:** We may need to introduce more solitary unit tests for the slowest components or optimize the PBT generation strategies.
- **If HAPI FHIR becomes a bottleneck:** We might explore lighter-weight compliant servers, but only if they offer strict spec parity.
