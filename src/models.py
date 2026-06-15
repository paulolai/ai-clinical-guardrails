from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, Field

from src.extraction.models import ExtractedMedication, StructuredExtraction  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """Standard Result pattern for deterministic error handling.

    Uses dataclass instead of Pydantic BaseModel to support proper generic typing.
    """

    is_success: bool
    value: T | None = None
    error: E | None = None

    @classmethod
    def success(cls, value: T) -> "Result[T, E]":
        return cls(value=value, is_success=True)

    @classmethod
    def failure(cls, error: E) -> "Result[T, E]":
        return cls(error=error, is_success=False)

    def unwrap(self) -> T:
        """Return the success value or raise ValueError."""
        if self.is_success and self.value is not None:
            return self.value
        raise ValueError(f"Called unwrap() on a Failure: {self.error}")

    def unwrap_error(self) -> E:
        """Return the error value or raise ValueError."""
        if not self.is_success and self.error is not None:
            return self.error
        raise ValueError("Called unwrap_error() on a Success")

    def map(self, fn: "Callable[[T], U]") -> "Result[U, E]":
        """Transform the success value, preserving the error path."""
        if self.is_success:
            return Result.success(fn(self.value))  # type: ignore[arg-type]
        return Result.failure(self.error)  # type: ignore[arg-type]

    def map_error(self, fn: "Callable[[E], F]") -> "Result[T, F]":
        """Transform the error value, preserving the success path."""
        if not self.is_success:
            return Result.failure(fn(self.error))  # type: ignore[arg-type]
        return Result.success(self.value)  # type: ignore[arg-type]

    def chain(self, fn: "Callable[[T], Result[U, E]]") -> "Result[U, E]":
        """Monadic bind: apply fn only on success, short-circuit on failure."""
        if self.is_success:
            return fn(self.value)  # type: ignore[arg-type]
        return Result.failure(self.error)  # type: ignore[arg-type]


class ComplianceSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceAlert(BaseModel):
    rule_id: str
    message: str
    severity: ComplianceSeverity
    field: str | None = None


class PatientProfile(BaseModel):
    patient_id: str = Field(..., description="Unique clinical identifier")
    first_name: str
    last_name: str
    dob: date
    allergies: list[str] = Field(default_factory=list)
    diagnoses: list[str] = Field(default_factory=list)


class EMRContext(BaseModel):
    visit_id: str
    patient_id: str
    admission_date: datetime
    discharge_date: datetime | None = None
    attending_physician: str
    raw_notes: str


class AIGeneratedOutput(BaseModel):
    summary_text: str
    extracted_dates: list[date] = Field(default_factory=list)
    extracted_diagnoses: list[str] = Field(default_factory=list)
    extracted_medications: list["ExtractedMedication"] = Field(default_factory=list)
    suggested_billing_codes: list[str] = Field(default_factory=list)
    contains_pii: bool = False


class VerificationResult(BaseModel):
    is_safe_to_file: bool
    score: float = Field(..., ge=0.0, le=1.0)
    alerts: list[ComplianceAlert] = Field(default_factory=list)


class ClinicalNote(BaseModel):
    """AI-generated clinical note for review."""

    note_id: str = Field(..., description="Unique identifier for this note")
    patient_id: str = Field(..., description="FHIR Patient ID")
    encounter_id: str = Field(..., description="FHIR Encounter ID")
    generated_at: datetime = Field(..., description="When the AI generated this note")
    sections: dict[str, str] = Field(
        default_factory=dict, description="Note sections (chief_complaint, assessment, plan, etc.)"
    )
    extraction: StructuredExtraction = Field(..., description="Structured data extracted from the note")


class UnifiedReview(BaseModel):
    """Combined view for clinician review."""

    note: ClinicalNote = Field(..., description="The AI-generated note")
    emr_context: EMRContext = Field(..., description="Patient data from EMR at verification time")
    verification: VerificationResult = Field(..., description="Compliance verification results")
    review_url: str = Field(..., description="URL for accessing this review")
    created_at: datetime = Field(default_factory=datetime.now, description="When this review was generated")
