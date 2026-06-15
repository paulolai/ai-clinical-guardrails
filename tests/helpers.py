"""Shared test utilities for OTEL instrumentation tests."""

from collections.abc import Sequence

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class InMemorySpanExporter(SpanExporter):
    """Captures spans in memory for test assertions."""

    def __init__(self) -> None:
        self.spans: list = []

    def export(self, spans: Sequence[object]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.spans.clear()

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        return True

    def get_spans(self) -> list:
        return list(self.spans)

    def clear(self) -> None:
        self.spans.clear()
