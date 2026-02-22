import logging
from datetime import datetime
from typing import Any

import httpx

from ...models import EMRContext, PatientProfile

logger = logging.getLogger(__name__)

# Lazy imports to avoid loading all generated models at startup
_ImportedPatient: type | None = None
_ImportedEncounter: type | None = None


def _get_patient_model() -> "type[Any]":
    global _ImportedPatient
    if _ImportedPatient is None:
        from .generated import Patient

        _ImportedPatient = Patient
    return _ImportedPatient


def _get_encounter_model() -> "type[Any]":
    global _ImportedEncounter
    if _ImportedEncounter is None:
        from .generated import Encounter

        _ImportedEncounter = Encounter
    return _ImportedEncounter


class FHIRClient:
    """
    Wrapper Object for FHIR API interactions.
    Consumes the FULL set of official generated FHIR models while
    returning only the necessary clean domain objects.
    """

    def __init__(self, base_url: str = "http://hapi.fhir.org/baseR4"):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of httpx client for VCR compatibility."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_patient_profile(self, patient_id: str) -> PatientProfile:
        """Fetches and maps a patient using official generated classes."""
        response = await self._get_client().get(f"{self.base_url}/Patient/{patient_id}")
        response.raise_for_status()

        # 1. Parse into OFFICIAL generated model (lazy import)
        patient_model = _get_patient_model()
        raw_patient = patient_model.model_validate(response.json())

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
        response = await self._get_client().get(
            f"{self.base_url}/Encounter",
            params={"patient": patient_id, "_sort": "-date", "_count": 1},
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("entry"):
            raise ValueError(f"No encounters found for patient {patient_id}")

        # Parse into FULL spec generated model (lazy import)
        encounter_model = _get_encounter_model()
        raw_encounter = encounter_model.model_validate(data["entry"][0]["resource"])

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
        if self._client is not None:
            await self._client.aclose()
