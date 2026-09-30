const CACHE = "saint-bot-room-v1";
const SHELL = ["/", "/style.css", "/app.js", "/manifest.json"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(event.request, copy));
      return r;
    }).catch(() => caches.match(event.request))
  );
});
