"""Tests for pattern matcher module."""

from datetime import date

from src.extraction.models import ExtractedDiagnosis, ExtractedMedication, StructuredExtraction
from src.models import PatientProfile
from src.protocols.matcher import (
    AllergyPatternMatcher,
    FieldPresenceMatcher,
    MedicationPatternMatcher,
)


class TestMedicationPatternMatcher:
    """Tests for MedicationPatternMatcher."""

    def test_medication_matcher_detects_trigger(self):
        matcher = MedicationPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
            allergies=[],
            diagnoses=[],
        )
        extraction = StructuredExtraction(medications=[ExtractedMedication(name="warfarin")])

        pattern = {"medications": ["warfarin", "coumadin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True

    def test_medication_matcher_case_insensitive(self):
        matcher = MedicationPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(medications=[ExtractedMedication(name="WARFARIN")])

        pattern = {"medications": ["warfarin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True

    def test_medication_matcher_no_match(self):
        matcher = MedicationPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(medications=[ExtractedMedication(name="aspirin")])

        pattern = {"medications": ["warfarin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_medication_matcher_empty_extraction(self):
        matcher = MedicationPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(medications=[])

        pattern = {"medications": ["warfarin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_medication_matcher_empty_pattern(self):
        matcher = MedicationPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(medications=[ExtractedMedication(name="warfarin")])

        pattern = {"medications": []}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False


class TestAllergyPatternMatcher:
    """Tests for AllergyPatternMatcher."""

    def test_allergy_matcher_detects_match(self):
        matcher = AllergyPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
            allergies=["penicillin"],
        )
        extraction = StructuredExtraction()

        pattern = {"patient_allergies": ["penicillin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True

    def test_allergy_matcher_case_insensitive(self):
        matcher = AllergyPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
            allergies=["PENICILLIN"],
        )
        extraction = StructuredExtraction()

        pattern = {"patient_allergies": ["penicillin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True

    def test_allergy_matcher_no_match(self):
        matcher = AllergyPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
            allergies=["sulfa"],
        )
        extraction = StructuredExtraction()

        pattern = {"patient_allergies": ["penicillin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_allergy_matcher_empty_patient_allergies(self):
        matcher = AllergyPatternMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
            allergies=[],
        )
        extraction = StructuredExtraction()

        pattern = {"patient_allergies": ["penicillin"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False


class TestFieldPresenceMatcher:
    """Tests for FieldPresenceMatcher."""

    def test_field_presence_all_required_present(self):
        matcher = FieldPresenceMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="warfarin")],
            diagnoses=[],
        )

        pattern = {"required": ["medications"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True

    def test_field_presence_missing_field(self):
        matcher = FieldPresenceMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(medications=[])

        pattern = {"required": ["medications"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_field_presence_none_field(self):
        matcher = FieldPresenceMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(patient_name="John")

        pattern = {"required": ["medications"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_field_presence_multiple_required(self):
        matcher = FieldPresenceMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="warfarin")],
            diagnoses=[],
        )

        pattern = {"required": ["medications", "diagnoses"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is False

    def test_field_presence_all_multiple_required_present(self):
        matcher = FieldPresenceMatcher()
        patient = PatientProfile(
            patient_id="P1",
            first_name="John",
            last_name="Doe",
            dob=date(1980, 1, 1),
        )
        extraction = StructuredExtraction(
            medications=[ExtractedMedication(name="warfarin")],
            diagnoses=[ExtractedDiagnosis(text="diabetes")],
        )

        pattern = {"required": ["medications", "diagnoses"]}
        result = matcher.matches(patient, extraction, pattern)

        assert result is True
