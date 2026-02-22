from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, PatientProfile
from src.protocols.checkers.base import ProtocolChecker
from src.protocols.matcher import AllergyPatternMatcher, MedicationPatternMatcher


class AllergyChecker(ProtocolChecker):
    """Checks for conflicts between patient allergies and prescribed medications."""

    @property
    def name(self) -> str:
        return "allergy_checks"

    def check(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        alerts: list[ComplianceAlert] = []

        if not self.config or "allergy_checks" not in self.config.rules:
            return alerts

        allergy_matcher = AllergyPatternMatcher()
        med_matcher = MedicationPatternMatcher()

        for rule in self.config.rules["allergy_checks"]:
            # Check if patient has the allergy
            has_allergy = allergy_matcher.matches(
                patient, extraction, {"patient_allergies": rule.pattern.get("patient_allergies", [])}
            )

            # Check if conflicting med is prescribed
            has_conflict = med_matcher.matches(
                patient, extraction, {"medications": rule.pattern.get("conflicts", {}).get("medications", [])}
            )

            if has_allergy and has_conflict:
                alerts.append(self._create_alert(rule, patient, extraction))

        return alerts
