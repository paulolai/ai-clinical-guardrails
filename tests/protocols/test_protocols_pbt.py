from datetime import date
from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from src.extraction.models import ExtractedMedication, StructuredExtraction
from src.models import ComplianceSeverity, PatientProfile
from src.protocols.checkers.allergy_checker import AllergyChecker
from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity


# Strategies
@st.composite
def patient_with_allergies(draw: Any) -> PatientProfile:
    """Generate patient with random allergies."""
    allergies = draw(
        st.lists(
            st.sampled_from(["penicillin", "sulfa", "latex", "aspirin", "none"]), min_size=0, max_size=3, unique=True
        )
    )

    return PatientProfile(
        patient_id=draw(st.text(min_size=5, max_size=10)),
        first_name=draw(st.text(min_size=2, max_size=10)),
        last_name=draw(st.text(min_size=2, max_size=10)),
        dob=date(1980, 1, 1),
        allergies=allergies,
        diagnoses=[],
    )


@st.composite
def extraction_with_medications(draw: Any) -> StructuredExtraction:
    """Generate extraction with random medications."""
    med_names = draw(
        st.lists(
            st.sampled_from(["amoxicillin", "penicillin", "ibuprofen", "aspirin", "lisinopril"]),
            min_size=0,
            max_size=5,
            unique=True,
        )
    )

    medications = [ExtractedMedication(name=name) for name in med_names]

    return StructuredExtraction(medications=medications)


class TestAllergyCheckerPBT:
    """Property-based tests for allergy checker."""

    @given(patient=patient_with_allergies(), extraction=extraction_with_medications())
    def test_allergy_checker_never_crashes(self, patient: PatientProfile, extraction: StructuredExtraction) -> None:
        """Property: Allergy checker must never crash regardless of input."""
        config = ProtocolConfig(
            version="1.0",
            settings={},
            checkers={"allergy_checks": {"enabled": True}},
            rules={
                "allergy_checks": [
                    ProtocolRule(
                        name="Penicillin",
                        checker_type="allergy_checks",
                        pattern={
                            "patient_allergies": ["penicillin"],
                            "conflicts": {"medications": ["amoxicillin", "penicillin"]},
                        },
                        severity=ProtocolSeverity.CRITICAL,
                        message="Allergy conflict",
                    )
                ]
            },
        )

        checker = AllergyChecker(config)

        # Should never raise exception
        alerts = checker.check(patient, extraction)

        # Verify return type
        assert isinstance(alerts, list)
        for alert in alerts:
            assert alert.severity in [
                ComplianceSeverity.CRITICAL,
                ComplianceSeverity.HIGH,
                ComplianceSeverity.MEDIUM,
                ComplianceSeverity.LOW,
            ]

    @given(patient=patient_with_allergies(), extraction=extraction_with_medications())
    def test_allergy_conflict_always_detected(self, patient: PatientProfile, extraction: StructuredExtraction) -> None:
        """
        Property: If patient has penicillin allergy AND extraction has amoxicillin,
        MUST return CRITICAL alert.
        """
        # Skip if preconditions not met
        if "penicillin" not in patient.allergies:
            return
        if not any(m.name.lower() == "amoxicillin" for m in extraction.medications):
            return

        config = ProtocolConfig(
            version="1.0",
            settings={},
            checkers={"allergy_checks": {"enabled": True}},
            rules={
                "allergy_checks": [
                    ProtocolRule(
                        name="Penicillin",
                        checker_type="allergy_checks",
                        pattern={"patient_allergies": ["penicillin"], "conflicts": {"medications": ["amoxicillin"]}},
                        severity=ProtocolSeverity.CRITICAL,
                        message="Penicillin allergy",
                    )
                ]
            },
        )

        checker = AllergyChecker(config)
        alerts = checker.check(patient, extraction)

        # Must detect the conflict
        critical_alerts = [a for a in alerts if a.severity == ComplianceSeverity.CRITICAL]
        assert len(critical_alerts) >= 1
