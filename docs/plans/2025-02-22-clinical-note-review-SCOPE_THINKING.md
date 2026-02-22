# Clinical Note Review Scope - Decision Process

**Date:** 2025-02-22
**Status:** Scope locked for demo, may expand for production
**Related:** `2025-02-22-clinical-note-review-SCOPE.md`

---

## Goals and Non-Goals

### Goals
- Build working demo in 2-3 hours
- Demonstrate staff+ integration skills
- Show FHIR + AI safety + protocol checkers working together
- Prove the architecture works end-to-end

### Non-Goals (Explicitly Cut)
- Full production features
- Snapshot persistence (database)
- Complex freshness checking
- Web UI
- Production-grade caching
- Full test coverage
- Async job queues
- Multi-tenancy

---

## Alternatives Considered

### Option A: Full Implementation (Original Plan)
**What:** 11 tasks, ~100 steps, complete verification pipeline

**Tasks:**
1. Download FHIR R5 schema
2. Generate Pydantic models
3. Create domain wrapper layer
4. Create FHIR R5 client
5. Interface-specific CLI
6. Component testing
7. Create snapshot store
8. Create freshness checker
9. Create verification orchestrator
10. Create unified view builder
11. Create Review API

**Pros:**
- Complete system
- Production-ready
- Full test coverage

**Cons:**
- 8-10 hours of work
- Most features duplicate existing code
- Diminishing returns for demo

**Why Rejected:**
- ComplianceEngine already exists
- FHIR client already exists
- Protocol checkers already exist
- Building new parallel system instead of extending

---

### Option B: Proof of Concept (Minimal)
**What:** 2 tasks - Service + CLI only

**Tasks:**
1. Create ReviewService
2. Create CLI tool

**Pros:**
- 1 hour of work
- Shows core concept
- Minimal code

**Cons:**
- No API endpoints
- No domain models
- Hard to test manually
- Doesn't show integration depth

**Why Rejected:**
- Too minimal to demonstrate staff+ skills
- Doesn't touch enough of the system
- No way for reviewer to interact with it

---

### Option C: Integration Focus (SELECTED)
**What:** 4 tasks, ~25 steps, extend existing system

**Tasks:**
1. Extend domain models (2 models)
2. Create ReviewService (compose existing)
3. Add API endpoints (2 endpoints)
4. Create CLI tool (simple)

**Pros:**
- 2-3 hours of work
- Reuses existing systems
- Shows integration architecture
- Demonstrates composition
- Can test end-to-end

**Cons:**
- Not production-complete
- Missing caching
- Missing persistence

**Why Selected:**
- Best balance for demo
- Shows staff+ thinking (YAGNI)
- Demonstrates integration skills
- Leaves clear path for production

---

## Decision Criteria

| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Time to Demo | High | ❌ 8-10h | ✅ 1h | ✅ 2-3h |
| Shows Integration | Critical | ✅ Yes | ⚠️ Minimal | ✅ Yes |
| Reuses Existing | High | ❌ No | ⚠️ Partial | ✅ Yes |
| Staff+ Skills | Critical | ✅ Yes | ❌ No | ✅ Yes |
| Demo Quality | High | ✅ Production | ❌ Toy | ✅ Working |
| **TOTAL** | | ⚠️ Overkill | ❌ Too small | ✅ |

---

## What We Cut and Why

| Feature | Why Cut | Alternative |
|---------|---------|-------------|
| **Snapshot Store (DB)** | Complexity | In-memory for demo |
| **FreshnessChecker** | Complex change detection | Regenerate each time |
| **VerificationOrchestrator** | Duplicate | Extend ComplianceEngine |
| **UnifiedViewBuilder** | Over-engineering | Simple composition |
| **Full test suite** | Time | Component tests only |
| **Web UI** | Scope creep | CLI only |
| **Caching layer** | Complexity | None for demo |
| **Async job queue** | Infrastructure | Synchronous |

---

## What We Kept and Why

| Feature | Why Keep |
|---------|----------|
| **Domain models** | Need ClinicalNote, UnifiedReview |
| **ReviewService** | Core orchestration, shows architecture |
| **API endpoints** | Demonstrates FastAPI integration |
| **CLI tool** | Developer experience, easy to demo |
| **Component tests** | Prove it works against real FHIR |
| **Protocol checkers** | Shows safety integration |

---

## Trade-offs

### What We Accepted
- **Demo only:** Not production-complete
- **Regenerate each time:** No caching
- **In-memory storage:** Data lost on restart
- **Component tests only:** Not full coverage

### What We Gave Up
- **Production features:** Will need to add later
- **Performance:** No caching/optimization
- **Scalability:** Single-threaded demo
- **Persistence:** No database

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Reviewer thinks this is production | Document "DEMO" clearly |
| Hard to extend later | Clean architecture, clear boundaries |
| Tests aren't comprehensive | Component tests prove integration |
| Performance seems slow | Document "not optimized" |
| Missing critical features | Scope document lists what's out |

---

## Revisit Conditions

**Expand scope if:**
1. Moving to production
2. Performance requirements emerge
3. Need persistence/audit trail
4. Multiple users/concurrency needed

**Reduce scope if:**
1. Even 2-3 hours is too much
2. Can demonstrate with just CLI
3. Focus should be on different skills

**Trigger:** User request or time constraints

---

## Path to Production

**What's needed to make this production:**

1. **Add persistence:** PostgreSQL for snapshots
2. **Add caching:** Redis for EMR data
3. **Add freshness:** Proper change detection
4. **Add async:** Background job queue
5. **Add monitoring:** Metrics, alerting
6. **Add auth:** OAuth2, role-based access
7. **Expand tests:** Unit, integration, PBT
8. **Add UI:** React frontend

**Estimated effort:** 2-3 weeks (vs 2-3 hours for demo)

---

## Notes for Future Maintainers

**Why this scope feels "incomplete":**
- No database
- No caching
- Regenerates each time
- Minimal tests

**Why that's okay:**
- This is a demo, not production
- Architecture is sound
- Clear extension points
- Tests prove integration works

**When to worry:**
- If trying to use this in production as-is
- If performance becomes an issue
- If data loss is unacceptable

**Current thinking:**
- Scope is right for demonstrating staff+ skills
- Shows integration architecture
- Leaves clear production path
- Will expand if/when needed
