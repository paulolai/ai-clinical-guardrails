# VCR Implementation Status

## Summary

**Objective:** Speed up component tests using VCR (pytest-recording) and Syrupy snapshots

**Status:** PARTIALLY WORKING - FHIR models optimized but VCR not intercepting HTTP

## What Works

### ✅ Dependencies Installed
```toml
[project]
dependencies = [
    "pytest-recording>=0.13.1",
    "syrupy>=4.9.1",
]
```

### ✅ Configuration
```python
# tests/component/conftest.py
@pytest.fixture(scope="session")
def vcr_config():
    return {
        "filter_headers": ["authorization", "Authorization"],
    }
```

### ✅ Lazy Imports Optimized
**Before:**
```python
# Import took 16+ seconds
from src.integrations.fhir.client import FHIRClient
```

**After:**
```python
# Import takes 0.16 seconds
from src.integrations.fhir.client import FHIRClient
# Models loaded only when needed
```

Changes in `src/integrations/fhir/client.py`:
- Lazy initialization of httpx client
- Lazy import of generated FHIR models (49,810 lines)

### ✅ Cassettes Created
```
tests/component/cassettes/
├── test_fhir_client/
│   ├── test_fhir_client_can_fetch_patient.yaml
│   └── test_fhir_client_handles_missing_patient.yaml
```

### ✅ Snapshot Created
```
tests/component/__snapshots__/
└── test_fhir_client.ambr
```

### ✅ CI/CD Updated
Daily re-recording job in `.github/workflows/ci.yml`:
```yaml
validate-cassettes:
  runs-on: ubuntu-latest
  schedule:
    - cron: '0 2 * * *'
  steps:
    - Run tests with --record-mode=all
    - Check if cassettes changed
    - Fail if APIs drifted
```

### ✅ Documentation
Created `docs/testing/COMPONENT_TESTS.md` with usage guide.

## What's Broken

### ❌ VCR Not Intercepting HTTP
**Evidence:**
```bash
# This should be ~0.5s but takes 16s
$ uv run pytest tests/component/test_fhir_client.py -v
Test execution time: 16.823s  # ← Making real HTTP calls!

# But direct VCR works:
$ uv run pytest tests/component/test_vcr_direct.py -v
Test execution time: 0.18s   # ← Using cassette correctly
```

**Root Cause Unknown:**
- VCR patches httpcore but httpx.AsyncClient might not use it
- pytest-recording might not activate for async tests
- Client initialization timing issue

**Impact:**
- Tests pass but make real HTTP calls
- Requires network connectivity
- Slow (16s instead of 0.5s)
- No offline capability

## Test Results

### Current Behavior
```
tests/component/test_fhir_client.py::test_fhir_client_can_fetch_patient PASSED [100%]
============================== 2 passed in 17.02s ==============================
```

### Expected Behavior
```
tests/component/test_fhir_client.py::test_fhir_client_can_fetch_patient PASSED [100%]
============================== 2 passed in 0.52s ==============================
```

## Files Changed

```
src/integrations/fhir/client.py           # Added lazy imports
tests/component/conftest.py               # VCR config
tests/component/test_fhir_client.py       # Added @pytest.mark.vcr
tests/component/cassettes/                # Created cassettes
tests/component/__snapshots__/            # Created snapshot
.github/workflows/ci.yml                   # Added re-recording job
docs/testing/COMPONENT_TESTS.md           # Documentation
```

## Next Steps

See `docs/debugging/VCR_NOT_INTERCEPTING_HTTP.md` for detailed debugging plan.

**Quick Options:**
1. **Debug VCR** (2-4 hours) - Fix pytest-recording integration
2. **Switch to pytest-httpx** (1 hour) - Use different mocking library
3. **Accept current state** (0 hours) - Tests work but are slow

## Recommendations

**For Now:**
- Tests pass and validate functionality
- Slow but reliable
- Can run in CI with network access

**For Later:**
- Debug VCR or switch to pytest-httpx
- Goal: <1s test execution
- Enables offline development
- Faster CI feedback

## Technical Details

**Versions:**
- Python: 3.12.3
- pytest: 9.0.2
- pytest-recording: 0.13.4
- vcrpy: 8.1.1
- httpx: 0.28.1
- httpcore: 1.0.9

**VCR Configuration:**
```python
vcr_config = {
    "filter_headers": ["authorization", "Authorization"],
    "filter_post_data_parameters": ["api_key", "apikey"],
    "filter_query_parameters": ["api_key", "apikey"],
}
```

**Cassette Location:**
- Default: `tests/component/cassettes/{test_module}/{test_name}.yaml`
- Generated: Yes
- Being used: No (making real requests)
