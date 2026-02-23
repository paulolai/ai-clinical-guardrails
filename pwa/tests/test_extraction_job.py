# pwa/tests/test_extraction_job.py
"""Tests for extraction job."""


def test_extraction_job_exists() -> None:
    """Test that extraction job module exists."""
    from pwa.backend.jobs.extraction_job import process_extraction

    assert callable(process_extraction)
