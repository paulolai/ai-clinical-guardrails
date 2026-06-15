# Adding a New Compliance Rule

End-to-end walkthrough with two worked examples: drug interactions and duplicate therapy.

## The Pipeline

```
Clinical Insight → Requirements → Config → Checker → Test → Verified
```

## Step 1: Clinical Insight

The problem: AI-generated clinical notes might prescribe Warfarin (blood thinner) and Ibuprofen (NSAID) together. This combination increases bleeding risk. The existing engine catches date mismatches and PII leaks, but not drug interactions.

**Source:** `docs/plans/2026-02-22-medical-protocols-design.md`

## Step 2: Define the Invariant

The invariant that must always hold:

> If extraction contains both a trigger medication (Warfarin) AND a conflict medication (Ibuprofen), a CRITICAL alert MUST be raised.

This becomes a property-based test before any code is written.

## Step 3: Write the Rule Config

Add to `config/medical_protocols.yaml`:

```yaml
rules:
  drug_interactions:
    - name: "Warfarin NSAID"
      pattern:
        trigger:
          medications: ["warfarin", "coumadin"]
        conflicts:
          medications: ["ibuprofen", "naproxen", "aspirin"]
      severity: "CRITICAL"
      message: "Warfarin + NSAID increases bleeding risk"
```

The config is the source of truth. Clinical staff can add rules here without code changes.

## Step 4: Implement the Checker

Create `src/protocols/checkers/drug_checker.py`:

```python
class DrugInteractionChecker(ProtocolChecker):
    def check(self, patient, extraction) -> list[ComplianceAlert]:
        # Combine patient meds with extracted meds
        # For each rule: check if trigger AND conflict are both present
        # If both present → alert
```

The checker reads from the config, matches against extracted medications, and returns alerts. The base class (`ProtocolChecker`) provides `_create_alert()` for consistent alert formatting.

**Source:** `src/protocols/checkers/drug_checker.py` (37 lines)

## Step 5: Register the Checker

In `src/protocols/registry.py`, add to `checker_map`:

```python
checker_map = {
    "drug_interactions": DrugInteractionChecker,
    "allergy_checks": AllergyChecker,
    "required_fields": RequiredFieldsChecker,
}
```

The registry reads the config and instantiates enabled checkers.

## Step 6: Write the Property-Based Test

Before writing example tests, prove the invariant holds for random inputs:

```python
@given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
def test_both_sides_present_implies_alert(self, config, meds):
    # Generate random medication lists
    # Filter to cases where both trigger AND conflict are present
    # Assert: checker MUST return an alert

@given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
def test_only_one_side_present_implies_no_alert(self, config, meds):
    # Generate random medication lists
    # Filter to cases where only one side is present
    # Assert: checker MUST NOT return an alert
```

Hypothesis generates 200 random combinations per test run. If any combination violates the invariant, the test fails with a minimal counterexample.

**Source:** `tests/protocols/checkers/test_protocols_pbt.py`

## Step 7: Write Example Tests

Add specific examples for documentation:

```python
def test_detects_warfarin_nsaid_interaction():
    # Warfarin + Ibuprofen → CRITICAL alert
    ...

def test_no_alert_when_only_trigger_present():
    # Only Warfarin → no alert
    ...
```

**Source:** `tests/protocols/checkers/test_drug_checker.py`

## Step 8: Verify End-to-End

Test through the `ComplianceEngine` to confirm integration:

```python
engine = ComplianceEngine(protocol_config=config)
result = engine.verify(patient, context, ai_output)
assert not result.is_success  # Warfarin + Ibuprofen detected
```

**Source:** `tests/test_compliance.py::test_compliance_engine_with_protocols`

## Step 9: Add Traces

The engine automatically instruments verification spans:

```
compliance.verify
  ├── patient_id: "P-TEST"
  ├── compliance.outcome: "failure"
  ├── compliance.alert_count: 1
  └── compliance.verify.protocols
```

Alert events are attached to the span:

```python
span.add_event("alert", {
    "rule_id": "PROTOCOL_DRUG_INTERACTIONS_WARFARIN_NSAID",
    "severity": "critical",
    "message": "Warfarin + NSAID increases bleeding risk"
})
```

**Source:** `tests/test_telemetry.py`

---

## Worked Example 2: Duplicate Therapy Detection

Same pipeline, different matching pattern. This example shows what changes when the rule isn't about specific drug names — it's about therapeutic classes.

### Clinical Insight

A patient is on both Lisinopril and Enalapril. Both are ACE inhibitors. Taking two drugs from the same class increases side effects without additional benefit. The engine needs to catch redundant therapy.

**Source:** `docs/plans/2026-02-22-medical-protocols-design.md`

### Invariant

> If extraction contains more than N medications in the same drug class, an alert MUST be raised.

Unlike drug interactions (name-based matching), this requires **class-based matching** — grouping drugs into therapeutic categories first.

### Config

Add to `config/medical_protocols.yaml`:

