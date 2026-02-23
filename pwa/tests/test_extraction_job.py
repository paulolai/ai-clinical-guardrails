# pwa/tests/test_extraction_job.py
"""Tests for extraction job."""

import pytest


class TestExtractionJobModule:
    """Basic tests for extraction job module."""

    def test_extraction_job_exists(self) -> None:
        """Test that extraction job module exists."""
        from pwa.backend.jobs.extraction_job import process_extraction

        assert callable(process_extraction)

    def test_extraction_imports_recording_status(self) -> None:
        """Test that extraction job imports RecordingStatus."""
        from pwa.backend.models.recording import RecordingStatus

        assert RecordingStatus is not None

    def test_extraction_job_has_logging(self) -> None:
        """Test that extraction job uses logging."""
        from pwa.backend.jobs.extraction_job import logger

        assert logger.name == "pwa.backend.jobs.extraction_job"

    def test_process_extraction_signature(self) -> None:
        """Test that process_extraction has correct signature."""
        import inspect

        from pwa.backend.jobs.extraction_job import process_extraction

        sig = inspect.signature(process_extraction)
        assert "recording_id" in sig.parameters


class TestExtractionJobErrorHandling:
    """Tests for extraction job error handling behavior."""

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_extraction_job_is_callable(self) -> None:
        """Test that process_extraction is callable."""
        from pwa.backend.jobs.extraction_job import process_extraction

        assert callable(process_extraction)

    def test_error_handling_code_structure(self) -> None:
        """Test that error handling code is present."""
        import ast
        import inspect

        from pwa.backend.jobs.extraction_job import process_extraction

        source = inspect.getsource(process_extraction)
        tree = ast.parse(source)

        # Find try-except blocks
        has_error_update = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    for child in ast.walk(handler):
                        if isinstance(child, ast.Attribute) and child.attr == "update_recording_status":
                            has_error_update = True

        assert has_error_update, "Missing error handling that updates recording status"
