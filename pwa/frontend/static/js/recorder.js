/**
 * Recorder Module - Handles audio recording with offline storage
 */

// Module state (exposed to window for testing)
window.RecorderState = {
    mediaRecorder: null,
    audioChunks: [],
    recordingStartTime: null,
    timerInterval: null,
    isRecording: false,
    currentRecordingId: null,
    draftTranscript: '',
    recognition: null
};

/**
 * Toggle recording on/off
 */
async function toggleRecording() {
    if (!window.RecorderState.isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

/**
 * Initialize speech recognition for draft transcription
 * Online only - Web Speech API requires internet
 */
function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('[Recorder] Speech recognition not supported');
        return null;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    window.RecorderState.recognition = new SpeechRecognition();
    window.RecorderState.recognition.continuous = true;
    window.RecorderState.recognition.interimResults = true;
    window.RecorderState.recognition.lang = 'en-US';

    window.RecorderState.recognition.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                final += transcript;
            } else {
                interim += transcript;
            }
        }

        window.RecorderState.draftTranscript += final;
        updateDraftTranscript(window.RecorderState.draftTranscript + interim);
    };

    window.RecorderState.recognition.onerror = (event) => {
        console.error('[Recorder] Speech recognition error:', event.error);
    };

    return window.RecorderState.recognition;
}

/**
 * Update draft transcript display
 * @param {string} text
 */
function updateDraftTranscript(text) {
    let draftEl = document.getElementById('draft-transcript');
    if (!draftEl) {
        draftEl = document.createElement('div');
        draftEl.id = 'draft-transcript';
        draftEl.className = 'draft-transcript';

        const container = document.querySelector('.recorder-container');
        if (container) {
            container.appendChild(draftEl);
        }
    }

    draftEl.textContent = text ? `Draft: ${text}` : '';
    draftEl.style.display = text ? 'block' : 'none';
}

/**
 * Start recording
 */
async function startRecording() {
    try {
        // Reset state
        window.RecorderState.audioChunks = [];
        window.RecorderState.draftTranscript = '';
        window.RecorderState.currentRecordingId = generateUUID();

        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create media recorder
        window.RecorderState.mediaRecorder = new MediaRecorder(stream);

        window.RecorderState.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                window.RecorderState.audioChunks.push(event.data);
            }
        };

        window.RecorderState.mediaRecorder.onstop = async () => {
            await handleRecordingComplete();
        };

        // Start recording
        window.RecorderState.mediaRecorder.start(100); // Collect data every 100ms
        window.RecorderState.isRecording = true;
        window.RecorderState.recordingStartTime = Date.now();

        // Update UI
        document.getElementById('record-btn').classList.add('recording');
        document.getElementById('record-text').textContent = 'Stop Recording';
        document.getElementById('recording-status').classList.remove('hidden');

        // Start timer
        window.RecorderState.timerInterval = setInterval(updateTimer, 1000);

        // Start draft transcription if online
        if (navigator.onLine && window.RecorderState.recognition) {
            try {
                window.RecorderState.recognition.start();
            } catch (e) {
                console.log('[Recorder] Could not start speech recognition:', e.message);
            }
        }

        console.log('[Recorder] Started recording:', window.RecorderState.currentRecordingId);

    } catch (error) {
        console.error('[Recorder] Error starting recording:', error);
        alert('Could not start recording. Please ensure microphone access is allowed.');
    }
}

/**
 * Stop recording
 */
async function stopRecording() {
    if (!window.RecorderState.mediaRecorder || !window.RecorderState.isRecording) return;

    // Stop media recorder
    window.RecorderState.mediaRecorder.stop();
    window.RecorderState.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    window.RecorderState.isRecording = false;

    // Stop speech recognition
    if (window.RecorderState.recognition) {
        try {
            window.RecorderState.recognition.stop();
        } catch (e) {
            // Already stopped
        }
    }

    // Clear timer
    clearInterval(window.RecorderState.timerInterval);

    // Update UI
    document.getElementById('record-btn').classList.remove('recording');
    document.getElementById('record-text').textContent = 'Start Recording';
    document.getElementById('recording-status').classList.add('hidden');
    document.getElementById('upload-status').classList.remove('hidden');

    console.log('[Recorder] Stopped recording');
}

/**
 * Handle recording complete
 */
async function handleRecordingComplete() {
    const audioBlob = new Blob(window.RecorderState.audioChunks, { type: 'audio/wav' });
    const durationSeconds = Math.floor((Date.now() - window.RecorderState.recordingStartTime) / 1000);

    console.log('[Recorder] Recording complete:', {
        id: window.RecorderState.currentRecordingId,
        duration: durationSeconds,
        size: audioBlob.size
    });

    // Save to IndexedDB
    const recording = {
        id: window.RecorderState.currentRecordingId,
        patient_id: typeof patientId !== 'undefined' ? patientId : 'unknown',
        clinician_id: 'current-clinician', // TODO: Get from auth
        audio_blob: audioBlob,
        draft_transcript: window.RecorderState.draftTranscript || null,
        duration_seconds: durationSeconds,
        created_at: new Date().toISOString(),
        sync_status: 'pending_upload',
        retry_count: 0
    };

    try {
        await window.RecordingStorage.saveRecording(recording);
        console.log('[Recorder] Saved to IndexedDB:', window.RecorderState.currentRecordingId);

        // Show appropriate message
        if (navigator.onLine) {
            document.getElementById('upload-status').classList.add('hidden');
            document.getElementById('result').classList.remove('hidden');
            document.getElementById('result').innerHTML = `
                <h3>Recording Saved</h3>
                <p>Status: <span id="recording-status-text">Pending Upload</span></p>
                <p>Your recording will be uploaded shortly.</p>
                <a href="/queue" class="btn">View Queue</a>
            `;

            // Trigger upload
            await window.UploadManager.queueUpload(window.RecorderState.currentRecordingId);
        } else {
            document.getElementById('upload-status').classList.add('hidden');
            document.getElementById('result').classList.remove('hidden');
            document.getElementById('result').innerHTML = `
                <h3>Recording Saved Locally</h3>
                <p>You are currently offline.</p>
                <p>Your recording has been saved and will upload when you reconnect.</p>
                <a href="/queue" class="btn">View Queue</a>
            `;
        }

        // Clear draft transcript
        updateDraftTranscript('');

    } catch (error) {
        console.error('[Recorder] Error saving recording:', error);
        document.getElementById('upload-status').classList.add('hidden');
        document.getElementById('result').classList.remove('hidden');
        document.getElementById('result').innerHTML = `
            <h3>Error Saving Recording</h3>
            <p>There was an error saving your recording: ${error.message}</p>
            <button class="btn" onclick="location.reload()">Try Again</button>
        `;
    }
}

/**
 * Update timer display
 */
function updateTimer() {
    const elapsed = Math.floor((Date.now() - window.RecorderState.recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('timer').textContent = `${minutes}:${seconds}`;
}

/**
 * Generate UUID
 * @returns {string}
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Initialize speech recognition on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initSpeechRecognition();
    });
} else {
    initSpeechRecognition();
}

console.log('[Recorder] Module loaded');
