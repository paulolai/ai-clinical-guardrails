from datetime import date
from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import PatientProfile
from src.protocols.checkers.allergy_checker import AllergyChecker
from src.protocols.checkers.drug_checker import DrugInteractionChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity

KNOWN_TRIGGER_MEDS = ["warfarin", "lisinopril", "metformin", "aspirin", "methotrexate"]
KNOWN_CONFLICT_MEDS = ["ibuprofen", "potassium", "alcohol", "aspirin", "nsaids"]
KNOWN_ALLERGIES = ["penicillin", "sulfa", "aspirin", "latex", "codeine"]
KNOWN_ALLERGY_CONFLICT_MEDS = ["amoxicillin", "bactrim", "aspirin", "gloves", "tylenol"]

RULE_SEVERITIES = [ProtocolSeverity.CRITICAL, ProtocolSeverity.HIGH, ProtocolSeverity.WARNING, ProtocolSeverity.INFO]


@st.composite
def drug_interaction_rule_strategy(draw: Any) -> ProtocolRule:
    trigger = draw(st.sampled_from(KNOWN_TRIGGER_MEDS))
    conflict = draw(st.sampled_from([m for m in KNOWN_CONFLICT_MEDS if m != trigger]))
    severity = draw(st.sampled_from(RULE_SEVERITIES))
    return ProtocolRule(
        name=f"{trigger.title()} {conflict.title()}",
        checker_type="drug_interactions",
        pattern={"trigger": {"medications": [trigger]}, "conflicts": {"medications": [conflict]}},
        severity=severity,
        message=f"{trigger} + {conflict} interaction",
    )


@st.composite
def drug_interaction_config_strategy(draw: Any) -> ProtocolConfig:
    rules = draw(st.lists(drug_interaction_rule_strategy(), min_size=1, max_size=5, unique_by=lambda r: r.name))
    return ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={"drug_interactions": rules},
    )


@st.composite
def allergy_rule_strategy(draw: Any) -> ProtocolRule:
    allergy = draw(st.sampled_from(KNOWN_ALLERGIES))
    conflict_idx = draw(st.sampled_from(range(len(KNOWN_ALLERGY_CONFLICT_MEDS))))
    conflict_med = draw(st.sampled_from([KNOWN_ALLERGY_CONFLICT_MEDS[conflict_idx]]))
    severity = draw(st.sampled_from(RULE_SEVERITIES))
    return ProtocolRule(
        name=f"{allergy.title()} {conflict_med.title()} allergy",
        checker_type="allergy_checks",
        pattern={
            "patient_allergies": [allergy],
            "conflicts": {"medications": [conflict_med]},
        },
        severity=severity,
        message=f"Allergy: {allergy} conflicts with {conflict_med}",
    )


@st.composite
def allergy_interaction_config_strategy(draw: Any) -> ProtocolConfig:
    rules = draw(st.lists(allergy_rule_strategy(), min_size=1, max_size=5, unique_by=lambda r: r.name))
    return ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={"allergy_checks": rules},
    )


@st.composite
def medication_list_strategy(draw: Any, candidates: list[str] | None = None) -> list[ExtractedMedication]:
    pool = candidates or (KNOWN_TRIGGER_MEDS + KNOWN_CONFLICT_MEDS)
    count = draw(st.integers(min_value=1, max_value=6))
    chosen = draw(st.lists(st.sampled_from(pool), min_size=count, max_size=count))
    return [ExtractedMedication(name=m) for m in chosen]


@st.composite
def patient_with_allergies_strategy(draw: Any, allergy_pool: list[str] | None = None) -> PatientProfile:
    pool = allergy_pool or KNOWN_ALLERGIES
    count = draw(st.integers(min_value=1, max_value=min(4, len(pool))))
    allergies = draw(st.lists(st.sampled_from(pool), min_size=count, max_size=count, unique=True))
    return PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=allergies,
        diagnoses=[],
    )


def empty_extraction() -> StructuredExtraction:
    return StructuredExtraction(medications=[])


class TestDrugInteractionCheckerPBT:
    @given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
    @settings(max_examples=200)
    def test_both_sides_present_implies_alert(
        self, config: ProtocolConfig, meds: list[ExtractedMedication]
    ) -> None:
        # If extraction contains BOTH trigger AND conflict for a rule, alert is raised.
        trigger_conflict_pairs = []
        for rule in config.rules["drug_interactions"]:
            trigger = rule.pattern["trigger"]["medications"][0].lower()
            conflict = rule.pattern["conflicts"]["medications"][0].lower()
            trigger_conflict_pairs.append((trigger, conflict))

        med_names = {m.name.lower() for m in meds}
        matched_rules = [
            (t, c) for t, c in trigger_conflict_pairs if t in med_names and c in med_names
        ]
        assume(len(matched_rules) > 0)

        checker = DrugInteractionChecker(config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=[], diagnoses=[],
        )
        extraction = StructuredExtraction(medications=meds)

        alerts = checker.check(patient, extraction)
        assert len(alerts) >= len(matched_rules)

    @given(config=drug_interaction_config_strategy(), meds=medication_list_strategy())
    @settings(max_examples=200)
    def test_only_one_side_present_implies_no_alert(
        self, config: ProtocolConfig, meds: list[ExtractedMedication]
    ) -> None:
        # If only trigger OR only conflict (not both) for all rules, no alert.
        trigger_conflict_pairs = []
        for rule in config.rules["drug_interactions"]:
            trigger = rule.pattern["trigger"]["medications"][0].lower()
            conflict = rule.pattern["conflicts"]["medications"][0].lower()
            trigger_conflict_pairs.append((trigger, conflict))

        med_names = {m.name.lower() for m in meds}
        any_full_match = any(t in med_names and c in med_names for t, c in trigger_conflict_pairs)
        any_side_match = any(t in med_names or c in med_names for t, c in trigger_conflict_pairs)

        assume(any_side_match and not any_full_match)

        checker = DrugInteractionChecker(config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=[], diagnoses=[],
        )
        extraction = StructuredExtraction(medications=meds)

        alerts = checker.check(patient, extraction)
        assert len(alerts) == 0

    @given(config=drug_interaction_config_strategy())
    @settings(max_examples=100)
    def test_empty_extraction_never_alerts(self, config: ProtocolConfig) -> None:
        """Empty extraction MUST never produce alerts regardless of config."""
        checker = DrugInteractionChecker(config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=[], diagnoses=[],
        )
        alerts = checker.check(patient, empty_extraction())
        assert len(alerts) == 0

    @given(config=drug_interaction_config_strategy())
    @settings(max_examples=100)
    def test_no_config_rules_never_alerts(self, config: ProtocolConfig) -> None:
        """If config has no drug_interactions rules, no alerts."""
        empty_config = ProtocolConfig(
            version="1.0", settings={}, checkers={}, rules={},
        )
        checker = DrugInteractionChecker(empty_config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=[], diagnoses=[],
        )
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="warfarin"), ExtractedMedication(name="ibuprofen")]
        )
        alerts = checker.check(patient, extraction)
        assert len(alerts) == 0


