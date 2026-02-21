# Debugging Guide

Systematic troubleshooting for test failures and integration issues.

## Quick Reference

| Issue | Command | Link |
|-------|---------|------|
| Test failure | `uv run pytest tests/test_compliance.py -v --tb=short` | [Guide](./guides/debugging.md) |
| Hypothesis failure | `uv run pytest tests/ --hypothesis-seed=12345` | [Guide](./guides/debugging.md) |
| FHIR connection | `curl http://hapi.fhir.org/baseR4/Patient/90128869` | [Guide](./guides/fhir-integration.md) |
| Import error | `export PYTHONPATH="${PYTHONPATH}:."` | [Guide](./guides/debugging.md) |

## Common Issues

### Test Not Found
```bash
# Check file naming
ls tests/test_*.py  # Should match pattern

# Run from project root
cd /home/paulo/ai-clinical-guardrails
uv run pytest tests/
```

### Import Errors
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:."

# Or install editable
uv pip install -e .
```

### Hypothesis Shrinking
```bash
# Reproduce specific failure
uv run pytest tests/ --hypothesis-seed=1234567890

# Disable shrinking temporarily
uv run pytest tests/ --hypothesis-phases=explicit,reuse,generate
```

### FHIR Connection
```bash
# Test connectivity
curl http://hapi.fhir.org/baseR4/metadata

# Check specific patient
curl http://hapi.fhir.org/baseR4/Patient/90128869
```

## Debugging Commands

```bash
# Stop on first failure
uv run pytest tests/ -x

# Enter pdb on failure
uv run pytest tests/ --pdb

# Show local variables
uv run pytest tests/ --showlocals

# Verbose with output
uv run pytest tests/ -v -s
```

## See Also

- [Detailed Debugging Guide](./guides/debugging.md)
- [Integration Testing](./INTEGRATION_TESTING.md)
- [Testing Workflows](./TESTING_WORKFLOWS.md)
