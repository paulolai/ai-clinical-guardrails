# GitHub Workflow Learnings

CI/CD improvements and optimizations.

## 2025-02-21: Template Entry

**Context:** Template for future entries.

**Problem:** Example problem.

**Solution:** Example solution.

**Root Cause:** Example root cause.

**Prevention:** Example prevention.

**Related:** N/A

---

## CI/CD Best Practices

### uv in GitHub Actions
```yaml
- uses: astral-sh/setup-uv@v2
- run: uv sync
- run: uv run pytest tests/
```

### Matrix Testing
```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
```

### Conditional Jobs
```yaml
component-tests:
  if: github.event.schedule == '0 0 * * *'
```

## Template

**Context:**

**Problem:**

**Solution:**

**Root Cause:**

**Prevention:**

**Related:**
