# Clinical Transcription PWA

## Database Persistence

This application uses SQLite with WAL (Write-Ahead Logging) mode for data persistence.

### Data Seeding

To populate the database with test data:

```bash
# Run the seed script
PYTHONPATH=/home/paulo/ai-clinical-guardrails/.worktrees/phase-1-5-persistence uv run python scripts/seed_db.py
```

This creates 5 test recordings with varied statuses (PENDING, PROCESSING, COMPLETED, ERROR).

### Backup

To create a hot backup of the database:

```bash
# Run the backup script
PYTHONPATH=/home/paulo/ai-clinical-guardrails/.worktrees/phase-1-5-persistence uv run python scripts/backup_db.py
```

Backups are stored in the `backups/` directory with timestamps.

### Persistence Verification

Run the persistence tests:

```bash
cd /home/paulo/ai-clinical-guardrails/.worktrees/phase-1-5-persistence
uv run pytest pwa/tests/test_persistence.py -v
```

These tests verify:
- Data persists across database sessions
- Status updates persist after reconnect
- Multiple recordings persist correctly
- Clinician queries work after reconnect
- Server restart simulation (most realistic test)

### Manual Verification

To manually verify persistence:

1. Start the server: `uv run python pwa/backend/main.py`
2. Create a recording via API
3. Stop the server (Ctrl+C)
4. Restart the server
5. Query the recording - it should still exist

### Database Location

- **Development:** `./data/clinical.db`
- **Test:** In-memory (per-test isolation)
- **Backups:** `./backups/clinical_YYYYMMDD_HHMMSS.db`

### Configuration

Database URL is configured in `pwa/backend/config.py`:

```python
database_url: str = "sqlite+aiosqlite:///./data/clinical.db"
```

Override with environment variable:

```bash
PWA_DATABASE_URL="sqlite+aiosqlite:///./custom/path.db" uv run python pwa/backend/main.py
```
