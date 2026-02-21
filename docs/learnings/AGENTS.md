# Learning Documentation Guide

**Critical:** Whenever you solve a significant problem, discover an important pattern, or learn something valuable for future development, you **must** document it here.

This is not optional - it's essential for project knowledge retention.

## When to Document

### Required Documentation
- Infrastructure fixes → `critical_infrastructure_fixes.md`
- API integration discoveries → `api_consistency_learnings.md`
- Testing improvements → `pbt_debugging.md`
- Workflow optimizations → `github_workflow.md`
- New patterns that solve recurring problems → appropriate file

### Decision Tree
```
Is this a significant fix or discovery?
├── Yes
│   ├── Infrastructure issue? → critical_infrastructure_fixes.md
│   ├── API pattern learned? → api_consistency_learnings.md
│   ├── Testing insight? → pbt_debugging.md
│   ├── CI/CD improvement? → github_workflow.md
│   └── Unsure? → critical_infrastructure_fixes.md (default)
└── No → Skip
```

## Documentation Format

### Learning Entry Template
```markdown
## YYYY-MM-DD: Brief Title

**Context:** What were you trying to do?

**Problem:** What went wrong?

**Solution:** How did you fix it?

**Root Cause:** Why did this happen?

**Prevention:** How to avoid this in the future?

**Related:** Links to issues, PRs, or other docs
```

### Example Entry
```markdown
## 2025-02-21: Hypothesis Deadline Timeouts in CI

**Context:** Property-based tests were failing in CI but passing locally.

**Problem:** Tests exceeded 200ms deadline due to slower CI runners.

**Solution:** Added `@settings(deadline=None)` to long-running tests.

**Root Cause:** CI runners are slower than local machines.

**Prevention:** Always consider CI performance when writing tests.
Use `deadline=None` or increase deadline for integration tests.

**Related:** See commit abc123, issue #45
```

## Learning Files

### critical_infrastructure_fixes.md
Infrastructure, CI/CD, build issues, environment problems.

### api_consistency_learnings.md
FHIR API patterns, external service integration lessons.

### pbt_debugging.md
Property-based testing insights, Hypothesis patterns.

### github_workflow.md
CI/CD improvements, GitHub Actions optimizations.

## Adding New Learnings

1. Choose appropriate file
2. Add entry at top (newest first)
3. Include date and clear title
4. Follow template format
5. Link to related commits/PRs

## Review Schedule

- **Weekly:** Scan for patterns
- **Monthly:** Consolidate similar learnings
- **Quarterly:** Archive outdated learnings to `archive/`
