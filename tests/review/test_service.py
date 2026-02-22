"""Unit tests for ReviewService."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    PatientProfile,
    Result,
    UnifiedReview,
    VerificationResult,
)
from src.review.service import ReviewService, ReviewServiceError


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client."""
    client = MagicMock()
    client.get_patient_profile = AsyncMock()
    client.get_latest_encounter = AsyncMock()
    return client


@pytest.fixture
def sample_patient():
    """Create a sample patient profile."""
    return PatientProfile(
        patient_id="test-patient-001",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=["Penicillin"],
        diagnoses=["Hypertension"],
    )


@pytest.fixture
def sample_emr_context():
    """Create a sample EMR context."""
    return EMRContext(
        visit_id="visit-001",
        patient_id="test-patient-001",
        admission_date=datetime(2026, 1, 15, 10, 0, 0),
        discharge_date=datetime(2026, 1, 15, 18, 0, 0),
        attending_physician="Dr. Smith",
        raw_notes="Patient admitted for observation",
    )


@pytest.fixture
def sample_clinical_note():
    """Create a sample clinical note with extraction."""
    extraction = StructuredExtraction(
        patient_name="John Doe",
        patient_age="46",
        visit_type="Inpatient",
        temporal_expressions=[
            ExtractedTemporalExpression(
                text="January 15, 2026",
                type=TemporalType.ABSOLUTE_DATE,
                normalized_date=date(2026, 1, 15),
            ),
        ],
        medications=[
            ExtractedMedication(
                name="Lisinopril",
                dosage="10mg",
                frequency="daily",
                status=MedicationStatus.ACTIVE,
            ),
        ],
        diagnoses=[
            ExtractedDiagnosis(
                text="Hypertension",
                icd10_code="I10",
            ),
        ],
    )

    return ClinicalNote(
        note_id="note-001",
        patient_id="test-patient-001",
        encounter_id="enc-001",
        generated_at=datetime.now(),
        sections={
            "chief_complaint": "Chest pain",
            "assessment": "Patient presents with chest pain",
            "plan": "Monitor and observe",
        },
        extraction=extraction,
    )


@pytest.fixture
def sample_verification_result():
    """Create a sample successful verification result."""
    return VerificationResult(
        is_safe_to_file=True,
        score=0.95,
        alerts=[],
    )


class TestReviewServiceInstantiation:
    """Test ReviewService can be instantiated."""

    def test_review_service_can_be_instantiated_with_fhir_client(self, mock_fhir_client):
        """Test that ReviewService can be created with a FHIR client."""
        service = ReviewService(fhir_client=mock_fhir_client)
        assert service.fhir_client == mock_fhir_client


class TestCreateReview:
    """Test create_review workflow."""

    @pytest.mark.asyncio
    async def test_create_review_returns_unified_review(
        self,
        mock_fhir_client,
        sample_patient,
        sample_emr_context,
        sample_clinical_note,
        sample_verification_result,
    ):
        """Test that create_review returns a UnifiedReview."""
        # Arrange
        mock_fhir_client.get_patient_profile.return_value = sample_patient
        mock_fhir_client.get_latest_encounter.return_value = sample_emr_context

        with patch(
            "src.review.service.ComplianceEngine.verify",
            return_value=Result.success(sample_verification_result),
        ):
            service = ReviewService(fhir_client=mock_fhir_client)

            # Act
            result = await service.create_review(sample_clinical_note)

        # Assert
        assert isinstance(result, UnifiedReview)
        assert result.note == sample_clinical_note
        assert result.emr_context == sample_emr_context
        assert result.verification == sample_verification_result
        assert result.review_url == f"/review/{sample_clinical_note.note_id}"
        assert isinstance(result.created_at, datetime)

    @pytest.mark.asyncio
    async def test_create_review_contains_note_emr_context_verification(
        self,
        mock_fhir_client,
        sample_patient,
        sample_emr_context,
        sample_clinical_note,
        sample_verification_result,
    ):
        """Test that UnifiedReview contains all required fields."""
        # Arrange
        mock_fhir_client.get_patient_profile.return_value = sample_patient
        mock_fhir_client.get_latest_encounter.return_value = sample_emr_context

        with patch(
            "src.review.service.ComplianceEngine.verify",
            return_value=Result.success(sample_verification_result),
        ):
            service = ReviewService(fhir_client=mock_fhir_client)

            # Act
            review = await service.create_review(sample_clinical_note)

        # Assert
        assert review.note is not None
        assert review.emr_context is not None
        assert review.verification is not None
        assert review.note.note_id == sample_clinical_note.note_id
        assert review.emr_context.patient_id == sample_patient.patient_id

    @pytest.mark.asyncio
    async def test_create_review_with_verification_failure(
        self,
        mock_fhir_client,
        sample_patient,
        sample_emr_context,
        sample_clinical_note,
    ):
        """Test that create_review handles verification failure gracefully."""
        # Arrange
        critical_alert = ComplianceAlert(
            rule_id="CRITICAL_ERROR",
            message="Critical verification error",
            severity=ComplianceSeverity.CRITICAL,
        )

        mock_fhir_client.get_patient_profile.return_value = sample_patient
        mock_fhir_client.get_latest_encounter.return_value = sample_emr_context

        with patch(
            "src.review.service.ComplianceEngine.verify",
            return_value=Result.failure([critical_alert]),
        ):
            service = ReviewService(fhir_client=mock_fhir_client)

            # Act
            review = await service.create_review(sample_clinical_note)

        # Assert
        assert isinstance(review, UnifiedReview)
        assert review.verification is not None
        assert review.verification.is_safe_to_file is False
        assert review.verification.score == 0.0
        assert len(review.verification.alerts) == 1
        assert review.verification.alerts[0].rule_id == "CRITICAL_ERROR"

    @pytest.mark.asyncio
    async def test_create_review_fhir_patient_fetch_failure(
        self,
        mock_fhir_client,
        sample_clinical_note,
    ):
        """Test that create_review raises ReviewServiceError when patient fetch fails."""
        # Arrange
        mock_fhir_client.get_patient_profile.side_effect = Exception("Network error")

        service = ReviewService(fhir_client=mock_fhir_client)

        # Act & Assert
        with pytest.raises(ReviewServiceError) as exc_info:
            await service.create_review(sample_clinical_note)

        assert "Failed to fetch patient profile" in str(exc_info.value)
        assert "test-patient-001" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_review_fhir_encounter_fetch_failure(
        self,
        mock_fhir_client,
        sample_patient,
        sample_clinical_note,
    ):
        """Test that create_review raises ReviewServiceError when encounter fetch fails."""
        # Arrange
        mock_fhir_client.get_patient_profile.return_value = sample_patient
        mock_fhir_client.get_latest_encounter.side_effect = Exception("Timeout")

        service = ReviewService(fhir_client=mock_fhir_client)

        # Act & Assert
        with pytest.raises(ReviewServiceError) as exc_info:
            await service.create_review(sample_clinical_note)

        assert "Failed to fetch encounter" in str(exc_info.value)
        assert "test-patient-001" in str(exc_info.value)


