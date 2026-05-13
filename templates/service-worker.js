const STATIC_CACHE = 'tj-naturals-static-v5';
const DYNAMIC_CACHE = 'tj-naturals-dynamic-v5';

const STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/images/tjlogo(3).png',
    '/static/images/icon-192.png',
    '/static/images/icon-512.png',
    '/static/offline.html'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .catch((err) => console.error('[SW] Static caching failed:', err))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => Promise.all(
            cacheNames
                .filter((cacheName) => cacheName.startsWith('tj-naturals-') && cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE)
                .map((cacheName) => caches.delete(cacheName))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        return;
    }

    if (url.origin !== self.location.origin) {
        return;
    }

    if (request.method !== 'GET') {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(networkFirst(request));
        return;
    }

    if (
        url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/payments/') ||
        url.pathname.startsWith('/chatbot/')
    ) {
        return;
    }

    if (isStaticAsset(request)) {
        event.respondWith(cacheFirst(request));
    } else {
        event.respondWith(networkFirst(request));
    }
});

function isStaticAsset(request) {
    const url = new URL(request.url);
    return url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/');
}

async function cacheFirst(request) {
    try {
        const cache = await caches.open(STATIC_CACHE);
        const cached = await cache.match(request);

        if (cached) {
            return cached;
        }

        const response = await fetch(request);
        if (response.ok && canCache(request, response)) {
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.error('[SW] Cache-first failed:', error);
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            if (canCache(request, networkResponse)) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        }

        throw new Error('Network response not ok');
    } catch (error) {
        const cache = await caches.open(DYNAMIC_CACHE);
        const cached = await cache.match(request);

        if (cached) {
            return cached;
        }

        const acceptHeader = request.headers.get('accept') || '';
        if (acceptHeader.includes('text/html')) {
            const offlinePage = await caches.match('/static/offline.html');
            if (offlinePage) {
                return offlinePage;
            }
            return new Response(
                '<html><body style="font-family:sans-serif;text-align:center;padding:40px;">' +
                '<h1>You are offline</h1><p>Please check your connection and try again.</p></body></html>',
                {
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: { 'Content-Type': 'text/html' }
                }
            );
        }

        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

function canCache(request, response) {
    const url = new URL(request.url);
    return url.origin === self.location.origin && (response.type === 'basic' || response.type === 'default');
}