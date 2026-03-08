"""Configuration for component tests with VCR."""

import re

import pytest


def normalize_request_body(body):
    """Normalize request body by masking dynamic dates.

    This ensures cassettes remain valid regardless of when tests are run,
    as the LLM extraction prompt includes the current date which changes daily.
    """
    if body and isinstance(body, str):
        # Replace ISO format dates (YYYY-MM-DD) with placeholder
        return re.sub(r"Reference Date: \d{4}-\d{2}-\d{2}", "Reference Date: <DATE_MASKED>", body)
    return body


def mask_reference_date(request):
    """Replace reference dates in request body before recording to cassette."""
    if request.body and isinstance(request.body, str):
        request.body = normalize_request_body(request.body)
    return request


def pytest_configure(config):
    """Register custom VCR matchers during pytest configuration."""
    import vcr

    def date_agnostic_matcher(r1, r2):
        """Custom matcher that ignores date differences in request bodies.

        This allows cassettes recorded on different days to match replay requests.
        """
        # First check standard matchers (method, uri, etc.)
        if r1.method != r2.method:
            return False
        if r1.uri != r2.uri:
            return False

        # Normalize both bodies and compare
        # Handle both string and bytes bodies
        def get_body_str(body):
            if body is None:
                return None
            if isinstance(body, bytes):
                return body.decode("utf-8")
            return body

        body1 = normalize_request_body(get_body_str(r1.body))
        body2 = normalize_request_body(get_body_str(r2.body))

        if body1 != body2:
            raise AssertionError(
                f"Request bodies don't match:\n"
                f"  Expected: {body2[:200] if body2 else None}...\n"
                f"  Got: {body1[:200] if body1 else None}..."
            )

        return True

    # Monkey-patch VCR to inject our matcher on each instance creation
    _original_vcr_init = vcr.VCR.__init__

    def _patched_vcr_init(self, *args, **kwargs):
        _original_vcr_init(self, *args, **kwargs)
        # Add our matcher to this instance
        self.matchers["date_agnostic"] = date_agnostic_matcher

    vcr.VCR.__init__ = _patched_vcr_init


@pytest.fixture(scope="session")
def vcr_config():
    """VCR configuration to filter sensitive data."""
    return {
        "filter_headers": [
            "authorization",
            "Authorization",
        ],
        "allow_playback_repeats": True,
        "before_record_request": [mask_reference_date],
        "match_on": ["date_agnostic"],
    }
