# 15-Minute Quickstart

Get up and running with AI Clinical Guardrails in 15 minutes.

## Prerequisites

- Python 3.12+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Step 1: Clone and Setup (2 min)

```bash
git clone <repo>
cd ai-clinical-guardrails
uv sync
```

## Step 2: Run Your First Verification (5 min)

```bash
# Verify AI output against EMR
export PYTHONPATH=$PYTHONPATH:.
uv run python cli/api.py verify \
  --id 90128869 \
  --text "Patient seen on 2025-02-21 for follow-up."
```

Expected output:
```json
{
  "decision": "APPROVED",
  "violations": [],
  "audit_id": "..."
}
```

## Step 3: Run Tests (3 min)

```bash
# Fast tests only (no external services)
uv run pytest tests/ -m "not component" -v
```

## Step 4: Understand the Output (3 min)

- **decision**: APPROVED, REJECTED, or WARNING
- **violations**: List of compliance failures
- **audit_id**: Reference for audit trail

## Step 5: Inspect FHIR Data (2 min)

```bash
# View patient data from HAPI FHIR sandbox
uv run python cli/emr.py inspect 90128869
```

## Next Steps

- Read [AGENTS.md](../AGENTS.md) for principles
- Check [PYTHON_STANDARDS.md](PYTHON_STANDARDS.md) for code style
- See [FAQ.md](FAQ.md) for common questions
