"""Tests for protocol registry."""

from datetime import date

from src.extraction.models import StructuredExtraction
from src.models import PatientProfile
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity
from src.protocols.registry import ProtocolRegistry


def test_registry_runs_all_checkers():
    """Test that registry runs all enabled checkers and returns alerts."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}, "allergy_checks": {"enabled": True}},
        rules={"drug_interactions": [], "allergy_checks": []},
    )

    registry = ProtocolRegistry(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    extraction = StructuredExtraction()

    alerts = registry.check_all(patient, extraction)

    assert isinstance(alerts, list)


def test_registry_initializes_only_enabled_checkers():
    """Test that registry only initializes checkers marked as enabled."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={
            "drug_interactions": {"enabled": True},
            "allergy_checks": {"enabled": False},
            "required_fields": {"enabled": True},
        },
        rules={"drug_interactions": [], "allergy_checks": [], "required_fields": []},
    )

    registry = ProtocolRegistry(config)
    enabled = registry.get_enabled_checkers()

    assert "drug_interactions" in enabled
    assert "required_fields" in enabled
    assert "allergy_checks" not in enabled


def test_registry_returns_empty_list_when_no_checkers_enabled():
    """Test that registry returns empty list when no checkers are enabled."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": False}, "allergy_checks": {"enabled": False}},
        rules={"drug_interactions": [], "allergy_checks": []},
    )

    registry = ProtocolRegistry(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    extraction = StructuredExtraction()

    alerts = registry.check_all(patient, extraction)

    assert alerts == []
    assert registry.get_enabled_checkers() == []


def test_registry_aggregates_alerts_from_multiple_checkers():
    """Test that registry aggregates alerts from all enabled checkers."""
    # Create a rule that will trigger an alert
    rule = ProtocolRule(
        name="missing_required_field",
        checker_type="required_fields",
        pattern={"required": ["patient_name"]},
        severity=ProtocolSeverity.HIGH,
        message="Patient name is required",
    )

    config = ProtocolConfig(
        version="1.0", settings={}, checkers={"required_fields": {"enabled": True}}, rules={"required_fields": [rule]}
    )

    registry = ProtocolRegistry(config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    # Extraction missing patient_name - should trigger alert
    extraction = StructuredExtraction(
        patient_name=None,  # Missing required field
        visit_type="consultation",
    )

    alerts = registry.check_all(patient, extraction)

    assert len(alerts) == 1
    assert alerts[0].message == "Patient name is required"


def test_registry_handles_missing_checker_config():
    """Test that registry handles missing checker configuration gracefully."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={
            "drug_interactions": {"enabled": True}
            # allergy_checks not in config
        },
        rules={"drug_interactions": []},
    )

    registry = ProtocolRegistry(config)

    # Should not raise error for missing checker
    enabled = registry.get_enabled_checkers()
    assert "drug_interactions" in enabled
    assert "allergy_checks" not in enabled
