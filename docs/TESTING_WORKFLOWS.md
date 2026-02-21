# Testing Workflows

Complete reference for running tests in the AI Clinical Guardrails project.

## Environment Setup

### Prerequisites
```bash
# Install dependencies
uv sync

# Verify installation
uv run python --version  # Should be 3.12+
```

## Quick Reference

| Command | Purpose | Speed |
|---------|---------|-------|
| `uv run pytest tests/ -v` | Run all tests | ~30s |
| `uv run pytest tests/ -m "not component"` | Unit tests only | ~5s |
| `uv run pytest tests/component/ -v` | Component tests | ~60s |
| `uv run pytest tests/test_compliance.py -v` | Specific file | Variable |
| `uv run pytest --cov=src` | With coverage | ~35s |

## Running Tests

### All Tests
```bash
uv run pytest tests/ -v
```

### Unit Tests (Fast Feedback)
```bash
# Exclude component tests
uv run pytest tests/ -m "not component" -v

# Or explicitly select unit tests
uv run pytest tests/test_compliance.py tests/test_api.py -v
```

### Component Tests
These require HAPI FHIR sandbox access:
```bash
# Set environment variable
export FHIR_BASE_URL="http://hapi.fhir.org/baseR4"

# Run component tests
uv run pytest tests/component/ -v
```

### Specific Test Categories
```bash
# By marker
uv run pytest tests/ -m "component" -v
uv run pytest tests/ -m "slow" -v

# By file
uv run pytest tests/test_compliance.py -v

# By test name pattern
uv run pytest tests/ -k "test_date" -v

# By specific test
uv run pytest tests/test_compliance.py::TestComplianceEngine::test_example -v
```

### With Coverage
```bash
# Terminal report
uv run pytest tests/ --cov=src --cov-report=term

# HTML report
uv run pytest tests/ --cov=src --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Debugging Tests
```bash
# Stop on first failure
uv run pytest tests/ -x

# Verbose with output
uv run pytest tests/ -v -s

# Enter debugger on failure
uv run pytest tests/ --pdb

# Specific test with debugging
uv run pytest tests/test_compliance.py::test_name -v --pdb
```

## Hypothesis Workflows

### Running Property Tests
```bash
# Run with default settings
uv run pytest tests/test_compliance.py -v

# Increase examples (more thorough)
uv run pytest tests/test_compliance.py --hypothesis-seed=12345

# Show statistics
uv run pytest tests/test_compliance.py --hypothesis-show-statistics

# Generate coverage
uv run pytest tests/test_compliance.py --hypothesis-cover
```

### Hypothesis Configuration
```python
# In conftest.py or test file
from hypothesis import settings

# Custom profile for CI
settings.register_profile("ci", max_examples=100, deadline=None)
settings.register_profile("dev", max_examples=10, deadline=None)
settings.register_profile("debug", max_examples=1, verbosity=Verbosity.verbose)

# Load profile
# In pytest.ini: addopts = --hypothesis-profile=ci
```

### Debugging Failed Hypothesis Tests
```bash
# Replay specific failure
uv run pytest tests/test_compliance.py --hypothesis-seed=1234567890

# With extra verbosity
uv run pytest tests/test_compliance.py --hypothesis-verbosity=verbose

# Save examples to file
uv run pytest tests/test_compliance.py --hypothesis-print-seed=always
```

## Test Configuration

### pytest.ini
```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
markers = [
    "component: marks tests as component tests (requires external services)",
    "slow: marks tests as slow",
    "property: marks tests as property-based tests",
]
```

### Pyproject.toml Section
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "component: requires external services",
    "slow: slow running tests",
]
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v2
      - run: uv sync
      - run: uv run pytest tests/ -m "not component" -v
  component-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v2
      - run: uv sync
      - run: uv run pytest tests/component/ -v
```

### Pre-commit Hook
```bash
#!/bin/bash
# .husky/pre-commit
uv run pytest tests/ -m "not component" -x || exit 1
uv run ruff check . || exit 1
```

## Common Scenarios

### Scenario: New Feature Development
```bash
# 1. Write test first (TDD)
# 2. Run to confirm it fails
uv run pytest tests/test_new_feature.py -v

# 3. Implement feature
# 4. Run until it passes
uv run pytest tests/test_new_feature.py -v

# 5. Run full suite to verify no regressions
uv run pytest tests/ -m "not component" -v
```

### Scenario: Debugging Production Issue
```bash
# 1. Reproduce with specific test
uv run pytest tests/test_issue.py -v --pdb

# 2. Run property test to find edge cases
uv run pytest tests/test_issue.py --hypothesis-seed=random

# 3. Verify fix
uv run pytest tests/ -v
```

### Scenario: Release Preparation
```bash
# 1. Full test suite
uv run pytest tests/ -v

# 2. Coverage check
uv run pytest tests/ --cov=src --cov-fail-under=80

# 3. Component tests
uv run pytest tests/component/ -v

# 4. Generate attestation report
uv run python scripts/generate_attestation.py
```

## Troubleshooting

### Tests Not Found
```bash
# Check file naming
ls tests/test_*.py  # Should match pattern

# Check pytest config
cat pyproject.toml | grep -A 10 pytest
```

### Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:."

# Or run from project root
cd /path/to/project && uv run pytest tests/
```

### Hypothesis Shrinking Taking Too Long
```bash
# Disable shrinking temporarily
uv run pytest tests/ --hypothesis-phases=explicit,reuse,generate

# Or set deadline
from hypothesis import settings
settings.default.deadline = None  # Disable timing
```

## Performance Optimization

### Parallel Execution
```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Run in parallel
uv run pytest tests/ -n auto
```

### Selective Testing
```bash
# Only changed files
uv run pytest tests/ --testmon

# Failed first
uv run pytest tests/ --ff

# Last failed
uv run pytest tests/ --lf
```

## Next Steps

- See [Debugging Guide](./DEBUGGING_GUIDE.md) for troubleshooting
- See [Integration Testing](./INTEGRATION_TESTING.md) for component test specifics
- See [Testing Framework](./TESTING_FRAMEWORK.md) for philosophy
