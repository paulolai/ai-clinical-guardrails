# pwa/backend/database.py
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./data/clinical.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)


# ENABLE HIGH CONCURRENCY
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    """Configure SQLite PRAGMA settings for high concurrency."""
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


# AsyncSession factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    # Import models to register them with Base.metadata
    from pwa.backend.models.recording_sql import RecordingModel  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
