from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .engine import ComplianceEngine
from .instrumentation import ComplianceTracer
from .integrations.fhir.client import FHIRClient
from .models import AIGeneratedOutput, EMRContext, PatientProfile, Result, VerificationResult

# Global instances
tracer = ComplianceTracer(run_id="api-session")
# Formal Wrapped Client for EMR
emr_client = FHIRClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await emr_client.close()


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


@app.post("/verify", response_model=VerificationResult)
async def verify_compliance(request: ComplianceRequest):
    """Manual verification endpoint."""
    if not request.patient or not request.context:
        raise HTTPException(status_code=400, detail="Manual patient and context required")

    result = ComplianceEngine.verify(request.patient, request.context, request.ai_output)
    return _process_result(request.patient.patient_id, request.context.visit_id, result)


@app.post("/verify/fhir/{patient_id}", response_model=VerificationResult)
async def verify_fhir_compliance(patient_id: str, request: ComplianceRequest):
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


def _process_result(patient_id: str, visit_id: str, result: Result):
    if result.is_success:
        verification = result.value
    else:
        verification = VerificationResult(is_safe_to_file=False, score=0.0, alerts=result.error)
    tracer.log_interaction(patient_id, visit_id, verification)
    return verification


@app.get("/stats")
async def get_compliance_stats():
    return tracer.stats


@app.get("/health")
async def health_check():
    return {"status": "operational", "emr_integration": "FHIR R4 Connected"}
