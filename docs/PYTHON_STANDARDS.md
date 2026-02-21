# Python Engineering Standards

This document defines the coding standards for Python development in this repository. All contributors must adhere to these guidelines to maintain a "Staff-Level" quality bar.

---

## 1. Type Safety (Strict)

We do not write untyped Python.
- **Rule:** All function signatures must have type hints.
- **Rule:** Use `mypy` strict mode.
- **Rule:** No `Any` unless absolutely necessary (comment with justification).
- **Rule:** Use Pydantic `BaseModel` for all data structures (no raw dictionaries).

```python
# ❌ BAD
def process_data(data):
    return data["id"]

# ✅ GOOD
from pydantic import BaseModel

class RequestData(BaseModel):
    id: str

def process_data(data: RequestData) -> str:
    return data.id
```

---

## 2. Error Handling (Result Pattern)

We treat errors as values, not exceptions, for business logic.
- **Rule:** Use `Result[T, E]` for expected failures (validation, business rules).
- **Rule:** Only raise Exceptions for unrecoverable system crashes.

### Implementation

```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

@dataclass(frozen=True)
class Failure(Generic[E]):
    error: E

type Result[T, E] = Success[T] | Failure[E]

# Usage
def divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Failure("Division by zero")
    return Success(a / b)

# Pattern matching
result = divide(10, 2)
match result:
    case Success(value):
        print(f"Result: {value}")
    case Failure(error):
        print(f"Error: {error}")
```

### Wrapping External Libraries

```python
async def get_patient(self, patient_id: str) -> Result[Patient, FHIRError]:
    try:
        response = await self.client.get(f"Patient/{patient_id}")
        return Success(Patient.model_validate(response.json()))
    except httpx.HTTPError as e:
        return Failure(FHIRError.from_exception(e))
```

---

## 3. Testing Philosophy (The Trophy)

We prioritize Component Tests (Real I/O) and Property Tests over Mock-heavy unit tests.

### 3.1 Property-Based Testing (Hypothesis)

If a function has business logic, it must have a hypothesis test.

```python
from hypothesis import given, strategies as st

@given(st.dates(), st.dates())
def test_date_range_invariant(start, end):
    if end >= start:
        ctx = EMRContext(admission_date=start, discharge_date=end)
        assert ctx.date_range[0] == start
```

### 3.2 Component Tests (Real Sandbox)

Prove integration with the real HAPI FHIR sandbox before mocking.

```python
@pytest.mark.component
async def test_client_fetches_real_patient():
    client = FHIRClient()
    result = await client.get_patient_profile("90128869")
    assert result.value.patient_id == "90128869"
```

---

## 4. Integration Patterns (Wrapper Pattern)

Isolate business logic from external complexity.

```
External API → Generated Models → Wrapper → Clean Domain Models → Business Logic
  Complex         Verbose          Filter      Simple/Stable
```

### Core Rules

1. Never leak generated/external models to business logic
2. Always return `Result[T, E]` for operations that can fail
3. Map errors to domain-specific error types
4. Return clean domain models

### FHIR Integration

```python
class FHIRClient:
    async def get_patient(self, patient_id: str) -> Result[PatientProfile, FHIRError]:
        # Call external API
        response = await self._client.get(f"{self.base_url}/Patient/{patient_id}")
        
        # Parse into generated model
        fhir_patient = Patient.model_validate(response.json())
        
        # Map to domain model (clean interface)
        return Success(PatientProfile.from_fhir(fhir_patient))
```

**Note:** FHIR uses `RootModel` for primitives. Access via `.root`:

```python
patient_id = str(fhir_patient.id.root) if fhir_patient.id else "unknown"
first_name = " ".join([str(g.root) for g in name.given]) if name.given else "Unknown"
```

---

## 5. Resilience Patterns

### 5.1 Retry with Exponential Backoff

```python
import asyncio
from typing import TypeVar

T = TypeVar('T')

async def retry_with_backoff(
    coro,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return await coro
        except exceptions as e:
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                raise
```

### 5.2 Circuit Breaker

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    timeout: timedelta = timedelta(minutes=1)
    
    def __post_init__(self):
        self.failures = 0
        self.last_failure = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func):
        if self.state == CircuitState.OPEN:
            if self._should_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit is open")
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
```

---

## 6. Code Organization

```
src/
├── models.py          # Pure data shapes (Pydantic)
├── engine.py          # Business logic (Functional Core)
├── integrations/      # I/O wrappers
│   ├── fhir/
│   └── audit/
└── api.py             # Imperative Shell (HTTP layer)
```

---

## 7. Forbidden Patterns

❌ **Never do:**
- Return `None` for errors
- Catch generic `Exception`
- Use untyped `dict` for data
- Leak generated models to business logic

✅ **Always do:**
- Use `Result[T, E]` for failures
- Catch specific exceptions
- Use Pydantic models
- Return domain models

---

## 8. Tooling

- **Linter:** `ruff`
- **Type Checker:** `mypy` (strict mode)
- **Test Runner:** `pytest`
- **Package Manager:** `uv`

---

## 9. CLI Development

Every major interface needs a CLI for debugging.

```bash
# FHIR Interface
uv run python cli/fhir.py inspect <patient_id>

# API Interface
uv run python cli/api.py verify --id <id> --text <text>
```

CLI files named after the interface they serve.
