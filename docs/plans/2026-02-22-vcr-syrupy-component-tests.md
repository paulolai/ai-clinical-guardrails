# VCR + Syrupy Component Test Speedup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Speed up component/integration tests by recording HTTP interactions (VCR) and response snapshots (syrupy), enabling offline replay with periodic validation against live APIs.

**Architecture:** Add pytest-recording (VCR) to capture HTTP traffic to cassettes, syrupy to snapshot response data for contract validation. Tests run in "replay mode" by default (fast), CI runs daily in "record mode" to detect API drift. Snapshot files committed to git for transparency.

**Tech Stack:** pytest-recording (v4.x), syrupy (4.x), pytest-asyncio (existing), httpx (existing)

---

## Current State Analysis

**Component tests needing optimization:**
- `tests/component/test_fhir_client.py` - 2 tests hitting HAPI FHIR sandbox
- `tests/component/test_llm_extraction.py` - 8 tests hitting Synthetic LLM API (skipped without SYNTHETIC_API_KEY)
- `tests/component/test_cli_e2e.py` - 4 CLI tests hitting Synthetic LLM API

**Pain points:**
- Tests require live API access and valid credentials
- Slow due to network latency
- Flaky if APIs are down or rate-limited
- CI can't run component tests without secrets

---

## Task 1: Install Dependencies

**Files:**
- Modify: `pyproject.toml:7-24` (dependencies list)

**Step 1: Add pytest-recording and syrupy**

Add to dependencies list:
```toml
dependencies = [
    # ... existing dependencies ...
    "pytest-recording>=0.13.0",  # VCR for HTTP recording
    "syrupy>=4.0.0",             # Snapshot testing
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: Dependencies installed successfully

**Step 3: Verify installation**

Run: `uv run pytest --version`
Expected: pytest 9.0.2+ with recording plugin loaded

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add pytest-recording and syrupy for component tests"
```

---

## Task 2: Configure pytest-recording

**Files:**
- Modify: `pyproject.toml:64-70` (pytest configuration)

**Step 1: Add pytest-recording configuration**

Append to `[tool.pytest.ini_options]`:
```toml
[tool.pytest.ini_options]
# ... existing config ...
# VCR configuration
vcr-record-mode = "none"  # Default: don't record, replay existing cassettes
vcr-cassette-dir = "tests/component/cassettes"  # Where to store recordings
vcr-match-on = ["method", "scheme", "host", "port", "path", "query", "body"]
```

**Step 2: Create cassette directory**

Run: `mkdir -p tests/component/cassettes`

**Step 3: Add .gitignore entry**

