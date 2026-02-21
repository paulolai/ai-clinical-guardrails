# Integration & Component Testing

Guide for testing external integrations and real API interactions.

## Philosophy

**Golden Rule:** Prove integration with real sandbox before mocking in CI.

**Test Types:**
- **Component Tests:** Real external services (HAPI FHIR, EMR APIs)
- **Integration Tests:** End-to-end workflows
- **Unit Tests:** Isolated logic

## Component Tests

### Markers
```python
import pytest

@pytest.mark.component
async def test_fhir_client_fetch():
    """Requires HAPI FHIR sandbox."""
    client = FHIRClient()
    patient = await client.get_patient("90128869")
    assert patient is not None
```

### TestDataManager Pattern
```python
@pytest.fixture
async def test_data_manager():
    manager = TestDataManager()
    yield manager
    await manager.cleanup_all()

@pytest.mark.component
async def test_with_cleanup(test_data_manager):
    patient = await test_data_manager.create_patient("Test")
    result = await process_patient(patient.id)
    assert result.is_success
    # Cleanup automatic
```

### Data Isolation
```python
import uuid

def create_unique_name(base: str) -> str:
    return f"{base}-{uuid.uuid4()[:8]}"
```

## Running Tests

**Local:**
```bash
# All component tests
uv run pytest tests/component/ -v

# Specific test
uv run pytest tests/component/test_fhir_client.py::test_fetch -v

# With debugging
uv run pytest tests/component/ -v -s --pdb
```

**CI/CD:**
Component tests skip by default. Run in nightly builds:
```yaml
- name: Component Tests
  if: github.event.schedule == '0 0 * * *'
  run: uv run pytest tests/component/ -v
```

## Mock Strategy

**When to Mock:** After component tests prove integration works.

```python
# conftest.py
@pytest.fixture
def mock_fhir_client():
    mock = Mock(spec=FHIRClient)
    mock.get_patient.return_value = Success(
        Patient(id="123", resource_type="Patient")
    )
    return mock
```

**Mock Verification:**
```python
@pytest.mark.component
async def test_mock_matches_real():
    """Verify mock matches actual API behavior."""
    real = FHIRClient()
    mock = create_mock()
    
    real_result = await real.get_patient("123")
    mock_result = await mock.get_patient("123")
    
    assert real_result.is_success == mock_result.is_success
```

## FastAPI TestClient

```python
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_verify_endpoint():
    response = client.post("/verify", json={
        "patient_id": "90128869",
        "text": "Patient seen today.",
        "dates": ["2025-02-21"]
    })
    assert response.status_code == 200
    assert response.json()["is_success"] is True
```

## Best Practices

1. **Isolate External Dependencies**
```python
@pytest.mark.skipif(
    not os.getenv("FHIR_BASE_URL"),
    reason="FHIR_BASE_URL not set"
)
async def test_conditional():
    pass
```

2. **Retry Transient Failures**
```python
@pytest.mark.component
async def test_with_retry():
    for attempt in range(3):
        try:
            return await client.get_patient("123")
        except NetworkError:
            if attempt == 2:
                raise
            await asyncio.sleep(1)
```

3. **Document Required Setup**
```python
@pytest.mark.component
async def test_external_api():
    """
    Requires:
    - HAPI FHIR at FHIR_BASE_URL
    - Network connectivity
    - Patient 90128869 exists
    
    Run: export FHIR_BASE_URL=http://hapi.fhir.org/baseR4
    """
    pass
```

## Troubleshooting

**Connection Refused:**
```bash
curl $FHIR_BASE_URL/metadata  # Verify server
env | grep -i proxy          # Check proxy
```

**Data Leaks:**
- Use `TestDataManager` for cleanup
- Unique names with UUIDs
- Check for missing `await` in async cleanup

**Flaky Tests:**
- Add `@flaky(max_runs=3)` for known issues
- Improve data isolation

## See Also

- [Testing Workflows](./TESTING_WORKFLOWS.md) - Commands
- [Testing Framework](./TESTING_FRAMEWORK.md) - Philosophy
- [Debugging Guide](./DEBUGGING_GUIDE.md) - Troubleshooting
