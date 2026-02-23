# Clinical Transcription PWA - Phase 1.5 Kickoff: Persistence Layer

**Date:** 2025-02-23
**Status:** 🚀 Ready to Start
**Depends on:** Phase 1 (Prototype) Complete ✅
**Blocks:** Phase 2 (Offline Capabilities)
**Branch:** `phase-1-5-persistence`

---

## The Problem

Phase 1 uses **in-memory Python dictionaries** (`_recordings: dict = {}`). This creates critical blockers for Phase 2:

### Why This Blocks Phase 2

| Phase 2 Feature | Why In-Memory Breaks It |
|----------------|------------------------|
| **Offline Sync** | Client and server states diverge on server restart. Sync logic requires stable server state. |
| **Queue Management** | Queue disappears on deploy/restart. Clinicians lose recordings. |
| **Reliability** | Production deployments restart. Data loss is unacceptable for patient records. |

### Review Finding

> "Building complex sync logic on top of a volatile dict is engineering malpractice."
> — Phase 1 Review

---

## Mission

**Replace in-memory storage with PostgreSQL** to create a stable foundation for offline capabilities.

**Success Criteria:**
- [ ] Data persists across server restarts
- [ ] Same API surface (no breaking changes)
- [ ] Async SQLAlchemy for performance
- [ ] Alembic migrations for schema management
- [ ] Tests use real database (not mocks)

---

## Scope

### In Scope (Must Have)

1. **Database Setup**
   - PostgreSQL container (Docker)
   - SQLAlchemy 2.0 async models
   - Database connection pooling
   - Health checks

2. **Model Migration**
   - Convert Recording Pydantic model to SQLAlchemy table
   - All existing fields preserved
   - Proper indexes (patient_id, clinician_id, status)

3. **Service Layer Rewrite**
   - RecordingService uses async SQLAlchemy
   - Same method signatures (no breaking changes)
   - Transaction support

4. **Testing**
   - Tests use test database (pytest-postgresql or Docker)
   - Migration tests
   - No mocked database

5. **Migrations**
   - Alembic setup
   - Initial migration (Phase 1.5)
   - Migration documentation

### Out of Scope (Phase 2)

- File storage (audio still in memory for now)
- Database backup procedures
- Read replicas
- Connection retry logic
- Monitoring

---

## Architecture

### Before (Phase 1)

```python
class RecordingService:
    _recordings: dict = {}  # In-memory only

    def create_recording(...):
        recording = Recording(...)
        self._recordings[recording.id] = recording
        return recording
```

**Problem:** `_recordings` is empty on every server restart.

### After (Phase 1.5)

```python
class RecordingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recording(...):
        recording = RecordingModel(...)  # SQLAlchemy
        self.db.add(recording)
        await self.db.commit()
        return Recording.from_orm(recording)  # Back to Pydantic
```

**Benefit:** Data persists in PostgreSQL.

---

## Implementation Plan

### Week 1: Database Foundation

**Day 1-2: Setup**
- [ ] Add SQLAlchemy + asyncpg dependencies
- [ ] Create database.py with engine/session
- [ ] Docker Compose for PostgreSQL
- [ ] Health check endpoint for DB

**Day 3-4: Models**
- [ ] Create RecordingModel (SQLAlchemy)
- [ ] Map Pydantic Recording ↔ SQLAlchemy RecordingModel
- [ ] Add indexes

**Day 5: Alembic**
- [ ] Initialize Alembic
- [ ] Create initial migration
- [ ] Document migration workflow

### Week 2: Service Migration

**Day 6-7: Rewrite Service**
- [ ] RecordingService with async SQLAlchemy
- [ ] Dependency injection for DB session
- [ ] Transaction handling

**Day 8-9: Tests**
- [ ] Test database setup
- [ ] Rewrite tests to use real DB
- [ ] Migration tests

**Day 10: Polish**
- [ ] Error handling
- [ ] Documentation
- [ ] Verify no breaking changes

---

## Technical Details

### Dependencies

