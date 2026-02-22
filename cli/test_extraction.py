"""CLI tool for testing extraction accuracy with real LLM API.

Usage:
    uv run python cli/test_extraction.py --transcript-id TX-001-follow-up
    uv run python cli/test_extraction.py --run-all
    uv run python cli/test_extraction.py --provider openai --model gpt-4o
"""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from src.extraction.llm_client import create_llm_client
from src.extraction.llm_parser import LLMTranscriptParser

app = typer.Typer(help="Test clinical data extraction accuracy")
console = Console()

SAMPLE_TRANSCRIPTS_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_transcripts.json"


def load_transcripts() -> list[dict[str, Any]]:
    """Load sample transcripts from fixtures."""
    with open(SAMPLE_TRANSCRIPTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["transcripts"]


def load_transcript_by_id(transcript_id: str) -> dict[str, Any] | None:
    """Load a specific transcript by ID."""
    transcripts = load_transcripts()
    for t in transcripts:
        if t["id"] == transcript_id:
            return t
    return None


def compare_extraction(result: Any, expected: dict[str, Any]) -> dict[str, Any]:
    """Compare extraction result with expected values."""
    comparison = {
        "patient_name": {
            "expected": expected.get("patient_name"),
            "actual": result.patient_name,
            "match": result.patient_name == expected.get("patient_name"),
        },
        "visit_type": {
            "expected": expected.get("visit_type"),
            "actual": result.visit_type,
            "match": result.visit_type == expected.get("visit_type"),
        },
        "medications": {
            "expected_count": len(expected.get("medications", [])),
            "actual_count": len(result.medications),
            "match": len(result.medications) >= len(expected.get("medications", [])),
        },
        "temporal_expressions": {
            "expected_count": len(expected.get("temporal_expressions", [])),
            "actual_count": len(result.temporal_expressions),
        },
        "confidence": result.confidence,
    }
    return comparison


async def test_single_transcript(
    transcript: dict[str, Any],
    provider: str = "synthetic",
    model: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Test extraction on a single transcript."""
    client = create_llm_client(provider, model=model)
    parser = LLMTranscriptParser(llm_client=client, reference_date=date.today())

    try:
        result = await parser.parse(transcript["text"])

        expected = transcript["expected_extractions"]
        comparison = compare_extraction(result, expected)

        # Calculate accuracy for this transcript
        checks = [
            comparison["patient_name"]["match"],
            comparison["visit_type"]["match"],
            comparison["medications"]["match"],
        ]
        accuracy = sum(checks) / len(checks) if checks else 0.0

        if verbose:
            console.print(f"\n[bold]Transcript: {transcript['id']}[/bold]")
            console.print(f"Text: {transcript['text'][:100]}...")
            console.print(f"\nExpected patient: {comparison['patient_name']['expected']}")
            console.print(f"Actual patient: {comparison['patient_name']['actual']}")
            console.print(f"Expected visit type: {comparison['visit_type']['expected']}")
            console.print(f"Actual visit type: {comparison['visit_type']['actual']}")
            console.print(f"Expected medications: {comparison['medications']['expected_count']}")
            console.print(f"Actual medications: {comparison['medications']['actual_count']}")
            console.print(f"Extraction confidence: {comparison['confidence']:.2f}")

            for med in result.medications:
                console.print(f"  - {med.name} ({med.status.value})")

        await client.close()

        return {
            "id": transcript["id"],
            "accuracy": accuracy,
            "confidence": comparison["confidence"],
            "comparison": comparison,
            "result": result,
        }

    except Exception as e:
        await client.close()
        return {
            "id": transcript["id"],
            "accuracy": 0.0,
            "error": str(e),
        }


@app.command()
def test_transcript(
    transcript_id: str = typer.Option(
        ..., "--transcript-id", "-t", help="Transcript ID to test (e.g., TX-001-follow-up)"
    ),
    provider: str = typer.Option("synthetic", "--provider", "-p", help="LLM provider (openai, azure, synthetic)"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name (optional)"),
    verbose: bool = typer.Option(True, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Test extraction on a single transcript."""
    transcript = load_transcript_by_id(transcript_id)

    if not transcript:
        console.print(f"[red]Transcript {transcript_id} not found[/red]")
        available = [t["id"] for t in load_transcripts()]
        console.print(f"Available IDs: {', '.join(available[:5])}...")
        raise typer.Exit(1)

    console.print(f"[bold]Testing extraction on {transcript_id}[/bold]")
    console.print(f"Provider: {provider}")
    console.print(f"Text: {transcript['text'][:100]}...\n")

    result = asyncio.run(test_single_transcript(transcript, provider, model, verbose))

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[green]Accuracy: {result['accuracy']:.1%}[/green]")
    console.print(f"Confidence: {result['confidence']:.2f}")


@app.command()
def test_all(
    provider: str = typer.Option("synthetic", "--provider", "-p", help="LLM provider"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Limit number of transcripts to test"),
) -> None:
    """Test extraction on all sample transcripts and report accuracy."""
    transcripts = load_transcripts()

    if limit:
        transcripts = transcripts[:limit]

    console.print(f"[bold]Testing extraction on {len(transcripts)} transcripts[/bold]")
    console.print(f"Provider: {provider}\n")

    results = []
    for transcript in transcripts:
        console.print(f"Processing {transcript['id']}...", end=" ")
        result = asyncio.run(test_single_transcript(transcript, provider, model, verbose=False))
        results.append(result)

        if "error" in result:
            console.print(f"[red]ERROR: {result['error'][:50]}...[/red]")
        else:
            console.print(f"[green]{result['accuracy']:.0%}[/green]")

    # Calculate overall accuracy
    successful = [r for r in results if "error" not in r]
    if successful:
        overall_accuracy = sum(r["accuracy"] for r in successful) / len(successful)
        avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
    else:
        overall_accuracy = 0.0
        avg_confidence = 0.0

    errors = [r for r in results if "error" in r]

    # Create results table
    table = Table(title="Extraction Accuracy Results")
    table.add_column("Transcript ID", style="cyan")
    table.add_column("Accuracy", justify="right")
    table.add_column("Confidence", justify="right")
    table.add_column("Status")

    for result in results:
        if "error" in result:
            table.add_row(
                result["id"],
                "N/A",
                "N/A",
                f"[red]Error: {result['error'][:30]}...[/red]",
            )
        else:
            status = "[green]PASS[/green]" if result["accuracy"] >= 0.8 else "[yellow]REVIEW[/yellow]"
            table.add_row(
                result["id"],
                f"{result['accuracy']:.0%}",
                f"{result['confidence']:.2f}",
                status,
            )

    console.print(table)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total transcripts: {len(results)}")
    console.print(f"Successful: {len(successful)}")
    console.print(f"Errors: {len(errors)}")
    console.print(f"Overall accuracy: {overall_accuracy:.1%}")
    console.print(f"Average confidence: {avg_confidence:.2f}")

    if overall_accuracy >= 0.8:
        console.print("\n[green]✓ Meets 80% accuracy threshold[/green]")
    else:
        console.print("\n[red]✗ Below 80% accuracy threshold[/red]")

    if errors:
        console.print("\n[yellow]Errors encountered:[/yellow]")
        for error in errors[:3]:
            console.print(f"  - {error['id']}: {error['error'][:50]}...")


@app.command()
def list_transcripts() -> None:
    """List available test transcripts."""
    transcripts = load_transcripts()

    table = Table(title="Available Test Transcripts")
    table.add_column("ID", style="cyan")
    table.add_column("Scenario")
    table.add_column("Complexity")
    table.add_column("Preview")

    for t in transcripts:
        preview = t["text"][:50] + "..."
        table.add_row(
            t["id"],
            t["metadata"]["scenario"],
            t["metadata"]["complexity"],
            preview,
        )

    console.print(table)
    console.print(f"\nTotal: {len(transcripts)} transcripts")


if __name__ == "__main__":
    app()
