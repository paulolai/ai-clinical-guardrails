# Critical Patterns

**For:** All developers
**Purpose:** Reusable patterns that must be followed

---

## Result Type

```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E')

@dataclass(frozen=True)
class Success(Generic[T]): value: T

@dataclass(frozen=True)
class Failure(Generic[E]): error: E

type Result[T, E] = Success[T] | Failure[E]
```

## Domain Wrapper

```python
# Never return generated FHIR models
async def get_patient(id: str) -> Result[PatientProfile, FHIRError]:
    raw = await fetch_from_fhir(id)
    fhir_patient = FHIRPatient.model_validate(raw)
    return Success(PatientProfile.from_fhir(fhir_patient))
```

## Wrapper Pattern

The **Wrapper Pattern** isolates business logic from external complexity:

1. **Consume** complex generated models (FHIR, API responses)
2. **Transform** to clean domain models
3. **Return** only domain models to business logic

**Why:** External APIs change; business logic shouldn't need to change with them.

## Functional Core, Imperative Shell

- **Core:** Pure functions with no side effects (testable, predictable)
- **Shell:** Handles I/O, calls core functions, manages state
- **Benefit:** Easy to test business logic in isolation

---

## 🚫 Forbidden Patterns

*   **Magic Dictionaries:** Never pass untyped `dict` objects. Use Pydantic models.
*   **Mock-Only Development:** You must prove integration with a real sandbox (CLI/Component Tests) before mocking it in CI.
*   **Implicit Failure:** Never return `None` or raise generic Exceptions for compliance failures. Return a structured `Failure` result.
