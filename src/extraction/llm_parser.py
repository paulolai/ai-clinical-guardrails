"""LLM-based clinical dictation parser.

Uses a language model to extract structured data from unstructured
transcripts, handling messy, real-world clinical dictation.
"""

import json
from datetime import date
from typing import Any

from src.extraction.llm_client import LLMClient, SyntheticLLMClient
from src.extraction.models import (
    ExtractedDiagnosis,
    ExtractedMedication,
    ExtractedTemporalExpression,
    MedicationStatus,
    StructuredExtraction,
    TemporalType,
)
from src.extraction.temporal import TemporalResolver

EXTRACTION_PROMPT_TEMPLATE = """You are a clinical data extraction assistant.
Parse unstructured clinical dictation and extract structured information.

Extract the following from the clinical transcript below. Return ONLY a JSON object.

Transcript:
{transcript}

Reference Date: {reference_date}

Return this JSON structure:
{{
  "patient_name": "extracted name or null",
  "patient_age": "age or null",
  "visit_type": "follow-up|acute-complaint|routine-check|post-operative|well-child-check|urgent-same-day|null",
  "confidence": 0.0-1.0,
  "extraction_notes": "any ambiguities",
  "medications": [
    {{
      "name": "medication name",
      "dosage": "dosage or null",
      "frequency": "frequency or null",
      "route": "route or null",
      "status": "started|stopped|continued|increased|decreased|unknown",
      "confidence": 0.0-1.0,
      "raw_text": "exact text from transcript"
    }}
  ],
  "diagnoses": [
    {{
      "condition": "condition name",
      "icd10_code": "ICD-10 code or null",
      "confidence": 0.0-1.0,
      "raw_text": "exact text from transcript"
    }}
  ],
  "temporal_expressions": [
    {{
      "text": "exact text from transcript",
      "interpretation": "what this likely means",
      "confidence": 0.0-1.0
    }}
  ],
  "vital_signs": [
    {{
      "type": "blood-pressure|temperature|heart-rate|weight|height|respiratory-rate",
      "value": "value with units",
      "raw_text": "exact text from transcript"
    }}
  ],
  "procedures": [
    {{
      "name": "procedure name",
      "date_description": "when it occurred or null",
      "raw_text": "exact text from transcript"
    }}
  ],
  "protocol_triggers": ["sepsis|stroke|MI|trauma"],
  "follow_up": "follow-up instructions or null",
  "additional_context": "other relevant information"
}}

Guidelines:
- Do not hallucinate information not in the transcript
- Mark unclear information with lower confidence
- Include exact raw text for verification
- For Australian context: recognise PBS medications, MBS terminology
- Confidence: 0.9+ for clear statements, 0.5-0.7 for ambiguous, <0.5 for uncertain"""


MEDICATION_STATUS_MAPPING = {
    "started": MedicationStatus.STARTED,
    "new": MedicationStatus.STARTED,
    "began": MedicationStatus.STARTED,
    "initiated": MedicationStatus.STARTED,
    "stopped": MedicationStatus.DISCONTINUED,
    "discontinued": MedicationStatus.DISCONTINUED,
    "ceased": MedicationStatus.DISCONTINUED,
    "continued": MedicationStatus.ACTIVE,
    "ongoing": MedicationStatus.ACTIVE,
    "unchanged": MedicationStatus.ACTIVE,
    "increased": MedicationStatus.INCREASED,
    "upped": MedicationStatus.INCREASED,
    "raised": MedicationStatus.INCREASED,
    "decreased": MedicationStatus.DECREASED,
    "reduced": MedicationStatus.DECREASED,
    "lowered": MedicationStatus.DECREASED,
}


