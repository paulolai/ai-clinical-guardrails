# ADR 012: Use fhir.resources Package (FHIR R5)

**Status:** Accepted
**Date:** 2026-02-22
**Proposer:** Principal Architect (Gemini CLI)
**Supersedes:** ADR 010 (Modular Generation), ADR 011 (Subset Generation)

## The Problem
Maintaining custom-generated Pydantic models for FHIR is proving complex and slow.
- **Monolithic Generation:** 20s import time.
- **Modular Generation:** Circular dependency hell (`_internal.py` is 1.2MB).
- **Subset Generation:** Requires complex custom scripting and strict manual dependency management.

## The Decision
We will adopt the community-standard **`fhir.resources`** library (version 8.x+), which supports **FHIR R5** and **Pydantic v2**.

1.  **Dependency:** `fhir.resources>=8.0.0`
2.  **FHIR Version:** Upgrade project from R4 to **R5** to match the library's support.
3.  **Endpoint:** Switch HAPI Sandbox to `http://hapi.fhir.org/baseR5`.
4.  **Refactor:** Update `FHIRClient` to use standard library imports.

## Why?
*   **Performance:** Instant imports (<1s) due to optimized package structure.
*   **Maintenance:** Offload model correctness and updates to the library maintainers.
*   **Standardization:** Aligns with the broader Python FHIR ecosystem.
*   **Future-Proofing:** Moving to FHIR R5 ensures compatibility with modern healthcare standards.

## Alternatives Rejected
*   **Sticking with R4:** The only Pydantic v2-compatible version of `fhir.resources` (8.x) requires R5. Downgrading Pydantic to v1 is not an option as our entire codebase uses v2.
    *   *See [FHIR R4 Support Strategy](../technical/FHIR_R4_SUPPORT_STRATEGY.md) for how to revert if strictly required.*
*   **Custom Generation:** Too much maintenance overhead for zero business value.

## Implementation Plan
1.  `uv add fhir.resources>=8.0.0`
2.  Delete `src/integrations/fhir/generated.py` and generation scripts.
3.  Update `FHIRClient` to import from `fhir.resources` and point to R5 sandbox.
4.  Update tests and snapshots.
