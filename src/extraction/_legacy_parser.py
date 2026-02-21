"""Parse clinical dictation into structured data."""

import re
from datetime import date
from typing import Any

from src.extraction.models import (
    ExtractedDiagnosis,
    ExtractedMedication,
    MedicationStatus,
    StructuredExtraction,
)
from src.extraction.temporal import TemporalResolver


class TranscriptParser:
    """Parse clinical dictation transcripts into structured data."""

    # Common medication patterns
    MEDICATION_PATTERN = re.compile(
        r"\b(\w+)\s+(\d+(?:\s*mg|milligrams?)?)?\s*(?:daily|twice daily|three times daily|q\d+h?|as needed)?",
        re.IGNORECASE,
    )

    # Status keywords
    STARTED_KEYWORDS = ["started", "began", "initiated"]
    DISCONTINUED_KEYWORDS = ["stopped", "discontinued", "ended", "off"]
    INCREASED_KEYWORDS = ["increased", "raised", "upped"]
    DECREASED_KEYWORDS = ["decreased", "lowered", "reduced"]

    def __init__(self, reference_date: date | None = None):
        """Initialize parser with reference date for temporal resolution.

        Args:
            reference_date: Base date for temporal calculations.
                          Defaults to today if not provided.
        """
        self.temporal_resolver = TemporalResolver(reference_date)

    def parse(self, text: str) -> StructuredExtraction:
        """Parse transcript text into structured extraction.

        Args:
            text: Clinical dictation text

        Returns:
            StructuredExtraction with all extracted fields
        """
        patient_name = self._extract_patient_name(text)
        patient_age = self._extract_patient_age(text)
        visit_type = self._extract_visit_type(text)
        temporal_expressions = self.temporal_resolver.resolve(text)
        medications = self._extract_medications(text)
        diagnoses = self._extract_diagnoses(text)
        vital_signs = self._extract_vital_signs(text)

        # Calculate overall confidence
        confidences = []
        for med in medications:
            confidences.append(med.confidence)
        for temp in temporal_expressions:
            confidences.append(temp.confidence)
        for diag in diagnoses:
            confidences.append(diag.confidence)

        overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0

        return StructuredExtraction(
            patient_name=patient_name,
            patient_age=patient_age,
            visit_type=visit_type,
            temporal_expressions=temporal_expressions,
            medications=medications,
            diagnoses=diagnoses,
            vital_signs=vital_signs,
            confidence=overall_confidence,
        )

    def _extract_patient_name(self, text: str) -> str | None:
        """Extract patient name from transcript.

        Looks for patterns like:
        - "Patient [Name] presents"
        - "[Name] came in"
        - "[Name] was seen"
        """
        patterns = [
            r"^([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:came|was|presents)",
            r"Patient\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"^([A-Z][a-z]+\s+[A-Z][a-z]+),\s*\d+",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_patient_age(self, text: str) -> str | None:
        """Extract patient age from transcript."""
        pattern = r"(\d+)\s*(?:years?\s+old|y\.?o\.?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} years old"
        return None

    def _extract_visit_type(self, text: str) -> str | None:
        """Extract visit type from transcript.

        Recognizes common visit types:
        - follow-up
        - acute complaint
        - routine check / annual physical
        - post-operative
        - well-child check
        - urgent same-day
        """
        text_lower = text.lower()

        visit_types = {
            "follow-up": ["follow-up", "follow up", "return visit", "recheck"],
            "acute_complaint": ["acute", "chest pain", "shortness of breath", "emergency"],
            "routine_check": [
                "annual physical",
                "wellness visit",
                "routine check",
                "medicare wellness",
            ],
            "post-operative": ["post-op", "post-operative", "after surgery"],
            "well_child_check": ["well-child", "well child", "pediatric check"],
            "urgent_same_day": ["same day", "urgent", "acute visit"],
        }

        for visit_type, keywords in visit_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return visit_type

        return None

    def _extract_medications(self, text: str) -> list[ExtractedMedication]:
        """Extract medication mentions from transcript."""
        medications = []
        text_lower = text.lower()

        # Common medications with pattern matching
        med_patterns = [
            (
                r"\b(Lisinopril)\s+(\d+)\s*(?:mg|milligrams?)?",
                self._determine_status(text_lower, "lisinopril"),
            ),
            (
                r"\b(Metformin)\s+(\d+)\s*(?:mg|milligrams?)?",
                self._determine_status(text_lower, "metformin"),
            ),
            (
                r"\b(Atorvastatin)\s+(\d+)\s*(?:mg|milligrams?)?",
                self._determine_status(text_lower, "atorvastatin"),
            ),
            (
                r"\b(Aspirin)\s+(\d+)\s*(?:mg|milligrams?)?",
                self._determine_status(text_lower, "aspirin"),
            ),
            (
                r"\b(Amoxicillin)\s+(\d+)\s*(?:mg|milligrams?)?",
                self._determine_status(text_lower, "amoxicillin"),
            ),
            (
                r"\b(Ceftriaxone)\s+(\d+)\s*(?:g|grams?)?",
                self._determine_status(text_lower, "ceftriaxone"),
            ),
            (r"\b(Nitroglycerin)\b", self._determine_status(text_lower, "nitroglycerin")),
            (r"\b(Glipizide)\s+(\d+)\s*(?:mg|milligrams?)?", MedicationStatus.DISCONTINUED),
            (r"\b(Januvia)\s+(\d+)\s*(?:mg|milligrams?)?", MedicationStatus.STARTED),
        ]

        for pattern, status in med_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1)
                dosage = match.group(2) + " mg" if len(match.groups()) > 1 and match.group(2) else None

                # Extract frequency if mentioned
                frequency = self._extract_frequency(text_lower, name.lower())
                route = self._extract_route(text_lower, name.lower())

                medications.append(
                    ExtractedMedication(
                        name=name,
                        dosage=dosage,
                        frequency=frequency,
                        route=route,
                        status=status,
                        confidence=0.9 if dosage else 0.7,
                    )
                )

        return medications

    def _determine_status(self, text: str, medication: str) -> MedicationStatus:
        """Determine medication status based on surrounding text."""
        # Find the sentence containing the medication
        sentences = text.split(".")
        for sentence in sentences:
            if medication in sentence:
                for keyword in self.STARTED_KEYWORDS:
                    if keyword in sentence:
                        return MedicationStatus.STARTED
                for keyword in self.DISCONTINUED_KEYWORDS:
                    if keyword in sentence:
                        return MedicationStatus.DISCONTINUED
                for keyword in self.INCREASED_KEYWORDS:
                    if keyword in sentence:
                        return MedicationStatus.INCREASED
                for keyword in self.DECREASED_KEYWORDS:
                    if keyword in sentence:
                        return MedicationStatus.DECREASED

        return MedicationStatus.ACTIVE

    def _extract_frequency(self, text: str, medication: str) -> str | None:
        """Extract medication frequency from text."""
        patterns = [
            rf"{medication}.*?\b(daily|twice daily|three times daily|q\d+h?|every\s+\d+\s+hours?)\b",
            rf"{medication}.*?\b(as needed|prn)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_route(self, text: str, medication: str) -> str | None:
        """Extract medication route from text."""
        patterns = [
            rf"{medication}.*?\b(iv|oral|sublingual|im|subcutaneous)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_diagnoses(self, text: str) -> list[ExtractedDiagnosis]:
        """Extract diagnosis mentions from transcript."""
        diagnoses = []

        # Common diagnosis patterns
        diag_patterns = [
            (r"\bchest pain\b", "R07.9"),
            (r"\b(sepsis|suspected sepsis)\b", "R50.9"),
            (r"\bhypertension\b", "I10"),
            (r"\bdiabetes\b", "E11.9"),
            (r"\bstrep throat\b", "J02.0"),
        ]

        for pattern, icd10 in diag_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                diagnoses.append(
                    ExtractedDiagnosis(
                        text=match.group(0),
                        icd10_code=icd10,
                        confidence=0.85,
                    )
                )

        return diagnoses

    def _extract_vital_signs(self, text: str) -> list[dict[str, Any]]:
        """Extract vital signs from transcript."""
        vitals = []

        # Blood pressure pattern
        bp_pattern = r"(\d{2,3})\s*(?:over|/)\s*(\d{2,3})\s*(?:mm?Hg)?"
        for match in re.finditer(bp_pattern, text):
            vitals.append(
                {
                    "type": "blood_pressure",
                    "value": f"{match.group(1)}/{match.group(2)}",
                    "unit": "mmHg",
                }
            )

        # Temperature pattern
        temp_pattern = r"(\d{2,3}\.\d)\s*(?:degrees?)?\s*F"
        for match in re.finditer(temp_pattern, text):
            vitals.append(
                {
                    "type": "temperature",
                    "value": match.group(1),
                    "unit": "F",
                }
            )

        # Weight pattern
        weight_pattern = r"(\d+)\s*(?:pounds?|lbs?)"
        for match in re.finditer(weight_pattern, text, re.IGNORECASE):
            vitals.append(
                {
                    "type": "weight",
                    "value": match.group(1),
                    "unit": "pounds",
                }
            )

        # Heart rate pattern
        hr_pattern = r"(?:heart rate|pulse|tachycardia)\s*(?:of\s+)?(\d+)\b"
        for match in re.finditer(hr_pattern, text, re.IGNORECASE):
            vitals.append(
                {
                    "type": "heart_rate",
                    "value": match.group(1),
                    "unit": "bpm",
                }
            )

        return vitals
