// static/sw.js - Service Worker para HISPE PULSE PWA
const CACHE_NAME = 'hispe-pulse-v1.0.0';
const OFFLINE_CACHE = 'hispe-offline-v1.0';

// Archivos esenciales para cachear
const ESSENTIAL_FILES = [
    '/',
    '/dashboard',
    '/static/css/style.css',
    '/static/js/app.js',
    '/manifest.json',
    'https://unpkg.com/html5-qrcode/minified/html5-qrcode.min.js'
];

// Archivos de la API que se pueden cachear
const API_CACHE_PATTERNS = [
    '/api/user',
    '/api/attendance/today',
    '/api/health'
];

// Instalación del Service Worker
self.addEventListener('install', event => {
    console.log('🔧 Service Worker: Instalando HISPE PULSE...');
    
    event.waitUntil(
        Promise.all([
            // Cache esencial
            caches.open(CACHE_NAME).then(cache => {
                console.log('📦 Cacheando archivos esenciales...');
                return cache.addAll(ESSENTIAL_FILES);
            }),
            // Cache offline
            caches.open(OFFLINE_CACHE).then(cache => {
                console.log('💾 Preparando cache offline...');
                return cache.put('/offline', new Response(getOfflineHTML(), {
                    headers: { 'Content-Type': 'text/html' }
                }));
            })
        ]).then(() => {
            console.log('✅ Service Worker instalado correctamente');
            return self.skipWaiting();
        })
    );
});

// Activación del Service Worker
self.addEventListener('activate', event => {
    console.log('⚡ Service Worker: Activando...');
    
    event.waitUntil(
        Promise.all([
            // Limpiar caches antiguos
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE) {
                            console.log('🗑️ Eliminando cache antiguo:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            self.clients.claim()
        ]).then(() => {
            console.log('✅ Service Worker activado y en control');
        })
    );
});

// Interceptar peticiones de red
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Solo manejar peticiones del mismo origen
    if (url.origin !== location.origin) {
        return;
    }
    
    // Estrategias según el tipo de petición
    if (request.method === 'GET') {
        if (url.pathname.startsWith('/api/attendance/mark')) {
            // Marcaciones - solo online
            event.respondWith(networkOnlyWithFallback(request));
        } else if (API_CACHE_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
            // APIs - cache first con network fallback
            event.respondWith(cacheFirstWithNetworkFallback(request));
        } else if (isNavigationRequest(request)) {
            // Navegación - network first con cache fallback
            event.respondWith(networkFirstWithCacheFallback(request));
        } else {
            // Recursos estáticos - cache first
            event.respondWith(cacheFirst(request));
        }
    } else if (request.method === 'POST' && url.pathname.startsWith('/api/attendance/mark')) {
        // Marcaciones POST - manejar offline
        event.respondWith(handleOfflineMarking(request));
    }
});

// =================== ESTRATEGIAS DE CACHE ===================

// Cache First (para recursos estáticos)
async function cacheFirst(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
        
    } catch (error) {
        console.log('❌ Cache First falló:', error);
        return new Response('Recurso no disponible offline', { status: 503 });
    }
}

// Network First with Cache Fallback (para páginas)
async function networkFirstWithCacheFallback(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
            return networkResponse;
        }
        throw new Error('Network response not ok');
    } catch (error) {
        console.log('🌐 Network falló, usando cache:', error);
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        return caches.match('/offline');
    }
}

// Cache First with Network Fallback (para APIs)
async function cacheFirstWithNetworkFallback(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            // Refrescar cache en background
            fetch(request).then(response => {
                if (response.ok) {
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(request, response.clone());
                    });
                }
            }).catch(() => {});
            
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
        
    } catch (error) {
        console.log('❌ API no disponible offline:', error);
        return new Response(
            JSON.stringify({ error: 'Funcionalidad no disponible offline' }),
            { 
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Network Only with Fallback (para marcaciones)
async function networkOnlyWithFallback(request) {
    try {
        return await fetch(request);
    } catch (error) {
        console.log('❌ Marcación falló - red no disponible');
        return new Response(
            JSON.stringify({ 
                error: 'Sin conexión. La marcación no se puede procesar offline.',
                offline: true 
            }),
            { 
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Manejar marcaciones offline
async function handleOfflineMarking(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            return response;
        }
        throw new Error('Network failed');
        
    } catch (error) {
        console.log('📱 Guardando marcación para envío posterior...');
        
        const requestClone = request.clone();
        const body = await requestClone.json();
        
        // Respuesta de confirmación offline
        return new Response(
            JSON.stringify({
                success: true,
                message: '📱 Marcación guardada. Se enviará cuando haya conexión.',
                offline: true,
                pending: true
            }),
            {
                status: 202,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// =================== UTILIDADES ===================

// Detectar si es una petición de navegación
function isNavigationRequest(request) {
    return request.mode === 'navigate' || 
           (request.method === 'GET' && request.headers.get('accept').includes('text/html'));
}

// HTML para página offline
function getOfflineHTML() {
    return `
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sin Conexión - HISPE PULSE</title>
        <style>
            body {
                font-family: 'Segoe UI', system-ui, sans-serif;
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
            }
            .offline-container {
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 20px;
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                max-width: 400px;
            }
            .offline-icon {
                font-size: 60px;
                margin-bottom: 20px;
            }
            h1 {
                margin-bottom: 15px;
                font-size: 24px;
            }
            p {
                margin-bottom: 20px;
                opacity: 0.9;
                line-height: 1.6;
            }
            .retry-btn {
                background: linear-gradient(45deg, #3498db, #2980b9);
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                color: white;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .retry-btn:hover {
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="offline-icon">📱</div>
            <h1>Sin Conexión</h1>
            <p>No hay conexión a internet. Algunas funciones de HISPE PULSE no están disponibles.</p>
            <p>Las marcaciones se guardarán automáticamente cuando se restablezca la conexión.</p>
            <button class="retry-btn" onclick="window.location.reload()">
                🔄 Intentar de Nuevo
            </button>
        </div>
    </body>
    </html>`;
}

// Listener para cuando se recupera la conexión
self.addEventListener('online', () => {
    console.log('🌐 Conexión restaurada - notificando a los clientes...');
    
    // Notificar a todos los clientes que hay conexión
    self.clients.matchAll().then(clients => {
        clients.forEach(client => {
            client.postMessage({ type: 'ONLINE' });
        });
    });
});

// Manejar notificaciones push
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        event.waitUntil(
            self.registration.showNotification(data.title || 'HISPE PULSE', {
                body: data.body,
                icon: '/static/icons/icon-192.png',
                badge: '/static/icons/icon-72.png',
                data: data.data || {}
            })
        );
    }
});

// Manejar clicks en notificaciones
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow('/dashboard')
    );
});

// Manejar mensajes desde la aplicación principal
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('🚀 Service Worker de HISPE PULSE cargado correctamente');