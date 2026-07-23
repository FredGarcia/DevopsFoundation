/* Service worker DOF-PREP : pre-cache complet pour un fonctionnement 100 %
 * hors-ligne apres la premiere visite. Strategie cache-first ; mettre a jour
 * CACHE a chaque changement d'un fichier pour invalider proprement.
 */
var CACHE = "dofprep-v2";
var ASSETS = [
  ".", "index.html", "app.css", "engine.js", "store.js", "app.js",
  "questions.json", "manifest.webmanifest",
  "icon-192.png", "icon-512.png", "icon-180.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(ASSETS); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(function (hit) {
      if (hit) return hit;
      return fetch(e.request).then(function (resp) {
        // met en cache les requetes same-origin reussies (resilience)
        try {
          var url = new URL(e.request.url);
          if (url.origin === self.location.origin && resp && resp.status === 200) {
            var copy = resp.clone();
            caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
          }
        } catch (err) {}
        return resp;
      }).catch(function () { return caches.match("index.html"); });
    })
  );
});
