"""Duplicate therapy checker for detecting redundant medications."""

from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, PatientProfile
from src.protocols.checkers.base import ProtocolChecker
from src.protocols.checkers.drug_class_matcher import DrugClassMatcher


class DuplicateTherapyChecker(ProtocolChecker):
    """Checks for multiple medications in the same therapeutic class."""

    @property
    def name(self) -> str:
        return "duplicate_therapy"

    def check(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        alerts: list[ComplianceAlert] = []

        if not self.config or "duplicate_therapy" not in self.config.rules:
            return alerts

        matcher = DrugClassMatcher()

        for rule in self.config.rules["duplicate_therapy"]:
            drug_class = rule.pattern.get("drug_class", "")
            max_count = rule.pattern.get("max_count", 1)

            if not drug_class:
                continue

            actual_count = matcher.count_by_class(extraction, drug_class)

            if actual_count > max_count:
                alerts.append(self._create_alert(rule, patient, extraction))

        return alerts
