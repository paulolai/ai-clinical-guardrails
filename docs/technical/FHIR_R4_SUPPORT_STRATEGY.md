# Strategy for FHIR R4 Support

**Context:**
The project currently uses **FHIR R5** via `fhir.resources` (version 8.x) to achieve sub-second import times and Pydantic v2 compatibility. However, **FHIR R4** remains the dominant industry standard (e.g., US Core, Argonaut, Australian Digital Health).

This document outlines the technical strategy for supporting R4 if required by a deployment environment.

---

## The Problem: Compatibility Matrix

| Library Version | FHIR Version | Pydantic Version | Status |
| :--- | :--- | :--- | :--- |
| `fhir.resources` 8.x | **R5** | **v2** | ✅ **Current (Fast)** |
| `fhir.resources` 7.x | R4B | v2 | ⚠️ Mixed Support |
| `fhir.resources` 6.x | **R4** | **v1** | ❌ **Incompatible** |

We cannot simply downgrade `fhir.resources` because our entire codebase relies on Pydantic v2 features (strict mode, `model_validate`, generic `Result` types).

---

## Strategy A: The "Subset Generation" Path (Recommended)

If R4 support is strictly required, we should return to **Custom Model Generation**, but with a strictly enforced **Subset Strategy** to avoid the performance penalties of the full 50,000-line spec.

### 1. The Method
Instead of generating the *entire* R4 spec (which causes 20s import lags), generate only the ~15 resources required for Clinical Guardrails.

### 2. Implementation Steps
1.  **Download R4 Schema:**
    ```bash
    curl -L -o specs/fhir.r4.schema.json https://www.hl7.org/fhir/R4/fhir.schema.json
    ```

2.  **Create Dependency Filter:**
    Write a script to parse the JSON Schema and extract *only* the definitions for:
    -   `Patient`
    -   `Encounter`
    -   `Observation`
    -   `Condition`
    -   `MedicationRequest`
    -   *(Plus their recursive dependencies)*

3.  **Patch the "OneOf" Recursion:**
    **Critical:** You MUST patch the `ResourceList` definition in the schema. By default, it contains a `oneOf` list of ALL 145+ resources. This causes any generated model (even a subset) to pull in the entire universe via circular references.

    *Patch Logic:*
    ```python
    # In generate_subset.py
    definitions["ResourceList"]["oneOf"] = [
        {"$ref": "#/definitions/Patient"},
        {"$ref": "#/definitions/Encounter"},
        # ... only your subset
    ]
    ```

4.  **Generate:**
    Run `datamodel-codegen` on this filtered schema file.
    ```bash
    uv run datamodel-codegen
        --input specs/fhir.r4.subset.json
        --output src/integrations/fhir/r4/generated.py
        --output-model-type pydantic_v2.BaseModel
    ```

### 3. Pros/Cons
*   ✅ **Pros:** Fast imports (<1s), Pydantic v2 native, Exact R4 compliance.
*   ❌ **Cons:** Maintenance burden of the generation script; manual updates needed when adding new resource types.

---

## Strategy B: The "Pydantic V1 Bridge" Path

Use the legacy `fhir.resources` 6.x library (R4) but wrap it in Pydantic v2 adapters.

### 1. Implementation
1.  Install `pydantic-settings` or `pydantic.v1` namespace shims.
2.  Install `fhir.resources==6.5.0`.
3.  Create a translation layer:

```python
# src/integrations/fhir/r4_adapter.py
from fhir.resources.patient import Patient as R4Patient # Pydantic v1 model
from pydantic import BaseModel # Pydantic v2

class PatientProfile(BaseModel):
    # Our internal domain model (v2)
    id: str

    @classmethod
    def from_r4(cls, r4_patient: R4Patient) -> "PatientProfile":
        return cls(
            id=r4_patient.id,
            # ... mapping logic
        )
```

### 2. Pros/Cons
*   ✅ **Pros:** Uses standard library, no custom generation.
*   ❌ **Cons:** Mixing Pydantic v1 and v2 is notoriously buggy; type checkers (MyPy) struggle with the dual namespaces; increased dependency bloat.

---

## Strategy C: Forking fhir.resources

Fork the `fhir.resources` repository and backport the Pydantic v2 generation templates to the R4 definition files.

*   ✅ **Pros:** Helps the community.
*   ❌ **Cons:** Extremely high effort; requires deep knowledge of the library's internal Jinja2 templates.

---

## Recommendation

Use **Strategy A (Subset Generation)** if R4 is mandated.
It aligns with our **Zero-Trust** philosophy (we control the schema) and **Performance** goals (only loading what we use).
