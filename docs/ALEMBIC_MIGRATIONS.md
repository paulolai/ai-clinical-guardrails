# Database Migrations with Alembic

This project uses Alembic for database schema migrations.

## Setup

Alembic is already initialized with the async template for SQLite support.

Key configuration:
- **Location**: `alembic/`
- **Versions**: `alembic/versions/`
- **Database**: SQLite with aiosqlite (`sqlite+aiosqlite:///./data/clinical.db`)
- **Batch Mode**: Enabled (`render_as_batch=True`) for SQLite compatibility

## SQLite-Specific Configuration

SQLite has limitations with ALTER COLUMN operations. We enable `render_as_batch=True` in `alembic/env.py` to wrap multiple ALTER operations in a transaction. This creates a new table with the desired schema, copies data, drops the old table, and renames the new one.

## Workflow

### Create a New Migration

After modifying SQLAlchemy models in `pwa/backend/models/`:

```bash
uv run alembic revision --autogenerate -m "Description of changes"
```

This will:
1. Compare current models with database schema
2. Generate a migration script in `alembic/versions/`
3. You should review the generated script before applying

### Apply Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Apply to specific revision
uv run alembic upgrade <revision_id>

# Apply one migration
uv run alembic upgrade +1
```

### Downgrade Migrations

```bash
# Downgrade one migration
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>

# Downgrade all (reset database)
uv run alembic downgrade base
```

### Check Current Status

```bash
# Show current revision
uv run alembic current

# Show migration history
uv run alembic history

# Show pending migrations
uv run alembic history --indicate-current
```

## Initial Setup (Already Done)

The following steps were completed during project setup:

1. **Added dependency**: `alembic>=1.13.0` in `pyproject.toml`
2. **Initialized Alembic**: `uv run alembic init -t async alembic`
3. **Configured alembic.ini**:
   - Set `sqlalchemy.url = sqlite+aiosqlite:///./data/clinical.db`
4. **Configured env.py**:
   - Imported `Base` from `pwa.backend.database`
   - Imported models to register with metadata
   - Set `target_metadata = Base.metadata`
   - Added `render_as_batch=True` for SQLite support
5. **Created initial migration**: `uv run alembic revision --autogenerate -m "Initial migration"`
6. **Applied migration**: `uv run alembic upgrade head`

## Best Practices

1. **Always review generated migrations** before applying
2. **Test migrations** on a copy of production data when possible
3. **Keep migrations small and focused** - one logical change per migration
4. **Never modify existing migrations** that have been applied to production
5. **Use meaningful migration names** that describe the change
6. **Include both upgrade and downgrade** paths in migrations

## Troubleshooting

### Migration fails with SQLite ALTER COLUMN error

SQLite doesn't support ALTER COLUMN directly. Ensure `render_as_batch=True` is set in both `run_migrations_offline()` and `do_run_migrations()` in `alembic/env.py`.

### Autogenerate detects no changes

Make sure models are imported in `alembic/env.py`. The import statement ensures models are registered with `Base.metadata`:

```python
from pwa.backend.models.recording_sql import RecordingModel  # noqa: F401
```

### Database locked errors

SQLite WAL mode is enabled in `pwa/backend/database.py` to support concurrent reads/writes. If you see locking errors, ensure no other process has the database open.

## Model Registration

When adding new models, ensure they are imported in `alembic/env.py` so Alembic can detect them:

```python
# In alembic/env.py
from pwa.backend.models.your_model import YourModel  # noqa: F401
```

The `# noqa: F401` comment prevents linting errors for unused imports while ensuring the model is registered.
