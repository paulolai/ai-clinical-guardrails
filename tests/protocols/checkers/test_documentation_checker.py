from datetime import date

from src.extraction.models import ExtractedMedication, ExtractedTemporalExpression, StructuredExtraction, TemporalType
from src.models import ComplianceSeverity, PatientProfile
from src.protocols.checkers.documentation_checker import RequiredFieldsChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def test_detects_missing_discharge_fields():
    """Test that missing required fields triggers an alert."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"required_fields": {"enabled": True}},
        rules={
            "required_fields": [
                ProtocolRule(
                    name="Discharge Summary",
                    checker_type="required_fields",
                    pattern={"encounter_type": "discharge", "required": ["medications", "temporal_expressions"]},
                    severity=ProtocolSeverity.HIGH,
                    message="Discharge summary missing required fields",
                )
            ]
        },
    )

    checker = RequiredFieldsChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Empty extraction - missing required fields
    extraction = StructuredExtraction()

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.HIGH
    assert alerts[0].message == "Discharge summary missing required fields"
    assert alerts[0].rule_id == "PROTOCOL_REQUIRED_FIELDS_DISCHARGE_SUMMARY"


def test_no_alert_when_all_fields_present():
    """Test that no alert is generated when all required fields are present."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"required_fields": {"enabled": True}},
        rules={
            "required_fields": [
                ProtocolRule(
                    name="Discharge Summary",
                    checker_type="required_fields",
                    pattern={"encounter_type": "discharge", "required": ["medications", "temporal_expressions"]},
                    severity=ProtocolSeverity.HIGH,
                    message="Discharge summary missing required fields",
                )
            ]
        },
    )

    checker = RequiredFieldsChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Extraction with all required fields
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="aspirin")],
        temporal_expressions=[ExtractedTemporalExpression(text="tomorrow", type=TemporalType.RELATIVE_DATE)],
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_alert_when_partial_fields_present():
    """Test that alert is generated when only some required fields are present."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"required_fields": {"enabled": True}},
        rules={
            "required_fields": [
                ProtocolRule(
                    name="Discharge Summary",
                    checker_type="required_fields",
                    pattern={
                        "encounter_type": "discharge",
                        "required": ["medications", "temporal_expressions", "diagnoses"],
                    },
                    severity=ProtocolSeverity.HIGH,
                    message="Discharge summary missing required fields",
                )
            ]
        },
    )

    checker = RequiredFieldsChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Extraction with only some required fields
    extraction = StructuredExtraction(
        medications=[ExtractedMedication(name="aspirin")],
        temporal_expressions=[],  # Missing
    )

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].severity == ComplianceSeverity.HIGH


def test_no_alert_without_config_rules():
    """Test that no alerts are generated when no rules configured."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"required_fields": {"enabled": True}},
        rules={},
    )

    checker = RequiredFieldsChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    extraction = StructuredExtraction()

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_no_alert_with_none_config():
    """Test that no alerts are generated when config is None."""
    checker = RequiredFieldsChecker(None)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    extraction = StructuredExtraction()

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 0


def test_multiple_rules():
    """Test handling of multiple required field rules."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"required_fields": {"enabled": True}},
        rules={
            "required_fields": [
                ProtocolRule(
                    name="Discharge Summary",
                    checker_type="required_fields",
                    pattern={"encounter_type": "discharge", "required": ["medications"]},
                    severity=ProtocolSeverity.HIGH,
                    message="Discharge summary missing medications",
                ),
                ProtocolRule(
                    name="Consultation Note",
                    checker_type="required_fields",
                    pattern={"encounter_type": "consultation", "required": ["diagnoses"]},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Consultation note missing diagnoses",
                ),
            ]
        },
    )

    checker = RequiredFieldsChecker(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Missing both medications and diagnoses
    extraction = StructuredExtraction()

    alerts = checker.check(patient, extraction)

    assert len(alerts) == 2
    severities = {alert.severity for alert in alerts}
    assert ComplianceSeverity.HIGH in severities
    assert ComplianceSeverity.CRITICAL in severities
