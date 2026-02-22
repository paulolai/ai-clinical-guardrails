# ADR 011: Subset FHIR Model Generation

**Status:** Accepted
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)
**Supersedes:** ADR 010 (Modular FHIR Models)

## The Problem
The full HL7 FHIR R4 JSON Schema produces a 50,000-line Python file when generated monolithically. This causes a **16-20 second import bottleneck**.

Attempts to split this file (ADR 010) failed because circular dependencies forced `datamodel-codegen` to create a massive `_internal.py` file (1.2MB), which still took **29 seconds** to load.

Attempts to use `fhir.resources` (standard library) failed because:
1.  Version 8.x supports Pydantic v2 but only supports **FHIR R5**.
2.  Version 6.x supports **FHIR R4** but relies on **Pydantic v1** (incompatible with our project).

## The Decision
We will generate a **Targeted Subset** of the FHIR R4 models using a custom extraction script.

1.  **Script:** `scripts/generate_fhir_models.py` reads the full R4 schema.
2.  **Subset:** It recursively resolves dependencies for a whitelist of resources (`Patient`, `Encounter`, etc.).
3.  **Patch:** It patches `ResourceList` (which usually pulls in all 140+ resources) to only reference our target subset, breaking the "world-graph" recursion.
4.  **Generation:** `datamodel-codegen` runs on this subset schema, producing a ~5,000 line file (vs 50,000).

## Why?
*   **Performance (20s -> 1s):** Import time is now ~1 second, which is acceptable for CLI usage.
*   **Correctness:** We use **FHIR R4** and **Pydantic v2**, meeting all architectural constraints.
*   **Zero-Trust:** We still generate models from the official schema, rather than handwriting them.
*   **Minimalism:** We only carry code for the 8-10 resources we actually use, reducing attack surface and noise.

## Implementation Details
*   **Schema Source:** `specs/fhir.r4.schema.json`
*   **Output:** `src/integrations/fhir/generated.py`
*   **Primitives:** Uses `RootModel[str]` for FHIR primitives (Id, Code), preserving the spec's structure.

## Alternatives Rejected
*   **fhir.resources:** Incompatible version matrix (R4 + Pydantic v2).
*   **Modular Generation:** Failed due to Python's circular import resolution overhead.
