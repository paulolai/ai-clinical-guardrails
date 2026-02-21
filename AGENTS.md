# AI Agent Operational Protocol

This document defines the **High-Assurance Engineering Standards** for this repository.

**For:** All AI assistants and developers
**Quick Start:**
- **Building?** → Read [Operational Workflows](docs/standards/OPERATIONAL_WORKFLOWS.md)
- **Testing?** → Read [Testing Standards](docs/standards/TESTING_STANDARDS.md)
- **Committing?** → Read [Commit Standards](docs/standards/COMMIT_STANDARDS.md)
- **New here?** → Read [RATIONALE.md](RATIONALE.md)

---

## 🏛 Core Philosophy: "Zero-Trust Engineering"

We operate on the principle that **External Data** (User Input, EMR APIs, AI Predictions) is inherently untrusted until verified by our system.

### Documentation Integrity: No Made-Up Numbers

**Critical Rule:** Never present estimates or projections as facts. Clearly distinguish between:
- **Known facts:** Data from actual measurements or established sources
- **Estimates:** Calculated projections with methodology explained
- **Placeholders:** Values yet to be determined

**Why:** In safety-critical healthcare systems, credibility is everything. Made-up numbers destroy trust with clinical stakeholders.

**What to do:**
- **For known facts:** Cite source: "Based on [Study X], [Y]% of clinicians..."
- **For estimates:** Label clearly: "Estimated: $[X]/year based on [Y] extractions/day"
- **For placeholders:** Use: `[TBD]`, `[To be determined]`, `[Pilot will establish]`

**Examples:**
```markdown
❌ "Reduces documentation time by 50%" (presented as fact)
✅ "Estimated 30-50% reduction based on similar systems; pilot will validate"
```

---

## Standards Quick Reference

| Standard | Purpose | Location |
|----------|---------|----------|
| **Operational Workflows** | How to build features | [docs/standards/OPERATIONAL_WORKFLOWS.md](docs/standards/OPERATIONAL_WORKFLOWS.md) |
| **Critical Patterns** | Code patterns to use | [docs/standards/CRITICAL_PATTERNS.md](docs/standards/CRITICAL_PATTERNS.md) |
| **Testing Standards** | How to test safely | [docs/standards/TESTING_STANDARDS.md](docs/standards/TESTING_STANDARDS.md) |
| **Commit Standards** | How to commit code | [docs/standards/COMMIT_STANDARDS.md](docs/standards/COMMIT_STANDARDS.md) |
| **Thinking Documentation** | When to document decisions | [THINKING_STANDARD.md](docs/THINKING_STANDARD.md) |

---

## Project Context

**Domain:** Healthcare / Clinical AI Safety
**Stack:** Python 3.12+, FastAPI, FHIR, Hypothesis
**Package Manager:** `uv`

**Essential Commands:**
```bash
# Run tests
uv run pytest tests/ -v

# Check code
uv run ruff check .

# Type check
uv run mypy src/

# Run API
uv run python main.py
```

---

## Getting Help

- **Fixing a bug?** → [Debugging Guide](docs/DEBUGGING_GUIDE.md)
- **Adding a feature?** → See [Operational Workflows](docs/standards/OPERATIONAL_WORKFLOWS.md)
- **Reviewing code?** → Check [Definition of Done](docs/standards/COMMIT_STANDARDS.md#definition-of-done)

---

*See [RATIONALE.md](RATIONALE.md) for architectural reasoning*
