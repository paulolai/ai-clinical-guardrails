# Rationale: The "Staff+" Engineer in the Age of AI
*From Code Author to System Architect*

**Staff+ Engineer:** *A technical leader who operates at the system level—setting technical strategy, defining architecture, and enabling teams—rather than just the task level.*

## The Thesis
This repository demonstrates a critical Staff+ competency: **Scaling engineering output through AI while maintaining the zero-defect quality standards required in regulated environments.**

The bulk of implementation code was AI-generated. My direct contributions were architectural specifications, constraint definitions, and high-level design decisions.
**My value is not the typing. My value is the *Governance*.**

I acted as the **Principal Architect** and **Product Director**, establishing the constraints, interfaces, and quality standards that the AI (my "implementation team") had to follow. This demonstrates the core Staff+ competency: **Scaling yourself by embedding your expertise into the system itself.**

## The Anti-Pattern This Avoids
Most AI-assisted development fails because developers treat AI as an autocomplete that happens to be confident. This leads to:
- Hallucinated dependencies that don't exist
- Tests that pass but don't verify
- Architecture that "works" but can't be reasoned about
- Accumulation of technical debt at unprecedented speed

I treat AI as a junior team member with **infinite stamina but zero judgment and zero growth.** The same constraints that make humans reliable (interfaces, contracts, verification) make AI reliable.

## The "Zero-Trust" Methodology
Reflecting my background in high-assurance environments (Commonwealth Bank, Health Tech), I treat AI-generated code exactly like I treat inputs in a regulated system: **Untrusted until Verified.**

This repository demonstrates how I operationalize this:

### 1. The "Constitution" (`AGENTS.md`)
I directed the creation of `AGENTS.md` to serve as the "immutable laws" of this repository. I did not draft these rules manually; I prompted the AI to codify them based on my specifications and then ratified them through high-level review.
*   **Principle:** "Zero-Trust Engineering" – External data (and AI suggestions) are guilty until proven innocent.
*   **Principle:** "Contract-First" – Logic is derived from specs, not improvised.
*   **Principle:** "No Magic" – Explicit types and `Result` patterns over exceptions.
*   **Why this matters:** A Staff Engineer doesn't need to draft every policy document; they need to set the strategic intent and have the judgment to approve the right standards.

### 2. Architectural Guardrails
I forced the AI to adopt a **Functional Core, Imperative Shell** architecture.
*   **The Problem:** AI models struggle with complex state management and side effects.
*   **The Solution:** I constrained the AI to write pure business logic (easy to verify) wrapped in strict integration layers (easy to inspect).
*   **Evidence:** See `src/integrations/fhir/client.py` for the clean domain wrapper versus the generated models in `src/integrations/fhir/generated.py`.

### 3. Verification over Validation
Standard unit tests are insufficient for AI code because AI (like humans) suffers from confirmation bias—it tests the happy path it just wrote.
*   **My Approach:** I mandated **Property-Based Testing (Hypothesis)**.
*   **The Check:** We don't ask "Does 1+1=2?"; we ask "For *any* valid input, is the invariant preserved?"
*   **Impact:** Hypothesis generates 100+ test cases per run, catching edge cases in clinical date boundaries that manual testing missed.
*   **Evidence:** See `tests/test_compliance.py` for the property-based safety proofs.

### 4. The "Prove Reality First" Testing Mandate
Most teams default to mocks because they're fast. I mandated the opposite:
*   **Component tests against real HAPI FHIR** before any mocking
*   **No mocks in CI** until component tests prove the integration works against the real sandbox
*   **Property-Based Testing** to catch edge cases humans (and AI) never consider

This mirrors my CBA work: you can't trust what you haven't proven against reality. See `docs/INTEGRATION_TESTING.md` and `tests/component/test_fhir_client.py`.

## Engineering Taste: The Missing Variable
AI can generate code, but it lacks **Taste**—the deep, intuitive sense for what constitutes "good" engineering design.

My primary contribution was not the implementation, but the **Taste** to guide it:
*   **Sensibility:** Knowing what "feels right" to work with—ergonomic APIs, clear domain boundaries, and obvious control flow.
*   **Risk Intuition:** Sensing the "hidden risks" in a proposed solution (e.g., race conditions, coupling, operational burden) before a single line of code is committed.
*   **Aesthetic Judgment:** Rejecting "clever" or "complex" code in favor of the "boring" solution that will survive in production for 5 years.

