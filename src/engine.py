import re
from typing import TYPE_CHECKING, List, Set

from .models import (
    AIGeneratedOutput,
    ComplianceAlert,
    ComplianceSeverity,
    EMRContext,
    PatientProfile,
    Result,
    VerificationResult,
)

if TYPE_CHECKING:
    from datetime import date


class ComplianceEngine:
    """
    Deterministic Verification Engine for AI-generated Clinical Documentation.
    Original implementation of high-assurance clinical guardrails.
    """

    @staticmethod
    def verify(
        patient: PatientProfile, context: EMRContext, ai_output: AIGeneratedOutput
    ) -> Result[VerificationResult, List[ComplianceAlert]]:
        """
        Pure function that verifies AI output against EMR source of truth.
        Returns a Result object wrapping either a VerificationResult or a list of critical alerts.
        """
        alerts: list[ComplianceAlert] = []

        # 1. Zero-Trust Date Verification
        # Ensures AI hasn't hallucinated dates outside the known clinical window
        ComplianceEngine._verify_date_integrity(context, ai_output, alerts)

        # 2. Administrative Protocol Enforcement
        # Codifies the rule: "Sepsis documentation requires Antibiotic confirmation"
        ComplianceEngine._verify_clinical_protocols(ai_output, alerts)

        # 3. Data Safety & PII Firewall
        # Detects patterns that should not exist in administrative summaries
        ComplianceEngine._verify_data_safety(ai_output, alerts)

        # Categorize results
        critical_alerts = [a for a in alerts if a.severity == ComplianceSeverity.CRITICAL]

        # If we have critical violations, we return a Failure Result
        if critical_alerts:
            return Result.failure(error=critical_alerts)

        # Calculate a trust score based on non-critical alerts
        high_alerts = [a for a in alerts if a.severity == ComplianceSeverity.HIGH]
        score = 1.0
        if high_alerts:
            score = 0.7
        elif alerts:
            score = 0.9

        verification = VerificationResult(is_safe_to_file=True, score=score, alerts=alerts)

        return Result.success(value=verification)

    @staticmethod
    def _verify_date_integrity(
        context: EMRContext, ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]
    ):
        allowed_dates: set[date] = {context.admission_date.date()}  # type: ignore
        if context.discharge_date:
            allowed_dates.add(context.discharge_date.date())

        for extracted_date in ai_output.extracted_dates:
            if extracted_date not in allowed_dates:
                alerts.append(
                    ComplianceAlert(
                        rule_id="INVARIANT_DATE_MISMATCH",
                        message=(
                            f"Extracted date {extracted_date} is outside "
                            "the allowed EMR context window."
                        ),
                        severity=ComplianceSeverity.CRITICAL,
                        field="extracted_dates",
                    )
                )

    @staticmethod
    def _verify_clinical_protocols(ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]):
        diagnoses_lower = [d.lower() for d in ai_output.extracted_diagnoses]
        is_sepsis_case = any("sepsis" in d for d in diagnoses_lower)
        mentions_antibiotics = "antibiotic" in ai_output.summary_text.lower()

        if is_sepsis_case and not mentions_antibiotics:
            alerts.append(
                ComplianceAlert(
                    rule_id="PROTOCOL_ADHERENCE_MISSING",
                    message=(
                        "Clinical Protocol: Sepsis diagnosis requires "
                        "explicit antibiotic documentation."
                    ),
                    severity=ComplianceSeverity.HIGH,
                    field="summary_text",
                )
            )

    @staticmethod
    def _verify_data_safety(ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]):
        # Original regex for generic PII detection (SSN-like patterns)
        # Demonstrates administrative safety without using external libraries
        pii_regex = r"\b\d{3}-\d{2}-\d{4}\b"
        if re.search(pii_regex, ai_output.summary_text):
            alerts.append(
                ComplianceAlert(
                    rule_id="SAFETY_PII_LEAK",
                    message=(
                        "Administrative Safety: Potential PII (SSN pattern) detected in summary."
                    ),
                    severity=ComplianceSeverity.CRITICAL,
                    field="summary_text",
                )
            )
