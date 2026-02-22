#!/usr/bin/env python3
"""CLI tool for clinical note review workflow."""

import sys
from datetime import datetime
from typing import Any

import httpx
import typer
from rich.console import Console

app = typer.Typer(help="CLI tool for clinical note review workflow.")
console = Console()

API_BASE = "http://localhost:8000"


def format_review(review_data: dict[str, Any]) -> str:
    """Format review data for display."""
    lines = []
    lines.append("=" * 80)
    lines.append("CLINICAL NOTE REVIEW")
    lines.append("=" * 80)
    lines.append("")

    # Patient info
    note = review_data.get("note", {})
    emr = review_data.get("emr_context", {})
    patient_id = note.get("patient_id", "Unknown")
    note_id = note.get("note_id", "Unknown")
    created_at = review_data.get("created_at", datetime.now().isoformat())

    # Try to get patient name from EMR context
    patient_name = "Unknown"
    raw_notes = emr.get("raw_notes", "")
    if raw_notes:
        # Try to extract name from raw_notes if available
        patient_name = emr.get("attending_physician", "Patient")

    lines.append(f"Patient: {patient_name} (ID: {patient_id})")
    lines.append(f"Review ID: {note_id}")
    if isinstance(created_at, str):
        lines.append(f"Created: {created_at}")
    else:
        lines.append(f"Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # AI Note sections
    lines.append("-" * 80)
    lines.append("AI NOTE SECTIONS")
    lines.append("-" * 80)
    sections = note.get("sections", {})
    if sections:
        for section_name, content in sections.items():
            lines.append(f"  {section_name}: {content}")
            lines.append("")
    else:
        lines.append("  (No sections provided)")
        lines.append("")

    # EMR Context
    lines.append("-" * 80)
    lines.append("EMR CONTEXT")
    lines.append("-" * 80)
    visit_id = emr.get("visit_id", "Unknown")
    admission_date = emr.get("admission_date", "Unknown")
    discharge_date = emr.get("discharge_date")
    attending = emr.get("attending_physician", "Unknown")

    lines.append(f"  Visit ID: {visit_id}")
    if isinstance(admission_date, str):
        lines.append(f"  Admission: {admission_date}")
    else:
        lines.append(f"  Admission: {admission_date.strftime('%Y-%m-%d %H:%M') if admission_date else 'Unknown'}")

    if discharge_date:
        if isinstance(discharge_date, str):
            lines.append(f"  Discharge: {discharge_date}")
        else:
            lines.append(f"  Discharge: {discharge_date.strftime('%Y-%m-%d %H:%M')}")

    lines.append(f"  Physician: {attending}")
    lines.append("")

    # Verification
    lines.append("-" * 80)
    lines.append("VERIFICATION RESULTS")
    lines.append("-" * 80)
    verification = review_data.get("verification", {})
    if verification:
        is_safe = verification.get("is_safe_to_file", False)
        status = "VERIFIED" if is_safe else "REJECTED"
        score = verification.get("score", 0.0)

        lines.append(f"  Status: {status}")
        lines.append(f"  Confidence: {score:.2f}")
        lines.append("")

        alerts = verification.get("alerts", [])
        if alerts:
            lines.append("  Alerts:")
            for alert in alerts:
                severity = alert.get("severity", "UNKNOWN").upper()
                message = alert.get("message", "No message")
                lines.append(f"    [{severity}] {message}")
        else:
            lines.append("  Alerts: None")

        lines.append("")

        # Discrepancies section
        lines.append("  Discrepancies: None")
    else:
        lines.append("  Status: ERROR - Verification failed")

    lines.append("")
    lines.append("=" * 80)
    review_url = review_data.get("review_url", f"/review/{note_id}")
    lines.append(f"REVIEW URL: {review_url}")
    lines.append("=" * 80)

    return "\n".join(lines)


@app.command()
def create(
    patient_id: str = typer.Option(..., help="Patient ID"),
    transcript: str = typer.Option(..., help="Transcript text"),
    encounter_id: str | None = typer.Option(None, help="Encounter ID (auto-generated if not provided)"),
    sections: list[str] | None = typer.Option(None, help="Note sections in format 'name:content'"),  # noqa: B008
    api_url: str = typer.Option("http://localhost:8000", help="API base URL"),
    show_json: bool = typer.Option(False, "--json", help="Also output raw JSON"),
) -> None:
    """Create a new clinical note review."""

    # Parse sections
    sections_dict = {}
    for section in sections or []:
        if ":" in section:
            name, content = section.split(":", 1)
            sections_dict[name.strip()] = content.strip()

    payload = {
        "patient_id": patient_id,
        "encounter_id": encounter_id or f"enc-{datetime.now().timestamp()}",
        "transcript": transcript,
        "sections": sections_dict,
    }

    try:
        response = httpx.post(f"{api_url}/review/create", json=payload, timeout=30.0)
        response.raise_for_status()

        review_data = response.json()

        # Print formatted output
        console.print(format_review(review_data))

        if show_json:
            console.print("\n" + "=" * 80)
            console.print("RAW JSON:")
            console.print("=" * 80)
            console.print_json(data=review_data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print(f"[red]❌ Error: Patient '{patient_id}' not found in EMR[/red]")
        else:
            console.print(f"[red]❌ API Error ({e.response.status_code}):[/red] {e.response.text}")
        sys.exit(1)
    except httpx.ConnectError:
        console.print(f"[red]❌ Error: Cannot connect to API at {api_url}[/red]")
        console.print("[yellow]   Make sure the API server is running (uv run python main.py)[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        sys.exit(1)


@app.command()
def view(
    note_id: str = typer.Option(..., help="Note ID to view"),
    api_url: str = typer.Option("http://localhost:8000", help="API base URL"),
) -> None:
    """View an existing review.

    Note: For demo purposes, GET /review/{note_id} returns 501 Not Implemented.
    Use 'create' command to generate new reviews.
    """

    try:
        response = httpx.get(f"{api_url}/review/{note_id}", timeout=20.0)
        response.raise_for_status()

        review_data = response.json()
        console.print(format_review(review_data))

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 501:
            console.print("[yellow]⚠️  Note: GET /review/{note_id} is not implemented in the demo version.[/yellow]")
            console.print("[yellow]   Use 'create' command to generate new reviews.[/yellow]")
        elif e.response.status_code == 404:
            console.print(f"[red]❌ Error: Review '{note_id}' not found[/red]")
        else:
            console.print(f"[red]❌ API Error ({e.response.status_code}):[/red] {e.response.text}")
        sys.exit(1)
    except httpx.ConnectError:
        console.print(f"[red]❌ Error: Cannot connect to API at {api_url}[/red]")
        console.print("[yellow]   Make sure the API server is running (uv run python main.py)[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
