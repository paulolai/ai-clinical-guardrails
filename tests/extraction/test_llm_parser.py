"""Tests for LLMTranscriptParser."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.extraction.llm_parser import LLMTranscriptParser
from src.extraction.models import (
    MedicationStatus,
    StructuredExtraction,
)


class TestLLMTranscriptParser:
    """Tests for LLMTranscriptParser."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock()
        return client

    @pytest.fixture
    def sample_llm_response(self) -> dict[str, object]:
        """Sample LLM JSON response."""
        return {
            "patient_name": "John Doe",
            "patient_age": "45",
            "visit_type": "follow-up",
            "confidence": 0.95,
            "extraction_notes": "Clear dictation",
            "medications": [
                {
                    "name": "Lisinopril",
                    "dosage": "10mg",
                    "frequency": "daily",
                    "route": "oral",
                    "status": "started",
                    "confidence": 0.9,
                    "raw_text": "started Lisinopril 10mg daily",
                }
            ],
            "diagnoses": [
                {
                    "condition": "hypertension",
                    "icd10_code": "I10",
                    "confidence": 0.85,
                    "raw_text": "hypertension",
                }
            ],
            "temporal_expressions": [
                {
                    "text": "yesterday",
                    "interpretation": "2024-01-14",
                    "confidence": 0.9,
                }
            ],
            "vital_signs": [
                {
                    "type": "blood-pressure",
                    "value": "120/80",
                    "raw_text": "BP 120/80",
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_parse_success(
        self,
        mock_llm_client: MagicMock,
        sample_llm_response: dict[str, object],
    ) -> None:
        """Test successful parsing of transcript."""
        mock_llm_client.complete.return_value = json.dumps(sample_llm_response)

        parser = LLMTranscriptParser(
            llm_client=mock_llm_client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse("Patient started Lisinopril yesterday.")

        assert isinstance(result, StructuredExtraction)
        assert result.patient_name == "John Doe"
        assert result.visit_type == "follow-up"
        assert result.confidence == 0.95
        assert len(result.medications) == 1
        assert result.medications[0].name == "Lisinopril"
        assert len(result.diagnoses) == 1

    @pytest.mark.asyncio
    async def test_parse_with_llm_failure(self, mock_llm_client: MagicMock) -> None:
        """Test fallback extraction when LLM fails."""
        mock_llm_client.complete.side_effect = Exception("API error")

        parser = LLMTranscriptParser(
            llm_client=mock_llm_client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse("Some transcript text")

        assert isinstance(result, StructuredExtraction)
        assert result.confidence == 0.1  # Low confidence fallback
        assert result.patient_name is None
        assert len(result.medications) == 0

    @pytest.mark.asyncio
    async def test_parse_with_temporal_expressions(
        self,
        mock_llm_client: MagicMock,
        sample_llm_response: dict[str, object],
    ) -> None:
        """Test that temporal expressions are resolved correctly."""
        mock_llm_client.complete.return_value = json.dumps(sample_llm_response)

        parser = LLMTranscriptParser(
            llm_client=mock_llm_client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse("Patient was seen yesterday.")

        # Should have temporal expressions from both rule-based and LLM
        assert len(result.temporal_expressions) > 0

    def test_medication_status_parsing(self) -> None:
        """Test medication status string parsing."""
        parser = LLMTranscriptParser()

        assert parser._parse_medication_status("started") == MedicationStatus.STARTED
        assert parser._parse_medication_status("stopped") == MedicationStatus.DISCONTINUED
        assert parser._parse_medication_status("continued") == MedicationStatus.ACTIVE
        assert parser._parse_medication_status("increased") == MedicationStatus.INCREASED
        assert parser._parse_medication_status("decreased") == MedicationStatus.DECREASED
        assert parser._parse_medication_status("unknown") == MedicationStatus.UNKNOWN

    def test_visit_type_normalization(self) -> None:
        """Test visit type string normalization."""
        parser = LLMTranscriptParser()

        assert parser._normalise_visit_type("follow up") == "follow-up"
        assert parser._normalise_visit_type("routine check") == "routine_check"
        assert parser._normalise_visit_type("urgent") == "urgent_same_day"
        assert parser._normalise_visit_type(None) is None

    @pytest.mark.asyncio
    async def test_parse_with_real_synthetic_client(self) -> None:
        """Integration test - only runs with real API key.

        Set SYNTHETIC_API_KEY env var to run this test.
        """
        import os

        api_key = os.environ.get("SYNTHETIC_API_KEY")
        if not api_key:
            pytest.skip("SYNTHETIC_API_KEY not set")

        from src.extraction.llm_client import SyntheticLLMClient

        client = SyntheticLLMClient(api_key=api_key)
        parser = LLMTranscriptParser(
            llm_client=client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse("Mrs. Johnson came in yesterday for follow-up. Started on Lisinopril 10mg daily.")

        assert isinstance(result, StructuredExtraction)
        assert result.patient_name is not None or result.confidence < 0.5
