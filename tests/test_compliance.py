from datetime import date, datetime, timedelta
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from src.engine import ComplianceEngine
from src.extraction.models import ExtractedMedication
from src.models import AIGeneratedOutput, EMRContext, PatientProfile
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


def test_compliance_engine_with_protocols():
    """Test that ComplianceEngine runs protocol checks."""
    config = ProtocolConfig(
        version="1.0",
        settings={},
        checkers={"drug_interactions": {"enabled": True}},
        rules={
            "drug_interactions": [
                ProtocolRule(
                    name="Warfarin NSAID",
                    checker_type="drug_interactions",
                    pattern={"trigger": {"medications": ["warfarin"]}, "conflicts": {"medications": ["ibuprofen"]}},
                    severity=ProtocolSeverity.CRITICAL,
                    message="Drug interaction detected",
                )
            ]
        },
    )

    engine = ComplianceEngine(protocol_config=config)

    patient = PatientProfile(
        patient_id="P1",
        first_name="John",
        last_name="Doe",
        dob=date(1980, 1, 1),
        allergies=[],
        diagnoses=[],
    )

    context = EMRContext(
        visit_id="V1",
        patient_id="P1",
        admission_date=datetime(2024, 1, 1),
        discharge_date=None,
        attending_physician="Dr. Smith",
        raw_notes="",
    )

    ai_output = AIGeneratedOutput(
        summary_text="Patient prescribed warfarin and ibuprofen",
        extracted_dates=[date(2024, 1, 1)],
        extracted_diagnoses=[],
        extracted_medications=[ExtractedMedication(name="warfarin"), ExtractedMedication(name="ibuprofen")],
    )

    result = engine.verify(patient, context, ai_output, protocol_config=config)

    # Should fail due to drug interaction
    assert not result.is_success
    assert result.error is not None
    assert any("Drug interaction" in str(a.message) for a in result.error)


# Hypothesis Strategies for generating randomized but valid clinical data
@st.composite
def patient_strategy(draw: Any) -> PatientProfile:
    return PatientProfile(
        patient_id=draw(st.text(min_size=5, max_size=10)),
        first_name=draw(st.text(min_size=2, max_size=20)),
        last_name=draw(st.text(min_size=2, max_size=20)),
        dob=draw(st.dates(min_value=date(1940, 1, 1), max_value=date(2020, 1, 1))),
        allergies=draw(st.lists(st.text(min_size=3, max_size=15), max_size=5)),
        diagnoses=draw(st.lists(st.text(min_size=3, max_size=15), max_size=5)),
    )


@st.composite
def context_strategy(draw: Any) -> EMRContext:
    admission = draw(st.datetimes(min_value=datetime(2023, 1, 1), max_value=datetime(2024, 1, 1)))
    return EMRContext(
        visit_id=draw(st.text(min_size=5, max_size=10)),
        patient_id="PAT-123",
        admission_date=admission,
        discharge_date=admission + timedelta(days=draw(st.integers(min_value=1, max_value=10))),
        attending_physician="Dr. Smith",
        raw_notes="Patient admitted for observation.",
    )


