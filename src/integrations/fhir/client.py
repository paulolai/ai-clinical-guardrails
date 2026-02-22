import logging
from datetime import datetime

import httpx

from ...models import EMRContext, PatientProfile

logger = logging.getLogger(__name__)


class FHIRClient:
    """
    Wrapper Object for FHIR API interactions.
    Consumes the official fhir.resources (Pydantic, FHIR R5) models while
    returning only the necessary clean domain objects.
    """

    def __init__(self, base_url: str = "http://hapi.fhir.org/baseR5"):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of httpx client for VCR compatibility."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_patient_profile(self, patient_id: str) -> PatientProfile:
        """Fetches and maps a patient using official fhir.resources classes."""
        # Lazy import to ensure instant CLI startup
        from fhir.resources.patient import Patient

        response = await self._get_client().get(f"{self.base_url}/Patient/{patient_id}")
        response.raise_for_status()

        # 1. Parse into OFFICIAL fhir.resources model
        raw_patient = Patient.model_validate(response.json())

        # 2. Map to Domain Wrapper
        name_obj = raw_patient.name[0] if raw_patient.name else None

        first_name = "Unknown"
        if name_obj and name_obj.given:
            first_name = " ".join(g for g in name_obj.given if g is not None)

        last_name = name_obj.family if (name_obj and name_obj.family) else "Unknown"

        # Parse birth date
        # fhir.resources parses birthDate as datetime.date automatically
        dob = raw_patient.birthDate if raw_patient.birthDate else datetime(1900, 1, 1).date()

        return PatientProfile(
            patient_id=raw_patient.id if raw_patient.id else patient_id,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
        )

    async def get_latest_encounter(self, patient_id: str) -> EMRContext:
        """Fetches latest encounter using official fhir.resources classes."""
        from fhir.resources.encounter import Encounter

        response = await self._get_client().get(
            f"{self.base_url}/Encounter",
            params={"patient": patient_id, "_sort": "-date", "_count": 1},
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("entry"):
            raise ValueError(f"No encounters found for patient {patient_id}")

        # Parse into OFFICIAL fhir.resources model
        raw_encounter = Encounter.model_validate(data["entry"][0]["resource"])

        # Admission/Discharge mapping
        admission_date: datetime | None = None
        discharge_date: datetime | None = None

        if raw_encounter.actualPeriod:  # R5 renamed period to actualPeriod? Check spec.
            # R5 spec says 'actualPeriod' for the actual start/end.
            if raw_encounter.actualPeriod.start:
                admission_date = raw_encounter.actualPeriod.start
            if raw_encounter.actualPeriod.end:
                discharge_date = raw_encounter.actualPeriod.end
        elif hasattr(raw_encounter, "period") and raw_encounter.period:
            # Fallback if R4/R5 ambiguity in library mapping, but R5 is explicit.
            if raw_encounter.period.start:
                admission_date = raw_encounter.period.start
            if raw_encounter.period.end:
                discharge_date = raw_encounter.period.end

        status = raw_encounter.status if raw_encounter.status else "unknown"

        if admission_date is None:
            raise ValueError(f"Encounter for patient {patient_id} has no admission date")

        return EMRContext(
            visit_id=raw_encounter.id if raw_encounter.id else "VISIT-UNKNOWN",
            patient_id=patient_id,
            admission_date=admission_date,
            discharge_date=discharge_date,
            attending_physician="FHIR Sandbox Provider",
            raw_notes=f"Encounter status: {status}",
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