class TestAllergyCheckerPBT:
    @given(
        config=allergy_interaction_config_strategy(),
        patient=patient_with_allergies_strategy(),
        meds=medication_list_strategy(candidates=KNOWN_ALLERGY_CONFLICT_MEDS),
    )
    @settings(max_examples=200)
    def test_allergy_and_conflict_med_implies_alert(
        self, config: ProtocolConfig, patient: PatientProfile, meds: list[ExtractedMedication]
    ) -> None:
        """If patient allergy X is configured AND extraction contains X-class conflict med, alert MUST be raised."""
        allergy_conflict_pairs = []
        for rule in config.rules["allergy_checks"]:
            allergy = rule.pattern["patient_allergies"][0].lower()
            conflict_med = rule.pattern["conflicts"]["medications"][0].lower()
            allergy_conflict_pairs.append((allergy, conflict_med))

        patient_allergies = {a.lower() for a in patient.allergies}
        med_names = {m.name.lower() for m in meds}
        matched_rules = [
            (a, c) for a, c in allergy_conflict_pairs
            if a in patient_allergies and c in med_names
        ]
        assume(len(matched_rules) > 0)

        checker = AllergyChecker(config)
        extraction = StructuredExtraction(medications=meds)
        alerts = checker.check(patient, extraction)
        assert len(alerts) >= len(matched_rules)

    @given(
        config=allergy_interaction_config_strategy(),
        patient=patient_with_allergies_strategy(),
        meds=medication_list_strategy(candidates=KNOWN_ALLERGY_CONFLICT_MEDS),
    )
    @settings(max_examples=200)
    def test_no_allergy_conflict_implies_no_alert(
        self, config: ProtocolConfig, patient: PatientProfile, meds: list[ExtractedMedication]
    ) -> None:
        """If no allergy-medications conflict exists across all rules, no alert MUST be raised."""
        allergy_conflict_pairs = []
        for rule in config.rules["allergy_checks"]:
            allergy = rule.pattern["patient_allergies"][0].lower()
            conflict_med = rule.pattern["conflicts"]["medications"][0].lower()
            allergy_conflict_pairs.append((allergy, conflict_med))

        patient_allergies = {a.lower() for a in patient.allergies}
        med_names = {m.name.lower() for m in meds}
        any_conflict = any(
            a in patient_allergies and c in med_names for a, c in allergy_conflict_pairs
        )
        assume(not any_conflict)

        checker = AllergyChecker(config)
        extraction = StructuredExtraction(medications=meds)
        alerts = checker.check(patient, extraction)
        assert len(alerts) == 0

    @given(config=allergy_interaction_config_strategy())
    @settings(max_examples=100)
    def test_empty_extraction_never_alerts(self, config: ProtocolConfig) -> None:
        """Empty extraction MUST never produce allergy alerts."""
        checker = AllergyChecker(config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=["penicillin"], diagnoses=[],
        )
        alerts = checker.check(patient, empty_extraction())
        assert len(alerts) == 0

    @given(config=allergy_interaction_config_strategy())
    @settings(max_examples=100)
    def test_no_allergies_never_alerts(self, config: ProtocolConfig) -> None:
        """Patient with no allergies MUST never trigger allergy alerts."""
        checker = AllergyChecker(config)
        patient = PatientProfile(
            patient_id="P1", first_name="John", last_name="Doe",
            dob=date(1980, 1, 1), allergies=[], diagnoses=[],
        )
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="amoxicillin")]
        )
        alerts = checker.check(patient, extraction)
        assert len(alerts) == 0

    @given(
        config=allergy_interaction_config_strategy(),
        patient=patient_with_allergies_strategy(allergy_pool=["unknown_allergy"]),
    )
    @settings(max_examples=100)
    def test_unconfigured_allergy_never_alerts(self, config: ProtocolConfig, patient: PatientProfile) -> None:
        """Allergy not referenced in any rule MUST never trigger an alert."""
        checker = AllergyChecker(config)
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="amoxicillin")]
        )
        alerts = checker.check(patient, extraction)
        assert len(alerts) == 0
