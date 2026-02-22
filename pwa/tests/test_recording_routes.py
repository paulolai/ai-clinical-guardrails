# pwa/tests/test_recording_routes.py
from fastapi.testclient import TestClient

from pwa.backend.main import app

client = TestClient(app)


def test_create_recording_endpoint() -> None:
    """Test creating a recording via API."""
    response = client.post("/api/v1/recordings", json={"patient_id": "patient-123", "duration_seconds": 120})

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["duration_seconds"] == 120
    assert "id" in data


def test_get_recording_endpoint() -> None:
    """Test getting a recording by ID."""
    # Create first
    create_response = client.post("/api/v1/recordings", json={"patient_id": "patient-123", "duration_seconds": 120})
    recording_id = create_response.json()["id"]

    # Get
    response = client.get(f"/api/v1/recordings/{recording_id}")
    assert response.status_code == 200
    assert response.json()["id"] == recording_id


def test_get_nonexistent_recording() -> None:
    """Test getting a recording that doesn't exist."""
    response = client.get("/api/v1/recordings/123e4567-e89b-12d3-a456-426614174000")
    assert response.status_code == 404
