"""Playwright tests for IndexedDB functionality."""

from playwright.sync_api import Page


def test_indexeddb_stores_recording(page: Page) -> None:
    """Test that IndexedDB can store and retrieve a recording."""
    # This test will initially fail because the service doesn't exist
    page.goto("http://localhost:8002/record/patient-123")

    # Execute IndexedDB operations via page.evaluate
    result = page.evaluate("""
        async () => {
            if (!window.RecordingStorage) {
                return { error: 'RecordingStorage not defined' };
            }

            const recording = {
                id: 'test-recording-123',
                patient_id: 'patient-123',
                clinician_id: 'clinician-456',
                duration_seconds: 60,
                audio_blob: new Blob(['test audio data'], { type: 'audio/wav' }),
                created_at: new Date().toISOString(),
                sync_status: 'pending_upload'
            };

            await window.RecordingStorage.saveRecording(recording);
            const retrieved = await window.RecordingStorage.getRecording('test-recording-123');

            // Clean up
            await window.RecordingStorage.deleteRecording('test-recording-123');

            return {
                saved: true,
                retrieved: retrieved ? true : false,
                id: retrieved?.id
            };
        }
    """)

    assert result.get("error") is None, f"IndexedDB service error: {result.get('error')}"
    assert result["saved"] is True
    assert result["retrieved"] is True
    assert result["id"] == "test-recording-123"


def test_indexeddb_lists_pending_recordings(page: Page) -> None:
    """Test listing pending recordings."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        async () => {
            if (!window.RecordingStorage) {
                return { error: 'RecordingStorage not defined' };
            }

            // Save two recordings
            await window.RecordingStorage.saveRecording({
                id: 'rec-1',
                patient_id: 'patient-123',
                sync_status: 'pending_upload',
                created_at: new Date().toISOString()
            });

            await window.RecordingStorage.saveRecording({
                id: 'rec-2',
                patient_id: 'patient-456',
                sync_status: 'uploaded',
                created_at: new Date().toISOString()
            });

            const pending = await window.RecordingStorage.getPendingRecordings();

            // Clean up
            await window.RecordingStorage.deleteRecording('rec-1');
            await window.RecordingStorage.deleteRecording('rec-2');

            return {
                pending_count: pending.length,
                pending_ids: pending.map(r => r.id)
            };
        }
    """)

    assert result.get("error") is None
    assert result["pending_count"] == 1
    assert "rec-1" in result["pending_ids"]
