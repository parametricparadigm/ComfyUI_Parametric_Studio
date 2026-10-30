/* Keeps the installed app opening when the computer is out of reach. Network first, always: the studio is live software, so the cache is only a fallback. API calls and media are never cached. */
const CACHE = "ps-shell-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil((async () => { for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k); await self.clients.claim(); })()));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/") || /\.(mp4|webm|m4a|flac|wav|webp|png|jpg)$/i.test(u.pathname)) return;
  e.respondWith((async () => {
    try { const r = await fetch(e.request); if (r.ok) (await caches.open(CACHE)).put(e.request, r.clone()); return r; }
    catch { const hit = await caches.match(e.request); if (hit) return hit; if (e.request.mode === "navigate") return new Response('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Studio offline</title><body style="background:#070908;color:#f6f6f1;font:16px system-ui;padding:32px"><h1 style="color:#f5c518">Can\'t reach your studio</h1><p>Check that the computer is on and that Tailscale is connected on both devices.</p>', { headers: { "Content-Type": "text/html" } }); throw new Error("offline"); }
  })());
});
