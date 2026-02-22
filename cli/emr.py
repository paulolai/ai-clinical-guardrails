import asyncio

import click

from src.integrations.fhir.client import FHIRClient


@click.group()
def cli() -> None:
    """Interface handle for the Upstream FHIR EMR."""
    pass


@cli.command()
@click.argument("patient_id")
def inspect(patient_id: str) -> None:
    """Directly inspect raw-to-wrapped FHIR data for a patient."""

    async def _run() -> None:
        client = FHIRClient()
        try:
            click.echo(f"🔍 [FHIR] Fetching Patient {patient_id}...")
            profile = await client.get_patient_profile(patient_id)
            click.secho(
                f"✅ Domain Profile: {profile.first_name} {profile.last_name} (DOB: {profile.dob})",
                fg="green",
            )

            try:
                context = await client.get_latest_encounter(patient_id)
                click.secho(
                    f"✅ Latest Visit: {context.visit_id} (Admitted: {context.admission_date})",
                    fg="green",
                )
            except Exception as e:
                click.secho(f"⚠️ Encounter Note: {str(e)}", fg="yellow")
        finally:
            await client.close()

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
