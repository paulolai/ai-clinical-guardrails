#!/usr/bin/env python3
"""Batch processing example with concurrent verification."""

import asyncio
from datetime import date, datetime

from src.engine import ComplianceEngine
from src.models import (
    AIGeneratedOutput,
    ComplianceAlert,
    EMRContext,
    PatientProfile,
    Result,
    VerificationResult,
)


async def process_single(
    engine: ComplianceEngine,
    patient: PatientProfile,
    context: EMRContext,
    ai_output: AIGeneratedOutput,
) -> Result[VerificationResult, list[ComplianceAlert]]:
    """Process a single verification."""
    return engine.verify(patient, context, ai_output)


async def process_batch(
    engine: ComplianceEngine, items: list[tuple[PatientProfile, EMRContext, AIGeneratedOutput]]
) -> list[Result[VerificationResult, list[ComplianceAlert]]]:
    """Process multiple verifications concurrently."""
    tasks = [process_single(engine, patient, context, ai_output) for patient, context, ai_output in items]
    return await asyncio.gather(*tasks)


async def main() -> None:
    """Demonstrate batch processing."""
    engine = ComplianceEngine()

    # Prepare test data
    base_date = datetime(2025, 2, 21)
    batch_items: list[tuple[PatientProfile, EMRContext, AIGeneratedOutput]] = []

    for i in range(5):
        patient = PatientProfile(
            patient_id=f"P-{i:04d}",
            first_name="Patient",
            last_name=f"Test{i}",
            dob=date(1980 + i, 1, 1),
            allergies=[],
            diagnoses=["Hypertension"],
        )

        context = EMRContext(
            visit_id=f"V-{i:04d}",
            patient_id=f"P-{i:04d}",
            admission_date=base_date,
            attending_physician="Dr. Smith",
            raw_notes="",
        )

        # Some items have dates outside range (will fail)
        ai_date = date(2025, 2, 21) if i < 3 else date(2024, 1, 1)
        ai_output = AIGeneratedOutput(
            summary_text=f"Patient seen on {ai_date}.",
            extracted_dates=[ai_date],
            extracted_diagnoses=["Hypertension"],
        )

        batch_items.append((patient, context, ai_output))

    # Process batch
    print(f"Processing {len(batch_items)} verifications...")
    results = await process_batch(engine, batch_items)

    # Analyze results
    successful = sum(1 for r in results if r.is_success)
    failed = len(results) - successful

    print("\nResults:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    for i, result in enumerate(results):
        patient_id = batch_items[i][0].patient_id
        if result.is_success:
            if result.value is None:
                print(f"\n  {patient_id}: ERROR (null result)")
                continue
            print(f"\n  {patient_id}: OK (score: {result.value.score:.2f})")
        else:
            print(f"\n  {patient_id}: FAILED")
            if result.error is None:
                print("    - Error: null error")
                continue
            for alert in result.error:
                print(f"    - {alert.rule_id}: {alert.message}")


if __name__ == "__main__":
    asyncio.run(main())
