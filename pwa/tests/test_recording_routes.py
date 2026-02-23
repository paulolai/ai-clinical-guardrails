# pwa/tests/test_recording_routes.py
import pytest
from fastapi.testclient import TestClient

from pwa.backend.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_create_recording_endpoint(client: TestClient) -> None:
    """Test creating a recording via API."""
    response = client.post("/api/v1/recordings", json={"patient_id": "patient-123", "duration_seconds": 120})

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "patient-123"
    assert data["duration_seconds"] == 120
    assert "id" in data


def test_get_recording_endpoint(client: TestClient) -> None:
    """Test getting a recording by ID."""
    # Create first
    create_response = client.post("/api/v1/recordings", json={"patient_id": "patient-123", "duration_seconds": 120})
    recording_id = create_response.json()["id"]

    # Get
    response = client.get(f"/api/v1/recordings/{recording_id}")
    assert response.status_code == 200
    assert response.json()["id"] == recording_id


def test_get_nonexistent_recording(client: TestClient) -> None:
    """Test getting a recording that doesn't exist."""
    response = client.get("/api/v1/recordings/123e4567-e89b-12d3-a456-426614174000")
    assert response.status_code == 404


def test_list_recordings(client: TestClient) -> None:
    """Test listing recordings for the current clinician."""
    # Create some recordings
    client.post("/api/v1/recordings", json={"patient_id": "patient-1", "duration_seconds": 60})
    client.post("/api/v1/recordings", json={"patient_id": "patient-2", "duration_seconds": 120})

    # List recordings
    response = client.get("/api/v1/recordings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_list_recordings_with_status_filter(client: TestClient) -> None:
    """Test listing recordings with status filter."""
    # Create a recording
    client.post("/api/v1/recordings", json={"patient_id": "patient-1", "duration_seconds": 60})

    # List pending recordings
    response = client.get("/api/v1/recordings?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(r["status"] == "pending" for r in data)
