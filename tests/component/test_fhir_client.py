import time

import httpx
import pytest

from src.integrations.fhir.client import FHIRClient
from src.models import PatientProfile


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fhir_client_can_fetch_patient() -> None:
    """Component Test: Verifies integration with HAPI FHIR Sandbox."""

    t0 = time.time()
    client = FHIRClient()
    t1 = time.time()
    print(f"\n  Client init: {t1 - t0:.3f}s")

    # Using a verified ID found in the sandbox
    patient_id = "90128869"

    try:
        t2 = time.time()
        profile = await client.get_patient_profile(patient_id)
        t3 = time.time()
        print(f"  API call: {t3 - t2:.3f}s")

        assert isinstance(profile, PatientProfile)
        assert profile.patient_id == patient_id
        assert profile.first_name is not None
    finally:
        t4 = time.time()
        await client.close()
        t5 = time.time()
        print(f"  Cleanup: {t5 - t4:.3f}s")

    print(f"  Total: {t5 - t0:.3f}s")


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
