# Rationale: BUSINESS_PURPOSE.md Design Decisions

## Overview

This document explains the thinking behind the business purpose documentation for the AI Clinical Guardrails repository. It captures the design decisions, trade-offs, and strategic intent that shaped the final document.

## The Challenge

The repository had strong technical documentation (`RATIONALE.md`, `AGENTS.md`) but lacked clear answers to:
- **What business problem does this solve?**
- **Who is the target audience?**
- **What is the specific use case?**

Without these, the repository risked appearing as "technology seeking a problem" rather than "solution to a real problem."

## Design Philosophy

### Approach C: The Hybrid Technical-Business Narrative

We chose **Approach C** (hybrid narrative) over:
- **Approach A** (formal business case with market sizing) - Too corporate, dilutes technical credibility
- **Approach B** (formal PRD with user stories) - Too product-management focused, doesn't showcase engineering depth

**Why Approach C wins:**
- Serves **dual audiences** without compromise
- Integrates naturally with existing `RATIONALE.md` technical narrative
- Demonstrates **Staff+ thinking**: connecting technical decisions to business outcomes
- Authentic to the portfolio purpose (technical showcase + hiring piece)

## Target Audience Strategy

### Primary Audience 1: Technical Hiring Managers

**What they need to see:**
- Can this candidate think beyond code?
- Do they understand business context?
- Can they articulate technical value?

**How we serve them:**
- "The Dual Promise" section speaks their language
- Technical decisions explicitly mapped to business outcomes
- "Staff+ Thesis" reinforces leadership positioning

### Primary Audience 2: Healthcare CIOs/CTOs

**What they need to see:**
- Is this solving a real problem I have?
- Can I trust this technical approach?
- What's the ROI?

**How we serve them:**
- Opens with business problem (clinician burnout)
- Concrete use case with workflow examples
- Success metrics tied to operational outcomes

**Secondary consideration:** This audience may never read the code, but seeing business fluency increases confidence in the technical solution.

## Use Case Selection: Why Voice Transcription?

### Alternatives Considered:

1. **NDIS/Aged Care market** (beachhead strategy)
   - *Pros:* Under-served market, real experience, less competition
   - *Cons:* Doesn't showcase FHIR/OpenAPI integration, core technical differentiator
   - *Decision:* Rejected. This is a technical showcase first.

2. **General clinical documentation**
   - *Pros:* Broad applicability
   - *Cons:* Too vague, hard to visualize
   - *Decision:* Rejected. Needed concrete anchor.

3. **Voice transcription → validated data entry**
   - *Pros:* Explains all three invariants (dates, protocols, PII), natural fit with current code, concrete and visualizable
   - *Decision:* Accepted.

### Why Voice Transcription Wins:
- **Explains all three invariants:** Dates, protocols, PII each have clear roles
- **Natural fit with current code:** Date verification, sepsis protocol checking, and PII scanning all map directly
- **Concrete and visualizable:** Easy to imagine "doctor dictates, system verifies"
- **Explains the "guardrails" concept:** The layer between AI and EMR

## Structural Decisions

### 1. The Mission (Not "Executive Summary")

**Decision:** Open with human impact, not business jargon.

**Why:**
- "Give clinicians their time back" is visceral
- Connects to real burnout crisis in healthcare
- Sets emotional hook before technical details

**Alternative considered:** Traditional executive summary with market sizing
**Rejected:** Too dry, doesn't differentiate from generic healthcare AI pitches

### 2. The Problem (Named and Specific)

**Decision:** Focus on "validation failure" not "AI hallucinations"

**Why:**
- "Hallucinations" is technical jargon
- "Validation" explains what the system actually does
- Three concrete examples make it tangible

**The "Paradox" framing:**
- Creates tension: We need speed AND safety
- Sets up the solution as resolving this tension
- Classic problem-solution narrative structure

### 3. The Solution (Process, Not Features)

**Decision:** Describe workflow steps, not system components

**Why:**
- Easier to visualize than architecture diagrams
- Shows clinician experience, not just technical implementation
- "Accelerate safely" is the core value prop

**Intentional omission:** No mention of specific technologies here
- Technologies belong in "Why This Architecture"
- Keeps solution section accessible to non-technical readers

### 4. The Specific Use Case (Concrete Example)

**Decision:** Include full workflow example with Mrs. Johnson

**Why:**
- Makes abstract concept concrete
- Shows extraction → verification → validation flow
- Three verification questions mirror the three invariants

**Alternative considered:** Multiple use cases
**Rejected:** Focus on depth over breadth. One well-explained example > three shallow ones

### 5. Architecture ↔ Business Value Table

**Decision:** Explicit mapping of technical choices to outcomes

**Why:**
- Demonstrates Staff+ competency (technical → business translation)
- Justifies "over-engineering" to technical skeptics
- Shows FHIR/OpenAPI showcase intent without saying "look at my integration skills"

**Pattern inspired by:**
- Quality framework Level 5: "Codegen for interface validation"
- Quality framework Level 7: "Zero-Trust Logic Separation"

### 6. Success Metrics (Three Categories)

**Decision:** Organize by stakeholder concern, not technical layer

- **Workflow Efficiency:** What clinicians care about
- **Safety & Compliance:** What regulators/CTOs care about
- **Adoption:** What product teams care about

