"""LLM client for Synthetic API integration.

Provides async interface to Synthetic's OpenAI-compatible API
for clinical data extraction from transcripts.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load secrets from .env.secrets file (not committed to git)
env_secrets_path = Path(".env.secrets")
if env_secrets_path.exists():
    load_dotenv(env_secrets_path)


class SyntheticLLMClient:
    """Async LLM client using Synthetic API (OpenAI-compatible).

    Uses the OpenAI SDK with Synthetic's base URL to extract
    structured clinical data from unstructured transcripts.

    Configuration:
        API key loaded from SYNTHETIC_API_KEY environment variable
        or from .env.secrets file (preferred, not committed).

    Example:
        >>> client = SyntheticLLMClient(model="hf:nvidia/Kimi-K2.5-NVFP4")
        >>> response = await client.complete("Extract data from: Patient has fever...")
    """

    DEFAULT_MODEL = "hf:nvidia/Kimi-K2.5-NVFP4"
    BASE_URL = "https://api.synthetic.new/openai/v1"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize Synthetic LLM client.

        Args:
            api_key: Synthetic API key. Defaults to SYNTHETIC_API_KEY env var.
            model: Model ID to use. Defaults to hf:nvidia/Kimi-K2.5-NVFP4.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("SYNTHETIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Synthetic API key required. Set SYNTHETIC_API_KEY environment variable "
                "or create .env.secrets file with SYNTHETIC_API_KEY=your_key"
            )

        self.model = model or self.DEFAULT_MODEL
        self.client = AsyncOpenAI(
            base_url=self.BASE_URL,
            api_key=self.api_key,
        )

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> str:
        """Send completion request to LLM with JSON mode enforcement.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Sampling temperature (0.0-1.0). Lower for more deterministic.
            max_tokens: Maximum tokens in response.

        Returns:
            JSON string response from LLM.

        Raises:
            Exception: If API call fails.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},  # Enforce JSON output
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty response")

        return content

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.close()

    async def __aenter__(self) -> "SyntheticLLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()
