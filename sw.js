// Patient zéro : rend le jeu installable et jouable en solo sans réseau.
// Toujours la version en ligne d'abord (pour avoir les mises à jour), la copie locale seulement en secours.
const CACHE = 'pz-v2';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png',
  'minis/hall.jpg', 'minis/pool.jpg', 'minis/office.jpg', 'minis/pipes.jpg', 'minis/forest.jpg', 'minis/circus.jpg', 'minis/fond-menu.jpg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // le relais en ligne et le serveur local ne passent jamais par le cache
  if (url.pathname.includes('/api/') || url.hostname.endsWith('supabase.co')) return;
  const keep = url.origin === location.origin || /cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net/.test(url.hostname);
  if (!keep) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {}); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: url.origin === location.origin }))
  );
});
