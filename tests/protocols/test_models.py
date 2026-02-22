from src.protocols.models import ProtocolRule, ProtocolSeverity


def test_protocol_rule_creation():
    rule = ProtocolRule(
        name="Warfarin NSAID",
        checker_type="drug_interactions",
        pattern={"trigger": ["warfarin"], "conflicts": ["ibuprofen"]},
        severity=ProtocolSeverity.CRITICAL,
        message="Warfarin + NSAID interaction detected",
    )
    assert rule.name == "Warfarin NSAID"
    assert rule.severity == ProtocolSeverity.CRITICAL
