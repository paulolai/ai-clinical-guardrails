#!/usr/bin/env python3
"""CLI tool for managing and testing medical protocol rules."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import PatientProfile
from src.protocols.config import load_protocol_config
from src.protocols.registry import ProtocolRegistry


def validate_config(args: argparse.Namespace) -> None:
    """Validate configuration file syntax."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    try:
        config = load_protocol_config(config_path)
        print("✓ Config loaded successfully")
        print(f"  Version: {config.version}")
        print(f"  Enabled checkers: {list(config.checkers.keys())}")
        print(f"  Total rules: {sum(len(rules) for rules in config.rules.values())}")

        # Show enabled checkers
        for checker_name, checker_config in config.checkers.items():
            enabled = checker_config.get("enabled", False)
            status = "✓ enabled" if enabled else "✗ disabled"
            print(f"  - {checker_name}: {status}")

            if enabled and checker_name in config.rules:
                print(f"    Rules: {len(config.rules[checker_name])}")

        sys.exit(0)
    except Exception as e:
        print(f"✗ Config validation failed: {e}")
        sys.exit(1)


def list_rules(args: argparse.Namespace) -> None:
    """List all configured rules."""
    config_path = Path(args.config)
    config = load_protocol_config(config_path)

    print(f"Protocol Rules (version {config.version})")
    print("=" * 60)

    for checker_name, rules in config.rules.items():
        checker_config = config.checkers.get(checker_name, {})
        enabled = checker_config.get("enabled", False)
        status = "[ENABLED]" if enabled else "[DISABLED]"

        print(f"\n{checker_name} {status}")
        print("-" * 40)

        for rule in rules:
            print(f"  • {rule.name}")
            print(f"    Severity: {rule.severity.value}")
            print(f"    Message: {rule.message}")


def check_transcript(args: argparse.Namespace) -> None:
    """Check a transcript against protocols."""
    config_path = Path(args.config)
    config = load_protocol_config(config_path)

    registry = ProtocolRegistry(config)

    # Create sample patient
    patient = PatientProfile(
        patient_id=args.patient_id or "CLI-PATIENT",
        first_name="Test",
        last_name="Patient",
        dob=date(1990, 1, 1),
        allergies=args.allergies.split(",") if args.allergies else [],
        diagnoses=[],
    )

    # Create extraction from medications list
    medications = [ExtractedMedication(name=m.strip()) for m in args.medications.split(",")] if args.medications else []
    extraction = StructuredExtraction(medications=medications)

    print(f"Checking patient: {patient.patient_id}")
    print(f"Allergies: {patient.allergies}")
    print(f"Medications: {[m.name for m in medications]}")
    print("-" * 60)

    alerts = registry.check_all(patient, extraction)

    if not alerts:
        print("✓ No protocol violations detected")
    else:
        print(f"⚠ {len(alerts)} protocol violation(s) detected:")
        for alert in alerts:
            print(f"  [{alert.severity.value}] {alert.message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Medical Protocols CLI - Validate and test clinical safety rules")
    parser.add_argument("--config", default="config/medical_protocols.yaml", help="Path to protocol configuration file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate-config command
    validate_parser = subparsers.add_parser("validate-config", help="Validate configuration file syntax")
    validate_parser.set_defaults(func=validate_config)

    # list-rules command
    list_parser = subparsers.add_parser("list-rules", help="List all configured rules")
    list_parser.set_defaults(func=list_rules)

    # check command
    check_parser = subparsers.add_parser("check", help="Check a transcript against protocols")
    check_parser.add_argument("--patient-id", help="Patient ID")
    check_parser.add_argument("--allergies", help="Comma-separated list of allergies")
    check_parser.add_argument("--medications", help="Comma-separated list of medications")
    check_parser.set_defaults(func=check_transcript)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
