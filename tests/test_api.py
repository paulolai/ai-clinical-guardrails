from datetime import date, datetime
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "emr_integration" in response.json()


def test_verify_success() -> None:
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
    response = client.post("/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_safe_to_file"] is True


@patch("src.api.emr_client.get_patient_profile")
@patch("src.api.emr_client.get_latest_encounter")
def test_verify_fhir_integrated(mock_encounter: Any, mock_patient: Any) -> None:
    # Setup mock FHIR data
    from src.models import EMRContext, PatientProfile

    mock_patient.return_value = PatientProfile(
        patient_id="F123", first_name="Fhir", last_name="User", dob=date(1980, 1, 1)
    )
    mock_encounter.return_value = EMRContext(
        visit_id="E1",
        patient_id="F123",
        admission_date=datetime(2024, 1, 1),
        attending_physician="Mock",
        raw_notes="",
    )

    payload = {
        "ai_output": {
            "summary_text": "Patient seen on 2024-01-01.",
            "extracted_dates": ["2024-01-01"],
        }
    }

    response = client.post("/verify/fhir/F123", json=payload)
    assert response.status_code == 200
    assert response.json()["is_safe_to_file"] is True
    mock_patient.assert_called_once_with("F123")


@patch("src.api.emr_client.get_patient_profile")
def test_verify_fhir_not_found(mock_patient: Any) -> None:
    mock_patient.side_effect = ValueError("Patient not found")
    payload = {"ai_output": {"summary_text": "text", "extracted_dates": []}}

    response = client.post("/verify/fhir/MISSING", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
