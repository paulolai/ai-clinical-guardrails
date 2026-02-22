"""Protocol registry for orchestrating compliance checkers."""

from typing import Any

from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, PatientProfile
from src.protocols.checkers.allergy_checker import AllergyChecker
from src.protocols.checkers.documentation_checker import RequiredFieldsChecker
from src.protocols.checkers.drug_checker import DrugInteractionChecker
from src.protocols.models import ProtocolConfig


class ProtocolRegistry:
    """Registry that orchestrates all protocol checkers."""

    def __init__(self, config: ProtocolConfig) -> None:
        self.config = config
        self._checkers: dict[str, Any] = {}
        self._initialize_checkers()

    def _initialize_checkers(self) -> None:
        """Initialize enabled checkers from config."""
        checker_map = {
            "drug_interactions": DrugInteractionChecker,
            "allergy_checks": AllergyChecker,
            "required_fields": RequiredFieldsChecker,
        }

        for checker_name, checker_class in checker_map.items():
            checker_config = self.config.checkers.get(checker_name, {})
            if checker_config.get("enabled", False):
                self._checkers[checker_name] = checker_class(self.config)  # type: ignore[abstract]

    def check_all(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        """Run all enabled checkers and aggregate alerts."""
        all_alerts: list[ComplianceAlert] = []

        for checker in self._checkers.values():
            alerts = checker.check(patient, extraction)
            all_alerts.extend(alerts)

        return all_alerts

    def get_enabled_checkers(self) -> list[str]:
        """Return list of enabled checker names."""
        return list(self._checkers.keys())
