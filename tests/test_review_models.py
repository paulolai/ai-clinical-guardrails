"""Tests for ClinicalNote and UnifiedReview models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.extraction.models import (
    ExtractedDiagnosis,
    ExtractedMedication,
    ExtractedTemporalExpression,
    MedicationStatus,
    StructuredExtraction,
    TemporalType,
)
from src.models import (
    ClinicalNote,
    ComplianceAlert,
    ComplianceSeverity,
    EMRContext,
    UnifiedReview,
    VerificationResult,
)


class TestClinicalNote:
    """Tests for the ClinicalNote model."""

    def test_create_clinical_note_with_valid_data(self):
        """Test creating a ClinicalNote with all required fields."""
        extraction = StructuredExtraction(
            patient_name="John Doe",
            patient_age="45",
            visit_type="Follow-up",
        )

        note = ClinicalNote(
            note_id="NOTE-001",
            patient_id="PAT-123",
            encounter_id="ENC-456",
            generated_at=datetime(2024, 1, 15, 10, 30),
            sections={
                "chief_complaint": "Chest pain",
                "assessment": "Stable angina",
                "plan": "Continue current medications",
            },
            extraction=extraction,
        )

        assert note.note_id == "NOTE-001"
        assert note.patient_id == "PAT-123"
        assert note.encounter_id == "ENC-456"
        assert note.generated_at == datetime(2024, 1, 15, 10, 30)
        assert note.sections["chief_complaint"] == "Chest pain"
        assert note.extraction.patient_name == "John Doe"

    def test_clinical_note_with_empty_sections(self):
        """Test ClinicalNote with empty sections (uses default)."""
        extraction = StructuredExtraction()

        note = ClinicalNote(
            note_id="NOTE-002",
            patient_id="PAT-456",
            encounter_id="ENC-789",
            generated_at=datetime(2024, 1, 15),
            extraction=extraction,
        )

        assert note.sections == {}

    def test_clinical_note_empty_patient_id_is_valid(self):
        """Test that empty patient_id is allowed (Pydantic default behavior)."""
        extraction = StructuredExtraction()

        # Note: Empty string is valid for str field unless min_length is specified
        note = ClinicalNote(
            note_id="NOTE-003",
            patient_id="",
            encounter_id="ENC-001",
            generated_at=datetime(2024, 1, 15),
            extraction=extraction,
        )

        assert note.patient_id == ""

    def test_clinical_note_missing_required_field_fails(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalNote(
                note_id="NOTE-004",
                # Missing patient_id
                encounter_id="ENC-001",
                generated_at=datetime(2024, 1, 15),
                extraction=StructuredExtraction(),
            )

        assert "patient_id" in str(exc_info.value)

    def test_clinical_note_with_nested_structured_extraction(self):
        """Test ClinicalNote with fully populated StructuredExtraction."""
        extraction = StructuredExtraction(
            patient_name="Jane Smith",
            patient_age="32",
            visit_type="Initial consultation",
            temporal_expressions=[
                ExtractedTemporalExpression(
                    text="yesterday",
                    type=TemporalType.RELATIVE_DATE,
                )
            ],
            medications=[
                ExtractedMedication(
                    name="Metformin",
                    dosage="500mg",
                    frequency="twice daily",
                    status=MedicationStatus.ACTIVE,
                )
            ],
            diagnoses=[
                ExtractedDiagnosis(
                    text="Type 2 Diabetes",
                    icd10_code="E11.9",
                )
            ],
        )

        note = ClinicalNote(
            note_id="NOTE-005",
            patient_id="PAT-789",
            encounter_id="ENC-999",
            generated_at=datetime(2024, 1, 15, 14, 0),
            sections={"assessment": "Diabetes management"},
            extraction=extraction,
        )

        assert len(note.extraction.medications) == 1
        assert note.extraction.medications[0].name == "Metformin"
        assert len(note.extraction.diagnoses) == 1
        assert note.extraction.diagnoses[0].icd10_code == "E11.9"


class TestUnifiedReview:
    """Tests for the UnifiedReview model."""

    def test_create_unified_review_with_valid_data(self):
        """Test creating a UnifiedReview with all components."""
        # Create ClinicalNote
        note = ClinicalNote(
            note_id="NOTE-001",
            patient_id="PAT-123",
            encounter_id="ENC-456",
            generated_at=datetime(2024, 1, 15, 10, 30),
            sections={"assessment": "Hypertension"},
            extraction=StructuredExtraction(patient_name="John Doe"),
        )

        # Create EMRContext
        emr_context = EMRContext(
            visit_id="VISIT-001",
            patient_id="PAT-123",
            admission_date=datetime(2024, 1, 15, 9, 0),
            attending_physician="Dr. Smith",
            raw_notes="Patient admitted for hypertension monitoring",
        )

        # Create VerificationResult
        verification = VerificationResult(
            is_safe_to_file=True,
            score=0.95,
            alerts=[
                ComplianceAlert(
                    rule_id="RULE-001",
                    message="Low severity alert",
                    severity=ComplianceSeverity.LOW,
                )
            ],
        )

        review = UnifiedReview(
            note=note,
            emr_context=emr_context,
            verification=verification,
            review_url="https://review.example.com/review/123",
        )

        assert review.note.note_id == "NOTE-001"
        assert review.emr_context.visit_id == "VISIT-001"
        assert review.verification.is_safe_to_file is True
        assert review.verification.score == 0.95
        assert review.review_url == "https://review.example.com/review/123"
        assert review.created_at is not None

    def test_unified_review_created_at_defaults_to_now(self):
        """Test that created_at defaults to current datetime."""
        before_creation = datetime.now()

        review = UnifiedReview(
            note=ClinicalNote(
                note_id="NOTE-002",
                patient_id="PAT-456",
                encounter_id="ENC-789",
                generated_at=datetime(2024, 1, 15),
                extraction=StructuredExtraction(),
            ),
            emr_context=EMRContext(
                visit_id="VISIT-002",
                patient_id="PAT-456",
                admission_date=datetime(2024, 1, 15),
                attending_physician="Dr. Jones",
                raw_notes="",
            ),
            verification=VerificationResult(
                is_safe_to_file=False,
                score=0.5,
            ),
            review_url="https://review.example.com/review/456",
        )

        after_creation = datetime.now()

        assert before_creation <= review.created_at <= after_creation

    def test_unified_review_empty_review_url_is_valid(self):
        """Test that empty review_url is allowed (Pydantic default behavior)."""
        # Note: Empty string is valid for str field unless min_length is specified
        review = UnifiedReview(
            note=ClinicalNote(
                note_id="NOTE-003",
                patient_id="PAT-789",
                encounter_id="ENC-999",
                generated_at=datetime(2024, 1, 15),
                extraction=StructuredExtraction(),
            ),
            emr_context=EMRContext(
                visit_id="VISIT-003",
                patient_id="PAT-789",
                admission_date=datetime(2024, 1, 15),
                attending_physician="Dr. Brown",
                raw_notes="",
            ),
            verification=VerificationResult(
                is_safe_to_file=True,
                score=1.0,
            ),
            review_url="",
        )

        assert review.review_url == ""

    def test_unified_review_nested_structured_extraction(self):
        """Test that StructuredExtraction is properly nested through ClinicalNote."""
        extraction = StructuredExtraction(
            patient_name="Alice Johnson",
            medications=[
                ExtractedMedication(name="Lisinopril", status=MedicationStatus.ACTIVE),
                ExtractedMedication(name="Atorvastatin", status=MedicationStatus.ACTIVE),
            ],
        )

        note = ClinicalNote(
            note_id="NOTE-004",
            patient_id="PAT-999",
            encounter_id="ENC-111",
            generated_at=datetime(2024, 1, 15),
            extraction=extraction,
        )

        review = UnifiedReview(
            note=note,
            emr_context=EMRContext(
                visit_id="VISIT-004",
                patient_id="PAT-999",
                admission_date=datetime(2024, 1, 15),
                attending_physician="Dr. White",
                raw_notes="",
            ),
            verification=VerificationResult(
                is_safe_to_file=True,
                score=0.9,
            ),
            review_url="https://review.example.com/review/999",
        )

        # Verify nested access to StructuredExtraction
        assert review.note.extraction.patient_name == "Alice Johnson"
        assert len(review.note.extraction.medications) == 2
        assert review.note.extraction.medications[0].name == "Lisinopril"
