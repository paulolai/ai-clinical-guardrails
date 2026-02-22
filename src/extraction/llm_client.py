"""Abstract LLM client with multi-provider support.

Provides async interface to various LLM providers (OpenAI, Azure OpenAI, Synthetic)
for clinical data extraction from transcripts.
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    RateLimitError,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

# LLM Configuration Constants
# These can be overridden via environment variables for different deployment scenarios
DEFAULT_LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120.0"))
DEFAULT_LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4000"))
DEFAULT_LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))

# Retry Configuration
LLM_RETRY_MAX_ATTEMPTS = int(os.environ.get("LLM_RETRY_MAX_ATTEMPTS", "3"))
LLM_RETRY_MAX_WAIT_SECONDS = int(os.environ.get("LLM_RETRY_MAX_WAIT_SECONDS", "60"))
LLM_RETRY_INITIAL_WAIT_SECONDS = int(os.environ.get("LLM_RETRY_INITIAL_WAIT_SECONDS", "1"))

# Load secrets from .env.secrets file (not committed to git)
env_secrets_path = Path(".env.secrets")
if env_secrets_path.exists():
    load_dotenv(env_secrets_path)


class EmptyResponseError(Exception):
    """Raised when LLM returns an empty response."""

    pass


class LLMClient(ABC):
    """Abstract base class for LLM clients.

    All LLM provider implementations must inherit from this class
    and implement the complete() method.

    Example:
        >>> client = OpenAILLMClient()
        >>> response = await client.complete("Extract data from: Patient has fever...")
    """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        timeout: float = DEFAULT_LLM_TIMEOUT_SECONDS,
    ) -> str:
        """Send completion request to LLM.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Sampling temperature (0.0-1.0). Lower for more deterministic.
            max_tokens: Maximum tokens in response.

        Returns:
            JSON string response from LLM.

        Raises:
            Exception: If API call fails.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        pass

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()


