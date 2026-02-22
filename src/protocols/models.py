from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ProtocolSeverity(StrEnum):
    """Severity levels for protocol violations."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class ProtocolRule:
    """A single protocol rule with pattern matching."""

    name: str
    checker_type: str
    pattern: dict[str, Any]
    severity: ProtocolSeverity
    message: str


@dataclass(frozen=True)
class ProtocolConfig:
    """Configuration for all protocol checkers."""

    version: str
    settings: dict[str, Any]
    checkers: dict[str, dict[str, Any]]
    rules: dict[str, list[ProtocolRule]]
