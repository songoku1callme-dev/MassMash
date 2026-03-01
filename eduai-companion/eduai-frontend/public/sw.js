/* EduAI Companion — Push Notification Service Worker (Supreme 12.0 Phase 5) */
/* eslint-disable no-restricted-globals */

self.addEventListener("push", (event) => {
  let data = { title: "EduAI", body: "Du hast eine neue Benachrichtigung!", icon: "/pwa-192x192.png" };
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
      url: data.url || "/",
      dateOfArrival: Date.now(),
    },
    actions: data.actions || [
      { action: "open", title: "Oeffnen" },
      { action: "close", title: "Schliessen" },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url || "/";

  if (event.action === "close") return;

  event.waitUntil(
    // eslint-disable-next-line no-undef
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
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

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});
