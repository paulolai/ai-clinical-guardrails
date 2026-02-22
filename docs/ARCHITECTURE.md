# System Architecture

## High-Level Flow

```
AI Service → Guardrails API → Compliance Engine → Audit Store
                ↓
            Protocol Checks (Drug Interactions, Allergies)
                ↓
            FHIR/EMR
```

## Component Breakdown

### 1. Guardrails API (FastAPI)
- Entry point for verification requests
- Handles authentication/authorization
- Returns structured Result[T, E]
- Endpoints: `/verify`, `/verify/fhir/{id}`, `/extract`

### 2. Compliance Engine
- **Core Invariants:** Date Integrity, Sepsis Protocol, PII Detection
- **Medical Protocols:** Drug Interactions, Allergy Conflicts, Required Fields ✅ NEW
- Pure functions, no side effects
- Rule evaluation pipeline
- Returns: APPROVED, REJECTED, or WARNING

### 3. Medical Protocols ✅ NEW
Configurable clinical safety rules via YAML:
- **ProtocolRegistry:** Orchestrates all protocol checkers
- **DrugInteractionChecker:** Warfarin + NSAID detection
- **AllergyChecker:** Penicillin allergy + Amoxicillin conflicts
- **RequiredFieldsChecker:** Discharge summary validation
- **Pattern Matchers:** Medication, Allergy, Field presence matching

### 4. FHIR Integration
- Wraps external EMR systems
- Maps FHIR → Domain models
- Returns Result[PatientProfile, FHIRError]
- HAPI FHIR sandbox support

### 5. Audit Store
- Immutable compliance logs
- Required for regulatory audits
- SHA-256 evidence hashing

### 6. CLI Tools
- `cli/emr.py`: Patient inspection
- `cli/api.py`: Verification testing
- `cli/protocols.py`: ✅ NEW - Protocol config validation and testing

## Data Flow

1. Request arrives with patient_id and ai_text
2. Extract structured data (medications, allergies, dates)
3. Fetch EMR context from FHIR
4. **Run protocol checks** (drug interactions, allergies, required fields) ✅ NEW
5. Run core compliance rules (date integrity, sepsis, PII)
6. Record decision to audit trail
7. Return result with audit_id and alerts

## Decision Matrix

| Scenario | Decision | Action |
|----------|----------|--------|
| No violations | APPROVED | Proceed to file |
| Minor issues | WARNING | Flag for review |
| Critical violations | REJECTED | Block and alert |
| **Drug interaction** | REJECTED | Block and alert clinician ✅ NEW |
| **Allergy conflict** | REJECTED | Block and alert clinician ✅ NEW |

## Medical Protocols Architecture ✅ NEW

```
VerificationRequest
    ↓
ProtocolRegistry.check_all(patient, extraction)
    ↓
├─ DrugInteractionChecker
│   └─ Detects: Warfarin + NSAID, duplicate therapies
│   └─ Severity: CRITICAL
│
├─ AllergyChecker
│   └─ Detects: Patient allergies + conflicting medications
│   └─ Severity: CRITICAL
│
└─ RequiredFieldsChecker
    └─ Validates: Discharge summaries, encounter requirements
    └─ Severity: HIGH
    ↓
Aggregated Alerts → ComplianceEngine
```

### Protocol Configuration
- **Format:** YAML (`config/medical_protocols.yaml`)
- **Structure:** Version, Settings, Checkers (enabled/disabled), Rules
- **Rule Definition:** Name, Pattern, Severity, Message
- **Hot Reload:** Disabled in production (configurable)

### Pattern Matching Engine
- **MedicationPatternMatcher:** Case-insensitive medication name matching
- **AllergyPatternMatcher:** Patient allergy cross-reference
- **FieldPresenceMatcher:** Required field validation

## File Structure

```
src/
├── engine.py                    # ComplianceEngine with protocol support
├── protocols/                   # ✅ NEW: Medical protocols system
│   ├── __init__.py
│   ├── config.py               # YAML config loader
│   ├── models.py               # ProtocolRule, ProtocolConfig
│   ├── matcher.py              # Pattern matchers
│   ├── registry.py             # ProtocolRegistry
│   └── checkers/
│       ├── base.py             # ProtocolChecker ABC
│       ├── drug_checker.py     # Drug interactions
│       ├── allergy_checker.py  # Allergy conflicts
│       └── documentation_checker.py  # Required fields
├── extraction/                  # LLM-based extraction
├── integrations/fhir/          # FHIR client
└── api.py                      # FastAPI endpoints

config/
└── medical_protocols.yaml      # ✅ NEW: Protocol rules

cli/
├── emr.py                      # Patient inspection
├── api.py                      # Verification testing
└── protocols.py                # ✅ NEW: Protocol CLI

tests/protocols/                 # ✅ NEW: 46 protocol tests
```

## Integration Points

### ComplianceEngine Integration
```python
# Optional protocol config
result = ComplianceEngine.verify(
    patient,
    context,
    ai_output,
    protocol_config=config  # NEW: Optional protocols
)
```

### CLI Usage
```bash
# Validate protocol config
uv run python cli/protocols.py validate-config

# Test specific interaction
uv run python cli/protocols.py check --medications "warfarin,ibuprofen"

# Test allergy conflict
uv run python cli/protocols.py check --allergies "penicillin" --medications "amoxicillin"
```

## Test Coverage

- **Unit Tests:** 46 protocol-specific tests
- **Property-Based Tests:** 2 PBT tests (100 examples each)
- **Integration Tests:** End-to-end with FHIR
- **Total:** 114/114 tests passing (100%)

## Performance

- **Protocol Check Overhead:** <10ms per verification
- **Pattern Compilation:** Once at startup (cached)
- **Memory:** <10MB for full rule set

---

*Last updated: 2026-02-22*
*Medical Protocols layer added*
