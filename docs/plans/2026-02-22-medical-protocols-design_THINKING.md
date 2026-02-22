# Medical Protocols Design - Decision Process

**Companion to:** `2026-02-22-medical-protocols-design.md`
**Purpose:** Document decision process, trade-offs, and alternatives considered

---

## Goals and Non-Goals

### Goals (What We're Doing)

1. **Configurable Rules:** Medical staff can add safety rules without code changes
2. **Pattern-Based Matching:** Use declarative patterns rather than hardcoded logic
3. **Critical Safety Coverage:** Drug interactions, allergies, documentation requirements
4. **Australian Healthcare Context:** PBS, MBS, local standards
5. **Fast Rule Updates:** Minutes, not days, to add new rules

### Non-Goals (What We're NOT Doing)

1. **Clinical Decision Support:** We're NOT replacing clinician judgment - just flagging potential issues
2. **Real-Time Drug Database:** Not integrating with external medication databases (v1)
3. **Machine Learning Rules:** Not using ML to discover interactions (v1)
4. **Complete Australian Formulary:** Starting with common interactions, not all PBS items
5. **Prescribing System:** Not generating prescriptions, only validating extractions

---

## Alternatives Considered

### Alternative 1: Hardcoded Rules (REJECTED)

**Approach:** Add `_verify_drug_interactions()`, `_verify_allergies()` methods to ComplianceEngine with if-statements.

**Pros:**
- Simple to implement
- Type-safe
- Fast execution

**Cons:**
- Requires code deployment for every new rule
- Medical staff dependent on developers
- Rules scattered across code files
- Can't disable rules per-environment

**Decision:** Rejected. The requirement is "I don't want to rebuild code for new rules."

---

### Alternative 2: Rules Engine Library (REJECTED)

**Approach:** Use existing Python rules engine like `durable-rules` or `business-rules`.

**Pros:**
- Battle-tested
- Rich feature set (chaining, priorities, etc.)
- Active community

**Cons:**
- Heavy dependency for our use case
- Learning curve for rule authors
- YAML/DSL mismatch with Python patterns
- May be overkill for simple pattern matching

**Decision:** Rejected. Too complex for our needs. Our rules are simple: "If patient has X and extraction has Y, alert."

---

### Alternative 3: Database-Driven Rules (REJECTED)

**Approach:** Store rules in PostgreSQL, load at runtime.

**Pros:**
- Easy to build admin UI
- Audit trail built-in
- Concurrent editing support

**Cons:**
- Requires database migration for schema changes
- More infrastructure (connection pooling, etc.)
- Harder to version control rules with code
- Overkill for read-heavy, write-rarely use case

**Decision:** Rejected. Rules change infrequently, don't need database overhead.

---

### Alternative 4: Config Files (SELECTED)

**Approach:** YAML/JSON files in `config/` directory, loaded at startup.

**Pros:**
- Simple to understand
- Version controlled with code
- Easy to review (pull requests)
- No database needed
- Fast loading
- Can hot-reload in development

**Cons:**
- Requires restart in production (unless hot-reload enabled)
- No built-in admin UI (would need to build one)
- Limited to file-based editing

**Decision:** Selected. Best balance of simplicity and flexibility.

---

## Decision Criteria

### Primary Drivers

1. **Safety-Critical Context:** Rules must be auditable and version controlled
2. **Medical Staff Workflow:** Pharmacists/clinicians need to add rules without waiting for dev team
3. **Australian Healthcare:** Must support PBS, MBS, local standards
4. **Performance:** Can't add significant latency to verification (already <100ms target)

### Constraints

1. **No External Dependencies:** Don't add heavy libraries unless necessary
2. **Type Safety:** Prefer Pydantic models over dicts
3. **Testability:** Must be testable with PBT
4. **Existing Patterns:** Follow Result pattern, Wrapper pattern, etc.

---

## Trade-offs

### Trade-off 1: YAML vs JSON

**YAML Selected**

**Pros of YAML:**
- Comments allowed (document WHY a rule exists)
- More readable for non-developers
- Multi-line strings for messages
- Standard in DevOps

**Cons of YAML:**
- Slightly slower parsing
- Whitespace-sensitive
- Security concerns with `!!` constructors (mitigated: use SafeLoader)

**Decision:** YAML. Medical staff will read these files.

---

### Trade-off 2: Hot Reload vs Restart

**Hot Reload: Disabled by Default**

**Pros of Hot Reload:**
- Instant rule updates in production
- No downtime

**Cons of Hot Reload:**
- Risk of loading broken config
- Harder to debug (which config version?)
- Race conditions possible

