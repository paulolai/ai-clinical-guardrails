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
- **Contract-First Integration:** Models validated against the **Full Official HL7 FHIR R5** standard.
- **Interface-Specific Tooling:** Dedicated CLI handles for each system interface (EMR vs. API).
- **Offline-First PWA:** Clinical transcription interface with local AI processing (Mac Studio deployment).
- **Invariant-Based Testing:** Uses Property-Based Testing (Hypothesis) to mathematically prove the guardrails can catch data hallucinations.

---

## 🏗 Architectural Patterns

| Pattern | Tool | Purpose |
| :--- | :--- | :--- |
| **Full Spec Validation** | `fhir.resources` | Validates data against the 50,000-line industry standard (R5). |
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
uv run python cli/emr.py inspect 90128869
```

**Guardrails API Interface:**
```bash
# Verify AI output via our service (API must be running)
uv run python cli/api.py verify-integrated --id 90128869 --text "Seen today." --dates "2025-02-20"
```

**Clinical Note Review Interface:**
```bash
# Create unified review for AI-generated note (API must be running)
uv run python cli/review.py create \
  --patient-id 90128869 \
  --transcript "Patient has hypertension, started on lisinopril"

# View formatted review with EMR context and verification results
uv run python cli/review.py view --note-id <note-id>
```

---

## 🚧 Work In Progress: Clinical Transcription PWA

We're building a **Progressive Web Application** for clinical voice transcription that runs entirely on-premise:

**Key Features:**
- 🎤 **Voice Recording** - Browser-based dictation with offline support
- 🤖 **Local AI Processing** - Whisper + Llama 3.1 70B on Mac Studio (128GB RAM)
- 🔒 **100% On-Premise** - Zero external dependencies, real patient data compliant
- 📱 **Offline-First** - Record offline, sync when connected
- ✅ **Integrated Verification** - Seamless integration with existing guardrails

**Architecture:**
- **Frontend:** HTMX (server-rendered) + Service Worker
- **Backend:** FastAPI (extends existing API)
- **AI:** Local Whisper + Local LLM (no cloud APIs)
- **Auth:** Self-hosted Keycloak
- **Deployment:** Docker Compose on Mac Studio

**Status:** [Design Complete](docs/plans/2025-02-23-clinical-transcription-pwa-design.md) | Implementation Phase: Pending

**Target Users:** 5-clinician medical practice (Australian GP/Specialist)

**Compliance:** Privacy Act 1988, AHPRA requirements, My Health Record ready

### 4. Run the API Server
```bash
uv run python main.py
```

---

## 📈 Verification Invariants

1.  **Date Integrity:** Every date extracted by the AI MUST exist within the patient's actual EMR context window.
2.  **Protocol Adherence:** Clinical triggers (e.g., Sepsis) must force documentation of mandatory actions.
3.  **Data Safety (PII):** Automated summaries are scanned for illegal patterns (e.g., Medicare Number) before they are safe to file.

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

## 🔧 Development

This project uses **[obra/superpowers](https://github.com/obra/superpowers)** - a collection of development skills and best practices that guide AI-assisted development workflows.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[RATIONALE](RATIONALE.md)** | Why this architecture exists |
| **[BUSINESS_PURPOSE](docs/BUSINESS_PURPOSE.md)** | What we're building and for whom |
| **[QUICKSTART](docs/QUICKSTART.md)** | 15-minute tutorial |
| **[AGENTS](AGENTS.md)** | Engineering principles & standards |
| **[PYTHON_STANDARDS](docs/PYTHON_STANDARDS.md)** | Code standards & patterns |
| **[ARCHITECTURE](docs/ARCHITECTURE.md)** | System design |
| **[THINKING_STANDARD](docs/THINKING_STANDARD.md)** | When and how to document decisions |
| **[FAQ](docs/FAQ.md)** | Common questions |
| **[GLOSSARY](docs/GLOSSARY.md)** | Terminology |
| **[CONTRIBUTING](CONTRIBUTING.md)** | How to extend |
| **[examples/](examples/)** | Runnable code |
