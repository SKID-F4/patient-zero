// Patient zéro : petit serveur de salon pour jouer en réseau local (même Wi-Fi).
// Aucune dépendance : node server.js, puis ouvrir l'adresse affichée.
// Le navigateur de l'hôte fait tourner la partie ; ce serveur ne fait que relayer les messages.
'use strict';
const http = require('http'), fs = require('fs'), path = require('path'), os = require('os');

const PORT = +process.env.PORT || 8790;
const ROOT = __dirname;
const MAX_GUESTS = 5;
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml',
};

const rooms = new Map(); // code -> { host: {id, res} | null, guests: Map<id, {id, name, skin, res}>, born }

function lanIps() {
  return Object.values(os.networkInterfaces()).flat()
    .filter(i => i && i.family === 'IPv4' && !i.internal && !i.address.startsWith('169.254.'))
    .map(i => i.address);
}
function newCode() {
  const A = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  let c; do { c = Array.from({ length: 4 }, () => A[Math.random() * A.length | 0]).join(''); } while (rooms.has(c));
  return c;
}
function push(res, obj) { try { res.write('data: ' + JSON.stringify(obj) + '\n\n'); } catch (e) { /* client parti */ } }
function readBody(req) {
  return new Promise((ok, ko) => {
    let b = '';
    req.on('data', c => { b += c; if (b.length > 256 * 1024) { ko(new Error('trop gros')); req.destroy(); } });
    req.on('end', () => ok(b)); req.on('error', ko);
  });
}
const json = (res, code, obj) => { res.writeHead(code, { 'content-type': 'application/json', 'cache-control': 'no-store' }); res.end(JSON.stringify(obj)); };
const validId = id => /^[a-z0-9]{6,24}$/i.test(id || '');
const cleanName = n => String(n || '').replace(/[<>&"'`]/g, '').trim().slice(0, 14) || 'Invité';

const server = http.createServer(async (req, res) => {
  let u;
  try { u = new URL(req.url, 'http://local'); } catch (e) { res.writeHead(400); return res.end(); }
  const q = u.searchParams;

  if (u.pathname === '/api/info') return json(res, 200, { ips: lanIps(), port: PORT });

  if (u.pathname === '/api/room' && req.method === 'POST') {
    const code = newCode();
    rooms.set(code, { host: null, guests: new Map(), born: Date.now() });
    return json(res, 200, { code });
  }

  if (u.pathname === '/api/events' && req.method === 'GET') {
    const room = rooms.get(String(q.get('room') || '').toUpperCase());
    const id = q.get('id');
    if (!room || !validId(id)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' });
    res.write(':ok\n\n');
    const isHost = q.get('host') === '1';
    if (isHost) {
      if (room.host && room.host.id !== id) { push(res, { t: 'error', m: 'Ce salon a déjà un hôte.' }); return res.end(); }
      room.host = { id, res };
      for (const g of room.guests.values()) push(res, { t: 'join', id: g.id, name: g.name, skin: g.skin });
    } else {
      if (!room.guests.has(id) && room.guests.size >= MAX_GUESTS) { push(res, { t: 'full' }); return res.end(); }
      const g = { id, res, name: cleanName(q.get('name')), skin: Math.max(0, Math.min(9, +q.get('skin') || 0)) };
      room.guests.set(id, g);
      if (room.host) push(room.host.res, { t: 'join', id, name: g.name, skin: g.skin });
      else push(res, { t: 'nohost' });
    }
    const beat = setInterval(() => { try { res.write(':\n\n'); } catch (e) { /* */ } }, 15000);
    req.on('close', () => {
      clearInterval(beat);
      if (isHost) {
        if (room.host && room.host.res === res) {
          room.host = null;
          for (const g of room.guests.values()) push(g.res, { t: 'hostgone' });
        }
      } else {
        const g = room.guests.get(id);
        if (g && g.res === res) { room.guests.delete(id); if (room.host) push(room.host.res, { t: 'leave', id }); }
      }
    });
    return;
  }

  if (u.pathname === '/api/send' && req.method === 'POST') {
    const room = rooms.get(String(q.get('room') || '').toUpperCase());
    const id = q.get('id');
    if (!room || !validId(id)) { res.writeHead(404); return res.end(); }
    let msg;
    try { msg = JSON.parse(await readBody(req)); } catch (e) { res.writeHead(400); return res.end(); }
    if (!msg || typeof msg.m !== 'object') { res.writeHead(400); return res.end(); }
    if (room.host && room.host.id === id) {
      if (msg.to) { const g = room.guests.get(msg.to); if (g) push(g.res, msg.m); }
      else for (const g of room.guests.values()) push(g.res, msg.m);
    } else if (room.guests.has(id) && room.host) {
      push(room.host.res, Object.assign({}, msg.m, { from: id }));
    }
    res.writeHead(204); return res.end();
  }

  // fichiers du jeu (jamais les fichiers cachés comme .git, ni ce serveur)
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); return res.end(); }
  let p;
  try { p = decodeURIComponent(u.pathname); } catch (e) { res.writeHead(400); return res.end(); }
  if (p === '/') p = '/index.html';
  if (p.split('/').some(s => s.startsWith('.')) || p === '/server.js') { res.writeHead(403); return res.end(); }
  const file = path.join(ROOT, path.normalize(p));
  if (!file.startsWith(ROOT + path.sep)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' }); return res.end('Introuvable'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : data);
  });
});

// ménage : salons vides depuis plus de 2 heures
setInterval(() => {
  const now = Date.now();
  for (const [c, r] of rooms) if (!r.host && !r.guests.size && now - r.born > 2 * 3600 * 1000) rooms.delete(c);
}, 10 * 60 * 1000);

server.on('error', err => {
  if (err.code === 'EADDRINUSE') console.log(`\n  Le salon tourne déjà sur ce PC : ouvre http://localhost:${PORT}\n`);
  else console.log('\n  Le serveur n’a pas pu démarrer :', err.message, '\n');
  process.exitCode = 1;
});
server.listen(PORT, '0.0.0.0', () => {
  console.log('\n  Patient zéro — salon en réseau local\n');
  console.log(`  Sur ce PC :        http://localhost:${PORT}`);
  for (const ip of lanIps()) console.log(`  Pour tes amis :    http://${ip}:${PORT}   (même Wi-Fi)`);
  console.log('\n  Laisse cette fenêtre ouverte pendant la partie. Ctrl+C pour arrêter.\n');
});
