from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.extraction.models import StructuredExtraction
from src.review.service import ReviewService, ReviewServiceError

from .engine import ComplianceEngine
from .instrumentation import ComplianceTracer, StatsDict
from .integrations.fhir.client import FHIRClient
from .integrations.fhir.workflow import VerificationWorkflow
from .models import (
    AIGeneratedOutput,
    ClinicalNote,
    ComplianceAlert,
    EMRContext,
    PatientProfile,
    Result,
    UnifiedReview,
    VerificationResult,
)

# Global instances
tracer = ComplianceTracer(run_id="api-session")
# Formal Wrapped Client for EMR
emr_client = FHIRClient()
# Workflow instance for extraction
verification_workflow = VerificationWorkflow(fhir_client=emr_client)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await emr_client.close()
    await verification_workflow.close()


app = FastAPI(
    title="Clinical Guardrails API",
    description="Deterministic Verification API for AI-generated Documentation Safety.",
    version="1.2.0",
    lifespan=lifespan,
)


class ComplianceRequest(BaseModel):
    patient: PatientProfile | None = None
    context: EMRContext | None = None
    ai_output: AIGeneratedOutput


class ExtractionRequest(BaseModel):
    patient_id: str = Field(..., description="FHIR patient identifier")
    transcript: str = Field(..., description="Voice transcription text to extract and verify")
    reference_date: date | None = Field(None, description="Reference date for temporal resolution (defaults to today)")


class CreateReviewRequest(BaseModel):
    """Request to create a clinical note review."""

    patient_id: str = Field(..., description="FHIR patient identifier")
    encounter_id: str = Field(..., description="FHIR encounter identifier")
    transcript: str = Field(..., description="Voice transcription or AI-generated note text")
    reference_date: date | None = Field(None, description="Reference date for temporal resolution")
    sections: dict[str, str] = Field(
        default_factory=dict, description="Note sections (chief_complaint, assessment, plan, etc.)"
    )

    def to_clinical_note(self, note_id: str, extraction: StructuredExtraction) -> ClinicalNote:
        """Convert request to ClinicalNote model."""
        return ClinicalNote(
            note_id=note_id,
            patient_id=self.patient_id,
            encounter_id=self.encounter_id,
            generated_at=datetime.now(),
            sections=self.sections,
            extraction=extraction,
        )


class ExtractedMedication(BaseModel):
    name: str
    status: str


class ExtractedTemporal(BaseModel):
    expression: str
    normalized_date: date | None = None


class ExtractionResult(BaseModel):
    medications: list[ExtractedMedication] = Field(default_factory=list)
    diagnoses: list[str] = Field(default_factory=list)
    temporal_expressions: list[ExtractedTemporal] = Field(default_factory=list)
    visit_type: str | None = None


class ExtractionResponse(BaseModel):
    patient_id: str
    transcript: str
    extraction: ExtractionResult
    verification: VerificationResult
    is_safe_to_file: bool
    processing_time_ms: int | None = None


@app.post("/verify", response_model=VerificationResult)
async def verify_compliance(request: ComplianceRequest) -> VerificationResult:
    """Manual verification endpoint."""
    if not request.patient or not request.context:
        raise HTTPException(status_code=400, detail="Manual patient and context required")

    result = ComplianceEngine.verify(request.patient, request.context, request.ai_output)
    return _process_result(request.patient.patient_id, request.context.visit_id, result)


@app.post("/verify/fhir/{patient_id}", response_model=VerificationResult)
async def verify_fhir_compliance(patient_id: str, request: ComplianceRequest) -> VerificationResult:
    """
    EMR-Integrated verification using Wrapped FHIR Client.
    """
    try:
        # 1. Use Wrapper to get clean domain objects
        patient = await emr_client.get_patient_profile(patient_id)
        context = await emr_client.get_latest_encounter(patient_id)

        # 2. Run Engine
        result = ComplianceEngine.verify(patient, context, request.ai_output)

        return _process_result(patient.patient_id, context.visit_id, result)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EMR Integration Error: {str(e)}") from e


def _process_result(
    patient_id: str, visit_id: str, result: Result[VerificationResult, list[ComplianceAlert]]
) -> VerificationResult:
    verification: VerificationResult
    if result.is_success:
        if result.value is None:
            raise ValueError("Success result has no value")
        verification = result.value
    else:
        alerts: list[ComplianceAlert] = result.error if result.error is not None else []
        verification = VerificationResult(is_safe_to_file=False, score=0.0, alerts=alerts)
    tracer.log_interaction(patient_id, visit_id, verification)
    return verification


