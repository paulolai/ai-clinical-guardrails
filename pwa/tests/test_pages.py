from fastapi.testclient import TestClient

from pwa.backend.main import app

client = TestClient(app)


def test_home_page() -> None:
    """Test that the home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Clinical Transcription" in response.text
