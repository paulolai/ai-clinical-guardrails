"""Tests for OpenTelemetry tracing in ComplianceEngine.

Uses InMemorySpanExporter to verify that verify() produces correct spans,
attributes, and events.
"""

from datetime import date, datetime

from src.engine import ComplianceEngine
from src.extraction.models import ExtractedMedication
from src.models import AIGeneratedOutput, EMRContext, PatientProfile
from tests.helpers import InMemorySpanExporter


def _make_patient(**overrides: object) -> PatientProfile:
    defaults = {
        "patient_id": "P-TEST",
        "first_name": "Jane",
        "last_name": "Doe",
        "dob": date(1985, 6, 15),
        "allergies": [],
        "diagnoses": [],
    }
    defaults.update(overrides)
    return PatientProfile(**defaults)  # type: ignore[arg-type]


def _make_context(**overrides: object) -> EMRContext:
    defaults = {
        "visit_id": "V-TEST",
        "patient_id": "P-TEST",
        "admission_date": datetime(2025, 3, 10),
        "discharge_date": datetime(2025, 3, 12),
        "attending_physician": "Dr. Test",
        "raw_notes": "Test encounter",
    }
    defaults.update(overrides)
    return EMRContext(**defaults)  # type: ignore[arg-type]


def _make_ai_output(**overrides: object) -> AIGeneratedOutput:
    defaults = {
        "summary_text": "Patient seen today.",
        "extracted_dates": [date(2025, 3, 10)],
        "extracted_diagnoses": [],
        "extracted_medications": [],
    }
    defaults.update(overrides)
    return AIGeneratedOutput(**defaults)  # type: ignore[arg-type]


class TestVerifyTraces:
    def test_verify_produces_span(self, otel_exporter: InMemorySpanExporter) -> None:
        engine = ComplianceEngine()
        result = engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(),
        )

        assert result.is_success
        spans = otel_exporter.get_spans()
        assert len(spans) >= 1

        verify_span = spans[0]
        assert verify_span.name == "compliance.verify"
        assert verify_span.attributes.get("patient_id") == "P-TEST"
        assert verify_span.attributes.get("visit_id") == "V-TEST"
        assert verify_span.attributes.get("compliance.outcome") == "success"

    def test_verify_failure_span_attributes(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        result = engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(
                summary_text="Medicare: 1234 56789 1",
                extracted_dates=[date(2025, 3, 10)],
            ),
        )

        assert not result.is_success
        spans = otel_exporter.get_spans()
        verify_span = spans[0]
        assert verify_span.attributes.get("compliance.outcome") == "failure"
        assert verify_span.attributes.get("compliance.critical_alerts") == 1

    def test_verify_records_alert_events(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(
                summary_text="Medicare: 1234 56789 1",
                extracted_dates=[date(2025, 3, 10)],
            ),
        )

        spans = otel_exporter.get_spans()
        verify_span = spans[0]
        events = verify_span.events
        assert len(events) >= 1

        pii_event = [e for e in events if e.name == "alert"]
        assert len(pii_event) >= 1
        attrs = pii_event[0].attributes
        assert attrs.get("rule_id") == "SAFETY_PII_LEAK"
        assert attrs.get("severity") == "critical"

    def test_verify_hallucinated_date_produces_alert_event(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(extracted_dates=[date(1900, 1, 1)]),
        )

        spans = otel_exporter.get_spans()
        events = spans[0].events
        date_events = [e for e in events if e.name == "alert"]
        assert any(e.attributes.get("rule_id") == "INVARIANT_DATE_MISMATCH" for e in date_events)

    def test_verify_sepsis_without_antibiotic_produces_high_alert(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(
                summary_text="Patient has sepsis.",
                extracted_dates=[date(2025, 3, 10)],
                extracted_diagnoses=["Severe Sepsis"],
            ),
        )

        spans = otel_exporter.get_spans()
        events = spans[0].events
        protocol_events = [e for e in events if e.name == "alert"]
        assert any(
            e.attributes.get("rule_id") == "PROTOCOL_ADHERENCE_MISSING"
            and e.attributes.get("severity") == "high"
            for e in protocol_events
        )

    def test_protocol_checks_produce_child_span(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        from src.protocols.models import ProtocolConfig, ProtocolRule, ProtocolSeverity

        config = ProtocolConfig(
            version="1.0",
            settings={},
            checkers={"drug_interactions": {"enabled": True}},
            rules={
                "drug_interactions": [
                    ProtocolRule(
                        name="Warfarin NSAID",
                        checker_type="drug_interactions",
                        pattern={
                            "trigger": {"medications": ["warfarin"]},
                            "conflicts": {"medications": ["ibuprofen"]},
                        },
                        severity=ProtocolSeverity.CRITICAL,
                        message="Drug interaction detected",
                    )
                ]
            },
        )
        engine = ComplianceEngine(protocol_config=config)
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(
                summary_text="Prescribed warfarin and ibuprofen",
                extracted_dates=[date(2025, 3, 10)],
                extracted_medications=[
                    ExtractedMedication(name="warfarin"),
                    ExtractedMedication(name="ibuprofen"),
                ],
            ),
        )

        spans = otel_exporter.get_spans()
        span_names = [s.name for s in spans]
        assert "compliance.verify.protocols" in span_names

    def test_alert_count_attribute(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(
                summary_text="Medicare: 1234 56789 1",
                extracted_dates=[date(1900, 1, 1)],
            ),
        )

        spans = otel_exporter.get_spans()
        verify_span = spans[0]
        alert_count = verify_span.attributes.get("compliance.alert_count")
        assert alert_count is not None
        assert alert_count >= 2

    def test_has_protocol_registry_attribute(
        self, otel_exporter: InMemorySpanExporter
    ) -> None:
        engine = ComplianceEngine()
        engine.verify(
            _make_patient(),
            _make_context(),
            _make_ai_output(),
        )

        spans = otel_exporter.get_spans()
        assert spans[0].attributes.get("has_protocol_registry") is False
