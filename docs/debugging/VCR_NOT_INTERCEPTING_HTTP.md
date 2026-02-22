# VCR Not Intercepting HTTP Calls - Debugging Plan

> **Status:** CRITICAL - Component tests make real HTTP calls instead of using cassettes
> **Created:** 2026-02-22
> **Estimated Time:** 2-4 hours

## Problem Statement

VCR (via pytest-recording) is **not intercepting HTTP requests** in component tests despite:
- Tests having `@pytest.mark.vcr` decorator
- Cassettes existing in `tests/component/cassettes/`
- VCR configuration in `tests/component/conftest.py`

**Evidence:**
```bash
# This takes 16+ seconds (real HTTP call)
$ uv run pytest tests/component/test_fhir_client.py -v
Test execution time: 16.823s

# But VCR works in isolation:
$ uv run pytest tests/component/test_vcr_direct.py -v
Test execution time: 0.18s
```

## Expected Behavior

With VCR working:
- First run: Records cassette (slow, real HTTP)
- Subsequent runs: Replays cassette (fast, ~0.1s, no network)

## Current State

### Files Modified
1. `src/integrations/fhir/client.py` - Added lazy httpx client initialization
2. `tests/component/conftest.py` - VCR config with header filtering
3. `tests/component/cassettes/` - FHIR cassettes exist
4. `tests/component/test_fhir_client.py` - Has `@pytest.mark.vcr`

### Configuration
```python
# tests/component/conftest.py
@pytest.fixture(scope="session")
def vcr_config():
    return {
        "filter_headers": ["authorization", "Authorization"],
    }
```

## Hypotheses (Ranked by Likelihood)

### 1. **pytest-recording vs VCR Compatibility** (HIGH)
pytest-recording might not be activating VCR properly for httpx in async tests.

**Check:**
- Does the VCR fixture actually get injected?
- Is the cassette being loaded before the test runs?
- Compare pytest-recording's approach with direct VCR usage

### 2. **Client Initialization Timing** (HIGH)
The FHIRClient creates httpx.AsyncClient lazily in `_get_client()`, which might happen after VCR patches.

**Check:**
- When does VCR patch httpcore vs when is the client created?
- Try creating client synchronously in `__init__`
- Check if `AsyncHTTPTransport` bypasses VCR

### 3. **Async Context Manager Issue** (MEDIUM)
The test pattern `async with client:` might interact differently with VCR's patching.

**Check:**
- Does VCR properly intercept async context managers?
- Try synchronous test first
- Check if `aclose()` affects VCR

### 4. **httpx/httpcore Version Mismatch** (MEDIUM)
VCR 8.1.1 might not fully support httpx 0.28.1 / httpcore 1.0.9.

**Check:**
- Downgrade httpx to 0.27.x
- Check VCR's supported versions
- Look for open issues in vcrpy repo

### 5. **Pytest Fixture Scope** (LOW)
Session-scoped VCR config might not apply to function-scoped test.

**Check:**
- Change vcr_config scope to function
- Try module-level pytestmark

## Debugging Tasks

### Task 1: Verify VCR Fixture Injection

**Goal:** Confirm that the VCR fixture is actually being used.

**Steps:**
1. Add debug output to `tests/component/test_fhir_client.py`:
```python
@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fhir_client_can_fetch_patient(vcr):  # Add vcr fixture
    """Component Test with VCR debugging."""
    print(f"\nVCR cassette: {vcr}")
    print(f"VCR cassette path: {vcr._path if hasattr(vcr, '_path') else 'N/A'}")
    print(f"VCR cassette mode: {vcr._config.record_mode if hasattr(vcr, '_config') else 'N/A'}")
    print(f"VCR cassette recorded: {len(vcr.playback_interactions) if hasattr(vcr, 'playback_interactions') else 'N/A'}")

    # Check httpcore before creating client
    import httpcore
    print(f"httpcore.AsyncConnectionPool module: {httpcore.AsyncConnectionPool.__module__}")

    client = FHIRClient()
    print(f"Client created, httpcore module: {httpcore.AsyncConnectionPool.__module__}")

    try:
        profile = await client.get_patient_profile("90128869")
        print(f"After API call, httpcore module: {httpcore.AsyncConnectionPool.__module__}")
    finally:
        await client.close()
```

2. Run the test:
```bash
uv run pytest tests/component/test_fhir_client.py::test_fhir_client_can_fetch_patient -v -s
```

**Expected:**
- VCR cassette should be loaded and show path
- httpcore module should be `vcr.stubs` (not `httpcore`)

**If httpcore is NOT patched:** → Investigate pytest-recording activation

### Task 2: Compare Direct VCR vs pytest-recording

**Goal:** Determine if the issue is pytest-recording specific.

