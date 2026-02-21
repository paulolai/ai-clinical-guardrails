from datetime import date, datetime
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
E = TypeVar("E")


class Result(BaseModel):
    """Standard Result pattern for deterministic error handling."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: T | None = None
    error: E | None = None
    is_success: bool

    @classmethod
    def success(cls, value: T) -> "Result[T, E]":
        return cls(value=value, is_success=True)

    @classmethod
    def failure(cls, error: E) -> "Result[T, E]":
        return cls(error=error, is_success=False)

    def __class_getitem__(cls, item):
        return super().__class_getitem__(item)


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
    suggested_billing_codes: list[str] = Field(default_factory=list)
    contains_pii: bool = False


class VerificationResult(BaseModel):
    is_safe_to_file: bool
    score: float = Field(..., ge=0.0, le=1.0)
    alerts: list[ComplianceAlert] = Field(default_factory=list)
