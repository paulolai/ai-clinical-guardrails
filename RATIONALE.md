# Architecture Rationale

Why this system is built the way it is.

## Zero-Trust Verification

AI-generated clinical documentation is treated as untrusted input. Every output is verified against the EMR source of truth before it can be filed. This mirrors the approach used in high-assurance financial systems: don't validate what you can verify.

The core invariants:
1. **Date Integrity** — Every extracted date must exist in the patient's EMR context window
2. **Protocol Adherence** — Clinical triggers (e.g., Sepsis) force documentation of mandatory actions
3. **Data Safety** — Automated summaries are scanned for PII patterns before filing
4. **Drug Interactions** — Configurable rules catch dangerous medication combinations
5. **Allergy Conflicts** — Patient allergies are checked against prescribed medications

## Functional Core, Imperative Shell

AI models struggle with complex state management and side effects. The architecture constrains this:

- **Core** (`src/engine.py`): Pure business logic — takes inputs, returns `Result[T, E]`. No side effects, no I/O. Easy to verify.
- **Shell** (`src/integrations/`, `src/api.py`): Integration layers that handle FHIR calls, LLM requests, and HTTP. Easy to inspect.

The `ComplianceEngine.verify()` method is the central pure function. It receives patient data, EMR context, and AI output, then returns a `Result` indicating whether the output is safe to file.

## The Result Pattern

Business logic errors (compliance violations, missing data) are not exceptions — they're expected outcomes. The `Result[T, E]` type makes error handling explicit and composable:

```python
result = engine.verify(patient, context, ai_output)
result.map(lambda v: file_to_emr(v))           # only on success
result.chain(lambda v: send_notification(v))    # short-circuits on failure
```

This prevents "exception swallowing" and makes the failure path visible in the type system.

## LLM-Based Extraction Over Regex

Early approaches used regex patterns to extract structured data from clinical transcripts. This failed for real-world dictation:

- Regex can't handle context: "Patient was on Lisinopril but we switched to Enalapril" — which is active?
- Temporal expressions: "yesterday", "two weeks ago" — regex can't resolve these relative to encounter dates
- Abbreviations and spelling variations: "Lisinopril" vs "lisinopril" vs "Prinivil"

The solution: LLM handles the unstructured parsing, deterministic validation handles the safety guarantees. Confidence scores flag uncertain extractions for human review.

## Property-Based Testing

Standard unit tests verify specific examples. Property-based testing (Hypothesis) generates 100+ random inputs per test run and proves invariants hold across all of them. For a clinical safety system, this catches edge cases that manual test cases miss.

The strategies in `tests/test_compliance.py` generate randomized patient profiles and EMR contexts, then verify that the engine correctly flags hallucinated dates, PII leaks, and protocol violations regardless of the input data.

## Component Tests Against Real FHIR

The component tests in `tests/component/` run against the HAPI FHIR R5 sandbox using VCR cassettes. This proves the integration works against the real API before any mocking is introduced. The cassettes are re-recorded daily in CI to detect API drift.

## HTMX for the Clinical Transcription PWA

For the clinician-facing interface, HTMX was chosen over React/Svelte because:

1. **Maintainability** — Server-rendered HTML is simpler to debug at 2am
2. **Hiring continuity** — Any Python developer can pick up HTMX
3. **Compliance** — Easier to audit than client-side JS bundles
4. **Existing stack** — Natural extension of FastAPI + Jinja2

The trade-off: less "resume impressiveness" for more system reliability.

## On-Premise Deployment

The system runs entirely on a Mac Studio (128GB RAM) for a 5-clinician practice:

- Local Whisper for transcription
- Local Llama 3.1 70B for extraction + verification
- Local Keycloak for auth
- SQLite (WAL mode) for persistence

Zero data leaves the building. No ongoing API costs. Works during internet outages. ~$8,000 one-time vs. thousands/month in API calls.

## See Also

- `AGENTS.md` — Engineering standards and constraints
- `docs/ARCHITECTURE_DECISIONS.md` — Full ADR log
- `docs/INTEGRATION_TESTING.md` — Component test strategy
