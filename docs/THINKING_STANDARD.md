# Thinking Documentation Standard

## Why Two Files?

**Context window management.** The decision is in AGENTS.md, the reasoning is here. Agents following the pattern don't need the full thinking every time.

## The Two-File Pattern

**Every significant decision document has two parts:**

1. **The Output** (`{name}.md`) - The polished, current-state document
2. **The Thinking** (`{name}_THINKING.md`) - The decision process, alternatives, trade-offs, and revisit conditions

## When to Create a _THINKING File

Create a `{filename}_THINKING.md` whenever:
- Multiple approaches were evaluated
- The decision spans more than a single line (use inline comments for code)
- The choice isn't obviously "best" and might be revisited
- Something significant was intentionally left out
- Trade-offs exist that future maintainers should understand

## What to Include in _THINKING

### Goals and Non-Goals
- **Goals:** What we decided to do and why
- **Non-Goals:** What we explicitly rejected and why

### Alternatives Considered
- What else was on the table?
- Why were they rejected (for now)?

### Decision Criteria
- What constraints drove the choice?
- What principles guided the decision?

### Trade-offs
- What did we give up?
- What are we accepting as technical debt?

### Risks and Mitigations
- What could go wrong?
- How are we guarding against it?

### Revisit Conditions
- When should this be re-evaluated?
- What would trigger a different decision?

## Reference Pattern

In the main document:
> See `{name}_THINKING.md` for the decision process and trade-offs.

## Special Cases

### RATIONALE.md
`RATIONALE.md` at the repository root is the **exception** to this pattern. It exists at the repository level to:
- Justify and explain the overall repository purpose
- Provide high-level architectural reasoning
- Serve as the top-level "why" for the entire project

It does not need a _THINKING companion because it IS the thinking document for the repo itself.

### ARCHITECTURE_DECISIONS.md (ADRs)
This file is a **collection of specific technical decisions**. It serves as the detailed "Thinking" for `ARCHITECTURE.md` regarding specific patterns (e.g., "Why Result Pattern?").
- `ARCHITECTURE.md`: Describes the *What* (The system structure)
- `ARCHITECTURE_DECISIONS.md`: Describes the *Why* (The specific choices)

You do not need a separate `ARCHITECTURE_THINKING.md` if `ARCHITECTURE_DECISIONS.md` covers the reasoning adequately.

## Examples

- `docs/BUSINESS_PURPOSE.md` + `docs/BUSINESS_PURPOSE_THINKING.md`
- `ARCHITECTURE.md` + `ARCHITECTURE_DECISIONS.md` (Specialized)
- `RATIONALE.md` (Root level, standalone)