```yaml
duplicate_therapy:
  - name: "Duplicate ACE Inhibitor"
    pattern:
      drug_class: "ACE_INHIBITOR"
      max_count: 1
    severity: "HIGH"
    message: "Multiple ACE inhibitors detected — consider consolidating"
```

Same format as drug interactions, but the pattern uses `drug_class` + `max_count` instead of trigger/conflict.

### Matcher (New Pattern)

Create `src/protocols/checkers/drug_class_matcher.py`:

```python
DRUG_CLASS_MAP = {
    "lisinopril": "ACE_INHIBITOR",
    "enalapril": "ACE_INHIBITOR",
    "atorvastatin": "STATIN",
    "rosuvastatin": "STATIN",
    # ... ~20 drugs mapped to 6 classes
}

class DrugClassMatcher:
    def count_by_class(self, extraction, drug_class: str) -> int:
        # Count how many extracted medications belong to the class
```

**Key difference from DrugInteractionChecker:** This introduces a new matcher concept. Drug interactions match individual medication names; duplicate therapy groups medications into classes first, then counts within a class. The matcher is extracted as its own module because it's reusable across different class-based rules.

### Checker

Create `src/protocols/checkers/duplicate_therapy_checker.py`:

```python
class DuplicateTherapyChecker(ProtocolChecker):
    def check(self, patient, extraction) -> list[ComplianceAlert]:
        # Uses DrugClassMatcher.count_by_class()
        # For each rule: if count > max_count → alert
```

Reads from config under the `duplicate_therapy` key. Same base class, same `_create_alert()` helper.

**Source:** `src/protocols/checkers/duplicate_therapy_checker.py`

### Registry

Add to `checker_map` in `src/protocols/registry.py`:

```python
checker_map = {
    "drug_interactions": DrugInteractionChecker,
    "duplicate_therapy": DuplicateTherapyChecker,
    "allergy_checks": AllergyChecker,
    "required_fields": RequiredFieldsChecker,
}
```

### Property-Based Tests

Prove the counting invariant:

```python
@given(extraction=extraction_strategy(), drug_class=st.sampled_from(["ACE_INHIBITOR", "STATIN", ...]))
def test_count_accurate(self, extraction, drug_class):
    # Verify count_by_class matches manual count

@given(extraction=extraction_with_class(drug_class), drug_class=st.sampled_from([...]))
def test_never_miss_class_member(self, extraction, drug_class):
    # Every drug in DRUG_CLASS_MAP for that class must be counted

@given(extraction=extraction_without_class(drug_class), drug_class=st.sampled_from([...]))
def test_never_false_positive(self, extraction, drug_class):
    # No alert when extraction has no drugs in that class
```

**Source:** `tests/protocols/checkers/test_protocols_pbt.py`

### Example Tests

```python
def test_duplicate_ace_inhibitors():
    # Lisinopril + Enalapril → HIGH alert
    ...

def test_single_ace_inhibitor_no_alert():
    # Only Lisinopril → no alert
    ...

def test_different_classes_no_alert():
    # Lisinopril (ACE) + Atorvastatin (statin) → no alert
    ...

def test_empty_extraction():
    # No medications → no alert
    ...
```

**Source:** `tests/protocols/checkers/test_duplicate_therapy.py`

### Engine Integration & Traces

Same as drug interactions — the engine calls all registered checkers and captures OTEL spans automatically. No additional work needed.

## Adding a New Checker Type

To add a completely new checker type (not just a new rule):

1. Create `src/protocols/checkers/new_checker.py` extending `ProtocolChecker`
2. Implement `check(patient, extraction) -> list[ComplianceAlert]`
3. Register in `src/protocols/registry.py` `checker_map`
4. Add config section in `config/medical_protocols.yaml`
5. Write PBT tests proving the invariants
6. Write example tests for documentation

## Files Involved

| File | Role |
|------|------|
| `config/medical_protocols.yaml` | Rule definitions (source of truth) |
| `src/protocols/models.py` | Data models (ProtocolConfig, ProtocolRule) |
| `src/protocols/config.py` | YAML loader |
| `src/protocols/checkers/base.py` | Abstract base class |
| `src/protocols/checkers/drug_checker.py` | Drug interaction logic |
| `src/protocols/checkers/drug_class_matcher.py` | Drug-to-class mapping and counting |
| `src/protocols/checkers/duplicate_therapy_checker.py` | Duplicate therapy logic |
| `src/protocols/registry.py` | Checker orchestration |
| `src/engine.py` | Integration with verification flow |
| `tests/protocols/checkers/test_protocols_pbt.py` | Property-based tests |
| `tests/protocols/checkers/test_drug_checker.py` | Example tests (drug interactions) |
| `tests/protocols/checkers/test_duplicate_therapy.py` | Example tests (duplicate therapy) |
| `tests/test_compliance.py` | End-to-end engine test |
| `tests/test_telemetry.py` | OTEL trace verification |
