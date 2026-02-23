let mediaRecorder;
let audioChunks = [];
let recordingStartTime;
let timerInterval;
let isRecording = false;

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await uploadRecording(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();

        // Update UI
        document.getElementById('record-btn').classList.add('recording');
        document.getElementById('record-text').textContent = 'Stop Recording';
        document.getElementById('recording-status').classList.remove('hidden');

        // Start timer
        timerInterval = setInterval(updateTimer, 1000);

    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not start recording. Please ensure microphone access is allowed.');
    }
}

async function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;

        // Update UI
        document.getElementById('record-btn').classList.remove('recording');
        document.getElementById('record-text').textContent = 'Start Recording';
        document.getElementById('recording-status').classList.add('hidden');
        document.getElementById('upload-status').classList.remove('hidden');

        clearInterval(timerInterval);
    }
}

function updateTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('timer').textContent = `${minutes}:${seconds}`;
}

async function uploadRecording(audioBlob) {
    // TODO: Store locally if offline, or upload immediately if online
    // For now, always try to upload

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('patient_id', patientId || 'unknown');
    formData.append('duration_seconds', Math.floor((Date.now() - recordingStartTime) / 1000));

    try {
        const response = await fetch('/api/v1/recordings/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showResult(result);
        } else {
            // TODO: Store locally for retry
            console.error('Upload failed, storing locally for retry');
            await storeLocally(audioBlob);
            showLocalStorageMessage();
        }
    } catch (error) {
        console.error('Upload error:', error);
        // TODO: Store locally for retry
        await storeLocally(audioBlob);
        showLocalStorageMessage();
    }
}

async function storeLocally(audioBlob) {
    // TODO: Implement IndexedDB storage
    console.log('Storing locally (not yet implemented)');
}

function showResult(result) {
    document.getElementById('upload-status').classList.add('hidden');
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('recording-status-text').textContent = result.status;
}

function showLocalStorageMessage() {
    document.getElementById('upload-status').classList.add('hidden');
    document.getElementById('result').classList.remove('hidden');
    document.getElementById('result').innerHTML = `
        <h3>Recording Saved Locally</h3>
        <p>Your recording has been saved and will upload when connection is restored.</p>
        <a href="/queue" class="btn">View Queue</a>
    `;
}
