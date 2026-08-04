const CACHE_NAME = "speakwise-v2";
const APP_SHELL = ["/", "/app.js", "/styles.css", "/manifest.json", "/icon.svg"];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  // API calls siempre van a red — cachear /api/* rompería transcribe/tutor/speak.
  if (event.request.url.includes("/api/")) {
    return;
  }
  // Network-first: en desarrollo activo, cache-first sirve versiones viejas
  // del app shell indefinidamente después de cada deploy (bug real
  // encontrado probando Fase 9). El cache queda solo como fallback offline.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
