/* test/proof/freeze4.mjs — the offline proof of beta/freeze4.html (Freeze v4: Nova's live face in a side panel).

   WHAT IS REAL in this run:   the page beta/freeze4.html, shared/nova-bridge.js, shared/face-panel.js, the freeze
                               judge (beta/lib/freeze-game.js + beta/freeze2), nova-lights, the HUD, Nova's body clips,
                               the replayed child (test/clips/*.json recordings).
   WHAT IS A STAND-IN:         the pod. There is no SoulX face and no live voice here. This file plays the pod:
                               · GET /token and the /rt WebSocket (it only logs what the page sends, and "speaks"
                                 when the page stages a line — like pod/rt_lk.py's speak-gate: nothing in a hard hold);
                               · the LiveKit client is replaced in the browser by a fake Room that publishes
                                   `nova-face`   = a canvas video: the still picture nova-face.png with a big
                                                   "STAND-IN — NOT SoulX" label and sound bars while "talking";
                                   `nova-avatar` = an audio track with a hum while "talking" (not her voice).
                               So this proves the PAGE (layout, badge, sizes, routing, red banners, untouched scoring).
                               It proves NOTHING about SoulX itself: lips, picture quality, latency, sync.

   node test/proof/freeze4.mjs            → docs/evidence/freeze4/  (run.log, *.png, *-console.log, *-rt.log, the mp4)   */
