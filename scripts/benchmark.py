#!/usr/bin/env python3
"""Performance benchmark script for Clinical Guardrails API.

Measures and documents latency percentiles (p50, p95, p99) for key endpoints.

Usage:
    uv run python scripts/benchmark.py [--iterations 100] [--warmup 10]

Example Output:
    ========================================
    Clinical Guardrails API - Performance Benchmark
    ========================================

    Configuration:
      Iterations: 100
      Warmup runs: 10

    Results:
      Endpoint: /health
        p50: 2.1ms | p95: 3.5ms | p99: 5.2ms

      Endpoint: /verify (manual)
        p50: 15.3ms | p95: 28.7ms | p99: 45.1ms

      Endpoint: /verify/fhir/{id}
        p50: 45.2ms | p95: 78.3ms | p99: 120.5ms

      Endpoint: /extract
        p50: 1250.0ms | p95: 1850.0ms | p99: 2200.0ms

    ========================================
"""

import argparse
import statistics
import time
from datetime import date, datetime
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app
from src.models import EMRContext, PatientProfile, Result, VerificationResult

client = TestClient(app)

# Sample data
SAMPLE_PATIENT = PatientProfile(
    patient_id="BENCH001",
    first_name="Bench",
    last_name="Mark",
    dob=date(1980, 1, 1),
)

SAMPLE_CONTEXT = EMRContext(
    visit_id="V-BENCH-001",
    patient_id="BENCH001",
    admission_date=datetime(2024, 2, 22, 10, 0, 0),
    attending_physician="Dr. Benchmark",
    raw_notes="Patient presents with chest pain.",
)

SAMPLE_TRANSCRIPT = """
Patient came in yesterday with chest pain. Started on Lisinopril 10mg daily.
Follow up in two weeks. Blood pressure was elevated at 150/90.
"""


def calculate_percentiles(latencies: list[float]) -> dict[str, float]:
    """Calculate p50, p95, p99 percentiles from latency list."""
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def percentile(p: float) -> float:
        """Calculate percentile using nearest-rank method."""
        k = int((p / 100) * (n - 1))
        return sorted_latencies[k]

    return {
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
        "min": sorted_latencies[0],
        "max": sorted_latencies[-1],
        "mean": statistics.mean(sorted_latencies),
    }


def benchmark_health(iterations: int) -> dict[str, float]:
    """Benchmark the /health endpoint."""
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get("/health")
        end = time.perf_counter()
        assert response.status_code == 200
        latencies.append((end - start) * 1000)  # Convert to ms

    return calculate_percentiles(latencies)


def benchmark_verify_manual(iterations: int) -> dict[str, float]:
    """Benchmark the /verify endpoint (manual)."""
    latencies = []
    payload = {
        "patient": {
            "patient_id": "P001",
            "first_name": "John",
            "last_name": "Smith",
            "dob": "1990-01-01",
        },
        "context": {
            "visit_id": "V100",
            "patient_id": "P001",
            "admission_date": "2024-02-01T10:00:00",
            "attending_physician": "Dr. House",
            "raw_notes": "Note.",
        },
        "ai_output": {
            "summary_text": "Patient seen on 2024-02-01.",
            "extracted_dates": ["2024-02-01"],
        },
    }

    for _ in range(iterations):
        start = time.perf_counter()
        response = client.post("/verify", json=payload)
        end = time.perf_counter()
        assert response.status_code == 200
        latencies.append((end - start) * 1000)

    return calculate_percentiles(latencies)


def benchmark_verify_fhir(iterations: int) -> dict[str, float]:
    """Benchmark the /verify/fhir/{id} endpoint."""
    latencies = []
    payload = {
        "ai_output": {
            "summary_text": "Patient seen on 2024-02-22.",
            "extracted_dates": ["2024-02-22"],
        }
    }

    with (
        patch("src.api.emr_client.get_patient_profile") as mock_patient,
        patch("src.api.emr_client.get_latest_encounter") as mock_encounter,
    ):
        mock_patient.return_value = SAMPLE_PATIENT
        mock_encounter.return_value = SAMPLE_CONTEXT

        for _ in range(iterations):
            start = time.perf_counter()
            response = client.post("/verify/fhir/BENCH001", json=payload)
            end = time.perf_counter()
            assert response.status_code == 200
            latencies.append((end - start) * 1000)

    return calculate_percentiles(latencies)


