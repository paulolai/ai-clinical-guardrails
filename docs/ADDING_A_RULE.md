# Adding a New Compliance Rule

End-to-end walkthrough using the drug interaction checker as a worked example.

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
| `src/protocols/registry.py` | Checker orchestration |
| `src/engine.py` | Integration with verification flow |
| `tests/protocols/checkers/test_protocols_pbt.py` | Property-based tests |
| `tests/protocols/checkers/test_drug_checker.py` | Example tests |
| `tests/test_compliance.py` | End-to-end engine test |
| `tests/test_telemetry.py` | OTEL trace verification |
