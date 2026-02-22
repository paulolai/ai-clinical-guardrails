from abc import ABC, abstractmethod

from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, ComplianceSeverity, PatientProfile
from src.protocols.models import ProtocolConfig, ProtocolRule


class ProtocolChecker(ABC):
    """Base class for protocol checkers."""

    def __init__(self, config: ProtocolConfig | None = None):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Return checker name."""
        pass

    @abstractmethod
    def check(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        """Check patient/extraction against rules."""
        pass

    def _create_alert(
        self, rule: ProtocolRule, patient: PatientProfile, extraction: StructuredExtraction
    ) -> ComplianceAlert:
        """Create compliance alert from rule violation."""
        # Map ProtocolSeverity to ComplianceSeverity
        severity_map = {
            "CRITICAL": ComplianceSeverity.CRITICAL,
            "HIGH": ComplianceSeverity.HIGH,
            "WARNING": ComplianceSeverity.MEDIUM,
            "INFO": ComplianceSeverity.LOW,
        }

        return ComplianceAlert(
            rule_id=f"PROTOCOL_{rule.checker_type.upper()}_{rule.name.upper().replace(' ', '_')}",
            message=rule.message,
            severity=severity_map.get(rule.severity.value, ComplianceSeverity.LOW),
            field="extraction",
        )
