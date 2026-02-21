# Common Patterns

Quick reference for production-ready patterns.

## Core Patterns

| Pattern | Problem | Solution | Link |
|---------|---------|----------|------|
| **Result Type** | Hidden exceptions | Explicit error handling | [Details](./patterns/result-type.md) |
| **Retry Logic** | Transient failures | Exponential backoff | [Details](./patterns/retry-logic.md) |
| **Circuit Breaker** | Cascade failures | Fail fast | [Details](./patterns/circuit-breaker.md) |

## Usage Checklist

- [ ] Use `Result[T, E]` for external API calls
- [ ] Add retry with backoff for network operations
- [ ] Use circuit breaker for external services
- [ ] Never return `None` for errors

## Quick Examples

### Result Type
```python
async def fetch() -> Result[Patient, FHIRError]:
    try:
        return Success(await api.get())
    except httpx.HTTPError as e:
        return Failure(FHIRError.from_exception(e))
```

### Retry
```python
result = await retry_with_backoff(
    fetch_patient("123"),
    max_retries=3,
    exceptions=(httpx.NetworkError,)
)
```

### Circuit Breaker
```python
breaker = CircuitBreaker(failure_threshold=5)
result = await breaker.call(lambda: api.fetch())
```

## See Also

- [Testing Patterns](../tests/AGENTS.md)
- [Integration Patterns](../src/integrations/AGENTS.md)
