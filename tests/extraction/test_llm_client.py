"""Tests for SyntheticLLMClient."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.extraction.llm_client import SyntheticLLMClient


class TestSyntheticLLMClient:
    """Tests for SyntheticLLMClient."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        client = SyntheticLLMClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == SyntheticLLMClient.DEFAULT_MODEL

    def test_init_with_custom_model(self) -> None:
        """Test initialization with custom model."""
        client = SyntheticLLMClient(
            api_key="test-key",
            model="custom-model",
        )
        assert client.model == "custom-model"

    def test_init_without_api_key_raises(self) -> None:
        """Test that initialization fails without API key."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="Synthetic API key required"),
        ):
            SyntheticLLMClient()

    def test_init_from_env(self) -> None:
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"SYNTHETIC_API_KEY": "env-key"}):
            client = SyntheticLLMClient()
            assert client.api_key == "env-key"

    @pytest.mark.asyncio
    async def test_complete_success(self) -> None:
        """Test successful completion call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"test": "data"}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.extraction.llm_client.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = mock_client
            client = SyntheticLLMClient(api_key="test-key")

            result = await client.complete("Test prompt")

            assert result == '{"test": "data"}'
            mock_client.chat.completions.create.assert_called_once()

            # Verify JSON mode is used
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["response_format"]["type"] == "json_object"

    @pytest.mark.asyncio
    async def test_complete_empty_response_raises(self) -> None:
        """Test that empty response raises ValueError."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.extraction.llm_client.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = mock_client
            client = SyntheticLLMClient(api_key="test-key")

            with pytest.raises(ValueError, match="empty response"):
                await client.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()

        with patch("src.extraction.llm_client.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = mock_client

            async with SyntheticLLMClient(api_key="test-key") as client:
                assert isinstance(client, SyntheticLLMClient)

            mock_client.close.assert_called_once()

    # Property-based negative and boundary tests
    @given(
        api_key=st.text(min_size=1, max_size=100),
        model=st.text(min_size=1, max_size=50) | st.just(None),
    )
    def test_init_with_various_api_keys(self, api_key: str, model: str | None) -> None:
        """Property: Should accept any non-empty API key and any model name."""
        kwargs: dict[str, Any] = {"api_key": api_key}
        if model is not None:
            kwargs["model"] = model

        client = SyntheticLLMClient(**kwargs)
        assert client.api_key == api_key
        if model:
            assert client.model == model

    @given(empty_key=st.just(""))
    def test_init_rejects_empty_api_keys(self, empty_key: str) -> None:
        """Property: Empty string API keys should be rejected (falls back to env)."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="Synthetic API key required"),
        ):
            SyntheticLLMClient(api_key=empty_key)

    @pytest.mark.asyncio
    @given(
        prompt=st.text(min_size=0, max_size=10000),
        temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        max_tokens=st.integers(min_value=1, max_value=4096),
    )
    async def test_complete_handles_various_prompts(self, prompt: str, temperature: float, max_tokens: int) -> None:
        """Property: Should handle prompts of various lengths and parameters."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "ok"}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.extraction.llm_client.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = mock_client
            client = SyntheticLLMClient(api_key="test-key")

            result = await client.complete(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            assert isinstance(result, str)
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["temperature"] == temperature
            assert call_args.kwargs["max_tokens"] == max_tokens

    @pytest.mark.asyncio
    @given(
        invalid_json=st.text(min_size=1).filter(lambda x: "{" not in x),
    )
    async def test_complete_preserves_invalid_json(self, invalid_json: str) -> None:
        """Property: LLM client should return raw content even if not valid JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = invalid_json

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.extraction.llm_client.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = mock_client
            client = SyntheticLLMClient(api_key="test-key")

            result = await client.complete("test")

            assert result == invalid_json