class OpenAILLMClient(LLMClient):
    """Async LLM client using OpenAI API.

    Uses the official OpenAI SDK to extract structured clinical data
    from unstructured transcripts.

    Configuration:
        API key loaded from OPENAI_API_KEY environment variable
        or from .env.secrets file (preferred, not committed).

    Example:
        >>> client = OpenAILLMClient(model="gpt-4o")
        >>> response = await client.complete("Extract data from: Patient has fever...")
    """

    DEFAULT_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI LLM client.

        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            model: Model ID to use. Defaults to gpt-4o.
            base_url: Optional custom base URL for OpenAI-compatible APIs.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or create .env.secrets file with OPENAI_API_KEY=your_key"
            )

        self.model = model or self.DEFAULT_MODEL
        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncOpenAI(**client_kwargs)

    @retry(
        wait=wait_exponential_jitter(
            initial=LLM_RETRY_INITIAL_WAIT_SECONDS,
            max=LLM_RETRY_MAX_WAIT_SECONDS,
            jitter=2,
        ),
        stop=stop_after_attempt(LLM_RETRY_MAX_ATTEMPTS),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        timeout: float = DEFAULT_LLM_TIMEOUT_SECONDS,
    ) -> str:
        """Send completion request to OpenAI API with JSON mode enforcement.

        Automatically retries on transient failures (connection errors, timeouts, rate limits).
        Uses exponential backoff with jitter to avoid thundering herd.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Sampling temperature (0.0-1.0). Lower for more deterministic.
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds. Default 120s for clinical extractions.

        Returns:
            JSON string response from LLM.

        Raises:
            Exception: If API call fails after all retries.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            timeout=timeout,
        )

        content: str | None = response.choices[0].message.content
        if content is None:
            raise EmptyResponseError("LLM returned empty response")

        return content

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.close()


class AzureOpenAILLMClient(LLMClient):
    """Async LLM client using Azure OpenAI Service.

    Uses the Azure OpenAI SDK to extract structured clinical data
    from unstructured transcripts. Supports Azure's enterprise features
    like private endpoints and managed identity.

    Configuration:
        AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com/)
        AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
        AZURE_OPENAI_API_VERSION: API version (e.g., 2024-02-01)

    Example:
        >>> client = AzureOpenAILLMClient(
        ...     endpoint="https://your-resource.openai.azure.com/",
        ...     deployment="gpt-4o",
        ... )
        >>> response = await client.complete("Extract data from: Patient has fever...")
    """

    DEFAULT_API_VERSION = "2024-02-01"

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        """Initialize Azure OpenAI LLM client.

        Args:
            endpoint: Azure OpenAI endpoint URL. Defaults to AZURE_OPENAI_ENDPOINT env var.
            api_key: Azure OpenAI API key. Defaults to AZURE_OPENAI_API_KEY env var.
            deployment: Model deployment name. Defaults to AZURE_OPENAI_DEPLOYMENT env var.
            api_version: Azure API version. Defaults to AZURE_OPENAI_API_VERSION or 2024-02-01.

        Raises:
            ValueError: If required configuration is missing.
        """
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.deployment = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        self.api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", self.DEFAULT_API_VERSION)

        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint required. Set AZURE_OPENAI_ENDPOINT environment variable "
                "or create .env.secrets file with AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
            )

        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key required. Set AZURE_OPENAI_API_KEY environment variable "
                "or create .env.secrets file with AZURE_OPENAI_API_KEY=your_key"
            )

        if not self.deployment:
            raise ValueError(
                "Azure OpenAI deployment name required. Set AZURE_OPENAI_DEPLOYMENT environment variable "
                "or create .env.secrets file with AZURE_OPENAI_DEPLOYMENT=your-deployment"
            )

        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    @retry(
        wait=wait_exponential_jitter(
            initial=LLM_RETRY_INITIAL_WAIT_SECONDS,
            max=LLM_RETRY_MAX_WAIT_SECONDS,
            jitter=2,
        ),
        stop=stop_after_attempt(LLM_RETRY_MAX_ATTEMPTS),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def complete(
        self,
        prompt: str,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        timeout: float = DEFAULT_LLM_TIMEOUT_SECONDS,
    ) -> str:
        """Send completion request to Azure OpenAI API with JSON mode enforcement.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Sampling temperature (0.0-1.0). Lower for more deterministic.
            max_tokens: Maximum tokens in response.

        Returns:
            JSON string response from LLM.

        Raises:
            Exception: If API call fails.
        """
        assert self.deployment is not None, "Deployment must be set"
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            timeout=timeout,
        )

        content: str | None = response.choices[0].message.content
        if content is None:
            raise EmptyResponseError("LLM returned empty response")

        return content

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.close()


class SyntheticLLMClient(OpenAILLMClient):
    """Async LLM client using Synthetic API (OpenAI-compatible).

    Synthetic provides an OpenAI-compatible API. This client extends
    OpenAILLMClient with Synthetic-specific defaults.

    Configuration:
        SYNTHETIC_API_KEY: Your Synthetic API key

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
        api_key = api_key or os.environ.get("SYNTHETIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Synthetic API key required. Set SYNTHETIC_API_KEY environment variable "
                "or create .env.secrets file with SYNTHETIC_API_KEY=your_key"
            )

        super().__init__(
            api_key=api_key,
            model=model or self.DEFAULT_MODEL,
            base_url=self.BASE_URL,
        )


def create_llm_client(
    provider: str = "openai",
    **kwargs: Any,
) -> LLMClient:
    """Factory function to create LLM client based on provider.

    Args:
        provider: LLM provider name (openai, azure, synthetic).
        **kwargs: Additional arguments passed to the client constructor.

    Returns:
        Configured LLM client instance.

    Raises:
        ValueError: If provider is not supported.

    Example:
        >>> client = create_llm_client("openai", model="gpt-4o")
        >>> client = create_llm_client("azure", deployment="gpt-4o")
        >>> client = create_llm_client("synthetic", model="hf:nvidia/Kimi-K2.5-NVFP4")
    """
    provider = provider.lower()

    if provider == "openai":
        return OpenAILLMClient(**kwargs)
    elif provider == "azure":
        return AzureOpenAILLMClient(**kwargs)
    elif provider == "synthetic":
        return SyntheticLLMClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers: openai, azure, synthetic")
