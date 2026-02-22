from datetime import date

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import ComplianceSeverity, PatientProfile
from src.protocols.checkers.allergy_checker import AllergyChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def test_detects_penicillin_allergy_conflict():
    """Test detection of penicillin allergy with amoxicillin prescription."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                )
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["penicillin"],
        diagnoses=[],
    )

    extraction = StructuredExtraction(medications=[ExtractedMedication(name="amoxicillin")])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.CRITICAL


def test_case_insensitive_allergy_matching():
    """Test that allergy and medication matching is case-insensitive."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["PENICILLIN"], "conflicts": {"medications": ["AMOXICILLIN"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                )
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["penicillin"],
        diagnoses=[],
    )

    extraction = StructuredExtraction(medications=[ExtractedMedication(name="amoxicillin")])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.CRITICAL


def test_no_alert_when_no_allergy():
    """Test that no alert is generated when patient has no matching allergy."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                )
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["sulfa"],  # Different allergy
        diagnoses=[],
    )

    extraction = StructuredExtraction(medications=[ExtractedMedication(name="amoxicillin")])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_no_alert_when_no_conflict():
    """Test that no alert is generated when conflicting med not prescribed."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                )
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["penicillin"],
        diagnoses=[],
    )

    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="aspirin")]  # Different med
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_empty_extraction_handling():
    """Test that empty extraction returns no alerts."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                )
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["penicillin"],
        diagnoses=[],
    )

    extraction = StructuredExtraction(medications=[])

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_multiple_allergy_rules():
    """Test detection of multiple allergy conflicts in one extraction."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"allergy_checks": {"enabled": True}},
        rules={
            "allergy_checks": [
                ProtocolRule(
                    name="Penicillin Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Patient allergic to penicillin",
                ),
                ProtocolRule(
                    name="Sulfa Allergy",
                    checker_type="allergy_checks",
                    pattern={"patient_allergies": ["sulfa"], "conflicts": {"medications": ["sulfamethoxazole"]}},
                    severity=ProtocolSeverity.HIGH,
                    message="Patient allergic to sulfa",
                ),
            ]
        },
    )

    checker = AllergyChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["penicillin", "sulfa"],
        diagnoses=[],
    )

    extraction = StructuredExtraction(
        medications=[
            ExtractedMedication(name="amoxicillin"),
            ExtractedMedication(name="sulfamethoxazole"),
        ]
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 2
    severities = {alert.severity for alert in alerts}
    assert ComplianceSeverity.CRITICAL in severities
    assert ComplianceSeverity.HIGH in severities
