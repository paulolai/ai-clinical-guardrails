# Commit Standards

**For:** All developers
**Purpose:** Standards for commits and pull requests

---

## Definition of Done

A feature is only complete when:

1.  The **CLI** can inspect the real data.
2.  The **Component Test** proves the integration works.
3.  The **Property Test** proves the logic is robust.
4.  The **README** is updated with the new capabilities.

## Before Committing

1. Run unit tests: `uv run pytest tests/ -m "not component" -x`
2. Run linter: `uv run ruff check .`
3. Update relevant AGENTS.md if patterns changed
4. **Regenerate ADRs:** If `docs/ARCHITECTURE_DECISIONS.md` changed, run `python3 scripts/generate_adr_summary.py`
5. Document significant learnings in `docs/learnings/`

## Commit Message Standards

```
[type]: Brief description

Detailed explanation if needed.

Fixes #[issue-number]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test changes
- `refactor`: Code refactoring
- `style`: Formatting changes

## Pull Request Requirements

- [ ] All tests pass
- [ ] Code reviewed by at least one other developer
- [ ] Documentation updated
- [ ] No forbidden patterns used
- [ ] CHANGELOG.md updated (if applicable)
