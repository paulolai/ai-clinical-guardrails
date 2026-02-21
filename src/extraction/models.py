"""Data models for extraction layer."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class TemporalType(StrEnum):
    """Types of temporal expressions."""

    RELATIVE_DATE = "relative_date"
    ABSOLUTE_DATE = "absolute_date"
    ABSOLUTE_TIME = "absolute_time"
    DURATION = "duration"
    AMBIGUOUS = "ambiguous"


class MedicationStatus(StrEnum):
    """Status of medication mentions."""

    ACTIVE = "active"
    STARTED = "started"
    DISCONTINUED = "discontinued"
    INCREASED = "increased"
    DECREASED = "decreased"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExtractedTemporalExpression:
    """A temporal expression extracted from text."""

    text: str
    type: TemporalType
    normalized_date: date | None = None
    confidence: float = 1.0
    note: str | None = None


@dataclass(frozen=True)
class ExtractedMedication:
    """A medication mention extracted from text."""

    name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus = MedicationStatus.UNKNOWN
    start_date: date | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ExtractedDiagnosis:
    """A diagnosis mention extracted from text."""

    text: str
    icd10_code: str | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ExtractionResult:
    """Result of extracting a specific field from text."""

    field_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredExtraction:
    """Complete structured data extracted from a transcript."""

    patient_name: str | None = None
    patient_age: str | None = None
    visit_type: str | None = None
    temporal_expressions: list[ExtractedTemporalExpression] = field(default_factory=list)
    medications: list[ExtractedMedication] = field(default_factory=list)
    diagnoses: list[ExtractedDiagnosis] = field(default_factory=list)
    vital_signs: list[dict] = field(default_factory=list)
    confidence: float = 1.0

    def has_low_confidence_extractions(self, threshold: float = 0.7) -> bool:
        """Check if any extraction has confidence below threshold."""
        for med in self.medications:
            if med.confidence < threshold:
                return True
        for temp in self.temporal_expressions:
            if temp.confidence < threshold:
                return True
        for diag in self.diagnoses:
            if diag.confidence < threshold:
                return True
        return self.confidence < threshold
