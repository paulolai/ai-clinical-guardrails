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
| **Architecture Rules** | Constraints & Decisions | [ADR-extracts.md](ADR-extracts.md) |
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

## Building New Features: Mandatory Sequence

**⚠️ CRITICAL:** When building any new feature, you MUST follow the **8-Step Lifecycle IN ORDER**:

1. **Business Requirements** - Define the problem before any technical work
2. **Requirements & Source Spec** - Identify upstream schemas
3. **Generated Model Layer** - Create type-safe representations
4. **Domain Wrapper Layer** - Isolate business logic from external complexity
5. **Interface-Specific CLI** - Build debugging handles
6. **Component Testing** - Prove integration against real systems
7. **Business Logic** - Implement safety rules
8. **System Verification** - Property-based testing

**📖 Full Details:** [WORKFLOW_SPEC.md](docs/WORKFLOW_SPEC.md)

**❌ NEVER skip Step 1.** Technical architecture cannot be designed without first understanding the business problem, stakeholders, and success metrics.

---

## Getting Help

- **Fixing a bug?** → [Debugging Guide](docs/DEBUGGING_GUIDE.md)
- **Adding a feature?** → See [Operational Workflows](docs/standards/OPERATIONAL_WORKFLOWS.md)
- **Reviewing code?** → Check [Definition of Done](docs/standards/COMMIT_STANDARDS.md#definition-of-done)

---

## Component Test Troubleshooting

### VCR Cassettes with Dynamic Dates

**Problem:** Tests with VCR cassettes fail when run on different days because the LLM extraction prompt includes `date.today()` in the reference date field, causing cassette request mismatch.

**Solution:** The `conftest.py` implements a custom VCR matcher that normalizes dates in request bodies before comparison:

```python
def normalize_request_body(body):
    """Normalize request body by masking dynamic dates."""
    if body and isinstance(body, str):
        return re.sub(
            r'Reference Date: \d{4}-\d{2}-\d{2}',
            'Reference Date: <DATE_MASKED>',
            body
        )
    return body

def date_agnostic_matcher(r1, r2):
    """Custom matcher that ignores date differences in request bodies."""
    if r1.method != r2.method:
        return False
    if r1.uri != r2.uri:
        return False

    # Normalize both bodies (handle bytes vs strings)
    def get_body_str(body):
        if body is None:
            return None
        if isinstance(body, bytes):
            return body.decode('utf-8')
        return body

    body1 = normalize_request_body(get_body_str(r1.body))
    body2 = normalize_request_body(get_body_str(r2.body))

    if body1 != body2:
        raise AssertionError(f"Request bodies don't match")
    return True

# Register the custom matcher in pytest_configure
def pytest_configure(config):
    import vcr
    _original_vcr_init = vcr.VCR.__init__
    def _patched_vcr_init(self, *args, **kwargs):
        _original_vcr_init(self, *args, **kwargs)
        self.matchers['date_agnostic'] = date_agnostic_matcher
    vcr.VCR.__init__ = _patched_vcr_init
```

**Key points:**
- The matcher normalizes dates in BOTH the incoming request AND the stored cassette request
- Handles both string and bytes bodies
- Registered via pytest_configure to ensure it's available for all VCR instances
- Cassettes still contain the original dates (no masking needed during recording)

**When to use:** This is automatically applied to all component tests using VCR.

### Cassette/Snapshot Validation

**Problem:** LLM responses are non-deterministic. Re-recording cassettes may produce slightly different responses (wording, timestamps, token counts) that don't indicate real problems.

**Solution:** Use `scripts/validate_cassettes.py` which:
1. Categorizes changes as "benign" (timestamps, tokens) or "suspicious" (missing data, errors)
2. Uses LLM to determine if changes require manual attention
3. Only fails CI if changes are significant (structural changes, errors, missing data)

**When to use:** The CI `validate-cassettes` job runs this automatically on schedule.

**Local validation:**
```bash
# After re-recording cassettes
uv run python scripts/validate_cassettes.py
```

**Output interpretation:**
- ✅ **PASS**: Changes are benign (timestamps, minor wording)
- ⚠️ **FAIL**: Changes require manual review (structural changes, errors)

---

*See [RATIONALE.md](RATIONALE.md) for architectural reasoning*
