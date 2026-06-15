"""OpenTelemetry telemetry setup.

Configures traces, metrics, and logs with OTLP exporter.
All functions are no-ops when OTEL is not configured (e.g., in tests without setup).
"""

import logging
import os
from typing import Any

from opentelemetry import metrics, trace

OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "false").lower() == "true"
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "ai-clinical-guardrails")
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

_meter: Any = None
_verification_counter: Any = None
_alert_counter: Any = None
_verification_latency: Any = None
_extraction_latency: Any = None


def setup_telemetry() -> None:
    """Initialize OpenTelemetry providers and instrumentors.

    Call once at application startup. When OTEL_ENABLED=false, this is a no-op.
    """
    global _meter, _verification_counter, _alert_counter, _verification_latency, _extraction_latency

    if not OTEL_ENABLED:
        logging.getLogger(__name__).debug("OTEL disabled (OTEL_ENABLED != true)")
        return

    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})

    # Traces
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # Metrics
    metric_exporter = OTLPMetricExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Logs
    log_exporter = OTLPLogExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(otel_handler)

    # Instrument logging (adds trace/span IDs to log records)
    LoggingInstrumentor().instrument(set_logging_format=False)

    # Create meter and instruments
    _meter = metrics.get_meter(OTEL_SERVICE_NAME)
    _verification_counter = _meter.create_counter(
        name="guardrail.verifications.total",
        description="Total number of compliance verifications",
        unit="1",
    )
    _alert_counter = _meter.create_counter(
        name="guardrail.alerts.total",
        description="Total number of compliance alerts by rule",
        unit="1",
    )
    _verification_latency = _meter.create_histogram(
        name="guardrail.verification.duration",
        description="Time to complete a verification",
        unit="ms",
    )
    _extraction_latency = _meter.create_histogram(
        name="guardrail.extraction.duration",
        description="Time to complete LLM extraction",
        unit="ms",
    )

    logging.getLogger(__name__).info(
        "OTEL initialized: service=%s endpoint=%s",
        OTEL_SERVICE_NAME,
        OTEL_EXPORTER_OTLP_ENDPOINT,
    )


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer by name."""
    return trace.get_tracer(name)


def get_verification_counter() -> Any:
    """Lazily access the verification counter metric."""
    return _verification_counter


def get_alert_counter() -> Any:
    """Lazily access the alert counter metric."""
    return _alert_counter


def get_verification_latency() -> Any:
    """Lazily access the verification latency histogram."""
    return _verification_latency


def get_extraction_latency() -> Any:
    """Lazily access the extraction latency histogram."""
    return _extraction_latency
