import logging
from datetime import datetime

import httpx

from ...models import EMRContext, PatientProfile
from .generated import Encounter, Patient

logger = logging.getLogger(__name__)


class FHIRClient:
    """
    Wrapper Object for FHIR API interactions.
    Consumes the FULL set of official generated FHIR models while
    returning only the necessary clean domain objects.
    """

    def __init__(self, base_url: str = "http://hapi.fhir.org/baseR4"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_patient_profile(self, patient_id: str) -> PatientProfile:
        """Fetches and maps a patient using official generated classes."""
        response = await self._client.get(f"{self.base_url}/Patient/{patient_id}")
        response.raise_for_status()

        # 1. Parse into OFFICIAL generated model
        raw_patient = Patient.model_validate(response.json())

        # 2. Map to Domain Wrapper
        name_obj = raw_patient.name[0] if raw_patient.name else None

        # Generated models use RootModels for primitive types (root: str)
        first_name = "Unknown"
        if name_obj and name_obj.given:
            first_name = " ".join([str(g.root) for g in name_obj.given])

        last_name = str(name_obj.family.root) if (name_obj and name_obj.family) else "Unknown"

        # Parse birth date string to date object
        dob_str = raw_patient.birthDate.root if raw_patient.birthDate else "1900-01-01"
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()

        return PatientProfile(
            patient_id=str(raw_patient.id.root) if raw_patient.id else patient_id,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
        )

    async def get_latest_encounter(self, patient_id: str) -> EMRContext:
        """Fetches latest encounter using official full-spec generated classes."""
        response = await self._client.get(
            f"{self.base_url}/Encounter",
            params={"patient": patient_id, "_sort": "-date", "_count": 1},
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("entry"):
            raise ValueError(f"No encounters found for patient {patient_id}")

        # Parse into FULL spec generated model
        raw_encounter = Encounter.model_validate(data["entry"][0]["resource"])

        # Admission/Discharge mapping with RootModel safety
        admission_date: datetime | None = None
        discharge_date: datetime | None = None

        if raw_encounter.period:
            if raw_encounter.period.start:
                admission_date = datetime.fromisoformat(raw_encounter.period.start.root)
            if raw_encounter.period.end:
                discharge_date = datetime.fromisoformat(raw_encounter.period.end.root)

        status = raw_encounter.status.value if raw_encounter.status else "unknown"

        if admission_date is None:
            raise ValueError(f"Encounter for patient {patient_id} has no admission date")

        return EMRContext(
            visit_id=str(raw_encounter.id.root) if raw_encounter.id else "VISIT-UNKNOWN",
            patient_id=patient_id,
            admission_date=admission_date,
            discharge_date=discharge_date,
            attending_physician="FHIR Sandbox Provider",
            raw_notes=f"Encounter status: {status}",
        )

    async def close(self) -> None:
        await self._client.aclose()
