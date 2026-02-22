from pathlib import Path

import pytest

from src.protocols.config import load_protocol_config
from src.protocols.models import ProtocolConfig, ProtocolSeverity


def test_load_valid_config():
    config_path = Path("config/medical_protocols.yaml")
    config = load_protocol_config(config_path)

    assert config.version == "1.0"
    assert "drug_interactions" in config.checkers
    assert "allergy_checks" in config.checkers


def test_config_returns_protocol_config_type():
    config_path = Path("config/medical_protocols.yaml")
    config = load_protocol_config(config_path)

    assert isinstance(config, ProtocolConfig)
    assert hasattr(config, "version")
    assert hasattr(config, "settings")
    assert hasattr(config, "checkers")
    assert hasattr(config, "rules")


def test_config_parses_rules_correctly():
    config_path = Path("config/medical_protocols.yaml")
    config = load_protocol_config(config_path)

    assert "drug_interactions" in config.rules
    assert "allergy_checks" in config.rules

    # Check drug interaction rule
    drug_rules = config.rules["drug_interactions"]
    assert len(drug_rules) == 1
    assert drug_rules[0].name == "Warfarin NSAID"
    assert drug_rules[0].checker_type == "drug_interactions"
    assert drug_rules[0].severity == ProtocolSeverity.CRITICAL
    assert "bleeding risk" in drug_rules[0].message


def test_missing_version_raises_error(tmp_path):
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text("""
settings:
  hot_reload: false
rules: {}
""")

    with pytest.raises(ValueError, match="version"):
        load_protocol_config(config_file)


def test_missing_rules_raises_error(tmp_path):
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text("""
version: "1.0"
settings:
  hot_reload: false
""")

    with pytest.raises(ValueError, match="rules"):
        load_protocol_config(config_file)
