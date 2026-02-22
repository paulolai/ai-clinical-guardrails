# Medical Protocols Compliance Layer

**For:** Clinical Safety & Australian Healthcare Compliance
**Purpose:** Configurable drug interaction, allergy, and documentation rule validation
**Date:** 2026-02-22
**See:** `2026-02-22-medical-protocols-design_THINKING.md` for decision process and trade-offs

---

## Executive Summary

**The Problem:**
The existing verification engine catches date mismatches, PII leaks, and sepsis protocol violations. But it doesn't check for:
- Drug interactions (Warfarin + NSAID combinations)
- Patient allergy conflicts (Penicillin-allergic patient prescribed Amoxicillin)
- Australian PBS/MBS compliance
- Required documentation fields for specific encounter types

**The Solution:**
A configurable protocol checker that loads safety rules from YAML/JSON configuration. Medical staff can add new rules without code changes. Rules use pattern-based matching on extracted structured data.

**Business Value:**
- **Patient Safety:** Prevent medication errors that cause 250,000+ adverse events annually
- **Compliance:** Meet Australian healthcare standards (PBS, MBS, My Health Record)
- **Efficiency:** Automate checks that clinicians currently do manually
- **Auditability:** All rules are visible in config files, not buried in code

---

## Business Context

### Why This Feature

Healthcare documentation has two types of errors:
1. **Technical Errors** (caught by existing engine): Wrong dates, PII leaks
2. **Clinical Errors** (NEW - this feature): Drug interactions, allergy misses, incomplete documentation

**Clinical errors are more dangerous** because:
- They directly harm patients
- They're harder to spot (look "correct" technically)
- They require medical knowledge to validate

**Australian Context:**
- PBS (Pharmaceutical Benefits Scheme) requires specific authority codes
- MBS (Medicare Benefits Schedule) item numbers must match services rendered
- My Health Record requires allergy documentation
- AHPRA mandates certain documentation standards

### Success Metrics

- **Catch Rate:** 100% of configured critical interactions flagged
- **False Positives:** <5% to avoid alert fatigue
- **Time to Add Rule:** <5 minutes (edit config, reload)
- **Performance Impact:** <10ms per verification

---

## Architecture

### High-Level Flow

```
Voice Transcription
    ↓
LLM Extraction (existing)
    ↓
StructuredExtraction + PatientProfile
    ↓
ProtocolRegistry.check_all()
    ├─ DrugInteractionChecker
    ├─ AllergyChecker
    ├─ PBSChecker
    ├─ MBSChecker
    └─ RequiredFieldsChecker
    ↓
ComplianceAlerts (aggregated)
    ↓
VerificationResult
```

### Component Design

#### 1. ProtocolConfig (`src/protocols/config.py`)

**Responsibility:** Load and validate rule configuration from YAML

**Interface:**
```python
class ProtocolConfig:
    @classmethod
    def load(cls, path: str) -> "ProtocolConfig": ...

    def get_rules(self, checker_type: str) -> list[ProtocolRule]: ...

    def is_enabled(self, checker_type: str) -> bool: ...
```

**Pattern:** Functional Core - Pure functions for loading/validation

---

#### 2. ProtocolRegistry (`src/protocols/registry.py`)

**Responsibility:** Orchestrate all protocol checkers

**Interface:**
```python
class ProtocolRegistry:
    def __init__(self, config: ProtocolConfig) -> None: ...

    def check_all(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction
    ) -> list[ComplianceAlert]: ...
```

**Pattern:** Imperative Shell - Calls pure checker functions

---

#### 3. PatternMatcher (`src/protocols/matcher.py`)

**Responsibility:** Match extraction data against rule patterns

**Pattern Types:**
- `MedicationMatcher`: Check medication names/classes
- `AllergyMatcher`: Cross-reference patient allergies
- `FieldPresenceMatcher`: Verify required fields exist
- `DrugClassMatcher`: Match by therapeutic class (ACE inhibitors, NSAIDs)

**Interface:**
```python
class PatternMatcher(ABC):
    @abstractmethod
    def match(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict
    ) -> bool: ...
```

---

#### 4. Specific Checkers

**DrugInteractionChecker** (`src/protocols/checkers/drug_checker.py`)

Checks for:
- Warfarin + NSAIDs (bleeding risk)
- ACE inhibitors + ARBs (duplicate therapy)
- Multiple drugs in same class

**Rule Pattern:**
```yaml
- name: "Warfarin NSAID Interaction"
  pattern:
    trigger_medications: ["warfarin", "coumadin"]
    conflict_medications: ["ibuprofen", "naproxen", "aspirin"]
  severity: CRITICAL
  message: "Warfarin + NSAID increases bleeding risk. Consider alternative."
```

---

**AllergyChecker** (`src/protocols/checkers/allergy_checker.py`)

Checks for:
- Penicillin allergy + Penicillin-class antibiotics
- Sulfa allergy + Sulfa drugs
- Patient-specific allergies