**Steps:**
1. Create `tests/component/test_vcr_comparison.py`:
```python
import httpx
import pytest
import vcr


# Test A: Direct VCR usage
@pytest.mark.asyncio
async def test_direct_vcr():
    """Direct VCR - should work."""
    my_vcr = vcr.VCR(record_mode='once')

    with my_vcr.use_cassette('tests/component/cassettes/direct/test_direct.yaml') as cass:
        print(f"\nDirect VCR: {cass}")
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/get")
            print(f"Direct response: {response.status_code}")


# Test B: pytest-recording
@pytest.mark.asyncio
@pytest.mark.vcr
default_cassette_name = "test_pytest_recording"
async def test_pytest_recording():
    """pytest-recording - might not work."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/get")
        print(f"pytest-recording response: {response.status_code}")


# Test C: With explicit cassette name
@pytest.mark.asyncio
@pytest.mark.vcr('explicit_cassette')
async def test_explicit_cassette():
    """pytest-recording with explicit cassette."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/get")
        print(f"Explicit cassette response: {response.status_code}")
```

2. Run all three:
```bash
rm -rf tests/component/cassettes/test_vcr_comparison tests/component/cassettes/direct
uv run pytest tests/component/test_vcr_comparison.py -v -s --record-mode=once
```

**Expected:**
- All should record cassettes
- Re-run should be fast (<1s)

**If pytest-recording tests are slow:** → Issue is with pytest-recording

### Task 3: Check httpx AsyncHTTPTransport

**Goal:** Determine if AsyncHTTPTransport bypasses VCR.

**Steps:**
1. Check if httpx uses AsyncHTTPTransport:
```python
# In test_fhir_client.py, add before creating client:
import httpx
client = httpx.AsyncClient()
print(f"Client transport: {client._transport}")
print(f"Transport type: {type(client._transport)}")
print(f"Transport module: {type(client._transport).__module__}")
await client.aclose()
```

2. Check if httpcore.AsyncConnectionPool is the issue:
```python
import httpcore
transport = httpcore.AsyncHTTPTransport()
print(f"Transport pool: {transport._pool}")
print(f"Pool type: {type(transport._pool)}")
print(f"Pool module: {type(transport._pool).__module__}")
```

**Expected:**
- If VCR is working, types should show `vcr.stubs.*`

**If types are from httpcore package:** → VCR not patching

### Task 4: Check pytest-recording Plugin Activation

**Goal:** Verify pytest-recording is properly loaded and activating VCR.

**Steps:**
1. Check pytest plugins:
```bash
uv run pytest --trace-config tests/component/test_fhir_client.py --collect-only 2>&1 | grep -i "vcr\|record"
```

2. Add to conftest.py:
```python
# Add at the end of conftest.py
def pytest_configure(config):
    print(f"\nPytest config plugins: {config.pluginmanager.get_plugins()}")
    print(f"VCR recording enabled: {config.getoption('vcr_record_mode', None)}")
```

3. Check if pytest-recording's vcr fixture is being used:
```python
# In test, check the vcr fixture
import pytest_recording
print(f"pytest_recording version: {pytest_recording.__version__}")
```

**Expected:**
- pytest-recording should be in plugin list
- vcr_record_mode should be set

### Task 5: Try Alternative Approaches

**If VCR with pytest-recording doesn't work, try:**

#### Option A: aioresponses
```python
import pytest
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_with_aioresponses():
    with aioresponses() as mocked:
        mocked.get(
            'http://hapi.fhir.org/baseR4/Patient/90128869',
            payload={'resourceType': 'Patient', 'id': '90128869'}
        )
        # Test code here
```

#### Option B: responses with async support
```python
import responses
import pytest

@pytest.mark.asyncio
@responses.activate
async def test_with_responses():
    responses.add(
        responses.GET,
        'http://hapi.fhir.org/baseR4/Patient/90128869',
        json={'resourceType': 'Patient', 'id': '90128869'},
        status=200
    )
    # Test code here
```

#### Option C: pytest-httpx
```bash
uv add --dev pytest-httpx
```
```python
import pytest

@pytest.mark.asyncio
async def test_with_pytest_httpx(httpx_mock):
    httpx_mock.add_response(
        url='http://hapi.fhir.org/baseR4/Patient/90128869',
        json={'resourceType': 'Patient', 'id': '90128869'}
    )
    # Test code here
```

## Success Criteria

VCR is working when:
1. ✅ `uv run pytest tests/component/test_fhir_client.py -v` runs in <1s
2. ✅ `uv run pytest tests/component/test_fhir_client.py -v --block-network` passes
3. ✅ Deleting cassettes causes test to fail (no network)
4. ✅ Test execution time is <0.5s (not 16s)

## References

- pytest-recording: https://github.com/kiwicom/pytest-recording
- VCR.py: https://vcrpy.readthedocs.io/
- httpx VCR support: Check vcrpy GitHub issues for httpx/async

## Notes

- VCR patches httpcore, not httpx directly
- Async tests might need special handling
- The generated models import (49,810 lines) is already optimized via lazy loading
- Current workaround: Tests work but make real HTTP calls
