# pwa/tests/test_verification_service.py
"""Tests for verification service."""

from pwa.backend.services.verification_service import VerificationService


def test_verification_service_exists() -> None:
    """Test that service exists."""
    service = VerificationService()
    assert service is not None


def test_verify_valid_medication() -> None:
    """Test verification of valid medication."""
    service = VerificationService()
    data = {"medications": [{"name": "Metformin", "dosage": "500mg"}], "confidence": 0.9}

    result = service.verify(data)

    assert result["passed"] is True
    assert result["score"] > 0.7