**Rule Pattern:**
```yaml
- name: "Penicillin Cross-Reactivity"
  pattern:
    patient_allergies: ["penicillin", "penicillins"]
    conflict_medications: ["amoxicillin", "ampicillin", "piperacillin"]
  severity: CRITICAL
  message: "Patient allergic to penicillin prescribed penicillin-class antibiotic"
```

---

**PBSChecker** (`src/protocols/checkers/pbs_checker.py`)

Checks for:
- Authority-required medications
- PBS eligibility criteria

**Rule Pattern:**
```yaml
- name: "Authority Required - Sildenafil"
  pattern:
    medications: ["sildenafil", "viagra"]
    requires_authority: true
  severity: WARNING
  message: "Sildenafil requires PBS Authority approval"
```

---

**RequiredFieldsChecker** (`src/protocols/checkers/documentation_checker.py`)

Checks for:
- Discharge summaries require follow-up plans
- Emergency encounters require triage category
- Specialist consults require referral reason

**Rule Pattern:**
```yaml
- name: "Discharge Summary Requirements"
  pattern:
    encounter_type: "discharge"
    required_fields: ["discharge_date", "follow_up_plan", "medications"]
  severity: HIGH
  message: "Discharge summary missing required fields: {missing}"
```

---

## Configuration Schema

```yaml
# config/medical_protocols.yaml
version: "1.0"

# Global settings
settings:
  hot_reload: false  # Enable for development
  cache_compiled_patterns: true

# Protocol checkers
checkers:
  drug_interactions:
    enabled: true
    description: "Critical drug interaction detection"

  allergy_checks:
    enabled: true
    description: "Patient allergy cross-reference"

  pbs_validation:
    enabled: true
    description: "PBS authority and eligibility checks"

  mbs_validation:
    enabled: false  # Not implemented in v1
    description: "MBS item number validation"

  required_fields:
    enabled: true
    description: "Documentation completeness checks"

# Rules organized by checker type
rules:
  drug_interactions:
    - name: "Warfarin NSAID"
      pattern:
        trigger: {medications: ["warfarin", "coumadin"]}
        conflicts: {medications: ["ibuprofen", "naproxen", "diclofenac", "aspirin"]}
      severity: CRITICAL
      message: "Warfarin + NSAID increases bleeding risk"

    - name: "Duplicate ACE Inhibitor"
      pattern:
        drug_class: "ACE_INHIBITOR"
        max_count: 1
      severity: HIGH
      message: "Multiple ACE inhibitors detected"

  allergy_checks:
    - name: "Penicillin Allergy"
      pattern:
        patient_allergies: ["penicillin", "penicillins"]
        conflicts: {medications: ["amoxicillin", "ampicillin", "piperacillin"]}
      severity: CRITICAL
      message: "Patient allergic to penicillin - review prescription"

    - name: "Sulfa Allergy"
      pattern:
        patient_allergies: ["sulfa", "sulfonamides"]
        conflicts: {medications: ["furosemide", "sulfamethoxazole"]}
      severity: CRITICAL
      message: "Patient allergic to sulfa drugs - review prescription"

  pbs_validation:
    - name: "Authority Required"
      pattern:
        medications: ["sildenafil", "tadalafil"]
        requires_authority: true
      severity: WARNING
      message: "Medication requires PBS Authority approval"

  required_fields:
    - name: "Discharge Summary"
      pattern:
        encounter_type: "discharge"
        required: ["discharge_date", "follow_up_plan", "medications"]
      severity: HIGH
      message: "Discharge summary incomplete - missing: {missing}"

    - name: "Emergency Encounter"
      pattern:
        encounter_type: "emergency"
        required: ["triage_category", "discharge_disposition"]
      severity: HIGH
      message: "Emergency documentation incomplete"
```

---

## Integration Points

### 1. Extend ComplianceEngine

Modify `src/engine.py` to call ProtocolRegistry:

```python
class ComplianceEngine:
    def __init__(self, protocol_config_path: str | None = None):
        self.protocol_registry = None
        if protocol_config_path:
            config = ProtocolConfig.load(protocol_config_path)
            self.protocol_registry = ProtocolRegistry(config)

    def verify(
        self,
        patient: PatientProfile,
        context: EMRContext,
        ai_output: AIGeneratedOutput
    ) -> Result[VerificationResult, list[ComplianceAlert]]:
        # Existing 3 invariants
        alerts = []
        self._verify_date_integrity(context, ai_output, alerts)
        self._verify_clinical_protocols(ai_output, alerts)
        self._verify_data_safety(ai_output, alerts)

        # NEW: Medical protocol checks
        if self.protocol_registry:
            # Convert AIGeneratedOutput to StructuredExtraction
            extraction = self._convert_to_extraction(ai_output)
            protocol_alerts = self.protocol_registry.check_all(patient, extraction)
            alerts.extend(protocol_alerts)

        # ... rest of verification logic
```

### 2. VerificationWorkflow Integration

Update `src/integrations/fhir/workflow.py`:

```python
class VerificationWorkflow:
    def __init__(
        self,
        fhir_client: FHIRClient,
        extraction_service: ExtractionService,
        protocol_config_path: str = "config/medical_protocols.yaml"
    ):
        self.fhir_client = fhir_client
        self.extraction_service = extraction_service
        self.compliance_engine = ComplianceEngine(protocol_config_path)
```

### 3. CLI Tool

Create `cli/protocols.py` for debugging:

```python
# Usage: uv run python cli/protocols.py check --patient-id 123 --transcript "..."
# Usage: uv run python cli/protocols.py validate-config config/medical_protocols.yaml
# Usage: uv run python cli/protocols.py list-rules
```

---

## Testing Strategy

### Unit Tests

Each checker tested in isolation:

```python
# tests/protocols/test_drug_checker.py
def test_warfarin_nsaid_interaction():
    patient = PatientProfile(
        active_medications=[ExtractedMedication(name="warfarin")]
    )
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="ibuprofen")]
    )

    checker = DrugInteractionChecker(config)
    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.CRITICAL
```

### Property-Based Tests

```python
# tests/protocols/test_protocols_pbt.py
@given(patient=patient_strategy(), extraction=extraction_strategy())
def test_allergy_checker_never_misses_conflicts(patient, extraction):
    """Property: If patient has allergy X and extraction contains X-class drug, MUST alert."""
    pass
```

### Configuration Tests

```python
# tests/protocols/test_config.py
def test_config_loads_valid_yaml():
    config = ProtocolConfig.load("config/medical_protocols.yaml")
    assert config.is_enabled("drug_interactions")
```

---

## Error Handling

### Invalid Configuration

- **Schema Validation:** Pydantic models for config structure
- **Graceful Degradation:** Invalid rules logged and skipped, valid rules still work
- **Startup Validation:** Fail fast on config errors (don't start with broken rules)

### Pattern Matching Failures

- **Unknown Medications:** Log warning, skip rule (don't block on data quality issues)
- **Missing Patient Data:** Treat as "no conflict" (false negative safer than false positive)

---

## Performance Considerations

### Caching

- Compile regex patterns once at load time
- Cache drug class lookups
- Patient profile cached across checks

### Target Metrics

- Config load: <100ms (one-time at startup)
- Per-check overhead: <10ms
- Memory overhead: <10MB for full rule set

---

## Deployment

### Environment Configuration

```bash
# .env
MEDICAL_PROTOCOLS_CONFIG=config/medical_protocols.yaml
ENABLE_HOT_RELOAD=false  # Only in dev
```

### Rule Management

- Rules live in git (version controlled)
- Deploy with application (not external dependency)
- Override path via environment variable for testing

---

## Future Extensions

### v2 Possibilities

1. **External Rule Sources:** Load rules from hospital clinical decision support system
2. **Severity Override:** Per-patient rule customization
3. **MBS Integration:** Real-time MBS item validation
4. **Drug Database:** Integration with Australian Medicines Handbook API
5. **Machine Learning:** Learn from false positives to tune thresholds

---

## Acceptance Criteria

- [ ] Configuration file loads and validates at startup
- [ ] Drug interaction checker flags Warfarin + NSAID combinations
- [ ] Allergy checker detects penicillin allergy + amoxicillin prescriptions
- [ ] PBS checker warns on authority-required medications
- [ ] Required fields checker validates discharge summary completeness
- [ ] All checkers have PBT coverage
- [ ] CLI tool can validate config and test rules
- [ ] Rules can be added/changed without code deployment
- [ ] Performance impact <10ms per verification

---

## Files to Create

```
config/
└── medical_protocols.yaml

src/protocols/
├── __init__.py
├── config.py
├── registry.py
├── matcher.py
├── models.py
└── checkers/
    ├── __init__.py
    ├── base.py
    ├── drug_checker.py
    ├── allergy_checker.py
    ├── pbs_checker.py
    └── documentation_checker.py

cli/
└── protocols.py

tests/protocols/
├── __init__.py
├── test_config.py
├── test_registry.py
├── test_matcher.py
├── test_drug_checker.py
├── test_allergy_checker.py
└── test_protocols_pbt.py
```

---

## Implementation Notes

**Completed:** See implementation plan `2026-02-22-medical-protocols-implementation.md`

**Files Created:**
- `src/protocols/` - Complete protocol checking system
- `config/medical_protocols.yaml` - Sample configuration
- `cli/protocols.py` - CLI debugging tool
- `tests/protocols/` - Comprehensive test suite with PBT

**Integration:**
- ComplianceEngine now accepts optional `protocol_config` parameter
- Protocol checks run after existing date/sepsis/PII checks
- Critical protocol violations return Failure Result

**Usage Example:**
```python
from src.protocols.config import load_protocol_config
from src.engine import ComplianceEngine

config = load_protocol_config("config/medical_protocols.yaml")
result = ComplianceEngine.verify(patient, context, ai_output, protocol_config=config)
```

**Test Results:**
- 114 total tests passing
- 46 new protocol tests
- 68 existing tests (no regressions)

---

*See [2026-02-22-medical-protocols-design_THINKING.md](2026-02-22-medical-protocols-design_THINKING.md) for decision process and alternatives considered.*
