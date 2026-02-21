# AI Clinical Guardrails

[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

**High-Assurance Documentation Safety**

> **The "Staff+" Thesis:** This repository demonstrates how to scale engineering output using AI while maintaining zero-defect quality standards. I acted as the Principal Architect, establishing the "Zero-Trust" constraints and verification systems that the AI implementation team operated within.
>
> [**Read the full Engineering Rationale →**](RATIONALE.md)

A deterministic verification platform designed to prevent LLM hallucinations and ensure process compliance in healthcare administrative workflows.

## 🎯 The Mission: Clinical-Grade AI Engineering

This project demonstrates how to productionize AI in highly regulated clinical environments using **Invariant-Based Verification**. 

It serves as a reference implementation for a modern, high-assurance AI stack using **Python (FastAPI)** and **FHIR**, adhering to the following engineering standards:

- **Zero-Trust Data Policy:** LLMs are never trusted with calendar logic or data extraction. Every output is verified against the EMR source of truth via deterministic Pydantic schemas.
- **Contract-First Integration:** Models generated directly from the **Full Official HL7 FHIR R4 JSON Schema**.
- **Interface-Specific Tooling:** Dedicated CLI handles for each system interface (EMR vs. API).
- **Invariant-Based Testing:** Uses Property-Based Testing (Hypothesis) to mathematically prove the guardrails can catch data hallucinations.

---

## 🏗 Architectural Patterns

| Pattern | Tool | Purpose |
| :--- | :--- | :--- |
| **Full Spec Generation** | `HL7 FHIR R4` | Uses the actual 50,000-line industry standard for data models. |
| **Domain Wrapper** | `FHIRClient` | Selective mapping that shields business logic from upstream EMR noise. |
| **Schema-First** | `Pydantic v2` | Strict runtime validation of clinical data. |
| **Result Pattern** | `Generic[T, E]` | Ensures deterministic error handling and prevents "exception-swallowing." |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- `uv` (recommended)

### 2. Installation
```bash
uv sync
```

### 3. Developer Debugging (CLI)
The project provides specific CLI tools named after the interfaces they serve:

**EMR (FHIR) Interface:**
```bash
export PYTHONPATH=$PYTHONPATH:.
# Directly inspect data in the HAPI FHIR Sandbox
uv run python cli/fhir.py inspect 90128869
```

**Guardrails API Interface:**
```bash
# Verify AI output via our service (API must be running)
uv run python cli/api.py verify-integrated --id 90128869 --text "Seen today." --dates "2025-02-20"
```

### 4. Run the API Server
```bash
uv run python main.py
```

---

## 📈 Verification Invariants

1.  **Date Integrity:** Every date extracted by the AI MUST exist within the patient's actual EMR context window.
2.  **Protocol Adherence:** Clinical triggers (e.g., Sepsis) must force documentation of mandatory actions.
3.  **Data Safety (PII):** Automated summaries are scanned for illegal patterns (e.g., SSN) before they are safe to file.

---

## 🧪 Testing

This project uses **Property-Based Testing (PBT)** to mathematically prove safety invariants hold across all possible inputs.

**Quick Start:**
```bash
# Run all tests
uv run pytest tests/ -v

# Run unit tests only (fast)
uv run pytest tests/ -m "not component" -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

**Documentation:**
- **[Testing Framework](docs/TESTING_FRAMEWORK.md)** - Mathematical safety proofs
- **[Testing Workflows](docs/TESTING_WORKFLOWS.md)** - Complete command reference
- **[Integration Testing](docs/INTEGRATION_TESTING.md)** - Component tests against real FHIR
- **[Debugging Guide](docs/DEBUGGING_GUIDE.md)** - Troubleshooting failed tests

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICKSTART](docs/QUICKSTART.md)** | 15-minute tutorial |
| **[AGENTS](AGENTS.md)** | Engineering principles |
| **[PYTHON_STANDARDS](docs/PYTHON_STANDARDS.md)** | Code standards & patterns |
| **[ARCHITECTURE](docs/ARCHITECTURE.md)** | System design |
| **[FAQ](docs/FAQ.md)** | Common questions |
| **[GLOSSARY](docs/GLOSSARY.md)** | Terminology |
| **[CONTRIBUTING](CONTRIBUTING.md)** | How to extend |
| **[examples/](examples/)** | Runnable code |
