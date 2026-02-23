#!/usr/bin/env python3
"""Seed database with test recordings for development."""

import asyncio
import sys

from pwa.backend.database import AsyncSessionLocal, init_db
from pwa.backend.models.recording import Recording, RecordingStatus
from pwa.backend.services.recording_service import RecordingService


async def create_test_recordings(service: RecordingService) -> list[tuple[str, Recording]]:
    """Create test recordings with varied statuses."""
    recordings = []

    # Recording 1: Pending status
    recording1 = await service.create_recording(
        patient_id="patient-001",
        clinician_id="clinician-001",
        duration_seconds=120,
        audio_file_path="/uploads/audio_001.webm",
    )
    recordings.append(("PENDING", recording1))
    print(f"  Created: {recording1.id} - Patient {recording1.patient_id} ({recording1.duration_seconds}s)")

    # Recording 2: Completed with transcript
    recording2 = await service.create_recording(
        patient_id="patient-002",
        clinician_id="clinician-001",
        duration_seconds=180,
        audio_file_path="/uploads/audio_002.webm",
    )
    await service.update_recording_status(recording2.id, RecordingStatus.COMPLETED)
    recordings.append(("COMPLETED", recording2))
    print(f"  Created: {recording2.id} - Patient {recording2.patient_id} ({recording2.duration_seconds}s)")

    # Recording 3: Error status
    recording3 = await service.create_recording(
        patient_id="patient-003",
        clinician_id="clinician-002",
        duration_seconds=90,
        audio_file_path="/uploads/audio_003.webm",
    )
    await service.update_recording_status(recording3.id, RecordingStatus.ERROR, "Transcription service timeout")
    recordings.append(("ERROR", recording3))
    print(f"  Created: {recording3.id} - Patient {recording3.patient_id} ({recording3.duration_seconds}s)")

    # Recording 4: Processing status
    recording4 = await service.create_recording(
        patient_id="patient-004",
        clinician_id="clinician-002",
        duration_seconds=240,
        audio_file_path="/uploads/audio_004.webm",
    )
    await service.update_recording_status(recording4.id, RecordingStatus.PROCESSING)
    recordings.append(("PROCESSING", recording4))
    print(f"  Created: {recording4.id} - Patient {recording4.patient_id} ({recording4.duration_seconds}s)")

    # Recording 5: Another completed from different clinician
    recording5 = await service.create_recording(
        patient_id="patient-005",
        clinician_id="clinician-003",
        duration_seconds=300,
        audio_file_path="/uploads/audio_005.webm",
    )
    await service.update_recording_status(recording5.id, RecordingStatus.COMPLETED)
    recordings.append(("COMPLETED", recording5))
    print(f"  Created: {recording5.id} - Patient {recording5.patient_id} ({recording5.duration_seconds}s)")

    return recordings


async def seed() -> int:
    """Initialize database and populate with test data.

    Returns:
        0 on success, 1 on error
    """
    print("=" * 60)
    print("Database Seeding Script")
    print("=" * 60)
    print()

    try:
        print("Step 1: Initializing database...")
        await init_db()
        print("  Database initialized successfully")
        print()

        print("Step 2: Creating test recordings...")
        async with AsyncSessionLocal() as session:
            service = RecordingService(session)
            recordings = await create_test_recordings(service)
        print()

        print("Step 3: Summary")
        print("-" * 60)
        print(f"Total recordings created: {len(recordings)}")
        print()
        print("Breakdown by status:")
        status_counts: dict[str, int] = {}
        for status, _ in recordings:
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        print()
        print("Clinicians with recordings:")
        clinician_ids = set()
        for _, recording in recordings:
            clinician_ids.add(recording.clinician_id)
        for clinician_id in sorted(clinician_ids):
            count = sum(1 for _, r in recordings if r.clinician_id == clinician_id)
            print(f"  {clinician_id}: {count} recording(s)")
        print()
        print("=" * 60)
        print("Database seeded successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: Failed to seed database: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(seed()))
