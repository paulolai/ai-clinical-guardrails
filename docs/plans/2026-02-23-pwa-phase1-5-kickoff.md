# Clinical Transcription PWA - Phase 1.5 Kickoff: Persistence Layer (SQLite Production Ready)

**Date:** 2026-02-23
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

**Replace in-memory storage with SQLite (Async)** to create a stable, high-performance foundation for offline capabilities without the operational overhead of Dockerized databases.

**Success Criteria:**
- [ ] Data persists across server restarts (`data/clinical.db`)
- [ ] **WAL Mode Enabled:** Supports high concurrency (readers don't block writers)
- [ ] **Online Backup:** Automated hot backups without stopping the server
- [ ] Async SQLAlchemy (`aiosqlite`) for performance
- [ ] Alembic migrations for schema management (Batch Mode)

---

## Scope

### In Scope (Must Have)

1. **Database Setup**
   - SQLite with `aiosqlite` driver
   - **Production Config:** `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`
   - Database location configuration (`data/clinical.db`)

2. **Model Migration**
   - Convert Recording Pydantic model to SQLAlchemy table
   - All existing fields preserved
   - JSON fields (`verification_results`) stored as TEXT (accessed via JSON functions)

3. **Service Layer Rewrite**
   - RecordingService uses async SQLAlchemy
   - Same method signatures (no breaking changes)
   - Transaction support with explicit commits

4. **Testing**
   - Tests use a fresh file-based SQLite DB per test session (or `:memory:` for speed)
   - No mocked database

5. **Migrations**
   - Alembic setup with `render_as_batch=True` (Critical for SQLite schema changes)
   - Initial migration (Phase 1.5)

6. **Operations (New)**
   - `backup_db.py` script using SQLite Online Backup API
   - `vacuum_db.py` maintenance script

### Out of Scope
- PostgreSQL / Docker containers
- File storage (audio still in memory/disk for now)
- "Hot Spare" Replication (Phase 3: Litestream)

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

### After (Phase 1.5)

```python
class RecordingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recording(...):
        recording = RecordingModel(...)  # SQLAlchemy
        self.db.add(recording)
        await self.db.commit()
        return Recording.from_orm(recording)
```

**Benefit:** Data persists in `clinical.db`.

---

## Implementation Plan

### Week 1: Database Foundation

**Day 1-2: Setup**
- [ ] Add `sqlalchemy` + `aiosqlite` dependencies
- [ ] Create `database.py` with `create_async_engine`
- [ ] **Critical:** Configure `PRAGMA` settings for concurrency (WAL)
- [ ] Create `scripts/backup_db.py` (Hot Backup)

**Day 3-4: Models**
- [ ] Create RecordingModel (SQLAlchemy)
- [ ] Map Pydantic Recording ↔ SQLAlchemy RecordingModel
- [ ] Handle JSON fields (SQLAlchemy `JSON` type)

**Day 5: Alembic**
- [ ] Initialize Alembic (`alembic init -t async`)
- [ ] Configure `env.py` for `render_as_batch=True` (SQLite limitation fix)
- [ ] Create initial migration

### Week 2: Service Migration

**Day 6-7: Rewrite Service**
- [ ] RecordingService with async SQLAlchemy
- [ ] Dependency injection for DB session

**Day 8-9: Tests**
- [ ] Update `conftest.py` to create fresh SQLite DBs for tests
- [ ] Rewrite service tests
- [ ] Create `seed_db.py` script

**Day 10: Polish**
- [ ] Verify persistence across restarts
- [ ] Test backup script while server is under load
- [ ] Documentation updated

---

## Technical Details

### Dependencies

```toml
[tool.poetry.dependencies]
sqlalchemy = {version = "^2.0.0"}
aiosqlite = "^0.19.0"
alembic = "^1.13.0"
```

### Production Database Configuration (WAL Mode)

```python
# pwa/backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import event, Engine

DATABASE_URL = "sqlite+aiosqlite:///./data/clinical.db"

engine = create_async_engine(DATABASE_URL)

# ENABLE HIGH CONCURRENCY
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Write-Ahead Logging: Readers don't block writers
    cursor.execute("PRAGMA journal_mode=WAL")
    # Sync Normal: Faster writes, safe enough for OS crashes (not power loss)
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Busy Timeout: Wait 5s before failing if locked
    cursor.execute("PRAGMA busy_timeout=5000")
    # Foreign Keys: Enforce constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### Hot Backup Script (No Downtime)

```python
# scripts/backup_db.py
import sqlite3
import shutil
from datetime import datetime

def backup():
    """Perform a hot backup using the SQLite Backup API."""
    src = sqlite3.connect("data/clinical.db")
    dst_name = f"backups/clinical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dst = sqlite3.connect(dst_name)

    with dst:
        src.backup(dst)  # Copies pages safely while DB is active

    dst.close()
    src.close()
    print(f"Backup created: {dst_name}")
```

### Database Schema

```python
# pwa/backend/models/sql_recording.py
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

class RecordingModel(Base):
    __tablename__ = "recordings"

    # ... standard fields ...

    # JSON handling in SQLite
    # SQLAlchemy handles serialization/deserialization automatically
    verification_results = Column(JSON)
```

---

## Testing Strategy

### Test Fixture

```python
@pytest_asyncio.fixture
async def db_session():
    # Use in-memory SQLite for fast tests
    # URI: sqlite+aiosqlite:///:memory:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Database Locking** | Enable **WAL mode** + `busy_timeout=5000`. Handles concurrent reads/writes well. |
| **Data Loss (Corruption)** | Use `backup_db.py` (Hot Backup API) scheduled via cron. Don't just `cp` the file. |
| **JSON Performance** | Use `json_extract` sparingly. For <100k rows, full scan is fast. |
| **Schema Changes** | Use Alembic `render_as_batch=True` mode (SQLite doesn't support `ALTER COLUMN` natively). |

---

## Definition of Done

- [ ] `clinical.db` created in `data/` directory
- [ ] WAL mode enabled (check for `-wal` and `-shm` files)
- [ ] SQLAlchemy models created
- [ ] Alembic migrations work (batch mode)
- [ ] RecordingService uses database
- [ ] `backup_db.py` script verified (creates valid backup while app runs)
- [ ] All tests pass
- [ ] Data persists across server restarts

---

## Next Steps

1. **Create Branch**
   ```bash
   git checkout main
   git pull
   git checkout -b phase-1-5-persistence
   ```

2. **Start Day 1**
   - Add `aiosqlite` dependency
   - Configure WAL mode

---

**Resources**
- [SQLAlchemy SQLite Async Guide](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#module-sqlalchemy.dialects.sqlite.aiosqlite)
- [SQLite WAL Mode](https://sqlite.org/wal.html)
- [SQLite Online Backup API](https://www.sqlite.org/backup.html)

**Ready to start?** Create the branch and begin Week 1.