**Decision:** Hot reload disabled by default. Enable only in development. Production gets config at startup.

---

### Trade-off 3: Severity Levels

**Using Existing Severity Enum**

Already have: `CRITICAL`, `HIGH`, `WARNING`, `INFO`

**Critical:** Blocks filing (drug interaction, allergy conflict)
**High:** Reduces trust score significantly (duplicate therapy)
**Warning:** Informational only (PBS authority required)

**Decision:** Reuse existing severity levels. Don't add complexity.

---

### Trade-off 4: Drug Class Matching

**Challenge:** "ACE Inhibitor" vs "Lisinopril", "Enalapril", "Ramipril"

**Options:**
1. **List all generic names:** Explicit but verbose
2. **Drug class abstraction:** "ACE_INHIBITOR" maps to list of names
3. **Regex patterns:** Flexible but error-prone

**Decision:** Option 2 for v1. Maintain a `drug_classes.json` mapping:

```json
{
  "ACE_INHIBITOR": ["lisinopril", "enalapril", "ramipril"],
  "NSAID": ["ibuprofen", "naproxen", "diclofenac"]
}
```

This separates drug classification from interaction rules.

---

## Risks and Mitigations

### Risk 1: Incomplete Drug Lists

**Risk:** We miss an interaction because a new drug isn't in our lists.

**Mitigation:**
- Start with high-risk interactions (Warfarin, known allergens)
- Document that this is "defense in depth" not "complete solution"
- Log unknown medications for analysis
- Plan for external drug database integration (v2)

### Risk 2: False Positives

**Risk:** Alert fatigue causes clinicians to ignore all alerts.

**Mitigation:**
- Target <5% false positive rate
- PBT to test boundary cases
- Severity levels (WARNING vs CRITICAL)
- Configurable per-environment

### Risk 3: Config Syntax Errors

**Risk:** Malformed YAML breaks system startup.

**Mitigation:**
- Pydantic models validate config structure
- Schema validation on load
- Graceful degradation (skip invalid rules, log warnings)
- CLI tool to validate config before deployment

### Risk 4: Performance Degradation

**Risk:** Pattern matching adds too much latency.

**Mitigation:**
- Compile patterns once at load time
- Target: <10ms overhead
- Benchmark in test suite
- Skip disabled checkers efficiently

### Risk 5: Medical Liability

**Risk:** System misses critical interaction, patient harmed.

**Mitigation:**
- Clear documentation: "This is a safety net, not a replacement for clinical judgment"
- Always show alerts, never auto-correct
- Audit trail of all verifications
- Limited scope (v1 = common interactions only)

---

## Revisit Conditions

**Revisit this design when:**

1. **Need Real-Time Drug Database:** If we integrate with MIMS or Australian Medicines Handbook API
2. **Rule Count Exceeds 500:** Performance may degrade, consider database or indexing
3. **Need Per-Patient Rules:** If rules need patient-specific customization
4. **Machine Learning Proven:** If we develop ML models that outperform pattern matching
5. **Multi-Tenant Requirement:** If different hospitals need completely different rule sets

---

## Pattern Decisions

### Why Separate Checkers?

Instead of one giant `check()` function, we have `DrugInteractionChecker`, `AllergyChecker`, etc.

**Reason:**
- Single Responsibility Principle
- Easier to test independently
- Can disable per-checker in config
- Clear separation of concerns

### Why ProtocolRegistry?

Central registry orchestrates all checkers.

**Reason:**
- One entry point for verification
- Handles config loading/checker instantiation
- Easy to add new checker types
- Consistent error handling

### Why PatternMatcher Abstraction?

Different checkers need different matching logic.

**Reason:**
- Medication matching: String similarity, class matching
- Allergy matching: Cross-reference lists
- Field matching: Presence check, type check
- Allows extending matching without changing checkers

---

## Integration Trade-offs

### Where to Call Protocol Checks?

**Options:**
1. In `ComplianceEngine.verify()` after existing checks
2. In `VerificationWorkflow` before calling `ComplianceEngine`
3. As a separate service call

**Decision:** Option 1 - extend `ComplianceEngine`.

**Reason:**
- Protocol checks ARE compliance checks
- Keeps all safety logic in one place
- Can share alert aggregation logic
- Simpler mental model

### How to Pass Extraction Data?

**Challenge:** `ComplianceEngine.verify()` takes `AIGeneratedOutput`, but checkers need `StructuredExtraction`.

**Options:**
1. Change `ComplianceEngine` signature (breaking change)
2. Convert `AIGeneratedOutput` to `StructuredExtraction` internally
3. Pass both types

**Decision:** Option 2 - internal conversion.

