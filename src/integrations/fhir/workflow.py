"""Integration workflow: Voice transcription → Extraction → FHIR → Verification.

This module provides the end-to-end workflow that:
1. Fetches patient context from FHIR
2. Extracts structured data from voice transcription
3. Verifies extraction against EMR source of truth
4. Returns verification result with alerts
"""

from datetime import date
from typing import TYPE_CHECKING

from src.engine import ComplianceEngine
from src.extraction.llm_parser import LLMTranscriptParser
from src.models import (
    AIGeneratedOutput,
    ComplianceAlert,
    ComplianceSeverity,
    EMRContext,
    PatientProfile,
    Result,
    VerificationResult,
)

from .client import FHIRClient

if TYPE_CHECKING:
    from src.extraction.models import StructuredExtraction


class VerificationWorkflowError(Exception):
    """Base error for verification workflow failures."""

    pass


class PatientNotFoundError(VerificationWorkflowError):
    """Patient not found in FHIR system."""

    pass


class ExtractionError(VerificationWorkflowError):
    """Failed to extract structured data from transcript."""

    pass


class VerificationWorkflow:
    """End-to-end workflow for verifying clinical documentation.

    Orchestrates the complete flow:
    FHIR Patient Data → Voice Extraction → Verification → Result
    """

    def __init__(
        self,
        fhir_client: FHIRClient | None = None,
        llm_parser: LLMTranscriptParser | None = None,
    ):
        """Initialize workflow with optional dependencies.

        Args:
            fhir_client: FHIR client for patient data. If None, creates default.
            llm_parser: LLM parser for transcript extraction. If None, creates default.
        """
        self.fhir_client = fhir_client or FHIRClient()
        self.llm_parser = llm_parser or LLMTranscriptParser()
        self.compliance_engine = ComplianceEngine()

    async def verify_patient_documentation(
        self,
        patient_id: str,
        transcript: str,
        reference_date: date | None = None,
    ) -> Result[VerificationResult, list[ComplianceAlert]]:
        """Verify clinical documentation for a patient.

        Complete workflow:
        1. Fetch patient profile and encounter from FHIR
        2. Extract structured data from voice transcript
        3. Verify extraction against EMR context
        4. Return verification result

        Args:
            patient_id: FHIR patient identifier
            transcript: Raw voice transcription text
            reference_date: Optional reference date for temporal resolution

        Returns:
            Result containing either VerificationResult or list of ComplianceAlerts
        """
        try:
            # Step 1: Fetch EMR context from FHIR
            patient, emr_context = await self._fetch_patient_context(patient_id)

            # Step 2: Extract structured data from transcript
            extraction = await self._extract_transcript(transcript, reference_date)

            # Step 3: Convert extraction to AI output format
            ai_output = self._convert_to_ai_output(extraction, transcript)

            # Step 4: Verify against EMR context
            result = self.compliance_engine.verify(patient, emr_context, ai_output)

            return result

        except PatientNotFoundError:
            return Result.failure(
                error=[
                    ComplianceAlert(
                        rule_id="FHIR_PATIENT_NOT_FOUND",
                        message=f"Patient {patient_id} not found in FHIR system",
                        severity=ComplianceSeverity.CRITICAL,
                        field="patient_id",
                    )
                ]
            )
        except ExtractionError as e:
            return Result.failure(
                error=[
                    ComplianceAlert(
                        rule_id="EXTRACTION_FAILED",
                        message=f"Failed to extract structured data: {str(e)}",
                        severity=ComplianceSeverity.CRITICAL,
                        field="transcript",
                    )
                ]
            )
        except Exception as e:
            return Result.failure(
                error=[
                    ComplianceAlert(
                        rule_id="WORKFLOW_ERROR",
                        message=f"Verification workflow failed: {str(e)}",
                        severity=ComplianceSeverity.CRITICAL,
                        field="workflow",
                    )
                ]
            )

    async def _fetch_patient_context(self, patient_id: str) -> tuple[PatientProfile, EMRContext]:
        """Fetch patient profile and latest encounter from FHIR.

        Args:
            patient_id: FHIR patient identifier

        Returns:
            Tuple of (PatientProfile, EMRContext)

        Raises:
            PatientNotFoundError: If patient or encounters not found
        """
        try:
            patient = await self.fhir_client.get_patient_profile(patient_id)
            emr_context = await self.fhir_client.get_latest_encounter(patient_id)
            return patient, emr_context
        except ValueError as e:
            raise PatientNotFoundError(f"Failed to fetch patient {patient_id}: {e}") from e
        except Exception as e:
            raise PatientNotFoundError(f"FHIR error for patient {patient_id}: {e}") from e

    async def _extract_transcript(self, transcript: str, reference_date: date | None = None) -> "StructuredExtraction":
        """Extract structured data from voice transcript.

        Args:
            transcript: Raw voice transcription
            reference_date: Optional reference date for temporal resolution

        Returns:
            StructuredExtraction with extracted fields

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            # Update parser reference date if provided
            if reference_date:
                from src.extraction.temporal import TemporalResolver

                self.llm_parser.temporal_resolver = TemporalResolver(reference_date)

            extraction = await self.llm_parser.parse(transcript)
            return extraction
        except Exception as e:
            raise ExtractionError(f"Transcript extraction failed: {e}") from e

    def _convert_to_ai_output(self, extraction: "StructuredExtraction", transcript: str) -> AIGeneratedOutput:
        """Convert extraction to AIGeneratedOutput format.

        Args:
            extraction: Structured extraction from LLM parser
            transcript: Original transcript text

        Returns:
            AIGeneratedOutput for verification engine
        """
        # Extract dates from temporal expressions
        extracted_dates = []
        for temp in extraction.temporal_expressions:
            if temp.normalized_date:
                extracted_dates.append(temp.normalized_date)

        # Extract diagnoses
        extracted_diagnoses = [d.text for d in extraction.diagnoses]

        # Build summary text from extraction
        summary_parts = [transcript]

        if extraction.medications:
            meds_text = "Medications: " + ", ".join([f"{m.name} ({m.status.value})" for m in extraction.medications])
            summary_parts.append(meds_text)

        if extraction.diagnoses:
            dx_text = "Diagnoses: " + ", ".join(extracted_diagnoses)
            summary_parts.append(dx_text)

        summary_text = "\n".join(summary_parts)

        return AIGeneratedOutput(
            summary_text=summary_text,
            extracted_dates=extracted_dates,
            extracted_diagnoses=extracted_diagnoses,
            suggested_billing_codes=[],  # Could be populated from extraction
            contains_pii=False,  # Could be detected from extraction
        )

    async def close(self) -> None:
        """Clean up resources."""
        await self.fhir_client.close()