class LLMTranscriptParser:
    """Parse clinical dictation using LLM-based extraction.

    Unlike rule-based parsers, this handles messy, unstructured,
    conversational clinical dictation by using a language model
    to understand context and extract meaning.
    """

    def __init__(
        self,
        llm_client: LLMClient | Any | None = None,
        reference_date: date | None = None,
    ):
        """Initialize LLM parser.

        Args:
            llm_client: LLM client for API calls. If None, creates SyntheticLLMClient.
                       Can also accept a mock client for testing.
            reference_date: Base date for temporal calculations
        """
        self.llm_client = llm_client or SyntheticLLMClient()
        self.temporal_resolver = TemporalResolver(reference_date)

    async def parse(self, text: str) -> StructuredExtraction:
        """Parse transcript text into structured extraction using LLM.

        Args:
            text: Clinical dictation text (can be messy, conversational)

        Returns:
            StructuredExtraction with all extracted fields
        """
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            transcript=text, reference_date=self.temporal_resolver.reference_date.isoformat()
        )

        try:
            llm_response = await self._call_llm(prompt)
            extraction_data = self._parse_llm_response(llm_response)
        except Exception as e:
            return self._create_fallback_extraction(text, str(e))

        structured = self._convert_to_structured(extraction_data, text)

        # Resolve temporal expressions
        temporal_expressions = self.temporal_resolver.resolve(text)
        temporal_expressions = self._merge_temporal_expressions(
            temporal_expressions, extraction_data.get("temporal_expressions", [])
        )

        return StructuredExtraction(
            patient_name=structured.get("patient_name"),
            patient_age=structured.get("patient_age"),
            visit_type=structured.get("visit_type"),
            temporal_expressions=temporal_expressions,
            medications=structured.get("medications", []),
            diagnoses=structured.get("diagnoses", []),
            vital_signs=structured.get("vital_signs", []),
            confidence=structured.get("overall_confidence", 0.5),
        )

    async def _call_llm(self, prompt: str, timeout: float = 120.0) -> str:
        """Call LLM with prompt and retry logic.

        Args:
            prompt: The formatted extraction prompt
            timeout: Request timeout in seconds (default 120s for clinical extraction)

        Returns:
            JSON string response from LLM

        Raises:
            Exception: If LLM call fails after all retries
        """
        return await self.llm_client.complete(prompt, timeout=timeout)

    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """Parse LLM JSON response."""
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result: dict[str, Any] = json.loads(cleaned)
        return result

    def _convert_to_structured(self, data: dict[str, Any], raw_text: str) -> dict[str, Any]:
        """Convert LLM output to structured extraction format."""
        result = {
            "patient_name": data.get("patient_name") or None,
            "patient_age": data.get("patient_age") or None,
            "visit_type": self._normalise_visit_type(data.get("visit_type")),
            "overall_confidence": data.get("confidence", 0.5),
        }

        # Convert medications
        medications = []
        for med in data.get("medications", []):
            medications.append(
                ExtractedMedication(
                    name=med.get("name", ""),
                    dosage=med.get("dosage"),
                    frequency=med.get("frequency"),
                    route=med.get("route"),
                    status=self._parse_medication_status(med.get("status", "unknown")),
                    confidence=med.get("confidence", 0.5),
                )
            )
        result["medications"] = medications

        # Convert diagnoses
        diagnoses = []
        for diag in data.get("diagnoses", []):
            diagnoses.append(
                ExtractedDiagnosis(
                    text=diag.get("condition", ""),
                    icd10_code=diag.get("icd10_code"),
                    confidence=diag.get("confidence", 0.5),
                )
            )
        result["diagnoses"] = diagnoses

        # Convert vital signs
        vital_signs = []
        for vs in data.get("vital_signs", []):
            vital_signs.append(
                {
                    "type": vs.get("type", ""),
                    "value": vs.get("value", ""),
                    "raw_text": vs.get("raw_text", ""),
                }
            )
        result["vital_signs"] = vital_signs

        return result

    def _merge_temporal_expressions(
        self, resolved_expressions: list[ExtractedTemporalExpression], llm_temporal: list[dict[str, Any]]
    ) -> list[ExtractedTemporalExpression]:
        """Merge rule-based temporal resolution with LLM insights."""
        merged = list(resolved_expressions)
        existing_texts = {e.text.lower() for e in merged}

        for temp in llm_temporal:
            text = temp.get("text", "")
            if text.lower() not in existing_texts:
                merged.append(
                    ExtractedTemporalExpression(
                        text=text,
                        type=TemporalType.AMBIGUOUS,
                        normalized_date=None,
                        confidence=temp.get("confidence", 0.4),
                        note=temp.get("interpretation"),
                    )
                )

        return merged

    def _normalise_visit_type(self, visit_type: str | None) -> str | None:
        """Normalise visit type string."""
        if not visit_type:
            return None

        mapping = {
            "follow-up": "follow-up",
            "follow up": "follow-up",
            "review": "follow-up",
            "acute-complaint": "acute_complaint",
            "acute complaint": "acute_complaint",
            "routine-check": "routine_check",
            "routine check": "routine_check",
            "annual": "routine_check",
            "post-operative": "post-operative",
            "post op": "post-operative",
            "well-child-check": "well_child_check",
            "well child": "well_child_check",
            "urgent-same-day": "urgent_same_day",
            "urgent": "urgent_same_day",
            "same day": "urgent_same_day",
        }

        normalized = visit_type.lower().strip()
        return mapping.get(normalized, normalized)

    def _parse_medication_status(self, status: str) -> MedicationStatus:
        """Parse medication status string to enum."""
        return MEDICATION_STATUS_MAPPING.get(status.lower().strip(), MedicationStatus.UNKNOWN)

    def _create_fallback_extraction(self, raw_text: str, error_message: str) -> StructuredExtraction:
        """Create low-confidence extraction when LLM fails."""
        return StructuredExtraction(
            patient_name=None,
            patient_age=None,
            visit_type=None,
            temporal_expressions=[],
            medications=[],
            diagnoses=[],
            vital_signs=[],
            confidence=0.1,
        )
