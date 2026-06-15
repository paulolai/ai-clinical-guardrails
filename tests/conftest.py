"""Root pytest configuration.

Provides OTEL test fixtures for verifying traces and metrics.
Uses session-scoped provider setup (OTEL global is set-once).
"""

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import src.telemetry as telemetry
from tests.helpers import InMemorySpanExporter

_shared_exporter = InMemorySpanExporter()
_shared_metric_reader = InMemoryMetricReader()
_shared_trace_provider: TracerProvider | None = None
_shared_meter_provider: MeterProvider | None = None


@pytest.fixture(scope="session", autouse=True)
def _setup_otel_providers() -> None:
    """Set up OTEL providers once for the entire test session."""
    global _shared_trace_provider, _shared_meter_provider

    _shared_trace_provider = TracerProvider()
    _shared_trace_provider.add_span_processor(SimpleSpanProcessor(_shared_exporter))
    trace.set_tracer_provider(_shared_trace_provider)

    _shared_meter_provider = MeterProvider(metric_readers=[_shared_metric_reader])
    metrics.set_meter_provider(_shared_meter_provider)

    meter = metrics.get_meter("test")
    telemetry._verification_counter = meter.create_counter(
        name="guardrail.verifications.total",
        description="Total number of compliance verifications",
        unit="1",
    )
    telemetry._alert_counter = meter.create_counter(
        name="guardrail.alerts.total",
        description="Total number of compliance alerts by rule",
        unit="1",
    )
    telemetry._verification_latency = meter.create_histogram(
        name="guardrail.verification.duration",
        description="Time to complete a verification",
        unit="ms",
    )
    telemetry._extraction_latency = meter.create_histogram(
        name="guardrail.extraction.duration",
        description="Time to complete LLM extraction",
        unit="ms",
    )

    yield

    if _shared_trace_provider:
        _shared_trace_provider.shutdown()
    if _shared_meter_provider:
        _shared_meter_provider.shutdown()


@pytest.fixture(autouse=True)
def _clear_spans() -> None:
    """Clear captured spans before each test."""
    _shared_exporter.clear()
    yield


@pytest.fixture()
def otel_exporter() -> InMemorySpanExporter:
    """Provide the shared in-memory span exporter for assertions."""
    return _shared_exporter