## The "Correction" Loop (A War Story)
Staff engineering isn't about getting it right the first time; it's about spotting the *wrong* path early.

### The LLM vs. Regex Decision: A Correction Loop Example

**The Wrong Path:** Early in the project, AI agents proposed extracting structured medical data (medications, diagnoses, dates) from clinical transcripts using regex patterns. The approach seemed straightforward: write patterns like `r"(\d+)\s*mg\s+(\w+)"` to extract dosages and drug names.

**The Problem:** As an engineer with domain knowledge, I recognized this approach was fundamentally flawed:
- Clinical dictation is messy, conversational, and highly variable
- Regex can't handle context: "Patient was on Lisinopril but we switched to Enalapril" - which is active?
- Abbreviations and spelling variations: "Lisinopril" vs "lisinopril" vs "Prinivil"
- Temporal expressions: "yesterday", "two weeks ago", "next Tuesday" - regex can't resolve these relative to encounter dates
- **Risk:** Missed medications or incorrect dates in a safety-critical system

**The Correction:** I steered the implementation toward an LLM-based extraction layer:
1. Use LLM to parse the unstructured clinical text
2. Extract structured data with confidence scores
3. Layer deterministic validation (the Verification Engine) on top
4. Never trust the extraction alone - always validate against EMR source of truth

**Why This Matters:** The regex approach would have worked for 80% of cases and failed catastrophically for 20%. In healthcare, that's unacceptable. The LLM approach handles the "messy reality" of clinical speech while the deterministic verification layer provides the safety guarantees.

**The Engineering Lesson:** AI agents (like junior engineers) reach for familiar tools (regex) without understanding domain complexity. The Staff+ engineer's job is to recognize when the "simple" solution is actually the risky one, and steer toward the "complex" solution that actually works.

**Evidence:** See `docs/technical/EXTRACTION_LAYER_DESIGN.md` for the full rationale on why LLM-based extraction was chosen over rule-based approaches, and how the confidence scoring + verification layer provides defense in depth.

## Extending Zero-Trust to Clinical Safety
The Medical Protocols layer extends the "Zero-Trust" methodology from technical safety (dates, PII) to clinical safety (drug interactions, allergies):

*   **Invariant 4: Drug Interaction Detection** - "Warfarin + NSAID combinations MUST trigger CRITICAL alert"
*   **Invariant 5: Allergy Conflict Detection** - "Penicillin-allergic patient + Amoxicillin MUST trigger CRITICAL alert"
*   **Invariant 6: Required Field Validation** - "Discharge summaries MUST include follow-up plans"

Each invariant uses Property-Based Testing (Hypothesis) to generate 100+ random combinations, proving the checker *never* misses a configured interaction. The protocol rules are YAML-configurable, allowing clinical staff to add safety rules without code changes.

**The Architectural Decision:** Keep the existing 3 invariants (date, sepsis, PII) in the core `ComplianceEngine`—they're domain-agnostic. Medical protocols are patient-context dependent, so they live in a separate `ProtocolRegistry` that can be enabled/disabled per-deployment. This maintains clean separation while allowing extensibility.

