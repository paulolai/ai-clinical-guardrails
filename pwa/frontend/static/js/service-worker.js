/**
 * Service Worker for Clinical Transcription PWA
 * Handles:
 * - Caching static assets for offline use
 * - Network interception for upload requests
 * - Background sync (Chrome/Android only)
 */

const CACHE_NAME = 'clinical-transcription-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/recorder.js',
    '/static/js/indexeddb-service.js',
    '/static/js/upload-manager.js',
    '/static/js/queue.js',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Skip waiting');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Cache failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== CACHE_NAME)
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Claiming clients');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (POST for uploads handled separately)
    if (request.method !== 'GET') {
        return;
    }

    // Strategy: Cache First for static assets, Network First for API
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirst(request));
    } else if (isAPIRequest(url.pathname)) {
        event.respondWith(networkFirst(request));
    }
});

// Sync event - background sync (Chrome/Android only)
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync event:', event.tag);

    if (event.tag === 'upload-recordings') {
        event.waitUntil(syncRecordings());
    }
});

/**
 * Check if path is a static asset
 * @param {string} pathname
 * @returns {boolean}
 */
function isStaticAsset(pathname) {
    return pathname.startsWith('/static/') || pathname === '/';
}

/**
 * Check if path is an API request
 * @param {string} pathname
 * @returns {boolean}
 */
function isAPIRequest(pathname) {
    return pathname.startsWith('/api/');
}

/**
 * Cache First strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function cacheFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);

    if (cached) {
        return cached;
    }

    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('[SW] Cache first fetch failed:', error);
        throw error;
    }
}

/**
 * Network First strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            // Cache successful API responses
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Fallback to cache
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(request);

        if (cached) {
            return cached;
        }

        throw error;
    }
}

/**
 * Sync recordings (background sync handler)
 * @returns {Promise<void>}
 */
async function syncRecordings() {
    console.log('[SW] Syncing recordings...');

    // Notify all clients to process queue
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({
            type: 'SYNC_RECORDINGS'
        });
    });
}

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
    console.log('[SW] Received message:', event.data);

    if (event.data === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('[SW] Service Worker loaded');
