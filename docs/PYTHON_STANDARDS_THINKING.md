# Python Standards Thinking

## 1. Strict Type Safety (`mypy --strict`)

### Goals
To eliminate entire classes of runtime errors (AttributeError, TypeError) before code is ever executed. In a safety-critical clinical domain, "runtime" is the wrong time to find a type mismatch.

### Alternatives Considered
*   **Gradual Typing (Default mypy):** Allow untyped functions and `Any`.
*   **Runtime Type Checking (Typeguard):** Check types during execution.

### Decision Criteria
*   **Safety:** We must be mathematically confident that data shapes match expectations.
*   **Refactoring:** We need to change code fearlessly; strict typing guarantees that refactoring didn't break interfaces.

### The Decision
We enforce `mypy --strict`. This disables `Any`, requires explicit `Optional`, and forces type hints on *everything*.

### Trade-offs
*   **Initial Friction:** Prototyping is slower. You can't just "pass a dict" and figure it out later.
*   **Library Friction:** some third-party libraries lack types. We accept the cost of writing stubs or explicit `cast` wrapper layers (Wrapper Pattern).

---

## 2. Result Pattern (`Result[T, E]`)

### Goals
To make error handling explicit, type-safe, and unavoidable. "Exceptions" should be reserved for truly exceptional system states (out of memory, code corruption), not business logic failures (validation error, patient not found).

### Alternatives Considered
*   **Exceptions (Standard Python):** `raise ValueError("Invalid DOB")`.
*   **Return None:** `if not found: return None`.
*   **Tuple Return:** `val, err = func()`.
*   **Libraries (dry-python/returns):** Heavy functional programming libraries.

### Decision Criteria
*   **Explicitness:** The function signature must tell the whole story. `-> int` that raises is a lie. `-> Result[int, ValueError]` is the truth.
*   **Forced Handling:** Callers must not be able to accidentally ignore an error.

### The Decision
We use a lightweight, custom `Result[T, E]` type alias over generic `Success`/`Failure` dataclasses.

*   **Why custom?** Libraries like `dry-python/returns` introduce significant API surface area and learning curve. We only need the core pattern.
*   **Why type alias?** Python 3.12 `type Result[T, E] = Success[T] | Failure[E]` provides excellent IDE support and pattern matching (`match result: case Failure(e): ...`).

---

## 3. Property-Based Testing (Hypothesis)

### Goals
To verify *invariants* (truths that always hold) rather than just *scenarios* (examples we thought of). Humans are bad at imagining edge cases; machines are good at it.

### Alternatives Considered
*   **Example-Based TDD (Standard):** Writing `test_add_1_plus_1`.
*   **Fuzzing:** Random input generation without reduction.

### Decision Criteria
*   **Completeness:** We need to cover the "unknown unknowns" of valid input space.
*   **Minimalism:** We want the smallest possible reproduction of a failure (Hypothesis shrinking).

### The Decision
Hypothesis is mandatory for all business logic. Standard unit tests are demoted to "documentation examples."

### Trade-offs
*   **Performance:** PBT tests are slower than unit tests (running 100x per test function).
*   **Cognitive Load:** Thinking in invariants ("Output is always sorted") is harder than thinking in examples ("Input [2,1] becomes [1,2]").

---

## 4. Tooling Choices (Ruff & uv)

### Goals
To minimize the "configuration tax" and maximize developer loop speed.

### Decisions
*   **Ruff over Flake8/Black/Isort:**
    *   *Speed:* Ruff is written in Rust and is orders of magnitude faster.
    *   *Simplicity:* Replaces 5+ tools and config files with one.
    *   *Adoption:* The Python community is consolidating on Ruff.

*   **uv over Pip/Poetry/PDM:**
    *   *Speed:* `uv` dependency resolution is nearly instant.
    *   *Standards:* Adheres to modern Python packaging standards (pyproject.toml) without locking us into a specific build backend workflow like Poetry sometimes does.
    *   *Experience:* A single binary that manages Python versions, virtual environments, and packages.

---

## 5. Pydantic v2

### Goals
To ensure data entering the system adheres to strict schemas at runtime, and to provide ergonomic data access.

### Alternatives Considered
*   **Dataclasses:** Built-in, but no validation.
*   **TypedDict:** Good for static analysis, but no runtime validation.
*   **Attrs:** Powerful, but Pydantic won the ecosystem war (FastAPI integration).

### The Decision
We use Pydantic v2 `BaseModel` for everything.
*   **Performance:** v2 core is written in Rust, minimizing the overhead of runtime validation.
*   **Serialization:** Built-in JSON serialization is critical for API responses.

---

## 6. Generic Syntax (`Generic[T, E]`)

### Context
Python 3.12 introduced cleaner syntax for generics (`class Box[T]: ...`).

### The Decision
We strictly use `type Result[T, E] = ...` for aliases, but standard `class Success(Generic[T])` for the concrete implementations.

### Reasoning
*   **Mypy Compatibility:** While 3.12 syntax is valid runtime Python, static analysis tools (mypy) sometimes lag or have edge cases with the newest syntax in complex nested scenarios.
*   **Clarity:** Explicitly inheriting from `Generic[T]` is the "boring," stable choice that every Python developer recognizes.

### Revisit Condition
We will switch to full PEP 695 syntax (`class Success[T]:`) once `mypy` support is fully mature and we encounter no edge cases in our CI pipeline.
