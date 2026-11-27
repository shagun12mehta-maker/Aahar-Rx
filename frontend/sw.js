const CACHE_NAME = "aahar-rx-member3-v2";
const PRECACHE_ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/tokens.css",
  "./css/app.css",
  "./vendor/react.production.min.js",
  "./vendor/react-dom.production.min.js",
  "./vendor/htm.umd.js",
  "./vendor/chart.umd.min.js",
  "./vendor/qrcode.min.js",
  "./data/i18n.json",
  "./data/pk_profiles.json",
  "./data/rules_bundle.json",
  "./data/voice_scripts.json",
  "./data/ux_voice_alerts.json",
  "./js/icons.js",
  "./js/clinicalEngine.js",
  "./js/components/AudioReminderPlayer.js",
  "./js/components/AbsorptionChart.js",
  "./js/components/ConsultDoctorModal.js",
  "./js/components/MedicineBoxScreen.js",
  "./js/components/Screens.js",
  "./js/App.js"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
    )
  );
});
