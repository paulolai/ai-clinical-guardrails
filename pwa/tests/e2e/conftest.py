"""E2E test configuration - isolated from backend fixtures."""

import pytest


@pytest.fixture(scope="session")  # type: ignore[misc]
def base_url() -> str:
    """Base URL for the PWA server."""
    return "http://localhost:8002"