**Reason:**
- Minimal breaking changes
- Conversion is mechanical (date strings → dates, etc.)
- Keeps API stable

---

## Testing Strategy Decisions

### Why PBT for Allergy Checker?

**Decision:** Use Hypothesis PBT to generate random patient profiles with allergies and extractions with medications.

**Property:** "If patient has allergy X and extraction contains X-class drug, MUST alert."

**Reason:**
- Allergy checking is safety-critical
- Edge cases hard to anticipate (compound allergies, spelling variations)
- PBT finds gaps in logic
- Follows existing pattern in `test_compliance.py`

### Why Unit Tests for Config?

**Decision:** Regular unit tests (not PBT) for config loading.

**Reason:**
- Config structure is fixed schema
- PBT would generate invalid configs (not useful)
- Focus on: valid config loads, invalid config errors, hot-reload works

---

## CLI Tool Decisions

### Why Create `cli/protocols.py`?

**Decision:** New CLI tool rather than extending existing `cli/api.py`.

**Reason:**
- Different use case (debug rules vs verify patient)
- Rule management is specialized
- Keeps `cli/api.py` focused on API operations
- Can have different permissions (devs vs operators)

### CLI Commands

```bash
# Validate config syntax
uv run python cli/protocols.py validate-config config/medical_protocols.yaml

# Test rules against sample data
uv run python cli/protocols.py test-rule --rule "Warfarin NSAID" --patient-id 123

# List all active rules
uv run python cli/protocols.py list-rules

# Check specific patient/transcript
uv run python cli/protocols.py check --patient-id 123 --transcript "..."
```

---

## Australian Healthcare Decisions

### Why PBS/MBS in v1?

**Decision:** Include PBS/MBS validation patterns.

**Reason:**
- Explicit requirement from user
- Australian context is project differentiator
- Pattern-based checking works (doesn't need real-time API)
- Can be disabled in non-AU deployments

### PBS Implementation Strategy

**Decision:** Pattern-based, not API-based.

**Approach:**
```yaml
- name: "Authority Required - Sildenafil"
  pattern:
    medications: ["sildenafil", "viagra"]
    requires_authority: true
```

**Not doing (v1):**
- Real-time PBS eligibility API calls
- Patient-specific PBS history lookup
- Authority code validation against Services Australia

**Why:** Simple pattern matching catches 80% of issues. Full integration is v2.

---

## Performance Decisions

### Caching Strategy

**Decision:** Cache compiled patterns at load time.

**Reason:**
- Regex compilation is expensive
- Rules don't change at runtime (production)
- 10-100 rules → negligible memory overhead

**Not caching:**
- Patient data (changes every request)
- Extraction results (unique per request)

### Target: <10ms Overhead

**Decision:** Per-verification overhead must be <10ms.

**Measurement:**
- Benchmark in `tests/benchmarks/test_performance.py`
- Before/after comparison
- p95/p99 latencies (not just average)

**Mitigation if exceeded:**
- Disable checkers by default
- Async parallel checking
- Lazy evaluation (stop at first CRITICAL)

---

## Documentation Decisions

### Why Two Files?

**Decision:** Follow project standard: `design.md` + `design_THINKING.md`.

**Reason:**
- Context window management (AGENTS.md vs thinking)
- Decision rationale available without cluttering main doc
- Future maintainers can understand trade-offs
- Consistent with other project docs

### What Goes Where?

**Main Doc:**
- Business context
- Architecture
- Interfaces
- Configuration examples
- Testing strategy
- Acceptance criteria

**Thinking Doc:**
- Alternatives considered
- Trade-offs
- Risks
- Revisit conditions
- Pattern decisions

---

## Summary

**Key Decisions:**
1. YAML configuration files (not hardcoded/database/external library)
2. Modular checker classes (not monolithic)
3. Pattern-based matching (not ML/rules engine)
4. Extend ComplianceEngine (not separate service)
5. Include PBS/MBS patterns (Australian context)
6. PBT for safety-critical checkers
7. <10ms performance target

**Trade-offs Accepted:**
- No hot reload in production (restart required)
- No admin UI (file-based editing)
- Incomplete drug database (v1 = common interactions)
- YAML security concerns (mitigated with SafeLoader)

**Risks Accepted:**
- May miss rare interactions (mitigated: log unknown drugs)
- False positives possible (mitigated: <5% target, severity levels)

**Revisit When:**
- Need real-time drug database integration
- Rule count exceeds 500
- Need per-patient rule customization
- Performance targets not met

---

*This document follows the [THINKING_STANDARD.md](../../THINKING_STANDARD.md) pattern.*
