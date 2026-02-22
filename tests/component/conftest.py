"""Configuration for component tests with VCR."""

import pytest


@pytest.fixture(scope="session")
def vcr_config():
    """VCR configuration to filter sensitive data."""
    return {
        "filter_headers": [
            "authorization",
            "Authorization",
        ],
    }
