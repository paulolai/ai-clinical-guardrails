import re
from typing import TYPE_CHECKING

# NEW: Import protocol components
from src.protocols.models import ProtocolConfig
from src.protocols.registry import ProtocolRegistry

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

    from src.extraction.models import StructuredExtraction


class ComplianceEngine:
    """
    Deterministic Verification Engine for AI-generated Clinical Documentation.
    Now includes configurable medical protocol checks.
    """

    def __init__(self, protocol_config: ProtocolConfig | None = None):
        """
        Initialize ComplianceEngine.

        Args:
            protocol_config: Optional protocol configuration for medical checks.
        """
        self.protocol_registry = None
        if protocol_config:
            self.protocol_registry = ProtocolRegistry(protocol_config)

    @staticmethod
    def verify(
        patient: PatientProfile,
        context: EMRContext,
        ai_output: AIGeneratedOutput,
        protocol_config: ProtocolConfig | None = None,
    ) -> Result[VerificationResult, list[ComplianceAlert]]:
        """
        Pure function that verifies AI output against EMR source of truth.

        Args:
            patient: Patient profile from EMR
            context: EMR context (dates, etc.)
            ai_output: AI-generated output to verify
            protocol_config: Optional protocol configuration

        Returns:
            Result with VerificationResult or list of critical alerts.
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

        # 4. NEW: Medical Protocol Checks
        if protocol_config:
            engine = ComplianceEngine(protocol_config)
            protocol_alerts = engine._verify_medical_protocols(patient, ai_output)
            alerts.extend(protocol_alerts)

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

    def _verify_medical_protocols(self, patient: PatientProfile, ai_output: AIGeneratedOutput) -> list[ComplianceAlert]:
        """Run medical protocol checks if registry is configured."""
        if not self.protocol_registry:
            return []

        # Convert AIGeneratedOutput to StructuredExtraction
        extraction = self._convert_to_extraction(ai_output)

        return self.protocol_registry.check_all(patient, extraction)

    @staticmethod
    def _convert_to_extraction(ai_output: AIGeneratedOutput) -> "StructuredExtraction":
        """Convert AIGeneratedOutput to StructuredExtraction for protocol checks."""
        from src.extraction.models import StructuredExtraction

        return StructuredExtraction(
            medications=ai_output.extracted_medications if hasattr(ai_output, "extracted_medications") else [],
            diagnoses=[],
            temporal_expressions=[],
            vital_signs=[],
        )

    @staticmethod
    def _verify_date_integrity(
        context: EMRContext, ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]
    ) -> None:
        allowed_dates: set[date] = {context.admission_date.date()}
        if context.discharge_date:
            allowed_dates.add(context.discharge_date.date())

        for extracted_date in ai_output.extracted_dates:
            if extracted_date not in allowed_dates:
                alerts.append(
                    ComplianceAlert(
                        rule_id="INVARIANT_DATE_MISMATCH",
                        message=(f"Extracted date {extracted_date} is outside the allowed EMR context window."),
                        severity=ComplianceSeverity.CRITICAL,
                        field="extracted_dates",
                    )
                )

    @staticmethod
    def _verify_clinical_protocols(ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]) -> None:
        diagnoses_lower = [d.lower() for d in ai_output.extracted_diagnoses]
        is_sepsis_case = any("sepsis" in d for d in diagnoses_lower)
        mentions_antibiotics = "antibiotic" in ai_output.summary_text.lower()

        if is_sepsis_case and not mentions_antibiotics:
            alerts.append(
                ComplianceAlert(
                    rule_id="PROTOCOL_ADHERENCE_MISSING",
                    message=("Clinical Protocol: Sepsis diagnosis requires explicit antibiotic documentation."),
                    severity=ComplianceSeverity.HIGH,
                    field="summary_text",
                )
            )

    @staticmethod
    def _verify_data_safety(ai_output: AIGeneratedOutput, alerts: list[ComplianceAlert]) -> None:
        # Original regex for generic PII detection (Medicare Number pattern)
        # Matches 10 digits, optionally space-separated (e.g., 2222 33333 1)
        pii_regex = r"\b\d{4}[ ]?\d{5}[ ]?\d{1}\b"
        if re.search(pii_regex, ai_output.summary_text):
            alerts.append(
                ComplianceAlert(
                    rule_id="SAFETY_PII_LEAK",
                    message=("Administrative Safety: Potential PII (Medicare Number pattern) detected in summary."),
                    severity=ComplianceSeverity.CRITICAL,
                    field="summary_text",
                )
            )
