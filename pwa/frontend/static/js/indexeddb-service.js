/**
 * IndexedDB Service for offline recording storage
 * Uses localForage for reliable cross-browser IndexedDB operations
 */

(function() {
    'use strict';

    // Initialize localForage instance for recordings
    const recordingStore = localforage.createInstance({
        name: 'ClinicalTranscription',
        storeName: 'recordings',
        description: 'Clinical transcription recordings'
    });

    /**
     * Save a recording to IndexedDB
     * @param {Object} recording - Recording object
     * @returns {Promise<void>}
     */
    async function saveRecording(recording) {
        if (!recording.id) {
            throw new Error('Recording must have an id');
        }

        // Ensure required fields
        const recordingData = {
            ...recording,
            updated_at: new Date().toISOString(),
            retry_count: recording.retry_count || 0
        };

        await recordingStore.setItem(recording.id, recordingData);
        console.log('[IndexedDB] Saved recording:', recording.id);
    }

    /**
     * Get a recording by ID
     * @param {string} id - Recording ID
     * @returns {Promise<Object|null>}
     */
    async function getRecording(id) {
        return await recordingStore.getItem(id);
    }

    /**
     * Get all recordings
     * @returns {Promise<Array>}
     */
    async function getAllRecordings() {
        const recordings = [];
        await recordingStore.iterate((value) => {
            recordings.push(value);
        });
        return recordings.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }

    /**
     * Get pending recordings (not yet uploaded)
     * @returns {Promise<Array>}
     */
    async function getPendingRecordings() {
        const all = await getAllRecordings();
        return all.filter(r => r.sync_status === 'pending_upload' || r.sync_status === 'failed');
    }

    /**
     * Get recordings by status
     * @param {string} status - sync_status to filter by
     * @returns {Promise<Array>}
     */
    async function getRecordingsByStatus(status) {
        const all = await getAllRecordings();
        return all.filter(r => r.sync_status === status);
    }

    /**
     * Update a recording
     * @param {string} id - Recording ID
     * @param {Object} updates - Fields to update
     * @returns {Promise<Object>} Updated recording
     */
    async function updateRecording(id, updates) {
        const existing = await getRecording(id);
        if (!existing) {
            throw new Error(`Recording ${id} not found`);
        }

        const updated = {
            ...existing,
            ...updates,
            updated_at: new Date().toISOString()
        };

        await recordingStore.setItem(id, updated);
        return updated;
    }

    /**
     * Delete a recording
     * @param {string} id - Recording ID
     * @returns {Promise<void>}
     */
    async function deleteRecording(id) {
        await recordingStore.removeItem(id);
        console.log('[IndexedDB] Deleted recording:', id);
    }

    /**
     * Get storage quota information
     * @returns {Promise<Object>}
     */
    async function getStorageInfo() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            const estimate = await navigator.storage.estimate();
            return {
                usage: estimate.usage || 0,
                quota: estimate.quota || 0,
                percentage: estimate.quota ? ((estimate.usage / estimate.quota) * 100).toFixed(2) : 0
            };
        }
        return { usage: 0, quota: 0, percentage: 0 };
    }

    /**
     * Clear all recordings (use with caution)
     * @returns {Promise<void>}
     */
    async function clearAll() {
        await recordingStore.clear();
        console.log('[IndexedDB] Cleared all recordings');
    }

    // Expose API globally
    window.RecordingStorage = {
        saveRecording,
        getRecording,
        getAllRecordings,
        getPendingRecordings,
        getRecordingsByStatus,
        updateRecording,
        deleteRecording,
        getStorageInfo,
        clearAll
    };

    console.log('[IndexedDB] RecordingStorage initialized');
})();
