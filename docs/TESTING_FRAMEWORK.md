# Clinical Testing Framework: Mathematical Safety Proofs

## Philosophy: High-Assurance Verification
For clinical documentation, "it works on my machine" is insufficient. We use **Property-Based Testing (PBT)** to prove that our safety invariants hold true across an infinite variety of patient profiles.

## The Stack
- **`pytest`**: The core test runner.
- **`Hypothesis`**: The PBT engine used to generate randomized clinical data.
- **`FastAPI TestClient`**: Used for integration testing the "Zero-Trust" API.

---

## 🔬 Test Layers

### 1. Domain Invariants (Hypothesis)
We don't test single examples. We define **Invariants**—rules that must *always* be true.
- **The Date Lock Invariant:** `assert not ComplianceEngine.verify(..., hallucinated_date).is_success`
- **The PII Firewall Invariant:** `assert not ComplianceEngine.verify(..., ssn_pattern).is_success`

### 2. Integration Tests (API)
We verify that the FastAPI `/verify` endpoint correctly consumes EMR context and returns the structured `Result` type, ensuring a safe contract for external integrations.

---

## 🤖 Zero-Trust Date Strategy
As learned from high-scale AI systems, LLMs are notoriously bad at calendar logic. Our testing framework enforces a **Zero-Trust policy**:
1.  We generate randomized `EMRContext` objects with strict admission/discharge windows.
2.  We generate `AIGeneratedOutput` with dates outside those windows.
3.  We prove the engine **mathematically blocks** the documentation every single time.

## 📊 Attestation Reporting
Every test run generates an `attestation_report.html`. This serves as the **Clinical Safety Case**, providing evidence to hospital stakeholders that the AI Agent is being monitored by a deterministic governor.

---

## 📖 Further Reading

- **[Testing Quick Start](../tests/README.md)** - Getting started with tests
- **[Testing Philosophy](../tests/AGENTS.md)** - Testing Trophy model, test categories
- **[Testing Workflows](TESTING_WORKFLOWS.md)** - Complete command reference
- **[Integration Testing](INTEGRATION_TESTING.md)** - Component tests with real FHIR
- **[Debugging Guide](DEBUGGING_GUIDE.md)** - Troubleshooting test failures
