# Testing Framework

## Philosophy

For clinical documentation, "it works on my machine" is insufficient. We use **Property-Based Testing (PBT)** to verify that safety invariants hold across a wide range of randomized inputs.

## The Stack

- **`pytest`**: The core test runner
- **`Hypothesis`**: The PBT engine used to generate randomized clinical data
- **`FastAPI TestClient`**: Used for integration testing the API

## Test Layers

### 1. Property-Based Invariants (Hypothesis)

We define invariants — rules that must always be true — and use Hypothesis to generate hundreds of random inputs per test run:

- **Date Lock**: Any date outside the EMR context window is flagged as a hallucination
- **PII Firewall**: Medicare Number patterns in summaries trigger a critical alert
- **Protocol Adherence**: Sepsis diagnoses without antibiotic documentation generate a HIGH alert

### 2. Component Tests (Real FHIR)

Tests against the HAPI FHIR R5 sandbox using VCR cassettes. Proves the integration works against the real API before any mocking is introduced.

### 3. API Integration Tests

Verifies that the FastAPI `/verify` endpoint correctly consumes EMR context and returns the structured `Result` type.

## Attestation Reporting

Every test run generates an `attestation_report.html` providing evidence of which safety invariants were verified and their outcomes.

## Further Reading

- [Testing Workflows](TESTING_WORKFLOWS.md) — Complete command reference
- [Integration Testing](INTEGRATION_TESTING.md) — Component tests with real FHIR
- [Debugging Guide](DEBUGGING_GUIDE.md) — Troubleshooting test failures
