/* EduAI Companion — Service Worker (Perfect School 4.1: PWA Offline + Push) */
/* eslint-disable no-restricted-globals */

const CACHE_NAME = "eduai-v14";
const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/quiz",
  "/chat",
  "/karteikarten",
  "/offline.html",
  "/pwa-192x192.png",
];

// --- Install: pre-cache static assets ---
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// --- Activate: clean old caches ---
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
  );
  self.clients.claim();
});

// --- Fetch: cache-first for static, network-first for API ---
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Network-first for API calls
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok && request.method === "GET") {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return res;
        })
        .catch(() =>
          caches.match(request).then(
            (cached) =>
              cached ||
              new Response(JSON.stringify({ error: "Offline", cached: false }), {
                headers: { "Content-Type": "application/json" },
              })
          )
        )
    );
    return;
  }

  // Cache-first for static assets, with network fallback
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return res;
        })
        .catch(() => caches.match("/offline.html"));
    })
  );
});

// --- Push notifications ---
self.addEventListener("push", (event) => {
  let data = {
    title: "EduAI",
    body: "Du hast eine neue Benachrichtigung!",
    icon: "/pwa-192x192.png",
  };
  try {
    if (event.data) {
      const payload = event.data.json();
      data = { ...data, ...payload };
    }
  } catch {
    if (event.data) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || "/pwa-192x192.png",
    badge: "/pwa-192x192.png",
    vibrate: [100, 50, 100],
    data: {
      url: data.url || "/dashboard",
      dateOfArrival: Date.now(),
    },
    actions: data.actions || [
      { action: "open", title: "Oeffnen" },
      { action: "close", title: "Schliessen" },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// --- Notification click ---
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url || "/dashboard";

  if (event.action === "close") return;

  event.waitUntil(
    // eslint-disable-next-line no-undef
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        // eslint-disable-next-line no-undef
        return clients.openWindow(url);
      })
  );
});
