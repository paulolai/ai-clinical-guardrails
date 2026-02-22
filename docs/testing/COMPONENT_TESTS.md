# Component Testing with VCR and Syrupy

## Overview

Component tests in this project use **VCR** (via pytest-recording) to capture HTTP interactions and **Syrupy** for response snapshots. This approach enables:

- **Fast local test runs** - Replay from recorded cassettes instead of hitting live APIs
- **Offline testing** - No API credentials required for local runs
- **API drift detection** - Daily CI re-recording validates that APIs haven't changed unexpectedly
- **Reproducible tests** - Cassettes committed to git ensure consistent test behavior

## How It Works

### VCR (HTTP Recording)

HTTP requests made during tests are intercepted and recorded to YAML cassette files:

- **First run** - Makes real HTTP calls and saves responses to cassette files
- **Subsequent runs** - Replays responses from cassettes (no network calls)
- **Cassette files** - Committed to git in `tests/component/cassettes/`

### Syrupy (Snapshots)

Response data structures are captured as snapshots:

- **Captures** - Expected response structure and values
- **Validates** - Actual response matches the snapshot
- **Snapshots** - Committed to git in `tests/component/__snapshots__/`
- **Updates** - Review changes like code changes in PRs

## File Structure

```
tests/component/
├── __snapshots__/          # Syrupy snapshot files (*.ambr)
│   └── test_fhir_client.ambr
├── cassettes/              # VCR cassette files (*.yaml)
│   └── test_fhir_client/
│       ├── test_fhir_client_can_fetch_patient.yaml
│       └── test_fhir_client_handles_missing_patient.yaml
├── test_fhir_client.py     # FHIR integration tests
├── test_llm_extraction.py  # LLM extraction tests
└── test_cli_e2e.py         # CLI end-to-end tests
```

## Running Tests

### Normal Mode (Replay from Cassettes)

```bash
# Fast - uses recorded cassettes, no network calls
uv run pytest tests/component/test_fhir_client.py -v
```

### Record Mode (Update Cassettes)

```bash
# Record new cassettes or update existing ones
uv run pytest tests/component/test_fhir_client.py -v --record-mode=once

# Force re-recording of all cassettes
uv run pytest tests/component/test_fhir_client.py -v --record-mode=all

# Update snapshots
uv run pytest tests/component/test_fhir_client.py -v --snapshot-update
```

### Review Changes

```bash
# See what changed in cassettes
git diff tests/component/cassettes/

# See what changed in snapshots
git diff tests/component/__snapshots__/

# Combined: update both cassettes and snapshots
uv run pytest tests/component/ -v --record-mode=all --snapshot-update
```

## Record Modes

VCR supports several recording modes:

- **`none`** (default) - Replay existing cassettes, fail if not found
- **`once`** - Record new cassettes, replay existing ones
- **`new_episodes`** - Record new requests, replay existing ones
- **`all`** - Re-record all cassettes (useful for validation)
- **`rewrite`** - Re-record all cassettes and remove old unused ones

## Writing Tests with VCR

### Basic Example

```python
import pytest
from syrupy.filters import props

@pytest.mark.asyncio
@pytest.mark.vcr
async def test_api_call(snapshot):
    """Test that makes HTTP calls - recorded by VCR."""
    client = MyAPIClient()
    result = await client.fetch_data()

    # Assert response matches snapshot
    assert result.model_dump() == snapshot(exclude=props("timestamp", "request_id"))
```

### Excluding Dynamic Fields

Use `exclude=props()` to exclude fields that change between runs:

```python
from syrupy.filters import props

# Exclude timestamp and request_id which change each call
assert result.model_dump() == snapshot(
    exclude=props("last_updated", "request_id", "created_at")
)
```

### Class-Level VCR Marker

Apply VCR to all tests in a class:

```python
@pytest.mark.vcr
class TestAPIClient:
    async def test_fetch(self):
        # Automatically recorded
        pass
```

## CI/CD Integration

### Regular PR/Push Tests

CI runs tests in replay mode (fast, no credentials needed):

```yaml
- name: Run Tests
  run: uv run pytest tests/ -v
```

### Daily Re-recording Validation

A scheduled CI job runs daily to detect API drift:

```yaml
- name: Re-record Component Tests
  run: uv run pytest tests/component/ -v --record-mode=all --snapshot-update

- name: Check for Changes
  run: |
    if git diff --quiet tests/component/cassettes/; then
      echo "✅ No changes detected"
    else
      echo "⚠️ API responses changed!"
      exit 1
    fi
```

If cassettes or snapshots change, the CI fails and notifies the team.

## Troubleshooting

### Tests Fail with "Cassette not found"

The cassette doesn't exist. Record it:

```bash
uv run pytest tests/component/test_file.py::test_name -v --record-mode=once
```

### Snapshot Mismatch

The actual response differs from the snapshot. Review the diff:

```bash
# Run to see the diff
uv run pytest tests/component/test_file.py::test_name -v

# Update if the change is expected
uv run pytest tests/component/test_file.py::test_name -v --snapshot-update
```

### Cassette Matching Issues

If a test makes multiple requests or requests change slightly, VCR might not find a match. Check the cassette file to see what was recorded and adjust the test or matching criteria.

### Network Access Blocked

Tests can run with network blocked to ensure VCR is working:

```bash
uv run pytest tests/component/ -v --block-network
```

## Best Practices

1. **Commit cassettes and snapshots** - They're needed for CI and other developers
2. **Exclude dynamic fields** - Timestamps, IDs, etc. that change between runs
3. **Review cassette changes** - Before committing, review `git diff` to understand API changes
4. **Keep cassettes small** - Avoid recording large responses; mock or truncate if needed
5. **Document API dependencies** - Note which external APIs are tested in docstrings

## Maintenance

When APIs change intentionally:

1. Run with `--record-mode=all` to update cassettes
2. Review changes with `git diff tests/component/cassettes/`
3. Update snapshots if response structure changed
4. Commit both cassettes and snapshots with clear commit messages
5. Notify the team of breaking API changes

## Resources

- [pytest-recording Documentation](https://github.com/kiwicom/pytest-recording)
- [Syrupy Documentation](https://github.com/syrupy-project/syrupy)
- [VCR.py Documentation](https://vcrpy.readthedocs.io/)
