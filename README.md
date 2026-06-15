# AI Clinical Guardrails

[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Tests](https://github.com/paulolai/ai-clinical-guardrails/actions/workflows/ci.yml/badge.svg)](https://github.com/paulolai/ai-clinical-guardrails/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue)](LICENSE)

A deterministic verification platform for preventing LLM hallucinations in healthcare documentation.

## What It Does

Verifies AI-generated clinical documentation against the EMR source of truth before it can be filed. Catches hallucinated dates, missing protocol documentation, PII leaks, and dangerous drug combinations.

**Read the [Architecture Rationale](RATIONALE.md) for why it's built this way.**

## Key Invariants

1. **Date Integrity** — Every extracted date must exist in the patient's EMR context window
2. **Protocol Adherence** — Clinical triggers (e.g., Sepsis) force documentation of mandatory actions
3. **Data Safety** — Automated summaries are scanned for PII patterns before filing
4. **Drug Interactions** — Configurable rules catch dangerous medication combinations
5. **Allergy Conflicts** — Patient allergies are checked against prescribed medications
6. **Duplicate Therapy** — Multiple medications in the same therapeutic class are flagged

## Quick Start

```bash
uv sync
uv run pytest tests/ -m "not component" -v
```

## Running the API

```bash
uv run python main.py
# Swagger UI: http://localhost:8000/docs
```

## CLI Tools

```bash
# Inspect patient data from HAPI FHIR sandbox
uv run python cli/emr.py inspect 90128869

# Verify AI output against EMR
uv run python cli/api.py verify-integrated --id 90128869 --text "Seen today." --dates "2025-02-20"

# Create clinical note review
uv run python cli/review.py create --patient-id 90128869 --transcript "Patient has hypertension, started on lisinopril"
```

## Testing

```bash
# Unit tests (fast)
uv run pytest tests/ -m "not component" -v

# All tests including component tests against real FHIR
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

The project uses [Property-Based Testing](https://hypothesis.readthedocs.io/) (Hypothesis) to generate randomized inputs and verify invariants hold across a wide range of clinical scenarios. Component tests run against the HAPI FHIR R5 sandbox using VCR cassettes.

## Tech Stack

- **Python 3.12+** / **FastAPI** / **Pydantic v2**
- **FHIR R5** via `fhir.resources`
- **Hypothesis** for property-based testing
- **OpenTelemetry** for traces, metrics, and logs (OTLP exporter)
- **SQLite** (WAL mode) for local persistence
- **HTMX** for the clinical transcription PWA (planned)

## Documentation

| Document | Purpose |
|----------|---------|
| [RATIONALE](RATIONALE.md) | Architecture decisions |
| [ADDING_A_RULE](docs/ADDING_A_RULE.md) | End-to-end workflow walkthrough |
| [AGENTS](AGENTS.md) | Engineering standards |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | System design |
| [TESTING_FRAMEWORK](docs/TESTING_FRAMEWORK.md) | Testing strategy |
| [INTEGRATION_TESTING](docs/INTEGRATION_TESTING.md) | Component test approach |
| [PYTHON_STANDARDS](docs/PYTHON_STANDARDS.md) | Code standards |
