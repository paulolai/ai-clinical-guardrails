"""Performance benchmarks for the Clinical Guardrails API.

Measures latency for key endpoints:
- /verify (manual verification)
- /verify/fhir/{id} (FHIR-integrated verification)
- /extract (extraction + verification)

Run with: uv run pytest tests/benchmarks/test_performance.py -v
"""

from datetime import date, datetime
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.models import EMRContext, PatientProfile

client = TestClient(app)

# Sample data for benchmarking
SAMPLE_PATIENT = PatientProfile(
    patient_id="BENCH001",
    first_name="Bench",
    last_name="Mark",
    dob=date(1980, 1, 1),
)

SAMPLE_CONTEXT = EMRContext(
    visit_id="V-BENCH-001",
    patient_id="BENCH001",
    admission_date=datetime(2024, 2, 22, 10, 0, 0),
    attending_physician="Dr. Benchmark",
    raw_notes="Patient presents with chest pain.",
)

SAMPLE_TRANSCRIPT = """
Patient came in yesterday with chest pain. Started on Lisinopril 10mg daily.
Follow up in two weeks. Blood pressure was elevated at 150/90.
"""


@pytest.mark.benchmark
class TestVerificationBenchmarks:
    """Benchmarks for verification endpoints."""

    def test_verify_manual_latency(self, benchmark: Any) -> None:
        """Benchmark manual verification endpoint latency."""
        payload = {
            "patient": {
                "patient_id": "P001",
                "first_name": "John",
                "last_name": "Smith",
                "dob": "1990-01-01",
            },
            "context": {
                "visit_id": "V100",
                "patient_id": "P001",
                "admission_date": "2024-02-01T10:00:00",
                "attending_physician": "Dr. House",
                "raw_notes": "Note.",
            },
            "ai_output": {
                "summary_text": "Patient seen on 2024-02-01.",
                "extracted_dates": ["2024-02-01"],
            },
        }

        def verify_request() -> dict[str, Any]:
            response = client.post("/verify", json=payload)
            assert response.status_code == 200
            return response.json()

        result = benchmark(verify_request)
        assert result["is_safe_to_file"] is True

    @patch("src.api.emr_client.get_patient_profile")
    @patch("src.api.emr_client.get_latest_encounter")
    def test_verify_fhir_latency(self, mock_encounter: Any, mock_patient: Any, benchmark: Any) -> None:
        """Benchmark FHIR-integrated verification endpoint latency."""
        mock_patient.return_value = SAMPLE_PATIENT
        mock_encounter.return_value = SAMPLE_CONTEXT

        payload = {
            "ai_output": {
                "summary_text": "Patient seen on 2024-02-22.",
                "extracted_dates": ["2024-02-22"],
            }
        }

        def verify_fhir_request() -> dict[str, Any]:
            response = client.post("/verify/fhir/BENCH001", json=payload)
            assert response.status_code == 200
            return response.json()

        result = benchmark(verify_fhir_request)
        assert result["is_safe_to_file"] is True


@pytest.mark.benchmark
@pytest.mark.component
class TestExtractionBenchmarks:
    """Benchmarks for extraction endpoint."""

    @patch("src.api.get_verification_workflow")
    def test_extract_endpoint_latency(
        self,
        mock_get_workflow: Any,
        benchmark: Any,
    ) -> None:
        """Benchmark extraction + verification endpoint latency."""
        from src.extraction.models import (
            ExtractedDiagnosis,
            ExtractedMedication,
            ExtractedTemporalExpression,
            MedicationStatus,
            StructuredExtraction,
            TemporalType,
        )
        from src.models import Result, VerificationResult

        # Create mock workflow instance
        mock_workflow = mock_get_workflow.return_value
        mock_workflow.verify_patient_documentation.return_value = Result.success(
            VerificationResult(
                is_safe_to_file=True,
                score=0.95,
                alerts=[],
            )
        )
        mock_workflow.get_last_extraction.return_value = StructuredExtraction(
            patient_name="Bench Mark",
            medications=[
                ExtractedMedication(
                    name="Lisinopril",
                    dosage="10mg",
                    status=MedicationStatus.STARTED,
                    confidence=0.95,
                )
            ],
            diagnoses=[
                ExtractedDiagnosis(
                    text="Chest pain",
                    confidence=0.92,
                )
            ],
            temporal_expressions=[
                ExtractedTemporalExpression(
                    text="yesterday",
                    type=TemporalType.RELATIVE_DATE,
                    normalized_date=date(2024, 2, 21),
                    confidence=0.88,
                ),
                ExtractedTemporalExpression(
                    text="two weeks",
                    type=TemporalType.DURATION,
                    confidence=0.85,
                ),
            ],
            visit_type="acute_complaint",
            confidence=0.91,
        )

        payload = {
            "patient_id": "BENCH001",
            "transcript": SAMPLE_TRANSCRIPT,
            "reference_date": "2024-02-22",
        }

        def extract_request() -> dict[str, Any]:
            response = client.post("/extract", json=payload)
            assert response.status_code == 200
            return response.json()

        result = benchmark(extract_request)
        assert result["is_safe_to_file"] is True
        assert "extraction" in result
        assert "processing_time_ms" in result


@pytest.mark.benchmark
def test_health_endpoint_latency(benchmark: Any) -> None:
    """Benchmark health check endpoint latency (baseline)."""

    def health_request() -> dict[str, Any]:
        response = client.get("/health")
        assert response.status_code == 200
        return response.json()

    result = benchmark(health_request)
    assert result["status"] == "operational"


class TestBenchmarkRequirements:
    """Verify benchmark requirements are met."""

    def test_extract_response_structure(self) -> None:
        """Verify /extract endpoint returns expected structure."""
        from src.extraction.models import (
            ExtractedDiagnosis,
            ExtractedMedication,
            ExtractedTemporalExpression,
            MedicationStatus,
            StructuredExtraction,
            TemporalType,
        )
        from src.models import Result, VerificationResult

        with patch("src.api.get_verification_workflow") as mock_get_workflow:
            mock_workflow = mock_get_workflow.return_value
            mock_workflow.verify_patient_documentation.return_value = Result.success(
                VerificationResult(is_safe_to_file=True, score=0.95, alerts=[])
            )
            mock_workflow.get_last_extraction.return_value = StructuredExtraction(
                patient_name="Test",
                medications=[
                    ExtractedMedication(
                        name="Aspirin",
                        status=MedicationStatus.ACTIVE,
                        confidence=0.9,
                    )
                ],
                diagnoses=[ExtractedDiagnosis(text="Headache", confidence=0.85)],
                temporal_expressions=[
                    ExtractedTemporalExpression(
                        text="today",
                        type=TemporalType.RELATIVE_DATE,
                        confidence=0.9,
                    )
                ],
                visit_type="routine",
                confidence=0.88,
            )

            payload = {
                "patient_id": "TEST001",
                "transcript": "Patient has headache today.",
            }
            response = client.post("/extract", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "patient_id" in data
            assert "transcript" in data
            assert "extraction" in data
            assert "verification" in data
            assert "is_safe_to_file" in data
            assert "processing_time_ms" in data

            # Check extraction structure
            extraction = data["extraction"]
            assert "medications" in extraction
            assert "diagnoses" in extraction
            assert "temporal_expressions" in extraction
            assert "visit_type" in extraction
