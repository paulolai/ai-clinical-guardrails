from fastapi.testclient import TestClient

from pwa.backend.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test that the PWA API health endpoint works."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "pwa" in response.json()["components"]
