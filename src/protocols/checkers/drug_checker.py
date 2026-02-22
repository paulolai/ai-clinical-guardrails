from src.extraction.models import StructuredExtraction
from src.models import ComplianceAlert, PatientProfile
from src.protocols.checkers.base import ProtocolChecker


class DrugInteractionChecker(ProtocolChecker):
    """Checks for drug interactions between patient medications and new prescriptions."""

    @property
    def name(self) -> str:
        return "drug_interactions"

    def check(self, patient: PatientProfile, extraction: StructuredExtraction) -> list[ComplianceAlert]:
        alerts: list[ComplianceAlert] = []

        if not self.config or "drug_interactions" not in self.config.rules:
            return alerts

        # Combine patient active meds with newly extracted meds
        patient_med_names = set()
        if hasattr(patient, "active_medications"):
            patient_med_names = {m.name.lower() for m in patient.active_medications}
        extracted_med_names = {m.name.lower() for m in extraction.medications}
        all_meds = patient_med_names | extracted_med_names

        for rule in self.config.rules["drug_interactions"]:
            trigger_meds = {m.lower() for m in rule.pattern.get("trigger", {}).get("medications", [])}
            conflict_meds = {m.lower() for m in rule.pattern.get("conflicts", {}).get("medications", [])}

            # Check if trigger med is present AND conflict med is present
            has_trigger = bool(trigger_meds & all_meds)
            has_conflict = bool(conflict_meds & all_meds)

            if has_trigger and has_conflict:
                alerts.append(self._create_alert(rule, patient, extraction))

        return alerts
