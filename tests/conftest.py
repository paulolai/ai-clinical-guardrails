"""Root pytest configuration.

This runs before any test collection to ensure environment is set up.
"""

import os

# Set a dummy API key for tests that import modules requiring it.
# Tests that specifically test "no API key" behavior should patch the env.
# Note: We check for falsy values (None, empty string) and override them.
api_key = os.environ.get("SYNTHETIC_API_KEY")
if not api_key:
    os.environ["SYNTHETIC_API_KEY"] = "test-api-key-for-ci"