def benchmark_extract(iterations: int) -> dict[str, float]:
    """Benchmark the /extract endpoint."""
    from src.extraction.models import (
        ExtractedDiagnosis,
        ExtractedMedication,
        ExtractedTemporalExpression,
        MedicationStatus,
        StructuredExtraction,
        TemporalType,
    )

    latencies = []
    payload = {
        "patient_id": "BENCH001",
        "transcript": SAMPLE_TRANSCRIPT,
        "reference_date": "2024-02-22",
    }

    # Create mock extraction
    mock_extraction = StructuredExtraction(
        patient_name="Bench Mark",
        medications=[
            ExtractedMedication(
                name="Lisinopril",
                dosage="10mg",
                status=MedicationStatus.STARTED,
                confidence=0.95,
            )
        ],
        diagnoses=[
            ExtractedDiagnosis(
                text="Chest pain",
                confidence=0.92,
            )
        ],
        temporal_expressions=[
            ExtractedTemporalExpression(
                text="yesterday",
                type=TemporalType.RELATIVE_DATE,
                normalized_date=date(2024, 2, 21),
                confidence=0.88,
            ),
            ExtractedTemporalExpression(
                text="two weeks",
                type=TemporalType.DURATION,
                confidence=0.85,
            ),
        ],
        visit_type="acute_complaint",
        confidence=0.91,
    )

    # Create mock verification result
    mock_result: Result[VerificationResult, Any] = Result.success(
        VerificationResult(
            is_safe_to_file=True,
            score=0.95,
            alerts=[],
        )
    )

    with (
        patch("src.api.verification_workflow.verify_patient_documentation") as mock_verify,
        patch("src.api.verification_workflow.get_last_extraction") as mock_get_extraction,
    ):
        mock_verify.return_value = mock_result
        mock_get_extraction.return_value = mock_extraction

        for _ in range(iterations):
            start = time.perf_counter()
            response = client.post("/extract", json=payload)
            end = time.perf_counter()
            assert response.status_code == 200
            latencies.append((end - start) * 1000)

    return calculate_percentiles(latencies)


def print_results(name: str, results: dict[str, float]) -> None:
    """Print benchmark results in a formatted way."""
    print(f"  {name}:")
    print(f"    p50: {results['p50']:.1f}ms | p95: {results['p95']:.1f}ms | p99: {results['p99']:.1f}ms")
    print(f"    (min: {results['min']:.1f}ms, max: {results['max']:.1f}ms, mean: {results['mean']:.1f}ms)")
    print()


def main() -> None:
    """Run performance benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark Clinical Guardrails API performance")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations per endpoint (default: 100)")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup runs (default: 10)")
    args = parser.parse_args()

    print("=" * 60)
    print("Clinical Guardrails API - Performance Benchmark")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Iterations: {args.iterations}")
    print(f"  Warmup runs: {args.warmup}")
    print()

    # Warmup runs
    if args.warmup > 0:
        print(f"Running {args.warmup} warmup iterations...")
        benchmark_health(args.warmup)
        print("Warmup complete.")
        print()

    # Run benchmarks
    print("Results:")
    print()

    print("  [1/4] Benchmarking /health endpoint...")
    health_results = benchmark_health(args.iterations)
    print_results("/health", health_results)

    print("  [2/4] Benchmarking /verify (manual) endpoint...")
    verify_results = benchmark_verify_manual(args.iterations)
    print_results("/verify (manual)", verify_results)

    print("  [3/4] Benchmarking /verify/fhir/{id} endpoint...")
    fhir_results = benchmark_verify_fhir(args.iterations)
    print_results("/verify/fhir/{id}", fhir_results)

    print("  [4/4] Benchmarking /extract endpoint...")
    extract_results = benchmark_extract(args.iterations)
    print_results("/extract", extract_results)

    print("=" * 60)
    print("Benchmark complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
