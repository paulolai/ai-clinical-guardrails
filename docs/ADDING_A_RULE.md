# Adding a New Compliance Rule

How a clinical safety rule goes from problem to production-tested code.

## What This Demonstrates

This repo uses a consistent pipeline for adding safety rules. Two things are enforced:

1. **Invariants are defined before code is written.** The test proves the rule works for randomized inputs, not just the examples you thought of.
2. **Rules are config-driven.** Clinical staff can add or modify rules in YAML without touching Python.

The pipeline is the same regardless of rule complexity. Two worked examples show what changes when the matching logic gets harder.

---

## Worked Example 1: Drug Interaction Detection

### Problem

AI-generated clinical notes might prescribe Warfarin (blood thinner) and Ibuprofen (NSAID) together. The existing engine catches date mismatches and PII leaks, but not drug interactions. This is a patient safety gap.

### Invariant

> If extraction contains both a trigger medication (Warfarin) AND a conflict medication (Ibuprofen), a CRITICAL alert must be raised.

### Implementation

**Config** — `config/medical_protocols.yaml`:

```yaml
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

**Checker** — `src/protocols/checkers/drug_checker.py` (37 lines):

```python
class DrugInteractionChecker(ProtocolChecker):
    def check(self, patient, extraction) -> list[ComplianceAlert]:
        # Combine patient meds with extracted meds
        # For each rule: check if trigger AND conflict are both present
        # If both present → alert
```

**Registry** — `src/protocols/registry.py` adds to `checker_map`:

```python
checker_map = {
    "drug_interactions": DrugInteractionChecker,
    ...
}
```

### Testing

**Property-based** — `tests/protocols/checkers/test_protocols_pbt.py`:

```python
@given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
def test_both_sides_present_implies_alert(self, config, meds):
    # When trigger AND conflict are both extracted, checker must alert

@given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
def test_only_one_side_present_implies_no_alert(self, config, meds):
    # When only one side is present, checker must not alert
```

Hypothesis generates 200 random medication combinations per run. The strategies draw from actual drug names and vary the count, order, and mix.

**Example tests** — `tests/protocols/checkers/test_drug_checker.py`:

```python
def test_detects_warfarin_nsaid_interaction():
    # Warfarin + Ibuprofen → CRITICAL alert

def test_no_alert_when_only_trigger_present():
    # Only Warfarin → no alert
```

**Engine integration** — `tests/test_compliance.py`:

```python
engine = ComplianceEngine(protocol_config=config)
result = engine.verify(patient, context, ai_output)
assert not result.is_success  # Warfarin + Ibuprofen detected
```

### Observability

The engine automatically captures OTEL spans. No per-checker instrumentation needed:

```
compliance.verify
  ├── patient_id: "P-TEST"
  ├── compliance.outcome: "failure"
  ├── compliance.alert_count: 1
  └── compliance.verify.protocols
```

Verified in `tests/test_telemetry.py` with `InMemorySpanExporter`.

---

## Worked Example 2: Duplicate Therapy Detection

This example shows what changes when the matching logic isn't about specific drug names — it's about therapeutic classes.

### Problem

A patient is on both Lisinopril and Enalapril. Both are ACE inhibitors. Taking two drugs from the same class increases side effects without additional benefit. The drug interaction checker can't catch this because it matches individual names, not drug classes.

### Invariant

> If extraction contains more than N medications in the same drug class, an alert must be raised.

### What's Different

Drug interactions use name-based matching: "is drug A in this list?" Duplicate therapy requires a new concept — grouping drugs into therapeutic categories, then counting within each group. This meant adding a new matcher type.

### Implementation

**Drug class map** — `src/protocols/checkers/drug_class_matcher.py`:

```python
DRUG_CLASS_MAP = {
    "lisinopril": "ACE_INHIBITOR",
    "enalapril": "ACE_INHIBITOR",
    "ramipril": "ACE_INHIBITOR",
    "atorvastatin": "STATIN",
    "rosuvastatin": "STATIN",
    # ~25 drugs mapped to 6 classes
}

class DrugClassMatcher(PatternMatcher):
    def count_by_class(self, extraction, drug_class: str) -> int:
        count = 0
        for med in extraction.medications:
            if DRUG_CLASS_MAP.get(med.name.lower()) == drug_class:
                count += 1
        return count
```

The matcher is its own module because it's reusable — any class-based rule (duplicate ACE inhibitors, duplicate statins, duplicate PPIs) uses the same mapping.

**Checker** — `src/protocols/checkers/duplicate_therapy_checker.py`:

```python
class DuplicateTherapyChecker(ProtocolChecker):
    def check(self, patient, extraction) -> list[ComplianceAlert]:
        matcher = DrugClassMatcher()
        for rule in self.config.rules["duplicate_therapy"]:
            actual_count = matcher.count_by_class(extraction, rule.pattern["drug_class"])
            if actual_count > rule.pattern["max_count"]:
                alerts.append(self._create_alert(rule, patient, extraction))
```

**Config** — two rules, same pattern format:

```yaml
duplicate_therapy:
  - name: "Duplicate ACE Inhibitor"
    pattern:
      drug_class: "ACE_INHIBITOR"
      max_count: 1
    severity: "HIGH"
    message: "Multiple ACE inhibitors detected — consider consolidating"

  - name: "Duplicate Statin"
    pattern:
      drug_class: "STATIN"
      max_count: 1
    severity: "HIGH"
    message: "Multiple statins detected"
```

### Testing

Same pattern as drug interactions. PBT proves the counting invariant; example tests document specific scenarios.

```python
# PBT: count_by_class accuracy
@given(extraction=medication_class_strategy(), drug_class=st.sampled_from(CLASSES))
def test_count_accurate(self, extraction, drug_class):
    matcher = DrugClassMatcher()
    assert matcher.count_by_class(extraction, drug_class) == expected_count

# Example: specific scenario
def test_duplicate_ace_inhibitors():
    extraction = StructuredExtraction(medications=[
        ExtractedMedication(name="lisinopril"),
        ExtractedMedication(name="enalapril"),
    ])
    checker = DuplicateTherapyChecker(config)
    alerts = checker.check(patient, extraction)
    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.HIGH
```

---

## Adding a New Checker Type

1. Create `src/protocols/checkers/new_checker.py` extending `ProtocolChecker`
2. Implement `check(patient, extraction) -> list[ComplianceAlert]`
3. Register in `src/protocols/registry.py` `checker_map`
4. Add config section in `config/medical_protocols.yaml`
5. Write PBT tests proving the invariants
6. Write example tests for documentation

## Files

| File | Role |
|------|------|
| `config/medical_protocols.yaml` | Rule definitions |
| `src/protocols/models.py` | ProtocolConfig, ProtocolRule |
| `src/protocols/config.py` | YAML loader |
| `src/protocols/checkers/base.py` | Abstract base class |
| `src/protocols/checkers/drug_checker.py` | Drug interaction matching |
| `src/protocols/checkers/drug_class_matcher.py` | Drug-to-class mapping |
| `src/protocols/checkers/duplicate_therapy_checker.py` | Duplicate therapy logic |
| `src/protocols/registry.py` | Checker orchestration |
| `src/engine.py` | Verification flow |
| `tests/protocols/checkers/test_protocols_pbt.py` | Property-based tests |
| `tests/protocols/checkers/test_drug_checker.py` | Drug interaction tests |
| `tests/protocols/checkers/test_duplicate_therapy.py` | Duplicate therapy tests |
| `tests/test_compliance.py` | Engine integration test |
| `tests/test_telemetry.py` | OTEL trace verification |