Append to `.gitignore` (create if doesn't exist):
```
# VCR cassettes (except YAML files which we commit)
# Note: We commit cassettes to version control for reproducibility
# Tests will fail if cassettes differ from actual API responses
```

**Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "config: add VCR recording configuration"
```

---

## Task 3: Configure syrupy

**Files:**
- Create: `tests/component/__snapshots__/.gitkeep`
- Modify: `pyproject.toml:64-70`

**Step 1: Create snapshot directory**

Run: `mkdir -p tests/component/__snapshots__`

**Step 2: Add syrupy configuration**

Append to `[tool.pytest.ini_options]`:
```toml
# Syrupy snapshot configuration
addopts = "--snapshot-warn-unused"
```

**Step 3: Commit**

```bash
git add tests/component/__snapshots__/.gitkeep pyproject.toml
git commit -m "config: add syrupy snapshot directory"
```

---

## Task 4: Update FHIR Client Tests with VCR

**Files:**
- Modify: `tests/component/test_fhir_client.py:1-34`

**Step 1: Add VCR decorator to existing tests**

```python
import httpx
import pytest

from src.integrations.fhir.client import FHIRClient
from src.models import PatientProfile


@pytest.mark.asyncio
@pytest.mark.vcr  # Add VCR recording
async def test_fhir_client_can_fetch_patient() -> None:
    """Component Test: Verifies integration with HAPI FHIR Sandbox."""
    client = FHIRClient()
    patient_id = "90128869"

    try:
        profile = await client.get_patient_profile(patient_id)

        assert isinstance(profile, PatientProfile)
        assert profile.patient_id == patient_id
        assert profile.first_name is not None
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.vcr  # Add VCR recording
async def test_fhir_client_handles_missing_patient() -> None:
    client = FHIRClient()
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_patient_profile("NON_EXISTENT_ID_XYZ_123")
    finally:
        await client.close()
```

**Step 2: Initial recording run**

Run: `uv run pytest tests/component/test_fhir_client.py -v --vcr-record=once`
Expected: Tests pass, cassettes created in `tests/component/cassettes/`

**Step 3: Verify replay mode**

Run: `uv run pytest tests/component/test_fhir_client.py -v`
Expected: Tests pass (using cached cassettes, no network calls)

**Step 4: Commit cassettes**

```bash
git add tests/component/test_fhir_client.py tests/component/cassettes/
git commit -m "test: add VCR recording to FHIR client tests"
```

---

## Task 5: Add Snapshot Assertions to FHIR Tests

**Files:**
- Modify: `tests/component/test_fhir_client.py:1-34`

**Step 1: Import syrupy and update test**

```python
import httpx
import pytest
from syrupy import snapshot

from src.integrations.fhir.client import FHIRClient
from src.models import PatientProfile


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fhir_client_can_fetch_patient(snapshot) -> None:  # Add snapshot fixture
    """Component Test: Verifies integration with HAPI FHIR Sandbox."""
    client = FHIRClient()
    patient_id = "90128869"

    try:
        profile = await client.get_patient_profile(patient_id)

        # Snapshot the profile data
        assert profile.model_dump() == snapshot(
            exclude=props("last_updated")  # Exclude dynamic fields
        )

        assert isinstance(profile, PatientProfile)
        assert profile.patient_id == patient_id
        assert profile.first_name is not None
    finally:
        await client.close()
```

**Step 2: Create initial snapshots**

Run: `uv run pytest tests/component/test_fhir_client.py::test_fhir_client_can_fetch_patient -v --snapshot-update`
Expected: Snapshot file created in `tests/component/__snapshots__/`

**Step 3: Verify snapshots**

Run: `uv run pytest tests/component/test_fhir_client.py -v`
Expected: Tests pass with snapshot assertions

**Step 4: Commit**

```bash
git add tests/component/test_fhir_client.py tests/component/__snapshots__/
git commit -m "test: add syrupy snapshots to FHIR client tests"
```

---

## Task 6: Update LLM Extraction Tests with VCR

**Files:**
- Modify: `tests/component/test_llm_extraction.py:1-230`

**Step 1: Add VCR decorator to TestLLMClientIntegration**

```python
@pytest.mark.vcr
class TestLLMClientIntegration:
    """Component tests for SyntheticLLMClient against real API."""
    # ... rest of class ...
```

**Step 2: Update test methods to use snapshot**

```python
@pytest.mark.vcr
class TestLLMClientIntegration:
    """Component tests for SyntheticLLMClient against real API."""

    @pytest.fixture
    def api_key(self) -> str | None:
        return os.environ.get("SYNTHETIC_API_KEY")

    async def test_client_can_connect_to_api(self, api_key: str | None, snapshot) -> None:
        """Verify LLM client can authenticate and connect to Synthetic API."""
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set - skipping real API test")

        async with SyntheticLLMClient(api_key=api_key) as client:
            response = await client.complete(
                prompt='You are a test assistant. Please return a JSON object with the key "status" and value "ok".',
                temperature=0.0,
                max_tokens=100,
            )

            result = json.loads(response)
            assert "status" in result
            # Snapshot the response structure
            assert result == snapshot(exclude=props("response_id", "created"))
```

**Step 3: Update parser tests with VCR and snapshots**

```python
@pytest.mark.vcr
class TestLLMParserIntegration:
    """Component tests for LLMTranscriptParser with real LLM."""

    @pytest.fixture
    def api_key(self) -> str | None:
        return os.environ.get("SYNTHETIC_API_KEY")

    @pytest_asyncio.fixture
    async def parser(self, api_key: str | None) -> AsyncGenerator[LLMTranscriptParser, None]:
        if api_key:
            client = SyntheticLLMClient(api_key=api_key)
            yield LLMTranscriptParser(llm_client=client)
            await client.close()
        else:
            pytest.skip("SYNTHETIC_API_KEY not set")

    async def test_parser_extracts_patient_name(self, parser: LLMTranscriptParser, snapshot) -> None:
        """Verify parser can extract patient name from transcript."""
        transcript = "Mrs. Sarah Johnson came in yesterday for her follow-up visit."

        result = await parser.parse(transcript)

        # Snapshot the full extraction result
        assert result.model_dump() == snapshot(exclude=props("processing_time_ms"))
        assert result.patient_name is not None or result.confidence < 0.6
```

**Step 4: Record cassettes for LLM tests**

Run: `uv run pytest tests/component/test_llm_extraction.py -v --vcr-record=once`
Expected: Tests pass, cassettes created

**Step 5: Update snapshots**

Run: `uv run pytest tests/component/test_llm_extraction.py -v --snapshot-update`
Expected: Snapshot files created

**Step 6: Commit**

```bash
git add tests/component/test_llm_extraction.py tests/component/cassettes/ tests/component/__snapshots__/
git commit -m "test: add VCR and syrupy to LLM extraction tests"
```

---

## Task 7: Update CLI E2E Tests with VCR

**Files:**
- Modify: `tests/component/test_cli_e2e.py:1-109`

**Step 1: Add module-level VCR marker**

```python
"""E2E tests for CLI extraction tool.

Tests the full CLI flow with real API calls.
"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from typer.testing import CliRunner

from cli.extract import app

runner = CliRunner()

pytestmark = [
    pytest.mark.component,
    pytest.mark.vcr,  # Add VCR to all tests in this module
]
```

**Step 2: Update tests to use snapshot for output validation**

```python
class TestCLIExtractE2E:
    """End-to-end tests for CLI extraction with real API."""

    @pytest.fixture
    def api_key(self) -> str | None:
        return os.environ.get("SYNTHETIC_API_KEY")

    def test_extract_from_text_with_real_api(self, api_key: str | None, snapshot) -> None:
        """E2E: Extract from text using real Synthetic API."""
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set")

        transcript = "Mrs. Sarah Johnson came in yesterday for follow-up. Started on Lisinopril 10mg daily."

        result = runner.invoke(app, ["extract", "--text", transcript], env={"SYNTHETIC_API_KEY": api_key})

        # Snapshot the output structure
        assert result.output == snapshot(exclude=props("timestamp"))
        assert result.exit_code == 0
        assert "Extraction Complete" in result.output or "patient" in result.output.lower()
```

**Step 3: Record cassettes and update snapshots**

Run: `uv run pytest tests/component/test_cli_e2e.py -v --vcr-record=once --snapshot-update`
Expected: Tests pass, cassettes and snapshots created

**Step 4: Commit**

```bash
git add tests/component/test_cli_e2e.py tests/component/cassettes/ tests/component/__snapshots__/
git commit -m "test: add VCR and syrupy to CLI E2E tests"
```

---

## Task 8: Create CI Job for Daily Re-recording

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add re-recording job to CI**

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # ... existing test job steps ...

  # NEW JOB: Daily re-recording validation
  validate-recordings:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    env:
      SYNTHETIC_API_KEY: ${{ secrets.SYNTHETIC_API_KEY }}
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Sync dependencies
        run: uv sync

      - name: Run tests with re-recording
        run: uv run pytest tests/component/ -v --vcr-record=all --snapshot-update

      - name: Check for cassette changes
        run: |
          if git diff --quiet tests/component/cassettes/; then
            echo "No cassette changes detected"
          else
            echo "Cassette changes detected! API responses may have changed."
            git diff --stat tests/component/cassettes/
            exit 1
          fi

      - name: Check for snapshot changes
        run: |
          if git diff --quiet tests/component/__snapshots__/; then
            echo "No snapshot changes detected"
          else
            echo "Snapshot changes detected! Response structures may have changed."
            git diff --stat tests/component/__snapshots__/
            exit 1
          fi
```

**Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add daily re-recording validation for component tests"
```

---

## Task 9: Add Documentation

**Files:**
- Create: `docs/testing/COMPONENT_TESTS.md`

**Step 1: Create documentation**

```markdown
# Component Testing with VCR and Syrupy

## Overview

Component tests use VCR (pytest-recording) to capture HTTP interactions and syrupy for response snapshots. This allows:
- Fast local test runs (replay from cassettes)
- Offline testing (no API credentials needed)
- Detection of API drift (via CI re-recording)

## How It Works

### VCR (HTTP Recording)

HTTP requests are intercepted and recorded to YAML cassette files:
- First run: Makes real HTTP calls, saves to cassette
- Subsequent runs: Replays from cassette (no network)
- Cassette files committed to git for reproducibility

### Syrupy (Snapshots)

Response data is snapshotted for contract validation:
- Captures expected response structure and values
- Fails if actual response differs from snapshot
- Snapshots reviewed like code changes

## Running Tests

### Normal Mode (Replay)
```bash
# Fast, uses recorded cassettes
uv run pytest tests/component/ -v
```

### Record Mode (Update Cassettes)
```bash
# Make new recordings, update snapshots
uv run pytest tests/component/ -v --vcr-record=all --snapshot-update

# Or record only new/missing cassettes
uv run pytest tests/component/ -v --vcr-record=once
```

### Review Changes
```bash
# See what changed in cassettes
git diff tests/component/cassettes/

# See what changed in snapshots
git diff tests/component/__snapshots__/

# Update snapshots if changes are expected
uv run pytest tests/component/ -v --snapshot-update
```

## File Structure

```
tests/component/
├── __snapshots__/          # Syrupy snapshot files (committed)
├── cassettes/              # VCR cassette files (committed)
│   ├── test_fhir_client/
│   │   ├── test_fhir_client_can_fetch_patient.yaml
│   │   └── test_fhir_client_handles_missing_patient.yaml
│   └── test_llm_extraction/
│       └── ...
├── test_fhir_client.py     # FHIR integration tests
├── test_llm_extraction.py  # LLM extraction tests
└── test_cli_e2e.py         # CLI end-to-end tests
```

## CI/CD

### Regular PR/Push
- Runs tests in replay mode (fast)
- No API credentials needed
- Validates code changes don't break contracts

### Daily Re-recording
- Runs at 2 AM UTC
- Re-records all HTTP interactions
- Fails if cassettes or snapshots differ
- Indicates API drift that needs attention

## Troubleshooting

### Tests fail with "Cassette not found"
```bash
# Record missing cassettes
uv run pytest tests/component/test_file.py::test_name -v --vcr-record=once
```

### Snapshot mismatch
```bash
# Review diff
uv run pytest tests/component/test_file.py::test_name -v

# Update if expected
uv run pytest tests/component/test_file.py::test_name -v --snapshot-update
```

### Exclude dynamic fields from snapshots

Use `exclude=props("field_name")` for timestamps, IDs, etc.:

```python
async def test_api_response(snapshot):
    result = await api.call()
    assert result.model_dump() == snapshot(
        exclude=props("timestamp", "request_id")
    )
```

## Maintenance

When APIs change intentionally:
1. Run with `--vcr-record=all` to update cassettes
2. Review changes in `git diff`
3. Update snapshots if response structure changed
4. Commit updated cassettes and snapshots
```

**Step 2: Commit**

```bash
git add docs/testing/COMPONENT_TESTS.md
git commit -m "docs: add VCR and syrupy testing guide"
```

---

## Task 10: Update README

**Files:**
- Modify: `README.md` (add testing section)

**Step 1: Add testing documentation to README**

Append to README.md:

```markdown
## Testing

### Component Tests

Component tests use VCR to record HTTP interactions:

```bash
# Run with recorded cassettes (fast, no API needed)
uv run pytest tests/component/ -v

# Update cassettes from live APIs
uv run pytest tests/component/ -v --vcr-record=all --snapshot-update
```

See [docs/testing/COMPONENT_TESTS.md](docs/testing/COMPONENT_TESTS.md) for details.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add component testing instructions to README"
```

---

## Summary

This plan implements:

1. **pytest-recording** for HTTP request/response capture
2. **syrupy** for response data snapshotting
3. **Cassette files** stored in `tests/component/cassettes/` (committed to git)
4. **Snapshot files** stored in `tests/component/__snapshots__/` (committed to git)
5. **Daily CI job** to detect API drift
6. **Documentation** for developers

**Expected Outcomes:**
- Component tests run in <5 seconds instead of minutes
- No API credentials required for local runs
- CI can run component tests without secrets
- API drift detected within 24 hours
- Full audit trail of API changes via git

---

## Verification Checklist

After implementation:

- [ ] `uv run pytest tests/component/ -v` completes in <10 seconds
- [ ] Tests pass without SYNTHETIC_API_KEY set locally
- [ ] CI job runs daily and validates cassettes
- [ ] Documentation is accurate and complete
- [ ] All cassettes and snapshots committed to git