```toml
[tool.poetry.dependencies]
sqlalchemy = {extras = ["asyncpg"], version = "^2.0.0"}
alembic = "^1.13.0"
pytest-postgresql = {version = "^6.0.0", optional = true}
```

### Database Schema

```sql
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR NOT NULL,
    clinician_id VARCHAR NOT NULL,
    audio_file_path VARCHAR,
    audio_file_size INTEGER,
    duration_seconds INTEGER,
    status VARCHAR NOT NULL DEFAULT 'pending',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    transcript TEXT,
    verification_results JSONB
);

CREATE INDEX idx_recordings_patient_id ON recordings(patient_id);
CREATE INDEX idx_recordings_clinician_id ON recordings(clinician_id);
CREATE INDEX idx_recordings_status ON recordings(status);
CREATE INDEX idx_recordings_created_at ON recordings(created_at);
```

### Pydantic ↔ SQLAlchemy Mapping

```python
# Pydantic (API layer)
class Recording(BaseModel):
    id: UUID
    patient_id: str
    # ... etc

    class Config:
        from_attributes = True  # Enable SQLAlchemy → Pydantic

# SQLAlchemy (Database layer)
class RecordingModel(Base):
    __tablename__ = "recordings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id = Column(String, nullable=False)
    # ... etc
```

### Service Pattern

```python
async def get_db():
    """Dependency for FastAPI routes."""
    async with async_session() as session:
        yield session

@router.post("")
async def create_recording(
    request: CreateRecordingRequest,
    db: AsyncSession = Depends(get_db)
):
    service = RecordingService(db)
    return await service.create_recording(...)
```

---

## Testing Strategy

### Database Fixture

```python
@pytest.fixture
def db():
    """Real database session for tests."""
    # Use test database or rollback transactions
    async with async_session() as session:
        yield session
        await session.rollback()
```

### Migration Test

```python
def test_migration_applies():
    """Verify Alembic migrations work."""
    alembic.command.upgrade(alembic_config, "head")
    # Verify tables exist
```

---

## Verification

### Before Phase 1.5

```bash
# Restart server
uv run python pwa/backend/main.py
# Create recording
# Restart server
# Recording is gone ❌
```

### After Phase 1.5

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Restart server multiple times
uv run python pwa/backend/main.py
# Create recording
# Restart server
# Recording persists ✅
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Migration complexity | Start with simple schema, add fields incrementally |
| Async SQLAlchemy learning curve | Start with sync, convert to async if needed |
| Test performance | Use transaction rollback, not DB recreation |
| Breaking changes | Keep same API signatures, internal implementation only |

---

## Definition of Done

- [ ] PostgreSQL container runs
- [ ] SQLAlchemy models created
- [ ] Alembic migrations work
- [ ] RecordingService uses database
- [ ] All tests pass with real database
- [ ] Data persists across server restarts
- [ ] No breaking changes to API
- [ ] Documentation updated

---

## Next Steps

1. **Create Branch**
   ```bash
   git checkout main
   git pull
   git checkout -b phase-1-5-persistence
   ```

2. **Start Day 1**
   - Add SQLAlchemy dependencies
   - Create database.py
   - Docker Compose setup

3. **Reference Docs**
   - SQLAlchemy 2.0 Async Guide
   - Alembic Tutorial
   - FastAPI + SQLAlchemy docs

---

## Resources

- **Phase 1 Summary:** [2025-02-23-pwa-phase1-implementation-summary.md](./2025-02-23-pwa-phase1-implementation-summary.md)
- **Phase 1 Review:** [PHASE1_REVIEW.md](../reviews/PHASE1_REVIEW.md)
- **Phase 2 Kickoff:** [2025-02-23-pwa-phase2-kickoff.md](./2025-02-23-pwa-phase2-kickoff.md)
- **Implementation Plan:** [2025-02-23-clinical-transcription-pwa-implementation.md](./2025-02-23-clinical-transcription-pwa-implementation.md)

---

**Ready to start?** Create the branch and begin Week 1.

**Remember:** Phase 2 (Offline) depends on this. Don't skip it.
