"""Extraction service wrapper for LLM container."""

from typing import Any

import httpx

LLM_URL = "http://localhost:8003"


class LLMService:
    """Service for extracting clinical data using LLM."""

    def __init__(self, model_name: str = "llama-3.1-8b"):
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=LLM_URL, timeout=120.0)

    async def extract(self, transcript: str, patient_id: str) -> dict[str, Any]:
        """Extract structured data from transcript.

        Args:
            transcript: Clinical transcript text
            patient_id: Patient identifier

        Returns:
            dict with extracted medications, conditions, allergies
        """
        response = await self.client.post("/extract", json={"transcript": transcript, "patient_id": patient_id})

        if response.status_code != 200:
            raise Exception(f"Extraction failed: {response.text}")

        result = response.json()
        return {
            "medications": result.get("medications", []),
            "conditions": result.get("conditions", []),
            "allergies": result.get("allergies", []),
            "confidence": result.get("confidence", 0.0),
            "model": self.model_name,
        }

    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
