#!/usr/bin/env python3
"""Basic verification example."""

import asyncio
from datetime import date, datetime

from src.engine import ComplianceEngine
from src.models import (
    AIGeneratedOutput,
    EMRContext,
    PatientProfile,
)


async def main() -> None:
    """Verify a simple AI output."""

    # Setup
    engine = ComplianceEngine()

    # Create patient profile
    patient = PatientProfile(
        patient_id="12345",
        first_name="John",
        last_name="Doe",
        dob=date(1975, 3, 20),
        allergies=["Penicillin"],
        diagnoses=["Hypertension"],
    )

    # Create EMR context
    context = EMRContext(
        visit_id="V-001",
        patient_id="12345",
        admission_date=datetime(2025, 2, 21, 9, 0, 0),
        attending_physician="Dr. Smith",
        raw_notes="Patient admitted for routine checkup",
    )

    # AI-generated text
    ai_output = AIGeneratedOutput(
        summary_text="Patient seen on 2025-02-21 for follow-up.",
        extracted_dates=[date(2025, 2, 21)],
        extracted_diagnoses=["Hypertension"],
    )

    # Verify against EMR
    result = engine.verify(patient, context, ai_output)

    # Handle result
    if result.is_success:
        if result.value is None:
            print("Error: Verification returned null value")
            return
        print(f"Decision: {'APPROVED' if result.value.is_safe_to_file else 'REJECTED'}")
        print(f"Safe to file: {result.value.is_safe_to_file}")
        print(f"Score: {result.value.score}")
        if result.value.alerts:
            print(f"Alerts ({len(result.value.alerts)}):")
            for alert in result.value.alerts:
                print(f"  [{alert.severity}] {alert.rule_id}: {alert.message}")
    else:
        if result.error is None:
            print("Error: Verification returned null error")
            return
        print("Verification failed with critical violations")
        print(f"Violations ({len(result.error)}):")
        for alert in result.error:
            print(f"  [{alert.severity}] {alert.rule_id}: {alert.message}")


if __name__ == "__main__":
    asyncio.run(main())