@app.post("/extract", response_model=ExtractionResponse)
async def extract_and_verify(request: ExtractionRequest) -> ExtractionResponse:
    """
    Extract structured data from voice transcript and verify against EMR.

    Complete workflow:
    1. Fetch patient context from FHIR
    2. Extract structured data from transcript using LLM
    3. Verify extraction against EMR source of truth
    4. Return extraction results with compliance verification

    Example:
        ```bash
        curl -X POST "http://localhost:8000/extract" \\
          -H "Content-Type: application/json" \\
          -d '{
            "patient_id": "90128869",
            "transcript": "Patient came in yesterday with chest pain. Started on Lisinopril.",
            "reference_date": "2025-02-22"
          }'
        ```
    """
    import time

    start_time = time.perf_counter()

    try:
        # Run the complete workflow: extraction + verification
        result = await verification_workflow.verify_patient_documentation(
            patient_id=request.patient_id,
            transcript=request.transcript,
            reference_date=request.reference_date,
        )

        # Calculate processing time
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        # Get verification result
        verification: VerificationResult
        if result.is_success:
            if result.value is None:
                raise ValueError("Success result has no value")
            verification = result.value
        else:
            alerts: list[ComplianceAlert] = result.error if result.error is not None else []
            verification = VerificationResult(is_safe_to_file=False, score=0.0, alerts=alerts)

        # Build extraction result from the workflow's last extraction
        extraction_result = ExtractionResult()
        try:
            # Get the last extraction from the workflow
            last_ext = verification_workflow.get_last_extraction()
            if last_ext:
                extraction_result = ExtractionResult(
                    medications=[ExtractedMedication(name=m.name, status=m.status.value) for m in last_ext.medications],
                    diagnoses=[d.text for d in last_ext.diagnoses],
                    temporal_expressions=[
                        ExtractedTemporal(expression=t.text, normalized_date=t.normalized_date)
                        for t in last_ext.temporal_expressions
                    ],
                    visit_type=last_ext.visit_type,
                )
        except Exception:
            # If we can't get extraction details, return empty extraction
            pass

        return ExtractionResponse(
            patient_id=request.patient_id,
            transcript=request.transcript,
            extraction=extraction_result,
            verification=verification,
            is_safe_to_file=verification.is_safe_to_file,
            processing_time_ms=processing_time_ms,
        )

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}") from e


@app.get("/stats")
async def get_compliance_stats() -> StatsDict:
    return tracer.stats


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "operational", "emr_integration": "FHIR R4 Connected"}


@app.post("/review/create", response_model=UnifiedReview)
async def create_review(request: CreateReviewRequest) -> UnifiedReview:
    """
    Create a unified review for an AI-generated clinical note.

    This endpoint:
    1. Extracts structured data from the transcript
    2. Fetches patient EMR data from FHIR
    3. Runs compliance verification
    4. Returns unified review with discrepancies highlighted

    Example:
        ```bash
        curl -X POST "http://localhost:8000/review/create" \\
          -H "Content-Type: application/json" \\
          -d '{
            "patient_id": "90128869",
            "encounter_id": "enc-123",
            "transcript": "Patient has hypertension, started on lisinopril",
            "sections": {"assessment": "Hypertension", "plan": "Start lisinopril"}
          }'
        ```
    """
    from src.extraction.llm_parser import LLMTranscriptParser

    # Generate unique note ID
    note_id = f"note-{datetime.now().timestamp()}"

    # Extract structured data from transcript (reuse existing extraction)
    parser = LLMTranscriptParser()
    extraction = await parser.parse(request.transcript)

    # Create ClinicalNote
    note = request.to_clinical_note(note_id, extraction)

    # Create review using service
    service = ReviewService(fhir_client=emr_client)
    try:
        review = await service.create_review(note)
        return review
    except ReviewServiceError as rse:
        # Check if underlying error is ValueError (patient not found)
        if rse.__cause__ and isinstance(rse.__cause__, ValueError):
            raise HTTPException(status_code=404, detail=str(rse.__cause__)) from rse
        raise HTTPException(status_code=500, detail=f"Review creation failed: {str(rse)}") from rse
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review creation failed: {str(e)}") from e


@app.get("/review/{note_id}", response_model=UnifiedReview)
async def get_review(note_id: str) -> UnifiedReview:
    """
    Get an existing review by note ID.

    Note: For this demo, we regenerate the review each time.
    Production would cache and check freshness.

    Example:
        ```bash
        curl "http://localhost:8000/review/note-123456"
        ```
    """
    # For demo: Return 501 Not Implemented
    # Production: Would fetch from cache/database
    raise HTTPException(
        status_code=501,
        detail="GET /review/{note_id} not implemented in demo. Use POST /review/create to generate new reviews.",
    )
