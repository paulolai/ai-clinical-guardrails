"""CLI tool for extracting structured data from clinical transcripts.

Uses LLM-based extraction to parse unstructured clinical dictation
and output structured JSON data.
"""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from src.extraction import LLMTranscriptParser, SyntheticLLMClient
from src.extraction.models import StructuredExtraction

app = typer.Typer(help="Extract structured data from clinical transcripts using LLM.")
console = Console()


def _check_api_key() -> str | None:
    """Check if SYNTHETIC_API_KEY is available."""
    import os

    return os.environ.get("SYNTHETIC_API_KEY")


@app.command()
def extract(
    text: str | None = typer.Option(None, "--text", "-t", help="Transcript text to extract from"),  # noqa: B008
    file: Path | None = typer.Option(None, "--file", "-f", help="Path to transcript file"),  # noqa: B008
    reference_date: str | None = typer.Option(
        None,
        "--date",
        "-d",
        help="Reference date for temporal expressions (YYYY-MM-DD). Defaults to today.",
    ),
    model: str = typer.Option(  # noqa: B008
        "hf:nvidia/Kimi-K2.5-NVFP4",
        "--model",
        "-m",
        help="Model ID to use for extraction",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path (JSON)"),  # noqa: B008
    pretty: bool = typer.Option(True, "--pretty/--no-pretty", help="Pretty print output"),  # noqa: B008
) -> None:
    """Extract structured data from a clinical transcript.

    Examples:
        # Extract from text
        python cli/extract.py --text "Patient came in yesterday..."

        # Extract from file
        python cli/extract.py --file transcript.txt

        # With specific date
        python cli/extract.py --file transcript.txt --date 2024-01-15

        # Save to file
        python cli/extract.py --file transcript.txt --output result.json
    """
    # Validate inputs
    if not text and not file:
        console.print("[red]❌ Error:[/red] Provide either --text or --file")
        raise typer.Exit(1)

    if text and file:
        console.print("[red]❌ Error:[/red] Provide only one of --text or --file")
        raise typer.Exit(1)

    # Check API key
    api_key = _check_api_key()
    if not api_key:
        console.print(
            Panel(
                "[red]SYNTHETIC_API_KEY not found![/red]\n\n"
                "Set it via environment variable:\n"
                "  export SYNTHETIC_API_KEY=your_key\n\n"
                "Or create .env.secrets file:\n"
                "  SYNTHETIC_API_KEY=your_key",
                title="API Key Required",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Read transcript
    if file:
        if not file.exists():
            console.print(f"[red]❌ Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        transcript_text = file.read_text()
    elif text:
        transcript_text = text
    else:
        console.print("[red]❌ Error:[/red] No transcript provided")
        raise typer.Exit(1)

    # Parse reference date
    ref_date = None
    if reference_date:
        try:
            ref_date = date.fromisoformat(reference_date)
        except ValueError:
            console.print(f"[red]❌ Error:[/red] Invalid date format: {reference_date}. Use YYYY-MM-DD.")
            raise typer.Exit(1) from None

    # Run extraction
    try:
        result = asyncio.run(_extract_async(transcript_text, ref_date, model, api_key))
    except Exception as e:
        console.print(f"[red]❌ Extraction failed:[/red] {str(e)}")
        raise typer.Exit(1) from None

    # Output results
    result_dict = _extraction_to_dict(result)

    if output:
        output.write_text(json.dumps(result_dict, indent=2))
        console.print(f"[green]✅ Results saved to:[/green] {output}")
    else:
        _print_extraction_result(result, result_dict, pretty)


async def _extract_async(
    text: str,
    reference_date: date | None,
    model: str,
    api_key: str,
) -> StructuredExtraction:
    """Async extraction wrapper."""
    async with SyntheticLLMClient(api_key=api_key, model=model) as client:
        parser = LLMTranscriptParser(llm_client=client, reference_date=reference_date)
        return await parser.parse(text)


def _extraction_to_dict(result: StructuredExtraction) -> dict[str, Any]:
    """Convert extraction result to dictionary."""
    return {
        "patient_name": result.patient_name,
        "patient_age": result.patient_age,
        "visit_type": result.visit_type,
        "confidence": result.confidence,
        "medications": [
            {
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "route": m.route,
                "status": m.status.value,
                "confidence": m.confidence,
            }
            for m in result.medications
        ],
        "diagnoses": [
            {
                "text": d.text,
                "icd10_code": d.icd10_code,
                "confidence": d.confidence,
            }
            for d in result.diagnoses
        ],
        "temporal_expressions": [
            {
                "text": t.text,
                "type": t.type.value,
                "normalized_date": t.normalized_date.isoformat() if t.normalized_date else None,
                "confidence": t.confidence,
                "note": t.note,
            }
            for t in result.temporal_expressions
        ],
        "vital_signs": result.vital_signs,
        "has_low_confidence": result.has_low_confidence_extractions(),
    }


def _print_extraction_result(
    result: StructuredExtraction,
    result_dict: dict[str, Any],
    pretty: bool,
) -> None:
    """Pretty print extraction result."""
    # Header
    confidence_color = "green" if result.confidence >= 0.8 else "yellow" if result.confidence >= 0.5 else "red"
    console.print(
        Panel(
            f"[bold]Extraction Complete[/bold]\n"
            f"Confidence: [{confidence_color}]{result.confidence:.2f}[/{confidence_color}]",
            border_style="blue",
        )
    )

    # Patient info
    if result.patient_name:
        console.print(f"\n[bold]Patient:[/bold] {result.patient_name}")
    if result.patient_age:
        console.print(f"[bold]Age:[/bold] {result.patient_age}")
    if result.visit_type:
        console.print(f"[bold]Visit Type:[/bold] {result.visit_type}")

    # Medications table
    if result.medications:
        console.print("\n[bold]Medications:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Dosage")
        table.add_column("Frequency")
        table.add_column("Status")
        table.add_column("Confidence")

        for med in result.medications:
            conf_color = "green" if med.confidence >= 0.8 else "yellow" if med.confidence >= 0.5 else "red"
            table.add_row(
                med.name,
                med.dosage or "-",
                med.frequency or "-",
                med.status.value,
                f"[{conf_color}]{med.confidence:.2f}[/{conf_color}]",
            )
        console.print(table)

    # Diagnoses table
    if result.diagnoses:
        console.print("\n[bold]Diagnoses:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Condition")
        table.add_column("ICD-10")
        table.add_column("Confidence")

        for diag in result.diagnoses:
            conf_color = "green" if diag.confidence >= 0.8 else "yellow" if diag.confidence >= 0.5 else "red"
            table.add_row(
                diag.text,
                diag.icd10_code or "-",
                f"[{conf_color}]{diag.confidence:.2f}[/{conf_color}]",
            )
        console.print(table)

    # Temporal expressions
    if result.temporal_expressions:
        console.print("\n[bold]Temporal Expressions:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Text")
        table.add_column("Type")
        table.add_column("Normalized Date")
        table.add_column("Confidence")

        for temp in result.temporal_expressions:
            conf_color = "green" if temp.confidence >= 0.8 else "yellow" if temp.confidence >= 0.5 else "red"
            table.add_row(
                temp.text,
                temp.type.value,
                temp.normalized_date.isoformat() if temp.normalized_date else "-",
                f"[{conf_color}]{temp.confidence:.2f}[/{conf_color}]",
            )
        console.print(table)

    # Vital signs
    if result.vital_signs:
        console.print("\n[bold]Vital Signs:[/bold]")
        for vs in result.vital_signs:
            console.print(f"  • {vs.get('type', 'unknown')}: {vs.get('value', '-')}")

    # Warnings
    if result.has_low_confidence_extractions():
        console.print("\n[yellow]⚠️  Warning: Some extractions have low confidence and should be reviewed.[/yellow]")

    # Raw JSON
    if pretty:
        console.print("\n[bold]Raw JSON Output:[/bold]")
        console.print(JSON(json.dumps(result_dict, indent=2)))


@app.command()
def test(
    index: int = typer.Option(0, "--index", "-i", help="Sample transcript index (0-9)"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty", help="Pretty print output"),
) -> None:
    """Extract from a built-in sample transcript.

    Examples:
        # Test with first sample
        python cli/extract.py test

        # Test with specific sample
        python cli/extract.py test --index 3
    """
    import json as json_mod

    # Load sample transcripts
    fixtures_path = Path("tests/fixtures/sample_transcripts.json")
    if not fixtures_path.exists():
        console.print("[red]❌ Error:[/red] Sample transcripts not found")
        raise typer.Exit(1)

    data = json_mod.loads(fixtures_path.read_text())
    transcripts = data.get("transcripts", [])

    if index < 0 or index >= len(transcripts):
        console.print(f"[red]❌ Error:[/red] Invalid index. Use 0-{len(transcripts) - 1}")
        raise typer.Exit(1)

    sample = transcripts[index]
    console.print(f"\n[bold]Sample {index}:[/bold] {sample['id']}")
    console.print(f"[dim]Scenario:[/dim] {sample['metadata']['scenario']}")
    console.print(f"[dim]Complexity:[/dim] {sample['metadata']['complexity']}")
    console.print(f"\n[bold]Transcript:[/bold]\n{sample['text']}\n")

    # Run extraction on this sample
    api_key = _check_api_key()
    if not api_key:
        console.print(
            Panel(
                "[red]SYNTHETIC_API_KEY not found![/red]\n\n"
                "Set it via environment variable:\n"
                "  export SYNTHETIC_API_KEY=your_key\n\n"
                "Or create .env.secrets file:\n"
                "  SYNTHETIC_API_KEY=your_key",
                title="API Key Required",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    try:
        result = asyncio.run(_extract_async(sample["text"], None, "hf:nvidia/Kimi-K2.5-NVFP4", api_key))
    except Exception as e:
        console.print(f"[red]❌ Extraction failed:[/red] {str(e)}")
        raise typer.Exit(1) from None

    result_dict = _extraction_to_dict(result)
    _print_extraction_result(result, result_dict, pretty)


@app.command()
def list_samples() -> None:
    """List available sample transcripts."""
    import json as json_mod

    fixtures_path = Path("tests/fixtures/sample_transcripts.json")
    if not fixtures_path.exists():
        console.print("[red]❌ Error:[/red] Sample transcripts not found")
        raise typer.Exit(1)

    data = json_mod.loads(fixtures_path.read_text())
    transcripts = data.get("transcripts", [])

    console.print(f"\n[bold]Available Sample Transcripts ({len(transcripts)} total):[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Index", justify="right", style="cyan")
    table.add_column("ID")
    table.add_column("Scenario")
    table.add_column("Complexity")
    table.add_column("Expected Alerts")

    for i, sample in enumerate(transcripts):
        metadata = sample["metadata"]
        table.add_row(
            str(i),
            sample["id"],
            metadata["scenario"],
            metadata["complexity"],
            ", ".join(metadata.get("expected_alerts", [])) or "None",
        )

    console.print(table)
    console.print("\n[dim]Use: python cli/extract.py test --index N[/dim]")


if __name__ == "__main__":
    app()
