"""Review service for orchestrating clinical note review workflows."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from src.engine import ComplianceEngine
from src.integrations.fhir.client import FHIRClient
from src.models import (
    AIGeneratedOutput,
    ClinicalNote,
    UnifiedReview,
    VerificationResult,
)

if TYPE_CHECKING:
    from src.extraction.models import StructuredExtraction


class ReviewServiceError(Exception):
    """Exception raised for errors in the ReviewService."""

    pass


class ReviewService:
    """Orchestrates the clinical note review workflow.

    This service coordinates between:
    - FHIR Client: Fetches patient data and encounter information
    - ComplianceEngine: Verifies AI-generated content against EMR data

    The workflow ensures that AI-generated clinical notes are validated
    against the source of truth (EMR) before being presented for review.
    """

    def __init__(self, fhir_client: FHIRClient):
        """Initialize the ReviewService.

        Args:
            fhir_client: Configured FHIR client for EMR data access
        """
        self.fhir_client = fhir_client

    async def create_review(self, note: ClinicalNote) -> UnifiedReview:
        """Create a unified review for a clinical note.

        Workflow:
        1. Fetch patient profile from FHIR
        2. Fetch latest encounter from FHIR
        3. Convert ClinicalNote to AIGeneratedOutput
        4. Run ComplianceEngine.verify()
        5. Build and return UnifiedReview

        Args:
            note: The AI-generated clinical note to review

        Returns:
            UnifiedReview containing the note, EMR context, and verification results

        Raises:
            ReviewServiceError: If FHIR data fetch fails
        """
        # 1. Fetch EMR data
        try:
            patient = await self.fhir_client.get_patient_profile(note.patient_id)
        except Exception as e:
            raise ReviewServiceError(f"Failed to fetch patient profile for {note.patient_id}: {e}") from e

        try:
            emr_context = await self.fhir_client.get_latest_encounter(note.patient_id)
        except Exception as e:
            raise ReviewServiceError(f"Failed to fetch encounter for patient {note.patient_id}: {e}") from e

        # 2. Convert note to AI output format
        ai_output = self._note_to_ai_output(note)

        # 3. Verify
        result = ComplianceEngine.verify(patient, emr_context, ai_output)

        # 4. Build unified review
        # If verification failed (critical alerts), we still return a review
        # but verification will reflect the failure state
        if result.is_success:
            verification = result.value
            assert verification is not None, "Result success must have a value"
        else:
            # Create a verification result indicating unsafe to file
            alerts = result.error if result.error else []
            verification = VerificationResult(
                is_safe_to_file=False,
                score=0.0,
                alerts=alerts,
            )

        return UnifiedReview(
            note=note,
            emr_context=emr_context,
            verification=verification,
            review_url=f"/review/{note.note_id}",
            created_at=datetime.now(),
        )

    def _note_to_ai_output(self, note: ClinicalNote) -> AIGeneratedOutput:
        """Convert ClinicalNote to AIGeneratedOutput for verification.

        This conversion extracts structured data from the note for
        compliance verification against EMR source of truth.

        Args:
            note: The clinical note to convert

        Returns:
            AIGeneratedOutput formatted for ComplianceEngine verification
        """
        extraction: StructuredExtraction = note.extraction

        # Build summary text from sections
        summary_parts = []
        for section_name, content in note.sections.items():
            summary_parts.append(f"{section_name}: {content}")
        summary_text = "\n".join(summary_parts)

        # Extract dates from temporal_expressions
        extracted_dates: list[date] = []
        for temp in extraction.temporal_expressions:
            if temp.normalized_date:
                extracted_dates.append(temp.normalized_date)

        # Extract diagnoses
        extracted_diagnoses: list[str] = [d.text for d in extraction.diagnoses]

        return AIGeneratedOutput(
            summary_text=summary_text,
            extracted_dates=extracted_dates,
            extracted_diagnoses=extracted_diagnoses,
            extracted_medications=extraction.medications,
            suggested_billing_codes=[],
            contains_pii=False,
        )
