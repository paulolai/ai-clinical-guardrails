/**
 * Queue UI Module
 * Displays and manages the recording queue
 */

(function() {
    'use strict';

    // DOM Elements
    let queueListEl;
    let connectionStatusEl;
    let recordingDetailEl;
    let detailContentEl;
    let iosWarningContainerEl;

    /**
     * Initialize queue UI
     */
    function init() {
        console.log('[QueueUI] Initializing...');

        // Get DOM elements
        queueListEl = document.getElementById('queue-list');
        connectionStatusEl = document.getElementById('connection-status');
        recordingDetailEl = document.getElementById('recording-detail');
        detailContentEl = document.getElementById('detail-content');
        iosWarningContainerEl = document.getElementById('ios-warning-container');

        // Setup listeners
        setupEventListeners();

        // Check iOS and show warning if needed
        if (isIOS()) {
            showIOSWarning();
        }

        // Initial load
        refresh();

        // Start polling for updates
        startPolling();
    }

    /**
     * Check if on iOS
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Show iOS warning
     */
    function showIOSWarning() {
        const warning = document.createElement('div');
        warning.className = 'ios-warning';
        warning.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <div>
                <strong>iOS Sync Limitation</strong><br>
                Keep this app open to sync recordings. iOS doesn't support background sync.
            </div>
        `;
        iosWarningContainerEl.appendChild(warning);
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Listen for upload status changes
        window.addEventListener('upload-status-change', (event) => {
            const { recordingId, status } = event.detail;
            console.log('[QueueUI] Upload status change:', recordingId, status);
            refresh();
        });

        // Listen for online/offline
        window.addEventListener('online', updateConnectionStatus);
        window.addEventListener('offline', updateConnectionStatus);

        // Initial status
        updateConnectionStatus();
    }

    /**
     * Update connection status indicator
     */
    function updateConnectionStatus() {
        if (!connectionStatusEl) return;

        const isOnline = navigator.onLine;
        const statusDot = connectionStatusEl.querySelector('.status-dot');
        const statusText = connectionStatusEl.querySelector('.status-text');

        if (isOnline) {
            connectionStatusEl.className = 'connection-indicator online';
            statusText.textContent = 'Online';
        } else {
            connectionStatusEl.className = 'connection-indicator offline';
            statusText.textContent = 'Offline - Sync paused';
        }
    }

    /**
     * Start polling for updates
     */
    function startPolling() {
        // Refresh every 10 seconds
        setInterval(() => {
            refresh();
        }, 10000);
    }

    /**
     * Refresh the queue display
     */
    async function refresh() {
        if (!queueListEl) return;

        try {
            const recordings = await window.RecordingStorage.getAllRecordings();
            renderQueue(recordings);
            updateConnectionStatus();
        } catch (error) {
            console.error('[QueueUI] Error refreshing queue:', error);
            queueListEl.innerHTML = '<p class="empty-state">Error loading queue</p>';
        }
    }

    /**
     * Render the queue
     * @param {Array} recordings
     */
    function renderQueue(recordings) {
        if (recordings.length === 0) {
            queueListEl.innerHTML = '<p class="empty-state">No recordings in queue</p>';
            return;
        }

        const html = recordings.map(recording => {
            const statusIcon = getStatusIcon(recording.sync_status);
            const statusClass = getStatusClass(recording.sync_status);
            const formattedDate = formatDate(recording.created_at);
            const duration = formatDuration(recording.duration_seconds);

            return `
                <div class="queue-item ${statusClass}" data-id="${recording.id}" onclick="QueueUI.showDetail('${recording.id}')">
                    <span class="status-icon">${statusIcon}</span>
                    <div class="recording-info">
                        <div class="recording-id">${recording.patient_id}</div>
                        <div class="recording-meta">
                            ${duration} • ${formattedDate} • ${formatStatus(recording.sync_status)}
                        </div>
                        ${recording.last_error ? `<div class="error-message">${recording.last_error}</div>` : ''}
                    </div>
                    <div class="recording-actions" onclick="event.stopPropagation()">
                        ${getActionButtons(recording)}
                    </div>
                </div>
            `;
        }).join('');

        queueListEl.innerHTML = html;
    }

    /**
     * Get status icon
     * @param {string} status
     * @returns {string}
     */
    function getStatusIcon(status) {
        const icons = {
            'pending_upload': '⏳',
            'uploading': '🔄',
            'uploaded': '✅',
            'failed': '❌'
        };
        return icons[status] || '❓';
    }

    /**
     * Get status CSS class
     * @param {string} status
     * @returns {string}
     */
    function getStatusClass(status) {
        return `status-${status}`;
    }

    /**
     * Format status for display
     * @param {string} status
     * @returns {string}
     */
    function formatStatus(status) {
        const labels = {
            'pending_upload': 'Pending Upload',
            'uploading': 'Uploading...',
            'uploaded': 'Uploaded',
            'failed': 'Failed - Will Retry'
        };
        return labels[status] || status;
    }

    /**
     * Format duration
     * @param {number} seconds
     * @returns {string}
     */
    function formatDuration(seconds) {
        if (!seconds) return '0s';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (mins > 0) {
            return `${mins}m ${secs}s`;
        }
        return `${secs}s`;
    }

    /**
     * Format date
     * @param {string} dateString
     * @returns {string}
     */
    function formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    /**
     * Get action buttons for recording
     * @param {Object} recording
     * @returns {string}
     */
    function getActionButtons(recording) {
        const buttons = [];

        // Retry button for failed uploads
        if (recording.sync_status === 'failed') {
            buttons.push(`<button class="btn-icon" onclick="QueueUI.retryUpload('${recording.id}')">Retry</button>`);
        }

        // Export button
        if (recording.audio_blob) {
            buttons.push(`<button class="btn-icon" onclick="QueueUI.exportRecording('${recording.id}')">Export</button>`);
        }

        // Delete button
        buttons.push(`<button class="btn-icon" onclick="QueueUI.deleteRecording('${recording.id}')">Delete</button>`);

        return buttons.join('');
    }

    /**
     * Show recording detail
     * @param {string} recordingId
     */
    async function showDetail(recordingId) {
        const recording = await window.RecordingStorage.getRecording(recordingId);
        if (!recording) return;

        const html = `
            <div class="detail-row">
                <span class="detail-label">ID:</span>
                <span class="detail-value">${recording.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Patient:</span>
                <span class="detail-value">${recording.patient_id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Duration:</span>
                <span class="detail-value">${formatDuration(recording.duration_seconds)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">${formatStatus(recording.sync_status)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span class="detail-value">${formatDate(recording.created_at)}</span>
            </div>
            ${recording.draft_transcript ? `
            <div class="detail-row">
                <span class="detail-label">Draft Transcript:</span>
                <div class="detail-value" style="margin-top: 8px; padding: 8px; background: white; border: 1px solid #ddd; border-radius: 4px;">
                    ${recording.draft_transcript}
                </div>
            </div>
            ` : ''}
            ${recording.retry_count ? `
            <div class="detail-row">
                <span class="detail-label">Retry Count:</span>
                <span class="detail-value">${recording.retry_count}</span>
            </div>
            ` : ''}
            ${recording.last_error ? `
            <div class="detail-row">
                <span class="detail-label">Last Error:</span>
                <span class="detail-value" style="color: #721c24;">${recording.last_error}</span>
            </div>
            ` : ''}
        `;

        detailContentEl.innerHTML = html;
        recordingDetailEl.classList.remove('hidden');
    }

    /**
     * Hide detail panel
     */
    function hideDetail() {
        recordingDetailEl.classList.add('hidden');
    }

    /**
     * Retry upload
     * @param {string} recordingId
     */
    async function retryUpload(recordingId) {
        console.log('[QueueUI] Retrying upload:', recordingId);
        await window.UploadManager.queueUpload(recordingId);
        refresh();
    }

    /**
     * Export recording
     * @param {string} recordingId
     */
    async function exportRecording(recordingId) {
        const recording = await window.RecordingStorage.getRecording(recordingId);
        if (!recording || !recording.audio_blob) {
            alert('Recording not found or no audio available');
            return;
        }

        // Confirm export
        if (!confirm('Export this recording? The audio file will be downloaded.')) {
            return;
        }

        // Create download link
        const url = URL.createObjectURL(recording.audio_blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `recording-${recordingId}.wav`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Delete recording
     * @param {string} recordingId
     */
    async function deleteRecording(recordingId) {
        if (!confirm('Are you sure you want to delete this recording?')) {
            return;
        }

        try {
            await window.RecordingStorage.deleteRecording(recordingId);
            refresh();
        } catch (error) {
            console.error('[QueueUI] Error deleting recording:', error);
            alert('Failed to delete recording');
        }
    }

    /**
     * Sync now - trigger queue processing
     */
    async function syncNow() {
        if (!navigator.onLine) {
            alert('You are offline. Sync will resume when connection is restored.');
            return;
        }

        connectionStatusEl.className = 'connection-indicator syncing';
        connectionStatusEl.querySelector('.status-text').textContent = 'Syncing...';

        await window.UploadManager.processQueue();

        // Refresh after a short delay to show updated status
        setTimeout(() => {
            refresh();
        }, 1000);
    }

    // Expose API globally
    window.QueueUI = {
        init,
        refresh,
        showDetail,
        hideDetail,
        retryUpload,
        exportRecording,
        deleteRecording,
        syncNow
    };

    console.log('[QueueUI] Loaded');
})();
