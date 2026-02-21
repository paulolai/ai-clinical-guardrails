# Documentation Review & Consolidation Plan

**Status:** Draft
**Date:** February 21, 2026
**Objective:** streamline documentation to match the "Staff-Level" engineering signal.

---

## 1. Current State Assessment

The repository currently contains a mix of **Core Protocol** documents (high signal) and **Legacy Artifacts** (noise). The transition to Python and the "Zero-Trust" philosophy is well-captured in the root files, but sub-directories contain fragmented or duplicate instructions.

### ✅ Core Documents (Keep & Refine)
| File | Purpose | Verdict |
| :--- | :--- | :--- |
| `README.md` | The public face; general mission statement. | **KEEP** |
| `AGENTS.md` | The mandatory engineering protocol. | **KEEP** |
| `docs/PYTHON_STANDARDS.md` | The technical "Law" for Python code. | **KEEP** |
| `docs/WORKFLOW_SPEC.md` | The step-by-step rebuild guide. | **KEEP** |
| `docs/TESTING_FRAMEWORK.md` | The mathematical verification philosophy. | **KEEP** |
| `docs/RESULT_PATTERN.md` | Justification for architectural choices. | **KEEP** |

### ❌ Redundant / Legacy (Consolidate & Delete)
| File | Issue | Action |
| :--- | :--- | :--- |
| `src/AGENTS.md` | Duplicates `PYTHON_STANDARDS.md`. | **DELETE** |
| `tests/AGENTS.md` | Duplicates `TESTING_FRAMEWORK.md`. | **DELETE** |
| `cli/AGENTS.md` | Minor CLI specific notes. | **MERGE** into `PYTHON_STANDARDS.md` |
| `docs/patterns/*` | Fragmented pattern notes. | **MERGE** into `PYTHON_STANDARDS.md` |
| `docs/learnings/*` | Legacy project notes (not relevant to demo). | **DELETE** |
| `docs/guides/*` | Overlaps with `WORKFLOW_SPEC.md`. | **DELETE** |
| `tests/README.md` | Redundant with root README. | **DELETE** |

---

## 2. Consolidation Strategy

We will move from a "dispersed knowledge" model to a **"Single Source of Truth"** model.

1.  **Code Standards:** All coding rules (API patterns, CLI naming, Error handling) go to `docs/PYTHON_STANDARDS.md`.
2.  **Process:** All workflow steps (How to build, How to test) go to `docs/WORKFLOW_SPEC.md`.
3.  **Philosophy:** High-level principles (Zero-Trust) stay in `AGENTS.md`.

## 3. Execution Plan

1.  **Update `docs/PYTHON_STANDARDS.md`:** Incorporate the "Interface-First CLI" naming convention from `cli/AGENTS.md`.
2.  **Cleanup:** Execute the deletion of all files marked ❌ above.
3.  **Verify:** Ensure `README.md` links only to existing, high-value documents.
