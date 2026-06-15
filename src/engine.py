import re
import time
from typing import TYPE_CHECKING

from src.protocols.models import ProtocolConfig
from src.protocols.registry import ProtocolRegistry
from src.telemetry import get_alert_counter, get_tracer, get_verification_counter, get_verification_latency

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

_tracer = get_tracer("ai-clinical-guardrails.engine")


class ComplianceEngine:
    """Deterministic Verification Engine for AI-generated Clinical Documentation.

    Includes configurable medical protocol checks via ProtocolRegistry.
    """

    def __init__(self, protocol_config: ProtocolConfig | None = None):
        """Initialize ComplianceEngine.

        Args:
            protocol_config: Optional protocol configuration for medical checks.
        """
        self.protocol_registry = None
        if protocol_config:
            self.protocol_registry = ProtocolRegistry(protocol_config)

    def verify(
        self,
        patient: PatientProfile,
        context: EMRContext,
        ai_output: AIGeneratedOutput,
    ) -> Result[VerificationResult, list[ComplianceAlert]]:
        """Verify AI output against EMR source of truth.

        Args:
            patient: Patient profile from EMR
            context: EMR context (dates, etc.)
            ai_output: AI-generated output to verify

        Returns:
            Result with VerificationResult or list of critical alerts.
        """
        start = time.perf_counter()

        with _tracer.start_as_current_span("compliance.verify") as span:
            span.set_attribute("patient_id", patient.patient_id)
            span.set_attribute("visit_id", context.visit_id)
            span.set_attribute("has_protocol_registry", self.protocol_registry is not None)

            alerts: list[ComplianceAlert] = []

            # 1. Zero-Trust Date Verification
            ComplianceEngine._verify_date_integrity(context, ai_output, alerts)

            # 2. Administrative Protocol Enforcement
            ComplianceEngine._verify_clinical_protocols(ai_output, alerts)

            # 3. Data Safety & PII Firewall
            ComplianceEngine._verify_data_safety(ai_output, alerts)

            # 4. Medical Protocol Checks
            if self.protocol_registry:
                with _tracer.start_as_current_span("compliance.verify.protocols"):
                    protocol_alerts = self._verify_medical_protocols(patient, ai_output)
                    alerts.extend(protocol_alerts)

            # Categorize results
            critical_alerts = [a for a in alerts if a.severity == ComplianceSeverity.CRITICAL]

            # Record metrics
            elapsed_ms = (time.perf_counter() - start) * 1000
            outcome = "failure" if critical_alerts else "success"
            span.set_attribute("compliance.outcome", outcome)
            span.set_attribute("compliance.alert_count", len(alerts))
            span.set_attribute("compliance.elapsed_ms", elapsed_ms)

            vc = get_verification_counter()
            if vc is not None:
                vc.add(1, {"outcome": outcome})
            vl = get_verification_latency()
            if vl is not None:
                vl.record(elapsed_ms)

            for alert in alerts:
                ac = get_alert_counter()
                if ac is not None:
                    ac.add(1, {"rule_id": alert.rule_id, "severity": alert.severity.value})
                span.add_event(
                    "alert",
                    {"rule_id": alert.rule_id, "severity": alert.severity.value, "message": alert.message},
                )

            # If we have critical violations, we return a Failure Result
            if critical_alerts:
                span.set_attribute("compliance.critical_alerts", len(critical_alerts))
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
            medications=ai_output.extracted_medications,
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
