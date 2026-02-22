from datetime import date

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import ComplianceSeverity, PatientProfile
from src.protocols.checkers.drug_checker import DrugInteractionChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def test_detects_warfarin_nsaid_interaction():
    # Create minimal config
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                )
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="warfarin"), ExtractedMedication(name="ibuprofen")]
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.CRITICAL


def test_case_insensitive_matching():
    """Test that medication matching is case-insensitive."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["Warfarin"]}, "conflicts": {"medications": ["IBUPROFEN"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                )
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Test with lowercase extraction
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="warfarin"), ExtractedMedication(name="ibuprofen")]
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.CRITICAL


def test_no_alert_when_only_trigger_present():
    """Test that no alert is generated when only trigger medication is present."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                )
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Only trigger med present
    extraction = StructuredExtraction(medications=[ExtractedMedication(name="warfarin")])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_no_alert_when_only_conflict_present():
    """Test that no alert is generated when only conflict medication is present."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                )
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Only conflict med present
    extraction = StructuredExtraction(medications=[ExtractedMedication(name="ibuprofen")])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_empty_extraction_handling():
    """Test that empty extraction returns no alerts."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                )
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Empty extraction
    extraction = StructuredExtraction(medications=[])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_multiple_interactions_in_one_extraction():
    """Test detection of multiple drug interactions in a single extraction."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Warfarin + NSAID interaction",
                ),
                ProtocolRule(
                    name="ACE Inhibitor Potassium",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["lisinopril"]}, "conflicts": {"medications": ["potassium"]}},
                    severity=ProtocolSeverity.HIGH,
                    message="ACE inhibitor + Potassium interaction",
                ),
            ]
        },
    )

    checker = DrugInteractionChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Both interactions present
    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="warfarin"),
            ExtractedMedication(name="ibuprofen"),
            ExtractedMedication(name="lisinopril"),
            ExtractedMedication(name="potassium"),
        ]
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 2
    severities = {alert.severity for alert in alerts}
    assert ComplianceSeverity.CRITICAL in severities
    assert ComplianceSeverity.HIGH in severities
