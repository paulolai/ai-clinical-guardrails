# Integration Layer

Standards for external service integrations.

## Overview

External integrations use the **Wrapper Pattern** to isolate business logic from external complexity.

```
External API → Generated Models → Wrapper → Clean Domain Models → Business Logic
  Complex          Verbose            Filter      Simple/Stable
```

## Core Rules

1. Never leak generated/external models to business logic
2. Always return Result[T, E] for operations that can fail
3. Map errors to domain-specific error types
4. Return clean domain models that business logic depends on

## Service Integrations

- **FHIR** - Patient data and encounters (**FHIR R5** via `fhir.resources`).
    - *Note:* If R4 support is required, see [FHIR R4 Support Strategy](../../docs/technical/FHIR_R4_SUPPORT_STRATEGY.md).
- **Audit** - Immutable compliance logs

## Quick Reference

### Result Type
```python
async def get_patient(id: str) -> Result[PatientProfile, FHIRError]:
    try:
        return Success(await fetch_from_api(id))
    except httpx.HTTPError as e:
        return Failure(FHIRError.from_exception(e))
```

### RootModel Access
```python
# FHIR uses RootModel for primitives
patient_id = str(patient.id.root) if patient.id else "unknown"
```

## Adding New Integrations

1. Create directory: src/integrations/<service>/
2. Create client: src/integrations/<service>/client.py
3. Add to AGENTS.md: Document patterns
4. Write component tests
5. Add CLI tool

## Documentation

- [Common Patterns](../docs/COMMON_PATTERNS.md)
- [Integration Testing](../docs/INTEGRATION_TESTING.md)
- [Python Standards](../docs/PYTHON_STANDARDS.md)
