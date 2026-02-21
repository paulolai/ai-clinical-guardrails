# Clinical Guardrails: Canonical Implementation Guide

This document defines the 8-step engineering lifecycle used to build the Clinical Guardrails platform. Following this sequence ensures contract-first integrity and high-assurance clinical safety.

---

## 🏗 The 8-Step Lifecycle

### Step 1: Business Requirements
**Goal:** Define the "why" and "what" before the "how".
- **Action:** Document the business problem being solved, success criteria, and expected behavior.
- **Key Questions:**
  - What clinical or operational problem does this solve?
  - What are the success metrics?
  - What are the regulatory/compliance constraints?
  - Who are the stakeholders and what do they need?
- **Output:** A clear requirements document approved by stakeholders before technical work begins.

### Step 2: Requirements & Source Spec
**Goal:** Identify the upstream source of truth.
- **Action:** Download the full official **HL7 FHIR R4 JSON Schema**.
- **Command:** `curl -L -o specs/fhir.r4.schema.json https://www.hl7.org/fhir/R4/fhir.schema.json`

### Step 3: Generated Model Layer
**Goal:** Create a 1:1 Python representation of the industry standard.
- **Tool:** `datamodel-code-generator`
- **Command:**
  ```bash
  uv run datamodel-codegen \
      --input specs/fhir.r4.schema.json \
      --input-file-type jsonschema \
      --output src/integrations/fhir/generated.py \
      --output-model-type pydantic_v2.BaseModel \
      --target-python-version 3.12 \
      --field-constraints \
      --disable-timestamp \
      --use-schema-description
  ```

### Step 4: Domain Wrapper Layer
**Goal:** Decouple the engine from FHIR's complexity.
- **Responsibility:** `src/integrations/fhir/client.py`
- **Pattern:** The `FHIRClient` must consume `generated.py` models and return clean domain objects (`PatientProfile`, `EMRContext`).
- **Key Insight:** FHIR primitives (Date, String, Id) are generated as Pydantic `RootModel` types. Always access via `.root` or `str()`.

### Step 5: Interface-Specific CLI Tooling
**Goal:** Enable developer debugging of the integration layer.
- **Responsibility:** `cli/fhir.py` (Handles EMR) and `cli/api.py` (Handles Guardrails Service).
- **Standard:** Tools must be named after the interface they serve.

### Step 6: Component Testing (Integration Proof)
**Goal:** Prove the integration layer works against real-world data.
- **Responsibility:** `tests/component/test_fhir_client.py`
- **Standard:** Use `pytest-asyncio` to verify fetching from the HAPI FHIR Sandbox (URL: `http://hapi.fhir.org/baseR4`).

### Step 7: Pure-Functional Business Logic
**Goal:** Implement safety guardrails with mathematical rigor.
- **Responsibility:** `src/engine.py` (`ComplianceEngine`)
- **Pattern:** Use the **Result Pattern** (`Result[T, E]`). Never throw exceptions for compliance violations.
- **Invariants:**
    1. **Date Integrity:** AI dates must exist in the EMR window.
    2. **Protocol Adherence:** Clinical triggers (Sepsis) require specific documentation.
    3. **Administrative Safety:** Scan for PII (Medicare Number patterns).

### Step 8: System Verification (PBT)
**Goal:** Prove the logic holds for all valid inputs.
- **Responsibility:** `tests/test_compliance.py`
- **Tool:** `Hypothesis`
- **Action:** Generate randomized `PatientProfile` and `EMRContext` objects to stress-test the engine.

---

## Testing Documentation

For detailed testing guidance:
- **[Testing Quick Start](../tests/README.md)** - Running tests
- **[Testing Philosophy](../tests/AGENTS.md)** - Testing Trophy model
- **[Testing Workflows](TESTING_WORKFLOWS.md)** - Command reference
- **[Integration Testing](INTEGRATION_TESTING.md)** - Component tests
- **[Debugging Guide](DEBUGGING_GUIDE.md)** - Troubleshooting