## Socio-Technical Design: The "Agent" as a Team Member
My background in Engineering Management (Team Topologies, Conway's Law) directly informed the architecture of this repository.

I treat AI agents like junior engineers who struggle with context switching. Just as I would structure a team to minimize cognitive load, I structured the code to minimize "context pollution" for the AI:
*   **Bounded Contexts:** I enforced strict modularity (e.g., `src/integrations/` vs `src/engine/`) so the AI never has to "hold the whole system in its head" at once.
*   **Explicit Contracts:** The `AGENTS.md` files act as "Team Charters," defining the exact inputs, outputs, and behaviors expected of each module, preventing the "drift" that occurs in human teams.
*   **Loose Coupling:** By using a functional, message-passing style, I created a system where individual components can be swapped or upgraded without complex refactoring.

## Alignment with Professional Experience
This approach directly mirrors my work at **Commonwealth Bank** and **Google**:
*   **Google:** Leveraging tooling and scale to enforce quality (e.g., Release Velocity).
*   **CBA:** Establishing the "Reference Implementation" for payments. This repo *is* a reference implementation for AI-assisted development.
*   **Health Tech:** "Zero-Trust" date resolution and clinical safety.

## How to Read This Repo
Don't just look at the code syntax. Look at the **meta-structure**:
1.  **Read `AGENTS.md` first:** This is the engineering culture I built.
2.  **Check `docs/learnings/`:** This shows how I systematize knowledge (Continuous Documentation).
3.  **Inspect the Tests:** See `tests/test_compliance.py` for how `Hypothesis` is used to catch "unknown unknowns."

**This is what I bring to a leadership role: The ability to harness powerful but chaotic forces (like AI or large teams) and channel them into reliable, high-quality software through rigorous engineering design.**

---

## 🎩 The Curator’s Note: Engineering as "Black Tie"
In an era where anyone can buy a tuxedo (the code), the true value lies in knowing the **Dress Code** for the occasion.

A tuxedo is a masterpiece of design, but wearing it to a beach barbecue isn’t "good taste"—it’s a lack of situational awareness. Similarly, engineering "Taste" is the ability to understand the **Venue** (in this case, a safety-critical clinical environment) and tailor the technical "Outfit" accordingly.

AI is a "Yes, And" machine. It will happily give you clever decorators, complex inheritance, and experimental libraries if you ask. My role as the Author was to say **"No"** to 90% of those suggestions. I chose a specific composition—**Pydantic + Hypothesis + Result Pattern**—not because they are the trendiest tools, but because they together create a singular, reinforced defense-in-depth strategy suited for the mission.

**I am the author of this repository not because I typed the characters, but because I provided the Judgment. I understood the Venue, I defined the Dress Code, and I had the Taste to ensure the system wasn't just a collection of features, but a cohesive, auditable platform.**

---

## Interview Context: What to Ask Me About
*Conversation starters for Staff+ interviews*

**"How do you prevent AI from introducing subtle bugs?"**
→ My Property-Based Testing strategy and why unit tests fail for generated code

**"How do you maintain code quality at scale?"**
→ Contract-First design and the Wrapper Pattern for isolation

**"What's your approach to AI-assisted development?"**
→ `AGENTS.md` as a cultural artifact - encoding standards so AI (and humans) know the rules

**"How do you handle regulated environments?"**
→ Zero-Trust verification and why deterministic systems beat probabilistic ones in healthcare/finance

---

## 🎙️ The Transcription Interface Decision: Pragmatism Over Hype

An upcoming feature demonstrates how "Taste" applies to technology selection: a Clinical Transcription PWA that lets clinicians dictate notes directly into the system.

### The Temptation: React/Svelte
The "obvious" choice for a modern web interface would be React or Svelte—trendy, marketable, with massive ecosystems. I evaluated all three:

| Framework | Pros | Cons |
|-----------|------|------|
| **React** | Industry standard, hiring pool | Complex, over-engineered for this use case |
| **Svelte** | Modern, compiles away | Small hiring pool, "too cutting edge" for healthtech maintenance |
| **HTMX** | Simple, Python-native, fast | Less "impressive" on resume |

### The Decision: HTMX

**Why:** This is a production system for a 5-clinician practice that I'll be maintaining solo. The technology choice must optimize for:

1. **Maintainability at 2am** - When production breaks, I don't want to debug React hooks or Svelte reactivity
2. **Hiring continuity** - If I get hit by a bus, another Python developer can pick up HTMX faster than modern JS frameworks
3. **Compliance simplicity** - Server-rendered HTML is easier to audit than client-side JS bundles
4. **Existing expertise** - We already have FastAPI + Jinja2; HTMX is a natural extension

**The Trade-off:** I sacrifice "resume impressiveness" for "system reliability." This is the Staff+ decision: choosing the boring technology that will survive over the shiny technology that looks good.

### The On-Premise Decision

**The constraint:** Real patient data, Australian compliance, friend's medical practice.

**The solution:** Everything runs on a Mac Studio 128GB RAM:
- Local Whisper (transcription)
- Local Llama 3.1 70B (extraction + verification)
- Local Keycloak (auth)
- Local PostgreSQL (data)

**Why not cloud:**
- Zero data leaves the building (compliance win)
- No ongoing API costs
- Works during internet outages
- No third-party dependencies to trust

**The cost:** ~$8,000 one-time vs. potentially thousands per month in API calls for 5 clinicians.

### The Engineering Lesson

Staff+ engineering isn't about picking the most impressive technology. It's about picking the technology that:
1. Fits the team (solo maintainer)
2. Fits the constraints (compliance, uptime)
3. Fits the timeline (6 months to production)
4. Survives the "hit by a bus" scenario

**See:** [Clinical Transcription PWA Design](docs/plans/2025-02-23-clinical-transcription-pwa-design.md) for full architecture
