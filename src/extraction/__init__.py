"""Voice Transcription Extraction Layer.

Converts clinician dictation into structured clinical data using LLM-based parsing.
"""

from src.extraction.llm_client import (
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    LLM_RETRY_INITIAL_WAIT_SECONDS,
    LLM_RETRY_MAX_ATTEMPTS,
    LLM_RETRY_MAX_WAIT_SECONDS,
    AzureOpenAILLMClient,
    LLMClient,
    OpenAILLMClient,
    SyntheticLLMClient,
    create_llm_client,
)
from src.extraction.llm_parser import LLMTranscriptParser
from src.extraction.models import (
    ExtractedDiagnosis,
    ExtractedMedication,
    ExtractedTemporalExpression,
    ExtractionResult,
    MedicationStatus,
    StructuredExtraction,
    TemporalType,
)
from src.extraction.temporal import TemporalResolver

__all__ = [
    # Configuration constants
    "DEFAULT_LLM_MAX_TOKENS",
    "DEFAULT_LLM_TEMPERATURE",
    "DEFAULT_LLM_TIMEOUT_SECONDS",
    "LLM_RETRY_INITIAL_WAIT_SECONDS",
    "LLM_RETRY_MAX_ATTEMPTS",
    "LLM_RETRY_MAX_WAIT_SECONDS",
    # Data models
    "ExtractedMedication",
    "ExtractedDiagnosis",
    "ExtractedTemporalExpression",
    "ExtractionResult",
    "StructuredExtraction",
    "MedicationStatus",
    "TemporalType",
    # Clients and parsers
    "LLMTranscriptParser",
    "LLMClient",
    "OpenAILLMClient",
    "AzureOpenAILLMClient",
    "SyntheticLLMClient",
    "create_llm_client",
    "TemporalResolver",
]
