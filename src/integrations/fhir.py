import logging
from datetime import datetime

import httpx

from ..models import EMRContext, PatientProfile

logger = logging.getLogger(__name__)


class FHIRAdapter:
    """
    Adapter for HL7 FHIR R4 standard.
    Connects to public HAPI FHIR server to demonstrate EMR integration.
    """

    def __init__(self, base_url: str = "http://hapi.fhir.org/baseR4"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def fetch_patient_context(
        self, patient_id: str
    ) -> tuple[PatientProfile, EMRContext] | None:
        """
        Fetches Patient and their latest Encounter from FHIR server.
        Demonstrates complex data mapping from FHIR standard to Domain models.
        """
        try:
            # 1. Fetch Patient Resource
            patient_res = await self._client.get(f"{self.base_url}/Patient/{patient_id}")
            if patient_res.status_code != 200:
                logger.error(f"FHIR Patient {patient_id} not found")
                return None

            p_data = patient_res.json()

            # 2. Fetch Latest Encounter
            encounter_res = await self._client.get(
                f"{self.base_url}/Encounter",
                params={"patient": patient_id, "_sort": "-date", "_count": 1},
            )

            e_data = encounter_res.json()
            latest_encounter = None
            if e_data.get("entry"):
                latest_encounter = e_data["entry"][0]["resource"]

            # 3. Map FHIR to Pydantic (High-Assurance Mapping)
            # FHIR names are complex: list of names with given/family lists
            first_name = "Unknown"
            last_name = "Unknown"
            if p_data.get("name"):
                name = p_data["name"][0]
                last_name = name.get("family", "Unknown")
                first_name = " ".join(name.get("given", ["Unknown"]))

            from datetime import date

            patient_profile = PatientProfile(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                dob=date.fromisoformat(p_data.get("birthDate", "1900-01-01")),
                diagnoses=[],  # Would normally fetch Condition resources
            )

            # Map Encounter to EMRContext
            admission_date = datetime.now()  # Fallback
            if latest_encounter and latest_encounter.get("period"):
                period = latest_encounter["period"]
                if period.get("start"):
                    # Strip timezone for simple ISO parsing in this demo
                    admission_date = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))

            emr_context = EMRContext(
                visit_id=(
                    latest_encounter.get("id", "VISIT-UNKNOWN")
                    if latest_encounter
                    else "VISIT-MOCK"
                ),
                patient_id=patient_id,
                admission_date=admission_date,
                attending_physician="Dr. FHIR Sandbox",
                raw_notes="Source: HAPI FHIR Public Sandbox",
            )

            return patient_profile, emr_context

        except Exception as e:
            logger.error(f"FHIR Integration Error: {str(e)}")
            return None

    async def close(self):
        await self._client.aclose()
