"""Pytest configuration for PWA tests."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pwa.backend.database import Base, get_db
from pwa.backend.main import app
from pwa.backend.models.recording_sql import RecordingModel  # noqa: F401

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_connection(test_engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Create a test database connection with transaction."""
    async with test_engine.connect() as connection, connection.begin() as transaction:
        yield connection
        # Rollback the transaction after each test
        await transaction.rollback()


@pytest_asyncio.fixture
async def test_db_session(test_db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session bound to the connection."""
    async_session = sessionmaker(
        bind=test_db_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def override_get_db(test_db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db dependency for tests."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    return _override_get_db


@pytest.fixture(autouse=True)
def setup_test_db(override_get_db: AsyncGenerator[AsyncSession, None]) -> None:
    """Automatically override database dependency for all tests."""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
