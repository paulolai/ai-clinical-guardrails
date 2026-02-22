"""E2E tests for CLI extraction tool.

Tests the full CLI flow with real API calls (recorded with VCR).
"""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from typer.testing import CliRunner

from cli.extract import app

runner = CliRunner()

# Enable VCR recording for all CLI tests
pytestmark = [
    pytest.mark.component,
    pytest.mark.vcr,
]


class TestCLIExtractE2E:
    """End-to-end tests for CLI extraction with real API."""

    @pytest.fixture
    def api_key(self) -> str | None:
        """Get API key from environment."""
        return os.environ.get("SYNTHETIC_API_KEY")

    def test_extract_from_text_with_real_api(self, api_key: str | None) -> None:
        """E2E: Extract from text using real Synthetic API."""
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set")

        transcript = "Mrs. Sarah Johnson came in yesterday for follow-up. Started on Lisinopril 10mg daily."

        result = runner.invoke(app, ["extract", "--text", transcript], env={"SYNTHETIC_API_KEY": api_key})

        print(f"\nExit code: {result.exit_code}")
        print(f"Output:\n{result.output}")

        # Should complete without error
        assert result.exit_code == 0
        # Should contain extraction results
        assert "Extraction Complete" in result.output or "patient" in result.output.lower()

    def test_extract_from_file_with_real_api(self, api_key: str | None) -> None:
        """E2E: Extract from file using real Synthetic API."""
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set")

        transcript = "Patient David Martinez presents with chest pain. Started on aspirin 325mg."

        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(transcript)
            temp_path = f.name

        try:
            result = runner.invoke(app, ["extract", "--file", temp_path], env={"SYNTHETIC_API_KEY": api_key})

            print(f"\nExit code: {result.exit_code}")
            print(f"Output:\n{result.output}")

            assert result.exit_code == 0
            assert "Extraction Complete" in result.output or "medications" in result.output.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_extract_without_api_key_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """E2E: CLI should fail gracefully without API key."""
        # Mock the _check_api_key function to return None
        import cli.extract as extract_module

        original_check = extract_module._check_api_key
        extract_module._check_api_key = lambda: None

        try:
            result = runner.invoke(app, ["extract", "--text", "Patient came in yesterday."])

            assert result.exit_code != 0
            assert "API Key" in result.output or "SYNTHETIC_API_KEY" in result.output
        finally:
            extract_module._check_api_key = original_check

    def test_extract_outputs_to_file(self, api_key: str | None) -> None:
        """E2E: Extract and save to output file."""
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set")

        transcript = "Patient has fever and started on antibiotics yesterday."

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = runner.invoke(
                app, ["extract", "--text", transcript, "--output", output_path], env={"SYNTHETIC_API_KEY": api_key}
            )

            print(f"\nExit code: {result.exit_code}")
            print(f"Output:\n{result.output}")

            assert result.exit_code == 0
            assert Path(output_path).exists()

            # Verify JSON was written
            import json

            data = json.loads(Path(output_path).read_text())
            assert "confidence" in data
        finally:
            Path(output_path).unlink(missing_ok=True)