**Why:** Shows understanding of different success criteria for different stakeholders

**Specific targets (40%, 50%, 100%):**
- Intentionally ambitious but plausible
- Shows we've thought about realistic outcomes
- Creates accountability for the claims

### 7. The Dual Promise (Two-Column Format)

**Decision:** Separate quotes for healthcare vs technical leadership

**Why:**
- Acknowledges different value propositions
- Healthcare: "Reduce burden, improve compliance"
- Technical: "Scale engineering, maintain safety"
- Shows ability to code-switch between domains

### 8. The Staff+ Thesis (Explicit Framing)

**Decision:** End with connection to RATIONALE.md

**Why:**
- Reinforces this is a portfolio piece demonstrating leadership
- "Governance over typing" is the core differentiator
- Invites reader to explore deeper technical rationale

## What Was Intentionally Left Out

### Market Sizing
**Why:** This is a technical showcase, not a startup pitch. Market data would be:
- Distracting from technical narrative
- Potentially outdated
- Not the focus for hiring managers

### Competitive Analysis
**Why:**
- Avoids "me too" framing
- Keeps focus on solution, not differentiation from competitors
- Prevents document from feeling like sales material

### Detailed User Personas
**Why:**
- Would add length without clarity
- "The Clinician" is sufficient for this context
- Detailed personas belong in full PRDs, not hybrid docs

### Technical Implementation Details
**Why:**
- Belongs in ARCHITECTURE.md, not business purpose
- Keeps document accessible to non-technical readers
- "Why This Architecture" section provides enough detail

### NDIS/Aged Care Specifics
**Why:**
- Chose technical showcase over market strategy
- FHIR integration is core differentiator
- Can add market-specific variants later if needed

## Writing Style Decisions

### Tone: Technical Confidence + Business Awareness

**Characteristics:**
- Direct, active voice ("Give clinicians their time back")
- Minimal jargon ("AI hallucinations" → "validation failure")
- Confident without being arrogant
- Data-informed but not data-heavy

**Avoided:**
- Buzzwords ("synergy," "paradigm shift")
- Hedging language ("might," "could," "perhaps")
- Over-formality ("The undersigned proposes...")

### Length: Substantial but Scannable

**Decision:** ~1000 words, structured for quick reading

**Why:**
- Long enough to demonstrate depth
- Short enough to read in one sitting
- Headers allow skimming for busy executives

## Statistical Framing

### The "One Day a Week" Framing

**Original:** "International studies show 2 hours documentation for every 1 hour care" (Sinsky et al.)
**Revised:** "Lose 15-20% of total working hours... equates to an entire day per week"

**Why changed:**
- The 2:1 ratio is US-specific and often disputed in Australian General Practice contexts.
- **RACGP / MABEL Data:** Australian studies consistently show GPs spend ~14-20% of time on non-billable work.
- "Losing a day a week" is a powerful, visceral metric that resonates locally without citing a potentially alienating US statistic.

**Note:** Australian-specific RACGP/AIHW data can be added later if this becomes a market-facing document.

## Integration with Repository

### Links and References

- Links to `RATIONALE.md` for deep technical dive
- Implicit connection to `AGENTS.md` principles
- Consistent with `README.md` structure and tone

### Future Integration Points

- Should reference `ARCHITECTURE.md` when discussing technical choices
- Could add link to `TESTING_FRAMEWORK.md` in "Property-Based Testing" row
- Success metrics could reference specific test files

## Success Criteria for This Document

**How we know it worked:**

1. **Technical readers** can understand business value without feeling patronized
2. **Business readers** can understand technical approach without feeling overwhelmed
3. **Hiring managers** see Staff+ capabilities (strategic thinking, technical depth)
4. **Repository feels complete** - no longer "technology seeking a problem"

**Validation method:**
- Ask: "Does this make the repository feel like a product, not just a demo?"
- Check: Can someone describe the value proposition in 30 seconds?

## Revision History

- **Initial draft:** Approach C hybrid narrative, voice transcription focus
- **Revision 1:** Added concrete workflow example (Mrs. Johnson)
- **Revision 2:** Changed "AMA" to "International studies" for geographic neutrality
- **Revision 3:** Added "Why This Architecture" table with explicit technical→business mapping

## Future Considerations

### If This Becomes a Commercial Product:
- Add market sizing section
- Include competitive analysis vs. existing solutions (Nuance, Suki, etc.)
- Add detailed user personas with pain point quantification
- Replace "International studies" with Australia-specific RACGP data

### If Used for Conference Talk:
- Extract "The Paradox" section as opening hook
- Use Mrs. Johnson example as case study
- Expand "Dual Promise" into two-slide comparison

### If Used for Investor Pitch:
- Add TAM/SAM/SOM analysis
- Include pilot results with real metrics
- Expand "Success Metrics" to show measurable traction

## Conclusion

This document represents a **portfolio-grade business narrative** that serves dual purposes:
1. **Technical showcase** demonstrating Staff+ capabilities
2. **Business fluency** showing ability to translate engineering to value

The design prioritizes:
- **Clarity** over comprehensiveness
- **Depth** over breadth
- **Authenticity** over marketing polish
- **Integration** with existing technical documentation

The result is a document that makes the repository feel like a **real product solving a real problem**, while showcasing the engineering excellence that makes it possible.
