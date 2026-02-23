/**
 * Upload Manager - Handles uploading recordings to server with retry logic
 * Features:
 * - Queue recordings for upload
 * - Retry with exponential backoff
 * - Online/offline detection
 * - iOS detection and warnings
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        MAX_RETRIES: 3,
        BASE_DELAY_MS: 1000,
        MAX_DELAY_MS: 30000,
        POLLING_INTERVAL_MS: 30000, // 30 seconds for iOS fallback
    };

    // State
    let isProcessing = false;
    let iOSWarningShown = false;
    let pollingInterval = null;

    /**
     * Detect if user is on iOS/Safari
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Detect if Background Sync API is supported
     * @returns {boolean}
     */
    function isBackgroundSyncSupported() {
        return 'serviceWorker' in navigator &&
               'sync' in ServiceWorkerRegistration.prototype;
    }

    /**
     * Check if browser is online
     * @returns {boolean}
     */
    function isOnline() {
        return navigator.onLine;
    }

    /**
     * Calculate retry delay with exponential backoff
     * @param {number} attempt - Retry attempt number (0-based)
     * @returns {number} Delay in milliseconds
     */
    function getRetryDelay(attempt) {
        const delay = Math.min(
            CONFIG.BASE_DELAY_MS * Math.pow(2, attempt),
            CONFIG.MAX_DELAY_MS
        );
        // Add jitter to prevent thundering herd
        return delay + Math.random() * 1000;
    }

    /**
     * Queue a recording for upload
     * @param {string} recordingId - Recording ID in IndexedDB
     * @returns {Promise<void>}
     */
    async function queueUpload(recordingId) {
        console.log('[UploadManager] Queuing upload for:', recordingId);

        // Update recording status to pending
        await window.RecordingStorage.updateRecording(recordingId, {
            sync_status: 'pending_upload'
        });

        // Trigger upload processing
        await processQueue();
    }

    /**
     * Upload a single recording
     * @param {Object} recording - Recording object from IndexedDB
     * @returns {Promise<boolean>} True if successful
     */
    async function uploadRecording(recording) {
        const recordingId = recording.id;

        try {
            // Update status to uploading
            await window.RecordingStorage.updateRecording(recordingId, {
                sync_status: 'uploading'
            });

            // Dispatch event for UI update
            dispatchStatusUpdate(recordingId, 'uploading');

            // Prepare form data
            const formData = new FormData();
            formData.append('audio', recording.audio_blob, `recording-${recordingId}.wav`);
            formData.append('patient_id', recording.patient_id);
            formData.append('duration_seconds', recording.duration_seconds);
            formData.append('local_storage_key', recordingId);
            if (recording.draft_transcript) {
                formData.append('draft_transcript', recording.draft_transcript);
            }

            // Upload
            const response = await fetch('/api/v1/recordings/upload', {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();

                // Mark as uploaded
                await window.RecordingStorage.updateRecording(recordingId, {
                    sync_status: 'uploaded',
                    server_id: result.id,
                    uploaded_at: new Date().toISOString()
                });

                dispatchStatusUpdate(recordingId, 'uploaded');
                console.log('[UploadManager] Upload successful:', recordingId);

                return true;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('[UploadManager] Upload failed:', error);

            // Increment retry count
            const updated = await window.RecordingStorage.updateRecording(recordingId, {
                sync_status: 'failed',
                retry_count: (recording.retry_count || 0) + 1,
                last_error: error.message
            });

            dispatchStatusUpdate(recordingId, 'failed', error.message);

            // Retry if under max retries
            if (updated.retry_count < CONFIG.MAX_RETRIES) {
                const delay = getRetryDelay(updated.retry_count - 1);
                console.log(`[UploadManager] Retrying ${recordingId} in ${delay}ms (attempt ${updated.retry_count}/${CONFIG.MAX_RETRIES})`);

                setTimeout(() => {
                    queueUpload(recordingId);
                }, delay);
            } else {
                console.error(`[UploadManager] Max retries reached for ${recordingId}`);
            }

            return false;
        }
    }

    /**
     * Process upload queue
     * @returns {Promise<void>}
     */
    async function processQueue() {
        if (isProcessing) {
            console.log('[UploadManager] Already processing queue');
            return;
        }

        if (!isOnline()) {
            console.log('[UploadManager] Offline, skipping queue processing');
            return;
        }

        isProcessing = true;

        try {
            // Get all pending recordings
            const pending = await window.RecordingStorage.getPendingRecordings();

            console.log(`[UploadManager] Processing ${pending.length} pending recordings`);

            // Upload each one
            for (const recording of pending) {
                if (!isOnline()) {
                    console.log('[UploadManager] Went offline, pausing queue');
                    break;
                }

                await uploadRecording(recording);
            }
        } finally {
            isProcessing = false;
        }
    }

    /**
     * Dispatch status update event
     * @param {string} recordingId
     * @param {string} status
     * @param {string|null} error
     */
    function dispatchStatusUpdate(recordingId, status, error = null) {
        window.dispatchEvent(new CustomEvent('upload-status-change', {
            detail: { recordingId, status, error }
        }));
    }

    /**
     * Show iOS warning (called when on iOS)
     */
    function showIOSWarning() {
        if (iOSWarningShown) return;

        const warning = document.createElement('div');
        warning.id = 'ios-sync-warning';
        warning.className = 'ios-warning';
        warning.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <span>iOS requires keeping this app open to sync recordings</span>
        `;

        const header = document.querySelector('header');
        if (header) {
            header.insertAdjacentElement('afterend', warning);
        }

        iOSWarningShown = true;
    }

    /**
     * Start iOS polling fallback
     */
    function startIOSPolling() {
        if (pollingInterval) return;

        console.log('[UploadManager] Starting iOS polling fallback');
        showIOSWarning();

        pollingInterval = setInterval(() => {
            if (isOnline()) {
                processQueue();
            }
        }, CONFIG.POLLING_INTERVAL_MS);
    }

    /**
     * Stop iOS polling
     */
    function stopIOSPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            console.log('[UploadManager] Stopped iOS polling');
        }
    }

    /**
     * Initialize upload manager
     */
    function init() {
        console.log('[UploadManager] Initializing...');

        // Listen for online/offline events
        window.addEventListener('online', () => {
            console.log('[UploadManager] Browser went online');
            processQueue();
        });

        window.addEventListener('offline', () => {
            console.log('[UploadManager] Browser went offline');
        });

        // iOS detection and fallback
        if (isIOS()) {
            console.log('[UploadManager] iOS detected, using polling fallback');
            startIOSPolling();
        } else if (!isBackgroundSyncSupported()) {
            console.log('[UploadManager] Background Sync not supported, using polling');
            startIOSPolling();
        }

        // Initial queue processing
        if (isOnline()) {
            processQueue();
        }
    }

    // Expose API globally
    window.UploadManager = {
        queueUpload,
        processQueue,
        isOnline,
        isIOS,
        isBackgroundSyncSupported,
        CONFIG,
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log('[UploadManager] Loaded');
})();
