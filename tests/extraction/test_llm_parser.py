"""Tests for LLMTranscriptParser."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.extraction.llm_parser import MEDICATION_STATUS_MAPPING, LLMTranscriptParser
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


# Property-based boundary and edge case tests
class TestLLMParserBoundaryCases:
    """Property-based tests for boundary conditions without hardcoded values."""

    @pytest.mark.asyncio
    @given(
        transcript=st.text(
            min_size=0,
            max_size=100000,  # Very large transcripts
            alphabet=st.characters(
                whitelist_categories=("L", "N", "P", "Z"),  # Letters, numbers, punctuation, separators
            ),
        ),
    )
    async def test_parse_handles_various_transcript_lengths(self, transcript: str) -> None:
        """Property: Parser should handle transcripts from empty to very large."""
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value='{"patient_name": null, "confidence": 0.5}')

        parser = LLMTranscriptParser(
            llm_client=mock_client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse(transcript)

        # Should always return a valid extraction
        assert isinstance(result, StructuredExtraction)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    @given(
        ref_date=st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31)),
    )
    async def test_parse_handles_various_reference_dates(self, ref_date: date) -> None:
        """Property: Parser should work with any valid reference date."""
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value='{"patient_name": "Test", "confidence": 0.8}')

        parser = LLMTranscriptParser(
            llm_client=mock_client,
            reference_date=ref_date,
        )

        result = await parser.parse("Patient seen yesterday.")

        assert isinstance(result, StructuredExtraction)

    @given(
        status_text=st.text(min_size=0, max_size=100),
    )
    def test_medication_status_handles_unexpected_values(self, status_text: str) -> None:
        """Property: Unknown medication statuses should map to UNKNOWN."""
        parser = LLMTranscriptParser()

        result = parser._parse_medication_status(status_text)

        # If it's not one of the known values, it should be UNKNOWN
        if status_text.lower() not in MEDICATION_STATUS_MAPPING:
            assert result == MedicationStatus.UNKNOWN

    @given(
        visit_type=st.one_of(
            st.none(),
            st.text(min_size=0, max_size=200),
        ),
    )
    def test_visit_type_normalization_boundaries(self, visit_type: str | None) -> None:
        """Property: Visit type normalization should handle any input gracefully."""
        parser = LLMTranscriptParser()

        result = parser._normalise_visit_type(visit_type)

        # Should never crash and should return None or a string
        assert result is None or isinstance(result, str)

    @pytest.mark.asyncio
    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    async def test_parse_preserves_confidence_bounds(self, confidence: float) -> None:
        """Property: Confidence should always be within [0, 1] range."""
        mock_response = {
            "patient_name": "Test Patient",
            "confidence": confidence,
            "medications": [],
            "diagnoses": [],
            "temporal_expressions": [],
            "vital_signs": [],
        }

        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value=json.dumps(mock_response))

        parser = LLMTranscriptParser(
            llm_client=mock_client,
            reference_date=date(2024, 1, 15),
        )

        result = await parser.parse("Test transcript")

        assert 0.0 <= result.confidence <= 1.0
