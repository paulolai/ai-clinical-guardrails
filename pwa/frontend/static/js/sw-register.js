/**
 * Service Worker Registration
 * Registers the service worker and handles iOS-specific limitations
 */

(function() {
    'use strict';

    // Check if service workers are supported
    if (!('serviceWorker' in navigator)) {
        console.log('[SW] Service Worker not supported in this browser');
        return;
    }

    /**
     * Detect iOS
     * @returns {boolean}
     */
    function isIOS() {
        const userAgent = navigator.userAgent;
        return /iPad|iPhone|iPod/.test(userAgent) ||
               (userAgent.includes('Macintosh') && 'ontouchend' in document);
    }

    /**
     * Register service worker
     */
    async function registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/static/js/service-worker.js');

            console.log('[SW] Registered successfully:', registration.scope);

            // Handle updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        console.log('[SW] New version available');
                        // Could show update notification here
                    }
                });
            });

            // iOS-specific handling
            if (isIOS()) {
                console.log('[SW] iOS detected - limited service worker support');
                handleIOSLimitations(registration);
            }

        } catch (error) {
            console.error('[SW] Registration failed:', error);
        }
    }

    /**
     * Handle iOS limitations
     * @param {ServiceWorkerRegistration} registration
     */
    function handleIOSLimitations(registration) {
        // iOS doesn't support background sync
        // The UploadManager will handle polling fallback

        // Listen for messages from SW
        navigator.serviceWorker.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'SYNC_RECORDINGS') {
                // Trigger queue processing via UploadManager
                if (window.UploadManager) {
                    window.UploadManager.processQueue();
                }
            }
        });
    }

    // Register when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', registerServiceWorker);
    } else {
        registerServiceWorker();
    }
})();
