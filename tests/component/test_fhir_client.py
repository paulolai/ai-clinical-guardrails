import httpx
import pytest

from src.integrations.fhir.client import FHIRClient
from src.models import PatientProfile


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fhir_client_can_fetch_patient() -> None:
    """Component Test: Verifies integration with HAPI FHIR Sandbox."""
    client = FHIRClient()
    # Using a verified ID found in the sandbox
    patient_id = "90128869"

    try:
        profile = await client.get_patient_profile(patient_id)

        assert isinstance(profile, PatientProfile)
        assert profile.patient_id == patient_id
        assert profile.first_name is not None
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fhir_client_handles_missing_patient() -> None:
    client = FHIRClient()
    try:
        # Purposely using an unlikely random string
        # Should raise HTTP error for non-existent patient
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_patient_profile("NON_EXISTENT_ID_XYZ_123")
    finally:
        await client.close()