import http from 'node:http';
import crypto from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { existsSync, mkdirSync, writeFileSync, rmSync, renameSync } from 'node:fs';
import { join, extname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium; try { ({ chromium } = require('playwright-core')); } catch { ({ chromium } = require('playwright')); }

const ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const OUT = join(ROOT, 'docs/evidence/freeze4'); mkdirSync(OUT, { recursive: true });
const ONLY = (process.argv[2] || '').split(',').filter(Boolean);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.png': 'image/png', '.jpg': 'image/jpeg' };

/* ───────── the stand-in pod: static files + /token + /rt ───────── */
function standInPod(){
  const pod = { rt: [], t0: Date.now(), gate: { on: false, mode: 'hard' }, speakUntil: 0, onSpeak: () => {}, audioMsgs: 0, sockets: new Set() };
  const stamp = () => ((Date.now() - pod.t0) / 1000).toFixed(2);
  const srv = http.createServer(async (req, res) => {
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/token'){ res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ url: 'ws://stand-in.invalid', token: 'stand-in', room: 'stand-in' })); return; }
    try {
      const p = join(ROOT, decodeURIComponent(u.pathname)); if (!p.startsWith(ROOT)){ res.writeHead(403).end(); return; }
      const st = await stat(p); const body = await readFile(st.isDirectory() ? join(p, 'index.html') : p);
      const type = TYPES[extname(p)] || 'application/octet-stream';
      if (req.method === 'HEAD'){ res.writeHead(200, { 'Content-Type': type, 'Content-Length': body.length }); res.end(); return; }
      const range = req.headers.range?.match(/bytes=(\d*)-(\d*)/);
      if (range){ const a = +range[1] || 0, b = range[2] ? +range[2] : body.length - 1;
        res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${a}-${b}/${body.length}`, 'Accept-Ranges': 'bytes', 'Content-Length': b - a + 1 }); res.end(body.subarray(a, b + 1)); return; }
      res.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': body.length }); res.end(body);
    } catch { res.writeHead(404).end(); }
  });
  srv.on('upgrade', (req, sock) => {
    if (!req.url.startsWith('/rt')){ sock.destroy(); return; }
    const acc = crypto.createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${acc}\r\n\r\n`);
    pod.sockets.add(sock); pod.rt.push(`${stamp()} OPEN ${req.url}`);
    const send = o => { const b = Buffer.from(JSON.stringify(o)); const h = b.length < 126 ? Buffer.from([0x81, b.length]) : Buffer.from([0x81, 126, b.length >> 8, b.length & 255]); try { sock.write(Buffer.concat([h, b])); } catch {} };
    let buf = Buffer.alloc(0);
    sock.on('data', d => { buf = Buffer.concat([buf, d]);
      for (;;){ if (buf.length < 2) return; let len = buf[1] & 127, off = 2;
        if (len === 126){ if (buf.length < 4) return; len = buf.readUInt16BE(2); off = 4; } else if (len === 127){ if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); off = 10; }
        const masked = buf[1] & 128; if (buf.length < off + (masked ? 4 : 0) + len) return;
        const op = buf[0] & 15; let data = buf.subarray(off + (masked ? 4 : 0), off + (masked ? 4 : 0) + len);
        if (masked){ const m = buf.subarray(off, off + 4); data = Buffer.from(data.map((x, i) => x ^ m[i & 3])); }
        buf = buf.subarray(off + (masked ? 4 : 0) + len);
        if (op === 8){ sock.end(); return; } if (op !== 1) continue;
        let m; try { m = JSON.parse(data.toString('utf8')); } catch { continue; }
        if (m.type === 'audio'){ pod.audioMsgs++; continue; }
        if (m.type === 'speak_gate'){ pod.gate = { on: !!m.on, mode: m.on ? (m.mode || 'hard') : 'hard' };
          pod.rt.push(`${stamp()} speak_gate ${m.on ? 'ON (' + pod.gate.mode + ')' : 'OFF (engine)'}`); send({ type: 'ack', of: 'speak_gate' }); continue; }
        if (m.type === 'nova-say'){
          if (pod.gate.on && pod.gate.mode !== 'air'){ pod.rt.push(`${stamp()} nova-say DROPPED (hard hold) "${m.text}"`); continue; }   // rt_lk SPEAK-GATE: refused in a hold
          const start = Math.max(Date.now() + 350, pod.speakUntil + 150), dur = Math.max(900, Math.min(4500, 55 * (m.text || '').length));
          pod.speakUntil = start + dur; pod.rt.push(`${stamp()} nova-say "${m.text}" → stand-in speaks ${dur} ms`);
          setTimeout(() => { send({ type: 'status', speaking: true }); pod.onSpeak(dur); }, start - Date.now());
          setTimeout(() => { send({ type: 'nova_done', text: m.text }); send({ type: 'status', speaking: false }); }, start + dur - Date.now());
          continue; }
        pod.rt.push(`${stamp()} ${m.type} ${JSON.stringify(m).slice(0, 160)}`);
      } });
    sock.on('close', () => pod.sockets.delete(sock)); sock.on('error', () => {});
  });
  return new Promise(ok => srv.listen(0, '127.0.0.1', () => ok({ pod, srv, url: `http://127.0.0.1:${srv.address().port}` })));
}

/* ───────── the stand-in LiveKit client (runs in the page before anything else) ───────── */
function standInLiveKit(cfg){
  const S = window.__standin = { cfg, speaking: false, faceOn: true, frames: 0, published: false };
  const RoomEvent = { TrackSubscribed: 'trackSubscribed', TrackUnsubscribed: 'trackUnsubscribed', Disconnected: 'disconnected' };
  class Room { constructor(){ this.h = {}; } on(ev, fn){ (this.h[ev] ||= []).push(fn); return this; } emit(ev, ...a){ (this.h[ev] || []).forEach(f => f(...a)); }
    async connect(){ setTimeout(() => publish(this), 500); } }
  function publish(room){
    if (S.published) return; S.published = true;
    if (cfg.voice){
      const ac = new AudioContext(), o = ac.createOscillator(), g = ac.createGain(), d = ac.createMediaStreamDestination();
      o.type = 'sawtooth'; o.frequency.value = 210; g.gain.value = 0; o.connect(g); g.connect(d); o.start(); S.gain = g;
      const t = d.stream.getAudioTracks()[0];
      room.emit(RoomEvent.TrackSubscribed, { kind: 'audio', mediaStreamTrack: t, attach(){ const a = document.createElement('audio'); a.srcObject = new MediaStream([t]); return a; } }, {}, { identity: 'nova-avatar' });
    }
    if (cfg.face){
      const c = document.createElement('canvas'); c.width = c.height = 512; const x = c.getContext('2d');
      const img = new Image(); img.src = '/nova-face.png';
      const draw = () => { if (!S.faceOn) return; S.frames++;
        x.fillStyle = '#5b3fa0'; x.fillRect(0, 0, 512, 512);
        if (img.complete && img.naturalWidth){ const s = Math.max(512 / img.naturalWidth, 512 / img.naturalHeight), w = img.naturalWidth * s, h = img.naturalHeight * s; x.drawImage(img, (512 - w) / 2, (512 - h) / 2, w, h); }
        x.fillStyle = '#ffe600'; x.fillRect(0, 0, 512, 92); x.fillStyle = '#111'; x.font = '900 46px sans-serif'; x.textAlign = 'center';
        x.fillText('STAND-IN FACE', 256, 44); x.font = '900 30px sans-serif'; x.fillText('NOT SoulX · test stream', 256, 80);
        if (S.speaking){ x.fillStyle = 'rgba(0,0,0,.55)'; x.fillRect(96, 400, 320, 76);
          for (let i = 0; i < 9; i++){ const hgt = 10 + 50 * Math.abs(Math.sin(S.frames * 0.5 + i * 1.3)); x.fillStyle = '#7ddba3'; x.fillRect(116 + i * 32, 438 - hgt / 2, 20, hgt); } }
        x.fillStyle = '#fff'; x.font = '700 18px monospace'; x.textAlign = 'right'; x.fillText('f' + S.frames, 504, 506); };
      S.timer = setInterval(draw, 40); draw();
      const vt = c.captureStream(25).getVideoTracks()[0]; S.faceTrack = vt;
      room.emit(RoomEvent.TrackSubscribed, { kind: 'video', mediaStreamTrack: vt }, {}, { identity: 'nova-face' });
    }
  }
  S.speak = ms => { S.speaking = true; if (S.gain) S.gain.gain.value = 0.25; clearTimeout(S.st); S.st = setTimeout(() => { S.speaking = false; if (S.gain) S.gain.gain.value = 0; }, ms); };
  S.stopFace = () => { S.faceOn = false; }; S.resumeFace = () => { S.faceOn = true; };
  Object.defineProperty(window, 'LivekitClient', { value: { Room, RoomEvent }, writable: false, configurable: false });   // the CDN script cannot replace it
}

/* ───────── helpers ───────── */
const results = []; const say = s => { console.log(s); results.push(s); };
const check = (name, ok, detail = '') => { say(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`); return ok; };
const CHROME = [process.env.CHROMIUM_PATH, '/usr/bin/google-chrome', '/opt/pw-browsers/chromium/chrome-linux/chrome'].find(p => p && existsSync(p));   // needs H.264 for Nova's body clips
const browser = await chromium.launch({ executablePath: CHROME, args: ['--autoplay-policy=no-user-gesture-required', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
say(`browser: ${CHROME} ${browser.version()}`);

async function open(name, query, { viewport = { width: 1280, height: 720 }, cfg = { face: true, voice: true }, record = false, page: file = 'beta/freeze4.html' } = {}){
  const { pod, srv, url } = await standInPod();
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, permissions: ['microphone', 'camera'], ...(record ? { recordVideo: { dir: join(OUT, '.tmp'), size: viewport } } : {}) });
  const page = await ctx.newPage(); const logs = [];
  page.on('console', m => logs.push(`[${m.type()}] ${m.text()}`)); page.on('pageerror', e => logs.push('[pageerror] ' + e.message));
  await page.route('**/livekit-client*', r => r.fulfill({ contentType: 'text/javascript', body: '/* stand-in run: the real livekit-client is replaced by test/proof/freeze4.mjs */' }));
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, r => r.request().url().includes('livekit-client') ? r.fallback() : r.abort());   // nothing else leaves the machine
  await page.addInitScript(standInLiveKit, cfg);
  pod.onSpeak = ms => page.evaluate(d => window.__standin?.speak(d), ms).catch(() => {});
  await page.goto(`${url}/${file}?${query}`);
  const shot = async tag => { const p = join(OUT, `${name}-${tag}.png`); await page.screenshot({ path: p }); say(`      screenshot ${p.replace(ROOT + '/', '')}`); };
  const close = async () => { const v = record ? page.video() : null; await ctx.close(); srv.close(); for (const s of pod.sockets) s.destroy();
    writeFileSync(join(OUT, `${name}-console.log`), logs.join('\n') + '\n'); writeFileSync(join(OUT, `${name}-rt.log`), pod.rt.join('\n') + `\n(mic audio messages received: ${pod.audioMsgs})\n`);
    return v ? await v.path() : null; };
  return { page, pod, logs, shot, close };
}
const geo = page => page.evaluate(() => { const r = id => { const b = document.getElementById(id).getBoundingClientRect(); return { x: +b.left.toFixed(1), y: +b.top.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1), r: +b.right.toFixed(1), b: +b.bottom.toFixed(1) }; };
  const nv = document.getElementById('nova'), pane = r('novaPane'); const scale = nv.videoWidth ? Math.min(pane.w / nv.videoWidth, pane.h / nv.videoHeight) : 0;
  return { rail: r('faceRail'), tile: r('faceTile'), cam: r('camPane'), fx: r('fx'), pane, bodyDrawn: { w: +(nv.videoWidth * scale).toFixed(1), h: +(nv.videoHeight * scale).toFixed(1) }, size: document.getElementById('faceRail').dataset.size, vw: innerWidth, vh: innerHeight }; });
const apart = (a, b) => a.r <= b.x + 0.5 || b.r <= a.x + 0.5 || a.b <= b.y + 0.5 || b.b <= a.y + 0.5;
const badge = page => page.evaluate(() => window.freeze4Face.state);
const waitBadge = (page, b, ms = 30000) => page.waitForFunction(x => window.freeze4Face?.state.badge === x, b, { timeout: ms, polling: 50 });
const settle = page => page.waitForTimeout(650);                                   // the 0.5 s width transition

const want = n => !ONLY.length || ONLY.includes(n);

/* ═════════ A — the whole game, landscape, English, recorded ═════════ */
if (want('A')){
  say('\n== A · full game, 1280x720, English, stand-in pod — recorded ==');
  const R = await open('A', 'replay=frozen-body,dance-hype,still-sway&rounds=3&checked=1&lang=en', { record: true });
  const { page, pod } = R;
  await page.waitForTimeout(1200); await R.shot('1-start-screen');
  await page.click('#go');
  await page.waitForFunction(() => window.freeze4Face?.state.live, null, { timeout: 15000 });
  check('A1 the face stream reaches the side panel through the bridge (nova-face → onFace → panel live)', true, JSON.stringify(await badge(page)));
  await waitBadge(page, 'talking'); await settle(page); const gBig = await geo(page); await R.shot('2-intro-talking-big');
  check('A2 while she talks the badge says Talking and the panel is big', gBig.size === 'big', `rail ${gBig.rail.w}px of ${gBig.vw}px`);
  await page.waitForFunction(() => window.novaEvents?.some(e => e.event === 'round_start'), null, { timeout: 30000 });
  await page.waitForFunction(() => window.freeze4Face.state.badge === 'watching' && window.freeze4Face.state.size === 'small', null, { timeout: 30000, polling: 50 });
  await settle(page); const gSmall = await geo(page); await R.shot('3-dance-watching-small');
  check('A3 quiet in the game: badge Watching, panel small', gSmall.size === 'small', `rail ${gSmall.rail.w}px`);
  check('A4 the panel never overlaps the child pane (small and big)', apart(gSmall.rail, gSmall.cam) && apart(gBig.rail, gBig.cam) && apart(gSmall.tile, gSmall.cam) && apart(gBig.tile, gBig.cam),
    `small rail x ${gSmall.rail.x}–${gSmall.rail.r}, big rail x ${gBig.rail.x}–${gBig.rail.r}, child pane starts x ${gSmall.cam.x}`);
  check('A5 the child pane and the light canvas keep the same box when the panel grows', JSON.stringify(gSmall.cam) === JSON.stringify(gBig.cam) && JSON.stringify(gSmall.fx) === JSON.stringify(gBig.fx) && gSmall.cam.w === gSmall.vw / 2,
    `child pane ${gSmall.cam.w}x${gSmall.cam.h} at x ${gSmall.cam.x} both times; canvas ${gSmall.fx.w}x${gSmall.fx.h}`);
  check('A6 her body stays whole (object-fit contain) — small: full height; big: scaled, not cropped', gSmall.bodyDrawn.w <= gSmall.pane.w + 0.5 && gSmall.bodyDrawn.h <= gSmall.pane.h + 0.5 && gBig.bodyDrawn.w <= gBig.pane.w + 0.5,
    `small: drawn ${gSmall.bodyDrawn.w}x${gSmall.bodyDrawn.h} in pane ${gSmall.pane.w}x${gSmall.pane.h}; big: drawn ${gBig.bodyDrawn.w}x${gBig.bodyDrawn.h} in pane ${gBig.pane.w}x${gBig.pane.h}`);
  await waitBadge(page, 'freeze', 40000); await page.waitForTimeout(700); await R.shot('4-freeze-hold-badge');
  check('A7 in the hold the badge says FREEZE!', (await badge(page)).badge === 'freeze');
  await page.waitForFunction(() => document.getElementById('end').classList.contains('on'), null, { timeout: 120000 });
  await page.waitForTimeout(1500); await waitBadge(page, 'talking', 15000).catch(() => {}); await settle(page); await R.shot('5-ending-talking');
  await page.waitForTimeout(9000); await R.shot('6-ending-listening');
  const log = await page.evaluate(() => window.freeze4Log), ev = await page.evaluate(() => window.novaEvents), brainLog = await page.evaluate(() => window.novaBrainLog);
  writeFileSync(join(OUT, 'A-page-log.json'), JSON.stringify({ freeze4Log: log, novaEvents: ev, novaBrainLog: brainLog }, null, 1));
  const badges = [...new Set(log.filter(l => l.kind === 'badge').map(l => l.detail))];
  check('A8 the badge used every state the phases need', ['listening', 'talking', 'watching', 'freeze'].every(b => badges.includes(b)), 'seen: ' + badges.join(', '));
  const held = log.filter(l => l.kind === 'line-held-back').length, lines = log.filter(l => l.kind === 'line').length;
  check('A8b in the game she is asked for at most ONE line per gap (never two stacked)', (() => { let mode = '', n = 0, worst = 0; for (const l of log){ if (l.kind === 'voice'){ mode = l.detail; n = 0; } if (l.kind === 'line' && mode === 'air'){ n++; worst = Math.max(worst, n); } } return worst === 1; })(), `${lines} lines asked for, ${held} held back`);
  // voice routing: engine → (air → mute → air)×rounds → engine ; and no voice start inside a mute
  const voice = log.filter(l => l.kind === 'voice').map(l => l.detail);
  check('A9 routing follows the phase machine: engine, then air/mute per round, then engine', voice[0] === 'engine' && voice.at(-1) === 'engine' && voice.join(' ') === 'engine air mute air mute air mute air engine', voice.join(' → '));
  let mute = false, bad = 0; for (const l of log){ if (l.kind === 'voice') mute = l.detail === 'mute'; if (mute && (l.kind === 'her-voice' && l.detail === 'start' || l.kind === 'line')) bad++; }
  check('A10 nothing is said or asked for inside a freeze hold', bad === 0 && !pod.rt.some(l => l.includes('DROPPED')), `${bad} violations; pod dropped ${pod.rt.filter(l => l.includes('DROPPED')).length}`);
  check('A11 the page never spoke by itself (no speech synthesis, no recorded speech files)', !(await page.evaluate(() => performance.getEntriesByType('resource').some(r => /audio\/freeze2\/.*\/(?!sting\.freeze)/.test(r.name)))), 'only the FREEZE sting was fetched from audio/freeze2');
  const medal = ev.find(e => e.event === 'medal');
  check('A12 the game ran to its medal', !!medal, JSON.stringify(medal?.detail));
  const video = await R.close();
  if (video){ const mp4 = join(OUT, 'freeze4-STANDIN-face-full-game.mp4');
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', video, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '30', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', mp4]);
    rmSync(join(OUT, '.tmp'), { recursive: true, force: true });
    say(`      recording ${mp4.replace(ROOT + '/', '')}  ${(+execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4], { encoding: 'utf8' })).toFixed(1)} s (no sound track — the stand-in voice is a hum)`); }
}

/* ═════════ B — the face stream is missing at the start → red banner, the game refuses ═════════ */
if (want('B')){
  say('\n== B · no face stream at all (voice present) → red banner, no game ==');
  const R = await open('B', 'replay=frozen-body&rounds=2&checked=1&autostart=1&facewait=3', { cfg: { face: false, voice: true } });
  await R.page.waitForFunction(() => !document.getElementById('banner').classList.contains('hidden'), null, { timeout: 15000 });
  const t = await R.page.evaluate(() => ({ text: document.getElementById('banner').innerText, bg: getComputedStyle(document.getElementById('banner')).backgroundColor, events: (window.novaEvents || []).length, rail: !document.getElementById('faceBanner').hidden, live: document.getElementById('faceRail').dataset.live }));
  await R.shot('1-red-banner-no-face'); await R.page.waitForTimeout(4000);
  const later = await R.page.evaluate(() => (window.novaEvents || []).length);
  check('B1 red banner names the missing SoulX face', /SoulX/.test(t.text) && t.bg === 'rgb(58, 13, 13)', t.text.replace(/\n/g, ' / '));
  check('B2 the game did not start (no round, no music cue)', t.events === 0 && later === 0, `nova events: ${later}`);
  check('B3 the panel shows no picture at all (no stand-by face)', t.rail && t.live === '0');
  await R.close();
}

/* ═════════ C — the face stream dies in the middle of a game → red in the panel; comes back → clears ═════════ */
if (want('C')){
  say('\n== C · the face stream stops mid-game → red banner in the panel; resumes → it clears ==');
  const R = await open('C', 'replay=frozen-body,dance-hype&rounds=2&checked=1&autostart=1&fast=1');
  const { page } = R;
  await page.waitForFunction(() => window.novaEvents?.some(e => e.event === 'round_start'), null, { timeout: 30000 });
  const t0 = Date.now(); await page.evaluate(() => window.__standin.stopFace());
  await page.waitForFunction(() => !document.getElementById('faceBanner').hidden, null, { timeout: 10000, polling: 50 }); const took = Date.now() - t0;
  await R.shot('1-face-lost-mid-game');
  const st = await page.evaluate(() => ({ text: document.getElementById('faceBanner').textContent, bg: getComputedStyle(document.getElementById('faceBanner')).backgroundColor, vis: getComputedStyle(document.getElementById('face')).visibility }));
  check('C1 a dead face stream turns the panel red within the stall limit (3 s + one check)', took >= 2500 && took <= 4500 && st.bg === 'rgb(58, 13, 13)', `${took} ms · "${st.text}"`);
  check('C2 the frozen last frame is hidden — no stale face pretending to be live', st.vis === 'hidden');
  await page.evaluate(() => window.__standin.resumeFace());
  await page.waitForFunction(() => document.getElementById('faceBanner').hidden, null, { timeout: 5000, polling: 50 });
  check('C3 the banner clears when frames come back', true);
  await page.waitForFunction(() => document.getElementById('end').classList.contains('on'), null, { timeout: 60000 });
  check('C4 the game itself went on to its end', true, JSON.stringify((await page.evaluate(() => window.novaEvents)).find(e => e.event === 'medal')?.detail));
  await R.close();
}

/* ═════════ D — phone, portrait, Hebrew ═════════ */
if (want('D')){
  say('\n== D · 432x768 portrait, Hebrew (stacked layout) ==');
  const R = await open('D', 'replay=frozen-body,dance-hype&rounds=2&checked=1&lang=he', { viewport: { width: 432, height: 768 } });
  const { page } = R; await page.click('#go');
  await waitBadge(page, 'talking'); await settle(page); const gBig = await geo(page); await R.shot('1-portrait-he-talking');
  await page.waitForFunction(() => window.novaEvents?.some(e => e.event === 'round_start'), null, { timeout: 30000 });
  await page.waitForFunction(() => window.freeze4Face.state.size === 'small', null, { timeout: 30000, polling: 50 }); await settle(page);
  const gSmall = await geo(page); await R.shot('2-portrait-he-dance');
  check('D1 stacked: the panel stays out of the child pane, small and big', apart(gSmall.rail, gSmall.cam) && apart(gBig.rail, gBig.cam), `rail bottom ${gBig.rail.b}, child pane top ${gBig.cam.y}`);
  check('D2 the child pane does not change when the panel grows', JSON.stringify(gSmall.cam) === JSON.stringify(gBig.cam), `${gSmall.cam.w}x${gSmall.cam.h}`);
  check('D3 Hebrew badge', /[֐-׿]/.test(await page.evaluate(() => document.getElementById('faceBadge').textContent)), await page.evaluate(() => document.getElementById('faceBadge').textContent));
  await R.close();
}

/* ═════════ E — scoring untouched: the same recorded child gets the same result as on freeze-nova.html ═════════ */
if (want('E')){
  say('\n== E · same replay through freeze-nova.html and freeze4.html → same outcomes ==');
  const q = 'replay=frozen-body,dance-hype,still-sway,dance-hype&rounds=4&checked=1&autostart=1&fast=1&mute=1';
  const run = async (file, name) => { const R = await open(name, q, { page: file }); await R.page.waitForFunction(() => document.getElementById('end').classList.contains('on'), null, { timeout: 90000 });
    const ev = await R.page.evaluate(() => window.novaEvents.filter(e => e.event !== 'round_start').map(e => e.event + (e.detail.round ? '@' + e.detail.round : '') + (e.detail.medal !== undefined ? ':' + e.detail.medal + ':' + e.detail.stars : '')));
    const stars = await R.page.evaluate(() => document.getElementById('stars').textContent); await R.shot('medal'); await R.close(); return { ev: ev.join(' '), stars }; };
  const a = await run('beta/freeze-nova.html', 'E-freeze-nova'), b = await run('beta/freeze4.html', 'E-freeze4');
  say(`      freeze-nova: ${a.ev}   stars ${a.stars}`); say(`      freeze4:     ${b.ev}   stars ${b.stars}`);
  check('E1 identical outcomes round by round, identical stars and medal', a.ev === b.ev && a.stars === b.stars);
}

await browser.close();
const fails = results.filter(r => r.startsWith('FAIL')).length, passes = results.filter(r => r.startsWith('PASS')).length;
say(`\n${passes} passed, ${fails} failed   (stand-in pod: no SoulX, no live voice — see the header of test/proof/freeze4.mjs)`);
writeFileSync(join(OUT, ONLY.length ? `run-${ONLY.join('')}.log` : 'run.log'), `test/proof/freeze4.mjs  ${new Date().toISOString()}\n` + results.join('\n') + '\n');
process.exit(fails ? 1 : 0);
