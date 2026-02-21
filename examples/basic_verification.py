#!/usr/bin/env python3
"""Basic verification example."""

import asyncio
from src.integrations.fhir import FHIRClient
from src.engine import ComplianceEngine
from src.models import AIOutput


async def main():
    """Verify a simple AI output."""

    # Setup
    fhir = FHIRClient()
    engine = ComplianceEngine()

    # AI-generated text
    ai_output = AIOutput(text="Patient seen on 2025-02-21 for follow-up.", dates=["2025-02-21"])

    # Verify against EMR
    patient_id = "90128869"
    result = await engine.verify_patient_output(patient_id, ai_output)

    # Handle result
    match result:
        case Success(report):
            print(f"Decision: {report.decision}")
            print(f"Safe to file: {report.is_safe}")
        case Failure(error):
            print(f"Verification failed: {error}")
            print(f"Violations: {error.violations}")

    await fhir.close()


if __name__ == "__main__":
    asyncio.run(main())
