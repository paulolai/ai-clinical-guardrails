# ADR 010: Modular FHIR Model Generation

**Status:** Proposed
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)

## The Problem
The current FHIR integration uses a single, monolithic `generated.py` file containing the full HL7 FHIR R4 specification (~50,000 lines, 3MB).

Even with lazy loading in `FHIRClient`, any import of this module (e.g., `from .generated import Patient`) causes Python to parse and execute the entire file. This results in a **16-20 second bottleneck** during the first interaction with the EMR layer, severely impacting CLI responsiveness and test suite execution time.

## The Decision
We will transition from a single-file model to a **Modular Package** generation strategy.

1.  **Regenerate Models:** Use `datamodel-codegen` to output a package (directory) instead of a single file.
2.  **Granular Imports:** Refactor `FHIRClient` to import specific resource models from their respective modules (e.g., `from .models.patient import Patient`).
3.  **Maintain Full Spec:** We continue to generate the *entire* FHIR R4 spec to ensure contract-first integrity, but we leverage Python's filesystem-based module system to only load what is used.

## Why?
*   **Performance (20s -> 20ms):** Python only parses the specific files required for the requested resource (e.g., `patient.py` and its direct dependencies like `human_name.py`), rather than the entire 50,000-line universe.
*   **Zero-Trust Integrity:** We maintain the "Full Official Spec" requirement. We are not "cherry-picking" or manually writing models, which would introduce "Contract Drift" risk.
*   **Developer Experience:** CLI tools (`cli/emr.py`) become "instant-on," which is critical for clinical workflows where sub-second latency is expected.
*   **Test Suite Efficiency:** Component tests can run in parallel without each process incurring a 20s startup tax.

## Alternatives Rejected

### 1. Manual Subset Models
**Rejected:** Hand-writing a `Patient` model would be fast but violates our **Contract-First** principle. It introduces the risk that our internal model deviates from the official HL7 standard, leading to silent failures in production EMR integrations.

### 2. Standard Lazy-Import Wrappers
**Rejected:** Tools like `lazy_import` still eventually trigger the full parse of the monolithic file upon the first attribute access. The bottleneck is the physical size of the single `.py` file.

### 3. External Libraries (e.g., fhir.resources)
**Rejected:** While comprehensive, external libraries often have their own large dependency trees and may not align with our specific Pydantic v2 / Python 3.12 performance targets. Generating our own modular code gives us full control over the Pydantic configuration (e.g., `extra='forbid'`).

## Implementation Plan
1. Update `docs/WORKFLOW_SPEC.md` with the new modular command.
2. Run the generator to create `src/integrations/fhir/models/`.
3. Update `src/integrations/fhir/client.py` to use granular imports.
4. Remove the obsolete `src/integrations/fhir/generated.py`.
5. Verify performance via `tests/component/test_fhir_client.py`.
