from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, PatientProfile
from src.protocols.checkers.base import ProtocolChecker
from src.protocols.matcher import FieldPresenceMatcher


class RequiredFieldsChecker(ProtocolChecker):
    """Checks for required fields in documentation based on encounter type."""

    @property
    def name(self) -> str:
        return "required_fields"

    def check(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        alerts: list[ComplianceAlert] = []

        if not self.config or "required_fields" not in self.config.rules:
            return alerts

        matcher = FieldPresenceMatcher()

        for rule in self.config.rules["required_fields"]:
            pattern = rule.pattern
            required_fields = pattern.get("required", [])

            # Check if all required fields are present
            all_present = matcher.matches(patient, extraction, {"required": required_fields})

            if not all_present:
                alerts.append(self._create_alert(rule, patient, extraction))

        return alerts
