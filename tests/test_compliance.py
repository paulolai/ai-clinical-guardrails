from datetime import date, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from src.engine import ComplianceEngine
from src.models import AIGeneratedOutput, EMRContext, PatientProfile


# Hypothesis Strategies for generating randomized but valid clinical data
@st.composite
def patient_strategy(draw):
    return PatientProfile(
        patient_id=draw(st.text(min_size=5, max_size=10)),
        first_name=draw(st.text(min_size=2, max_size=20)),
        last_name=draw(st.text(min_size=2, max_size=20)),
        dob=draw(st.dates(min_value=date(1940, 1, 1), max_value=date(2020, 1, 1))),
        allergies=draw(st.lists(st.text(min_size=3, max_size=15), max_size=5)),
        diagnoses=draw(st.lists(st.text(min_size=3, max_size=15), max_size=5)),
    )


@st.composite
def context_strategy(draw):
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
    def test_date_integrity_invariant(self, patient, context):
        """
        Property: If the AI generates a date NOT in the EMR source, it MUST return a Failure Result.
        """
        hallucinated_date = date(1999, 1, 1)  # Definitely not in context
        ai_output = AIGeneratedOutput(
            summary_text="Patient summary.",
            extracted_dates=[hallucinated_date],
            extracted_diagnoses=[],
        )

        result = ComplianceEngine.verify(patient, context, ai_output)

        # Verify it's a failure
        assert not result.is_success
        assert any(a.rule_id == "INVARIANT_DATE_MISMATCH" for a in result.error)

    @given(patient=patient_strategy(), context=context_strategy())
    def test_pii_leakage_invariant(self, patient, context):
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
        assert any(a.rule_id == "SAFETY_PII_LEAK" for a in result.error)

    @given(patient=patient_strategy(), context=context_strategy())
    def test_sepsis_protocol_invariant(self, patient, context):
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
        assert any(a.rule_id == "PROTOCOL_ADHERENCE_MISSING" for a in result.value.alerts)
        assert result.value.score < 1.0
