// Kante service worker. The build writes dist/sw.js from this file with the
// list of built files (see vite.config.ts).
const VERSION = "__VERSION__";
const PRECACHE = "__PRECACHE__";
const SHELL = "kante-shell-" + VERSION;
const MAP = "kante-map-v2";
const MAP_HOST = "vectortiles.geo.admin.ch";
const MAP_LIMIT = 900;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => (k.startsWith("kante-shell-") && k !== SHELL) || (k.startsWith("kante-map-") && k !== MAP)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAP_LIMIT; i++) await cache.delete(keys[i]);
}

const DAY = 86400000;

/**
 * Map style, glyphs, sprites and tiles: answer from the cache. Tiles and fonts
 * are refreshed after two weeks, the style after a day — always in the
 * background, so the worker stays free for the app shell.
 */
async function mapResource(request) {
  const cache = await caches.open(MAP);
  const hit = await cache.match(request, { ignoreVary: true });
  if (hit) {
    const age = Date.now() - Number(hit.headers.get("x-kante-at") || 0);
    const maxAge = /\.json(\?|$)/.test(request.url) ? DAY : 14 * DAY;
    if (age < maxAge) return hit;
  }
  const fresh = fetch(request)
    .then((res) => {
      if (res.ok) {
        const copy = res.clone();
        const headers = new Headers(copy.headers);
        headers.set("x-kante-at", String(Date.now()));
        copy.blob().then((body) => {
          cache.put(request, new Response(body, { status: 200, headers })).then(() => (Math.random() < 0.02 ? trim(cache) : undefined));
        });
      }
      return res;
    })
    .catch((err) => {
      if (hit) return hit;
      throw err;
    });
  return hit || fresh;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.hostname === MAP_HOST) {
    event.respondWith(mapResource(req));
    return;
  }
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (req.mode === "navigate") {
    // the app is one page: every route is the cached shell
    event.respondWith(caches.match("/index.html", { cacheName: SHELL, ignoreVary: true }).then((hit) => hit || fetch(req)));
    return;
  }
  // ignoreVary: servers that answer with "Vary: Origin" would otherwise never match a module request
  event.respondWith(caches.match(url.pathname, { cacheName: SHELL, ignoreVary: true }).then((hit) => hit || fetch(req)));
});