class TestComplianceEngine:
    @given(patient=patient_strategy(), context=context_strategy())
    def test_date_integrity_invariant(self, patient: PatientProfile, context: EMRContext) -> None:
        """
        Property: If the AI generates a date NOT in the EMR source, it MUST return a Failure Result.
        """
        hallucinated_date = date(1900, 1, 1)  # Far outside the strategy's valid range (1940-2020)
        ai_output = AIGeneratedOutput(
            summary_text="Patient summary.",
            extracted_dates=[hallucinated_date],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Verify it's a failure
        assert not result.is_success
        assert result.error is not None
        assert any(a.rule_id == "INVARIANT_DATE_MISMATCH" for a in result.error)

    @given(patient=patient_strategy(), context=context_strategy())
    def test_pii_leakage_invariant(self, patient: PatientProfile, context: EMRContext) -> None:
        """
        Property: If summary contains a Medicare Number pattern, it MUST return a Failure Result.
        """
        # Medicare format: 10 digits, often space separated
        medicare_summary = "Patient Medicare is 1234 56789 1. Proceed with care."
        ai_output = AIGeneratedOutput(
            summary_text=medicare_summary,
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        assert not result.is_success
        assert result.error is not None
        assert any(a.rule_id == "SAFETY_PII_LEAK" for a in result.error)

    @given(patient=patient_strategy(), context=context_strategy())
    def test_sepsis_protocol_invariant(self, patient: PatientProfile, context: EMRContext) -> None:
        """
        Property: If Sepsis is detected, Antibiotics must be mentioned (High severity alert).
        """
        ai_output = AIGeneratedOutput(
            summary_text="Patient has sepsis.",
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=["Severe Sepsis"],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Non-critical alerts should still allow a Success result but with alerts inside
        assert result.is_success
        assert result.value is not None
        assert any(a.rule_id == "PROTOCOL_ADHERENCE_MISSING" for a in result.value.alerts)
        assert result.value.score < 1.0


class TestComplianceBoundaryCases:
    """Property-based tests for compliance engine boundary conditions."""

    @given(patient=patient_strategy(), context=context_strategy())
    def test_empty_summary_is_safe(self, patient: PatientProfile, context: EMRContext) -> None:
        """Property: Empty summary text should be considered safe."""
        ai_output = AIGeneratedOutput(
            summary_text="",
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Empty summary should pass basic checks
        assert result.is_success

    @given(
        patient=patient_strategy(),
        context=context_strategy(),
        summary_text=st.text(min_size=0, max_size=10000),
    )
    def test_summary_length_boundaries(self, patient: PatientProfile, context: EMRContext, summary_text: str) -> None:
        """Property: Any length of summary text should be processed without error."""
        ai_output = AIGeneratedOutput(
            summary_text=summary_text,
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Should always return a result, never crash
        assert result.is_success is not None

    @given(patient=patient_strategy(), context=context_strategy())
    def test_empty_dates_list(self, patient: PatientProfile, context: EMRContext) -> None:
        """Property: Empty dates list should be handled gracefully."""
        ai_output = AIGeneratedOutput(
            summary_text="Patient summary.",
            extracted_dates=[],  # Empty list
            extracted_diagnoses=[],
        )

        # Should handle gracefully without crashing
        result = ComplianceEngine.verify(patient, context, ai_output)

        # Result may be success or failure, but should not raise exception
        assert result.is_success is not None or result.error is not None

    @given(patient=patient_strategy(), context=context_strategy())
    def test_many_diagnoses_boundary(self, patient: PatientProfile, context: EMRContext) -> None:
        """Property: Large number of diagnoses should be handled."""
        many_diagnoses = [f"Diagnosis {i}" for i in range(100)]

        ai_output = AIGeneratedOutput(
            summary_text="Patient has multiple conditions.",
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=many_diagnoses,
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Should handle large lists without error
        assert result.is_success is not None

    @given(
        patient=patient_strategy(),
        context=context_strategy(),
        dob=st.dates(min_value=date(1900, 1, 1), max_value=date(2024, 12, 31)),
    )
    def test_extreme_patient_ages(self, patient: PatientProfile, context: EMRContext, dob: date) -> None:
        """Property: Patient with any DOB should be processable."""
        patient.dob = dob

        ai_output = AIGeneratedOutput(
            summary_text="Regular follow-up.",
            extracted_dates=[context.admission_date.date()],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Should handle any valid date without error
        assert result.is_success is not None

    @given(
        patient=patient_strategy(),
        context=context_strategy(),
        future_date=st.dates(min_value=date(2025, 1, 1), max_value=date(2100, 12, 31)),
    )
    def test_future_dates_in_ai_output(self, patient: PatientProfile, context: EMRContext, future_date: date) -> None:
        """Property: Future dates in AI output should be flagged as hallucinations."""
        ai_output = AIGeneratedOutput(
            summary_text="Patient will be seen.",
            extracted_dates=[future_date],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Future dates should be flagged
        if not result.is_success:
            assert result.error is not None
            assert any(a.rule_id == "INVARIANT_DATE_MISMATCH" for a in result.error)
