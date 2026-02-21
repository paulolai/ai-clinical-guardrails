#!/usr/bin/env python3
"""Custom rule extension example."""

import asyncio
import re
from datetime import date

from src.engine import ComplianceEngine
from src.models import (
    AIGeneratedOutput,
    ComplianceAlert,
    ComplianceSeverity,
    EMRContext,
    PatientProfile,
    Result,
    VerificationResult,
)


class CustomComplianceEngine(ComplianceEngine):
    """Extended engine with custom rules."""

    @staticmethod
    def verify(
        patient: PatientProfile, context: EMRContext, ai_output: AIGeneratedOutput
    ) -> Result[VerificationResult, list[ComplianceAlert]]:
        """Verify with custom rules."""
        # Get base verification
        result = ComplianceEngine.verify(patient, context, ai_output)

        if not result.is_success:
            return result

        # Apply custom rules
        if result.value is None:
            return Result.failure(
                error=[
                    ComplianceAlert(
                        rule_id="CUSTOM_NULL_RESULT",
                        message="Verification returned null result",
                        severity=ComplianceSeverity.CRITICAL,
                    )
                ]
            )

        verification = result.value
        CustomComplianceEngine._check_medication_duplicates(ai_output, verification.alerts)
        CustomComplianceEngine._verify_allergy_warnings(patient, ai_output, verification.alerts)

        # Recalculate score if new alerts added
        if verification.alerts and any(a.severity == ComplianceSeverity.CRITICAL for a in verification.alerts):
            critical = [a for a in verification.alerts if a.severity == ComplianceSeverity.CRITICAL]
            return Result.failure(error=critical)

        return Result.success(value=verification)

    @staticmethod
    def _check_medication_duplicates(ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]) -> None:
        """Custom Rule: Detect duplicate medications."""
        meds = re.findall(r"\b(Metformin|Lisinopril|Insulin)\b", ai_output.summary_text)
        unique_meds = set(meds)

        if len(meds) != len(unique_meds):
            alerts.append(
                ComplianceAlert(
                    rule_id="CUSTOM_DUPLICATE_MEDICATION",
                    message=(f"Duplicate medication mentioned: {set(m for m in meds if meds.count(m) > 1)}"),
                    severity=ComplianceSeverity.HIGH,
                    field="summary_text",
                )
            )

    @staticmethod
    def _verify_allergy_warnings(
        patient: PatientProfile, ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]
    ) -> None:
        """Custom Rule: Verify allergy warnings are present."""
        if not patient.allergies:
            return

        for allergy in patient.allergies:
            if allergy.lower() not in ai_output.summary_text.lower():
                alerts.append(
                    ComplianceAlert(
                        rule_id="CUSTOM_ALLERGY_WARNING_MISSING",
                        message=f"Allergy '{allergy}' not documented in summary",
                        severity=ComplianceSeverity.MEDIUM,
                        field="summary_text",
                    )
                )


async def main() -> None:
    """Demonstrate custom rules."""
    engine = CustomComplianceEngine()

    patient = PatientProfile(
        patient_id="12345",
        first_name="Jane",
        last_name="Smith",
        dob=date(1980, 5, 15),
        allergies=["Penicillin", "Sulfa"],
        diagnoses=["Type 2 Diabetes"],
    )

    context = EMRContext(
        visit_id="V-001",
        patient_id="12345",
        admission_date=__import__("datetime").datetime(2025, 2, 21),
        attending_physician="Dr. Johnson",
        raw_notes="Patient with diabetes",
    )

    # AI output with duplicate medication
    ai_output = AIGeneratedOutput(
        summary_text="Patient takes Metformin and Metformin twice daily. No allergy info.",
        extracted_dates=[date(2025, 2, 21)],
        extracted_diagnoses=["Type 2 Diabetes"],
    )

    result = engine.verify(patient, context, ai_output)

    if result.is_success:
        if result.value is None:
            print("Error: Verification returned null value")
            return
        print(f"Safe to file: {result.value.is_safe_to_file}")
        print(f"Score: {result.value.score}")
        print(f"Alerts ({len(result.value.alerts)}):")
        for alert in result.value.alerts:
            print(f"  [{alert.severity}] {alert.rule_id}: {alert.message}")
    else:
        if result.error is None:
            print("Error: Verification returned null error")
            return
        print(f"Critical violations found: {len(result.error)}")
        for alert in result.error:
            print(f"  [{alert.severity}] {alert.message}")


if __name__ == "__main__":
    asyncio.run(main())
