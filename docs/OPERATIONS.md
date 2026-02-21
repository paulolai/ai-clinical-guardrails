# Operational Runbook (Local Development)

**Scope:** Local development operations and troubleshooting
**Environment:** Python 3.12+, uv package manager

---

## Quick Start

### Prerequisites
```bash
# Check Python version
python --version  # Should be 3.12+

# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup
```bash
# Clone and setup
git clone <repo>
cd ai-clinical-guardrails
uv sync
```

---

## Development Commands

### Run Tests
```bash
# Run all unit tests (fast)
uv run pytest tests/ -m "not component" -v

# Run specific test
uv run pytest tests/test_compliance.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
# Lint check
uv run ruff check .

# Type check (if mypy configured)
uv run mypy src/

# Format code
uv run ruff format .
```

### Run API Server
```bash
# Start FastAPI development server
uv run python main.py

# Server will be at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## CLI Tools

### Inspect Patient Data
```bash
# Fetch patient from FHIR sandbox
uv run python cli/fhir.py inspect 90128869
```

### Verify AI Output
```bash
# Verify text against EMR
uv run python cli/api.py verify \
  --id 90128869 \
  --text "Patient seen on 2025-02-21 for follow-up."
```

---

## Common Issues

### Import Errors
**Symptom:** `ModuleNotFoundError: No module named 'src'`

**Cause:** Running scripts from wrong directory or PYTHONPATH not set.

**Fix:**
```bash
# Always run from project root with uv
uv run python cli/fhir.py inspect 90128869

# Or use module syntax
uv run python -m cli.fhir inspect 90128869
```

### FHIR Connection Timeout
**Symptom:** `httpx.TimeoutException` or long delays

**Cause:** HAPI FHIR sandbox slow or unreachable.

**Fix:**
```bash
# Test FHIR connectivity
curl -v http://hapi.fhir.org/baseR4/metadata

# If timeout persists, check network
# Try increasing timeout in src/integrations/fhir/client.py
```

### Type Errors with Result Class
**Status:** Known Issue ⚠️

**Symptom:** `TypeError: <class 'src.models.Result'> cannot be parametrized`

**Details:** The Result generic type implementation has a bug. The `__class_getitem__` method doesn't properly inherit from `typing.Generic`.

**Workaround:** Code structure is correct but type hints may fail. Runtime behavior works correctly.

---

## Project Structure

```
ai-clinical-guardrails/
├── src/                    # Source code
│   ├── engine.py          # ComplianceEngine
│   ├── models.py          # Domain models
│   ├── api.py             # FastAPI endpoints
│   └── integrations/      # External services
│       └── fhir/          # FHIR client
├── tests/                 # Tests
│   ├── test_compliance.py # Property-based tests
│   └── component/         # Integration tests
├── cli/                   # Command line tools
├── examples/              # Runnable examples
└── docs/                  # Documentation
```

---

## Debugging Tips

### Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check FHIR Response
```bash
# Direct API call to see raw response
curl "http://hapi.fhir.org/baseR4/Patient/90128869" | python -m json.tool
```

### Run Single Test with Debugging
```bash
uv run pytest tests/test_compliance.py::TestComplianceEngine::test_date_integrity_invariant -v --tb=short
```

---

## Environment Variables

Create `.env` file for local development:

```bash
# FHIR Configuration (optional, defaults to HAPI public sandbox)
FHIR_BASE_URL=http://hapi.fhir.org/baseR4

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Known Limitations

1. **Result Type Bug:** Generic type parameters fail at runtime due to Pydantic/BaseModel conflict
2. **FHIR Sandbox:** Uses public HAPI server - rate limits may apply
3. **Examples:** basic_verification.py has import issues (see examples/ directory)

---

## Next Steps for Production

This runbook covers local development only. For production operations, document:

- Deployment procedures (Docker, k8s, etc.)
- Monitoring and alerting setup
- Database backup procedures
- Incident response playbooks
- Performance tuning guides

See AGENTS.md for architectural decisions and patterns.
