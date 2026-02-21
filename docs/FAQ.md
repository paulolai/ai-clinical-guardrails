# Frequently Asked Questions

## Why Property-Based Testing?

**Q:** Why not just write unit tests with specific examples?

**A:** Safety-critical systems need to prove invariants hold across ALL possible inputs, not just the ones we thought of. Hypothesis generates thousands of test cases automatically, finding edge cases we'd never consider.

---

## What's the Wrapper Pattern?

**Q:** Why can't I use FHIR models directly in business logic?

**A:** FHIR models are complex (50,000+ lines) and change frequently. The wrapper isolates our code from upstream changes and returns simple domain models like `PatientProfile` instead of `FHIRPatient`.

---

## How do I add a new compliance rule?

**Q:** I want to add a rule that checks for medication interactions. How?

**A:**
1. Add rule to `src/engine.py` in `_check_rules()`
2. Define violation type in `ViolationDetail`
3. Write property test in `tests/test_compliance.py`
4. Add component test in `tests/component/`

See [Contributing Guide](../CONTRIBUTING.md) for detailed steps.

---

## What's the difference between component and unit tests?

**Q:** When do I use `@pytest.mark.component`?

**A:** Component tests hit real external services (FHIR sandbox). Unit tests use mocks and test pure logic. Prove integration works with component tests first, then mock for CI speed.

---

## How do I debug a failing Hypothesis test?

**Q:** Hypothesis found a counterexample but I don't understand it.

**A:**
1. Reproduce with seed: `pytest tests/ --hypothesis-seed=12345`
2. Add print statements in test
3. Use `--hypothesis-verbosity=verbose`
4. See [Testing Workflows](TESTING_WORKFLOWS.md)

---

## Why Result[T, E] instead of exceptions?

**Q:** Why not just raise exceptions for errors?

**A:** Exceptions hide error paths. Result forces explicit handling and makes business logic errors part of the type system. You cannot ignore a `Failure` without the compiler/type checker complaining.

---

## How do I deploy this?

**Q:** What's the deployment process?

**A:**
1. Set environment variables (see `.env.example`)
2. Run `uv sync` to install dependencies
3. Start with `uv run python main.py`
4. For production, use Docker with health checks

See [Operations Guide](OPERATIONS.md) (TODO).

---

## What's Zero-Trust Engineering?

**Q:** What does "Zero-Trust" mean in this context?

**A:** Never trust external input (AI output, EMR data) without verification. Every piece of data from outside our system is assumed to be potentially incorrect until proven otherwise.

---

## How do I run just the fast tests?

**Q:** I want to skip component tests during development.

**A:**
```bash
uv run pytest tests/ -m "not component" -v
```

---

## What's an Invariant?

**Q:** The docs mention "invariants" - what are they?

**A:** An invariant is a condition that must always be true. Example: "All dates in AI output must be within patient's admission window." Property-based testing proves these hold for all inputs.

---

## Still have questions?

Check the [Glossary](GLOSSARY.md) for terminology, or review [AGENTS.md](../AGENTS.md) for core principles.
