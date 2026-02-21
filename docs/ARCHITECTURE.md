# System Architecture

## High-Level Flow

```
AI Service → Guardrails API → Compliance Engine → Audit Store
                ↓
            FHIR/EMR
```

## Component Breakdown

### 1. Guardrails API (FastAPI)
- Entry point for verification requests
- Handles authentication/authorization
- Returns structured Result[T, E]

### 2. Compliance Engine
- Pure functions, no side effects
- Rule evaluation pipeline
- Returns: APPROVED, REJECTED, or WARNING

### 3. FHIR Integration
- Wraps external EMR systems
- Maps FHIR → Domain models
- Returns Result[PatientProfile, FHIRError]

### 4. Audit Store
- Immutable compliance logs
- Required for regulatory audits
- SHA-256 evidence hashing

## Data Flow

1. Request arrives with patient_id and ai_text
2. Fetch EMR context from FHIR
3. Run compliance rules against context
4. Record decision to audit trail
5. Return result with audit_id

## Decision Matrix

| Scenario | Decision | Action |
|----------|----------|--------|
| No violations | APPROVED | Proceed to file |
| Minor issues | WARNING | Flag for review |
| Critical violations | REJECTED | Block and alert |
