#!/usr/bin/env python3
"""Complete end-to-end workflow example.

Demonstrates the full clinical documentation pipeline:
Voice Dictation → Extraction → FHIR Lookup → Verification → Result

Usage:
    uv run python examples/complete_workflow.py

Example Output:
    ========================================
    CLINICAL DOCUMENTATION VERIFICATION
    ========================================

    Patient: Johnson, Sarah (ID: 90128869)

    Transcript:
    "Mrs. Johnson came in yesterday with chest pain. Started her on Lisinopril. Follow up in two weeks."

    Extracted Data:
      - Medications: Lisinopril (started)
      - Temporal: yesterday → 2025-02-21, two weeks → 2025-03-07
      - Visit Type: acute_complaint

    Verification against EMR:
      ✓ Date matches encounter: 2025-02-21
      ✓ No critical compliance violations

    ========================================
    Result: APPROVED (Score: 0.9)

    Safe to auto-file: YES
    Audit trail logged for compliance
    ========================================
"""

import asyncio
from datetime import date

from src.integrations.fhir.workflow import VerificationWorkflow


async def main() -> None:
    """Run complete verification workflow example."""

    print("=" * 60)
    print("CLINICAL DOCUMENTATION VERIFICATION - END TO END")
    print("=" * 60)
    print()

    # Initialize the workflow
    workflow = VerificationWorkflow()

    # Example patient ID from HAPI FHIR sandbox
    # This is a real patient in the public sandbox
    patient_id = "90128869"

    # Simulated clinical dictation
    transcript = "Mrs. Johnson came in yesterday with chest pain. Started her on Lisinopril. Follow up in two weeks."

    print(f"Patient ID: {patient_id}")
    print(f"Reference Date: {date.today().isoformat()}")
    print()
    print("Clinical Transcript:")
    print(f'  "{transcript}"')
    print()
    print("-" * 60)
    print("Processing: Dictation → Extraction → Verification")
    print("-" * 60)
    print()

    try:
        # Run the complete workflow
        result = await workflow.verify_patient_documentation(
            patient_id=patient_id,
            transcript=transcript,
            reference_date=date.today(),
        )

        # Display results
        if result.is_success and result.value:
            verification = result.value
            print("✓ VERIFICATION COMPLETE")
            print()
            print(f"Decision: {'APPROVED' if verification.is_safe_to_file else 'REJECTED'}")
            print(f"Trust Score: {verification.score:.0%}")
            print(f"Safe to auto-file: {'YES' if verification.is_safe_to_file else 'NO - Manual review required'}")

            if verification.alerts:
                print()
                print(f"Alerts ({len(verification.alerts)}):")
                for alert in verification.alerts:
                    print(f"  [{alert.severity.upper()}] {alert.rule_id}")
                    print(f"    → {alert.message}")
                    if alert.field:
                        print(f"    → Field: {alert.field}")
            else:
                print()
                print("✓ No compliance alerts")

        else:
            print("✗ VERIFICATION FAILED - Critical Issues Found")
            print()
            if result.error:
                print(f"Critical Violations ({len(result.error)}):")
                for alert in result.error:
                    print(f"  [{alert.severity.upper()}] {alert.rule_id}")
                    print(f"    → {alert.message}")

        print()
        print("=" * 60)
        print("Workflow complete - Audit trail generated")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        raise
    finally:
        # Clean up resources
        await workflow.close()


if __name__ == "__main__":
    asyncio.run(main())
