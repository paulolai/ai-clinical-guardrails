# Clinical Note Review Architecture - Decision Process

**Date:** 2025-02-22
**Status:** Decisions documented, may be revisited
**Related:** `2025-02-22-clinical-note-review-design.md`

---

## Goals and Non-Goals

### Goals
- Demonstrate staff+ integration architecture skills
- Show FHIR R5 + AI safety systems working together
- Create working demo in 2-3 hours focused work
- Reuse existing ComplianceEngine, FHIR client, protocol checkers

### Non-Goals (Explicitly Rejected)
- Full production system with caching/persistence
- Complex freshness checking with change detection
- Web UI for clinicians
- Multi-EMR aggregation
- Async job queues

---

## Alternatives Considered

### Approach 1: Pipeline with Verified Snapshots
**What:** Verify at generation time, store immutable snapshots

**Pros:**
- Clear audit trail
- Fast review (data already verified)
- Simple mental model

**Cons:**
- High latency at generation
- Stale data if doctor reviews hours later
- Requires complex cache invalidation

**Why Rejected:**
- Stale data is unacceptable in healthcare
- Would need freshness checking anyway
- Adds complexity without solving core problem

---

### Approach 2: On-Demand Verification
**What:** Verify when doctor opens review, real-time against EMR

**Pros:**
- Always fresh data
- No storage complexity
- Lower storage costs

**Cons:**
- Review latency depends on EMR speed
- No audit trail
- EMR rate limiting risk
- Doctor waits during verification

**Why Rejected:**
- Unacceptable UX (doctor waiting 2-5 seconds per review)
- No compliance audit trail
- Fragile (EMR downtime = no reviews)

---

### Approach 3: Hybrid with Smart Re-Verification (SELECTED)
**What:** Verify at generation + cache, check freshness at review, re-verify if stale

**Pros:**
- Fast initial review (cached data)
- Automatic freshness guarantees
- Audit trail from snapshots
- Resilient to EMR downtime

**Cons:**
- Most complex implementation
- Requires change detection logic
- More moving parts

**Why Selected:**
- Best UX (fast + accurate)
- Production-grade (resilience)
- Demonstrates staff+ thinking (trade-offs)

---

## Decision Criteria

| Criterion | Weight | Approach 1 | Approach 2 | Approach 3 |
|-----------|--------|------------|------------|------------|
| Review Speed | High | ✅ Fast | ❌ Slow | ✅ Fast |
| Data Freshness | Critical | ⚠️ Stale | ✅ Fresh | ✅ Fresh |
| Audit Trail | Critical | ✅ Yes | ❌ No | ✅ Yes |
| EMR Resilience | High | ✅ Works | ❌ Fails | ✅ Works |
| Implementation | Medium | ⚠️ Medium | ✅ Simple | ⚠️ Complex |
| **TOTAL** | | ⚠️ | ❌ | ✅ |

---

## Trade-offs

### What We Accepted
- **Implementation complexity:** More code to write initially
- **Change detection:** Need to track EMR versions
- **Cache management:** Must handle invalidation

### What We Gave Up
- **Simplicity:** Not the easiest to understand
- **Quick wins:** Takes longer to implement
- **Pure approach:** Hybrid is messier than pure on-demand or pure snapshot

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Stale data served | Freshness checker with warnings |
| Cache grows too large | TTL on snapshots, LRU eviction |
| EMR version comparison breaks | Fallback to timestamp-based |
| Complexity hard to maintain | Well-documented service boundaries |

---

## Revisit Conditions

**Revisit this decision if:**
1. EMR provides reliable change notification webhooks
2. Performance requirements change (e.g., <100ms vs <500ms)
3. Audit requirements change (e.g., must re-verify every time)
4. Team size grows (can maintain more complex system)

**Trigger:** Any of the above conditions met

---

## Notes for Future Maintainers

**Why this isn't "obviously" the best choice:**
- Pure on-demand is simpler
- Pure snapshots are easier to reason about
- Hybrid requires understanding both patterns

**When to consider alternatives:**
- If EMR latency drops below 50ms consistently → Consider Approach 2
- If audit trail not required → Consider Approach 2
- If real-time collaboration needed → Consider Approach 1 with websockets

**Current thinking:**
- Hybrid approach is right for production healthcare
- Complexity is justified by safety requirements
- Will simplify if EMR infrastructure improves
