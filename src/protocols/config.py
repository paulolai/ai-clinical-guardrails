from pathlib import Path

import yaml

from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def load_protocol_config(path: Path) -> ProtocolConfig:
    """Load and validate protocol configuration from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    # Validate required fields
    if "version" not in data:
        raise ValueError("Configuration must have a 'version' field")
    if "rules" not in data:
        raise ValueError("Configuration must have a 'rules' field")

    # Parse rules by checker type
    rules: dict[str, list[ProtocolRule]] = {}
    for checker_type, rule_list in data.get("rules", {}).items():
        rules[checker_type] = [
            ProtocolRule(
                name=rule["name"],
                checker_type=checker_type,
                pattern=rule["pattern"],
                severity=ProtocolSeverity(rule["severity"]),
                message=rule["message"],
            )
            for rule in rule_list
        ]

    return ProtocolConfig(
        version=data["version"], settings=data.get("settings", {}), checkers=data.get("checkers", {}), rules=rules
    )