class TestNoteToAIOutput:
    """Test _note_to_ai_output conversion."""

    def test_note_to_ai_output_converts_properly(self, sample_clinical_note):
        """Test that _note_to_ai_output converts ClinicalNote properly."""
        # Arrange
        service = ReviewService(fhir_client=MagicMock())

        # Act
        ai_output = service._note_to_ai_output(sample_clinical_note)

        # Assert
        from src.models import AIGeneratedOutput

        assert isinstance(ai_output, AIGeneratedOutput)

        # Check summary text is built from sections
        assert "chief_complaint: Chest pain" in ai_output.summary_text
        assert "assessment: Patient presents with chest pain" in ai_output.summary_text
        assert "plan: Monitor and observe" in ai_output.summary_text

        # Check dates are extracted
        assert len(ai_output.extracted_dates) == 1
        assert ai_output.extracted_dates[0] == date(2026, 1, 15)

        # Check diagnoses are extracted
        assert len(ai_output.extracted_diagnoses) == 1
        assert ai_output.extracted_diagnoses[0] == "Hypertension"

        # Check medications are passed through
        assert len(ai_output.extracted_medications) == 1
        assert ai_output.extracted_medications[0].name == "Lisinopril"

        # Check defaults
        assert ai_output.suggested_billing_codes == []
        assert ai_output.contains_pii is False

    def test_note_to_ai_output_empty_extraction(self):
        """Test conversion with empty extraction."""
        # Arrange
        extraction = StructuredExtraction()
        note = ClinicalNote(
            note_id="note-empty",
            patient_id="patient-empty",
            encounter_id="enc-empty",
            generated_at=datetime.now(),
            sections={},
            extraction=extraction,
        )

        service = ReviewService(fhir_client=MagicMock())

        # Act
        ai_output = service._note_to_ai_output(note)

        # Assert
        assert ai_output.summary_text == ""
        assert ai_output.extracted_dates == []
        assert ai_output.extracted_diagnoses == []
        assert ai_output.extracted_medications == []

    def test_note_to_ai_output_multiple_dates(self):
        """Test conversion extracts all dates from temporal expressions."""
        # Arrange
        extraction = StructuredExtraction(
            temporal_expressions=[
                ExtractedTemporalExpression(
                    text="Jan 1",
                    type=TemporalType.ABSOLUTE_DATE,
                    normalized_date=date(2026, 1, 1),
                ),
                ExtractedTemporalExpression(
                    text="Jan 15",
                    type=TemporalType.ABSOLUTE_DATE,
                    normalized_date=date(2026, 1, 15),
                ),
                ExtractedTemporalExpression(
                    text="sometime",
                    type=TemporalType.RELATIVE_DATE,
                    normalized_date=None,  # No normalized date
                ),
            ],
        )
        note = ClinicalNote(
            note_id="note-dates",
            patient_id="patient-dates",
            encounter_id="enc-dates",
            generated_at=datetime.now(),
            sections={"section1": "content1"},
            extraction=extraction,
        )

        service = ReviewService(fhir_client=MagicMock())

        # Act
        ai_output = service._note_to_ai_output(note)

        # Assert
        assert len(ai_output.extracted_dates) == 2
        assert date(2026, 1, 1) in ai_output.extracted_dates
        assert date(2026, 1, 15) in ai_output.extracted_dates
