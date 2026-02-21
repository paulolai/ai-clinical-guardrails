"""Tests for SyntheticLLMClient."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
