import httpx
import typer
from rich.console import Console

app = typer.Typer(help="Interface handle for the Clinical Guardrails API.")
console = Console()
API_BASE = "http://localhost:8000"


@app.command()
def verify_integrated(
    id: str = typer.Option(..., help="Patient ID in EMR"),
    text: str = typer.Option(..., help="AI generated summary text"),
    dates: str | None = typer.Option(None, help="Comma-separated dates (YYYY-MM-DD)"),
) -> None:
    """Verify AI output using the service's FHIR integration."""
    extracted_dates = dates.split(",") if dates else []
    payload = {"ai_output": {"summary_text": text, "extracted_dates": extracted_dates}}

    try:
        response = httpx.post(f"{API_BASE}/verify/fhir/{id}", json=payload, timeout=20.0)
        _print_verification(response)
    except Exception as e:
        console.print(f"[red]❌ API Error:[/red] {str(e)}")


@app.command()
def stats() -> None:
    """Check current compliance session statistics from the API."""
    try:
        response = httpx.get(f"{API_BASE}/stats")
        console.print_json(data=response.json())
    except Exception as e:
        console.print(f"[red]❌ API Error:[/red] {str(e)}")


def _print_verification(response: httpx.Response) -> None:
    if response.status_code != 200:
        console.print(f"[red]❌ Server Error ({response.status_code}):[/red] {response.text}")
        return

    data = response.json()
    console.print("\n[bold blue]--- Verification Result ---[/bold blue]")

    if data["is_safe_to_file"]:
        console.print("[bold black on green] ✅ STATUS: SAFE TO FILE [/bold black on green]")
    else:
        console.print("[bold white on red] 🚫 STATUS: BLOCKED [/bold white on red]")

    console.print(f"Score: [bold]{data['score']}[/bold]")

    if data["alerts"]:
        console.print("\n[bold]Alerts:[/bold]")
        for alert in data["alerts"]:
            color = "red" if alert["severity"] == "critical" else "yellow"
            console.print(f"  - [[{color}]{alert['rule_id']}[/{color}]] {alert['message']}")


if __name__ == "__main__":
    app()
