from src.protocols.checkers.base import ProtocolChecker


def test_base_checker_interface():
    # Abstract class - just verify it exists
    assert hasattr(ProtocolChecker, "check")
    assert hasattr(ProtocolChecker, "name")
