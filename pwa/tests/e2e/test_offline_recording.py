"""Playwright tests for offline recording functionality."""

from playwright.sync_api import Page, expect


def test_recorder_module_loaded(page: Page) -> None:
    """Test that recorder module is loaded and has expected functions."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        () => {
            return {
                toggleRecordingDefined: typeof toggleRecording === 'function',
                startRecordingDefined: typeof startRecording === 'function',
                stopRecordingDefined: typeof stopRecording === 'function',
                handleRecordingCompleteDefined: typeof handleRecordingComplete === 'function',
                recorderStateDefined: typeof window.RecorderState !== 'undefined'
            };
        }
    """)

    assert result["toggleRecordingDefined"] is True, "toggleRecording not defined"
    assert result["startRecordingDefined"] is True, "startRecording not defined"
    assert result["stopRecordingDefined"] is True, "stopRecording not defined"
    assert result["handleRecordingCompleteDefined"] is True, "handleRecordingComplete not defined"
    assert result["recorderStateDefined"] is True, "RecorderState not defined"


def test_offline_storage_integration(page: Page) -> None:
    """Test that recording is saved to IndexedDB via handleRecordingComplete."""
    page.goto("http://localhost:8002/record/patient-123")

    # Simulate offline
    page.context.set_offline(True)

    # Call handleRecordingComplete directly with test data
    result = page.evaluate("""
        async () => {
            try {
                // Set up test state
                window.RecorderState.currentRecordingId = 'test-recording-' + Date.now();
                window.RecorderState.audioChunks = [new Blob(['test audio data'], { type: 'audio/wav' })];
                window.RecorderState.recordingStartTime = Date.now() - 2000; // 2 seconds ago
                window.RecorderState.draftTranscript = 'Test draft transcript';

                // Call handleRecordingComplete
                await handleRecordingComplete();

                // Check IndexedDB
                const recordings = await window.RecordingStorage.getAllRecordings();
                const testRecording = recordings.find(r => r.id === window.RecorderState.currentRecordingId);

                return {
                    success: true,
                    recordingFound: !!testRecording,
                    recordingId: window.RecorderState.currentRecordingId,
                    syncStatus: testRecording?.sync_status,
                    draftTranscript: testRecording?.draft_transcript
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message
                };
            }
        }
    """)

    # Restore online
    page.context.set_offline(False)

    assert result["success"] is True, f"handleRecordingComplete failed: {result.get('error')}"
    assert result["recordingFound"] is True, "Recording not found in IndexedDB"
    assert result["syncStatus"] == "pending_upload", (
        f"Expected sync_status 'pending_upload', got '{result.get('sync_status')}'"
    )


def test_recorder_ui_elements_exist(page: Page) -> None:
    """Test that required UI elements exist."""
    page.goto("http://localhost:8002/record/patient-123")

    # Check all required elements exist (timer is inside hidden recording-status)
    expect(page.locator("#record-btn")).to_be_visible()
    expect(page.locator("#record-text")).to_be_visible()
    expect(page.locator("#timer")).to_be_attached()  # Element exists even if hidden


def test_recorder_integrates_with_upload_manager(page: Page) -> None:
    """Test that recorder integrates with UploadManager."""
    page.goto("http://localhost:8002/record/patient-123")

    result = page.evaluate("""
        async () => {
            try {
                // Set up test state
                window.RecorderState.currentRecordingId = 'test-recording-upload-' + Date.now();
                window.RecorderState.audioChunks = [new Blob(['test audio data'], { type: 'audio/wav' })];
                window.RecorderState.recordingStartTime = Date.now() - 2000;
                window.RecorderState.draftTranscript = null;

                // Call handleRecordingComplete
                await handleRecordingComplete();

                // Check recording was queued for upload
                const recordings = await window.RecordingStorage.getAllRecordings();
                const testRecording = recordings.find(r => r.id === window.RecorderState.currentRecordingId);

                return {
                    recordingSaved: !!testRecording,
                    hasAudioBlob: testRecording?.audio_blob instanceof Blob,
                    hasDuration: typeof testRecording?.duration_seconds === 'number',
                    patientId: testRecording?.patient_id
                };
            } catch (error) {
                return {
                    recordingSaved: false,
                    error: error.message
                };
            }
        }
    """)

    assert result["recordingSaved"] is True, f"Recording not saved: {result.get('error')}"
    assert result["hasAudioBlob"] is True, "Recording missing audio blob"
    assert result["hasDuration"] is True, "Recording missing duration"
