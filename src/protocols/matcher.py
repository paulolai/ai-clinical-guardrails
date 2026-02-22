"""Pattern matcher implementations for protocol rules."""

from abc import ABC, abstractmethod
from typing import Any

from src.extraction.models import StructuredExtraction
from src.models import PatientProfile


class PatternMatcher(ABC):
    """Base class for pattern matching logic."""

    @abstractmethod
    def matches(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict[str, Any],
    ) -> bool:
        """Check if pattern matches patient/extraction data."""
        pass


class MedicationPatternMatcher(PatternMatcher):
    """Matches medication names in extraction against pattern."""

    def matches(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict[str, Any],
    ) -> bool:
        target_meds = {m.lower() for m in pattern.get("medications", [])}

        # Check extracted medications
        extracted_names = {m.name.lower() for m in extraction.medications}

        return bool(target_meds & extracted_names)


class AllergyPatternMatcher(PatternMatcher):
    """Matches patient allergies against conflict patterns."""

    def matches(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict[str, Any],
    ) -> bool:
        patient_allergies = {a.lower() for a in patient.allergies}
        target_allergies = {a.lower() for a in pattern.get("patient_allergies", [])}

        return bool(patient_allergies & target_allergies)


class FieldPresenceMatcher(PatternMatcher):
    """Matches required field presence in extraction."""

    def matches(
        self,
        patient: PatientProfile,
        extraction: StructuredExtraction,
        pattern: dict[str, Any],
    ) -> bool:
        required_fields = pattern.get("required", [])

        for field in required_fields:
            value = getattr(extraction, field, None)
            if value is None or (isinstance(value, list) and len(value) == 0):
                return False

        return True
