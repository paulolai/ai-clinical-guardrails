"""Tests for database module."""

import pytest
from sqlalchemy import text

from pwa.backend.database import engine, get_db, init_db


@pytest.mark.asyncio
async def test_database_connection():
    """Test that database connection works with PRAGMA settings."""
    async with engine.connect() as conn:
        # Test PRAGMA settings
        result = await conn.execute(text("PRAGMA journal_mode"))
        journal_mode = result.scalar()
        assert journal_mode == "wal", f"Expected WAL mode, got {journal_mode}"

        result = await conn.execute(text("PRAGMA synchronous"))
        sync_mode = result.scalar()
        assert sync_mode == 1, f"Expected synchronous=NORMAL (1), got {sync_mode}"

        result = await conn.execute(text("PRAGMA foreign_keys"))
        foreign_keys = result.scalar()
        assert foreign_keys == 1, f"Expected foreign_keys=ON, got {foreign_keys}"


@pytest.mark.asyncio
async def test_get_db_dependency():
    """Test get_db yields an async session."""
    async_gen = get_db()
    session = await anext(async_gen)
    assert session is not None
    await session.close()


@pytest.mark.asyncio
async def test_init_db():
    """Test init_db creates tables."""
    # This will test init_db when we add models later
    await init_db()
    # Just verify it doesn't throw
    assert True
