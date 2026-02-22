"""Configuration for component tests with VCR."""

import pytest


@pytest.fixture(scope="session")
def vcr_config():
    """VCR configuration to filter sensitive data."""
    return {
        "filter_headers": [
            "authorization",
            "Authorization",
            "x-api-key",
            "X-API-Key",
        ],
        "filter_post_data_parameters": [
            "api_key",
            "apikey",
        ],
        "filter_query_parameters": [
            "api_key",
            "apikey",
        ],
    }
