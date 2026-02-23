"""Tests for LLM extraction service."""


def test_llm_service_exists() -> None:
    """Test that LLM service can be imported."""
    from pwa.backend.services.extraction_service import LLMService

    assert LLMService is not None


def test_llm_extract_method() -> None:
    """Test that LLMService has extract method."""
    from pwa.backend.services.extraction_service import LLMService

    service = LLMService(model_name="llama-3.1-8b")
    assert hasattr(service, "extract")
    assert callable(service.extract)
