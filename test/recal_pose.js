#!/usr/bin/env node
/* DETECTION-MIGRATE test/recal_pose.js — recalibrates the Freeze stillness threshold
   for the MediaPipe engine (b0.10) using the page's REAL math, not a copy of it.

   Two phases, both against beta/freeze.html?test=1 served locally:
   - math : feeds synthetic toNova() frames through __test.poseFrame (→ Pose.ingest),
            measures the motion distribution per scenario (still / sway / fidget /
            dance / absent), mirrors each scenario at MoveNet pixel scale, and runs
            the per-kid calibration path (poseCal) to check the derived stillThr.
   - video: real engine end-to-end — Edge fake camera plays a real person video
            (upperbody-routine.mp4 → y4m), MediaPipe loads + tracks, we save the
            ?pose=1 overlay screenshot and the [POSE]/[CAL] log evidence.

   Usage: node test/recal_pose.js --phase math|video --port <cdp> --out <dir>
   (browser is launched by test/recal_pose.sh — same Edge-detached pattern as
   certify_loop.sh; node-spawned Chrome dies on this machine.) */
'use strict';
const fs = require('fs'), path = require('path');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const PHASE = arg('phase', 'math');
const PORT = +arg('port', 9433);
const OUT = arg('out', path.join(__dirname, 'sessions', 'recal'));
fs.mkdirSync(OUT, { recursive: true });

/* ---------- CDP (page-level ws, raw, zero deps) ---------- */
let ws, msgId = 0; const pending = new Map();
function cdp(method, params) {
  return new Promise((res, rej) => {
    const id = ++msgId; pending.set(id, { res, rej });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('CDP timeout ' + method)); } }, 120000);
  });
}
async function evalJs(expr, awaitP) {
  const r = await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: !!awaitP });
  if (r.exceptionDetails) throw new Error('page threw: ' + JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text).slice(0, 400));
  return r.result && r.result.value;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function connect() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
  const page = list.find(t => t.type === 'page' && /freeze/.test(t.url || ''));
  if (!page) throw new Error('no freeze page target; targets: ' + list.map(t => t.url).join(' | '));
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws')); });
  ws.onmessage = ev => { const m = JSON.parse(ev.data); const p = pending.get(m.id);
    if (p) { pending.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); } };
  await cdp('Runtime.enable'); await cdp('Page.enable');
}
async function waitTest(tmo) {
  const t0 = Date.now();
  while (Date.now() - t0 < (tmo || 30000)) {
    try { if (await evalJs('!!window.__test')) return; } catch (_) {}
    await sleep(500);
  }
  throw new Error('__test never armed');
}

/* ---------- synthetic body (deterministic PRNG — reproducible tables) ---------- */
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0;
  let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const BASE = { nose: [.50, .22], lShoulder: [.44, .34], rShoulder: [.56, .34],
  lElbow: [.40, .46], rElbow: [.60, .46], lWrist: [.38, .57], rWrist: [.62, .57],
  lPinky: [.375, .585], rPinky: [.625, .585], lIndex: [.372, .582], rIndex: [.628, .582],
  lThumb: [.380, .578], rThumb: [.620, .578], lHip: [.46, .58], rHip: [.54, .58],
  lKnee: [.45, .75], rKnee: [.55, .75], lAnkle: [.45, .90], rAnkle: [.55, .90],
  lHeel: [.445, .915], rHeel: [.555, .915], lFoot: [.46, .93], rFoot: [.54, .93] };
const FLICKER = ['lPinky', 'rPinky', 'lIndex', 'rIndex', 'lThumb', 'rThumb', 'lHeel', 'rHeel'];
// gauss via Box-Muller on the seeded PRNG
function gaussFn(rnd) { return () => { const u = Math.max(rnd(), 1e-9), v = rnd();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }; }
/* frames(n, opts): opts = {noise, swayAmp, swayHz, danceAmp, joints, scale:[sx,sy], vis} */
function frames(n, o, seed) {
  const rnd = mulberry32(seed), g = gaussFn(rnd), out = [];
  const names = o.joints || Object.keys(BASE);
  for (let f = 0; f < n; f++) {
    const t = f / 30;
    const sway = (o.swayAmp || 0) * Math.sin(2 * Math.PI * (o.swayHz || 0.25) * t);
    const dx = (o.danceAmp || 0) * Math.sin(2 * Math.PI * 1.2 * t);
    const dy = (o.danceAmp || 0) * 0.6 * Math.cos(2 * Math.PI * 0.9 * t);
    const fr = {};
    for (const k of names) {
      const [bx, by] = BASE[k];
      const limbBoost = /Wrist|Elbow|Pinky|Index|Thumb/.test(k) ? 1.8 : 1;   // arms travel most
      let x = bx + sway + dx * limbBoost + (o.noise || 0) * g();
      let y = by + dy * limbBoost + (o.noise || 0) * g();
      let vis = o.vis != null ? o.vis : (FLICKER.includes(k) ? 0.30 + 0.35 * rnd() : 0.85 + 0.13 * rnd());
      if (o.scale) { x *= o.scale[0]; y *= o.scale[1]; }
      fr[k] = { x, y, z: 0, vis: +vis.toFixed(3) };
    }
    out.push(fr);
  }
  return out;
}
const pct = (a, p) => { const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(s.length * p))]; };

/* ---------- phase: math ---------- */
async function phaseMath() {
  await waitTest();
  const engineOf = sc => sc.engine || 'mediapipe';
  const SCEN = [
    { name: 'still-noise (MP)',   o: { noise: 0.0015 } },
    { name: 'breath-sway (MP)',   o: { noise: 0.0015, swayAmp: 0.004 } },
    { name: 'fidgety-still (MP)', o: { noise: 0.004, swayAmp: 0.004 } },
    { name: 'dance (MP)',         o: { noise: 0.002, danceAmp: 0.045 } },
    { name: 'big-dance (MP)',     o: { noise: 0.002, danceAmp: 0.08 } },
    { name: 'absent-5joints (MP)', o: { noise: 0.0015, joints: ['nose', 'lShoulder', 'rShoulder', 'lHip', 'rHip'], vis: 0.9 }, absent: true },
    { name: 'still-noise (MoveNet px)', o: { noise: 0.0015, scale: [640, 480], vis: 0.9 }, engine: 'movenet' },
    { name: 'dance (MoveNet px)',       o: { noise: 0.002, danceAmp: 0.045, scale: [640, 480], vis: 0.9 }, engine: 'movenet' },
  ];
  const rows = [];
  for (let i = 0; i < SCEN.length; i++) {
    const sc = SCEN[i];
    await evalJs(`__test.poseCal(true)`);                       // reset EMA + lastJ + samples
    const fr = frames(360, sc.o, 1000 + i);                     // 12s @30fps equivalent
    const res = await evalJs(`(function(fs){ const out=[]; for(const f of fs){ const r=__test.poseFrame(f,'${engineOf(sc)}'); out.push({m:r.motion, p:r.present}); } return out; })(${JSON.stringify(fr)})`);
    const settled = res.slice(30);                              // let the EMA settle
    const motions = settled.filter(r => r.p).map(r => r.m);
    const presentFrac = settled.filter(r => r.p).length / settled.length;
    rows.push({ scenario: sc.name, engine: engineOf(sc), present: +presentFrac.toFixed(2),
      p10: motions.length ? +pct(motions, .10).toFixed(4) : null,
      p50: motions.length ? +pct(motions, .50).toFixed(4) : null,
      p90: motions.length ? +pct(motions, .90).toFixed(4) : null,
      absentExpected: !!sc.absent });
  }
  /* per-kid calibration path: pre-game window = still kid with breath sway */
  await evalJs(`__test.poseCal(true)`);
  const cal = frames(360, { noise: 0.0015, swayAmp: 0.004 }, 4242);
  await evalJs(`(function(fs){ for(const f of fs) __test.poseFrame(f,'mediapipe'); })(${JSON.stringify(cal)})`);
  const thr = await evalJs(`__test.poseCal(false)`);
  const stats = await evalJs(`__test.poseStats()`);
  const calLog = (await evalJs(`__test.logs(0)`)).filter(l => /\[CAL\]/.test(l.m)).map(l => l.m);
  const report = { thrAfterCal: thr, stats, calLog, rows };
  fs.writeFileSync(path.join(OUT, 'recal-math.json'), JSON.stringify(report, null, 2));
  /* verdicts */
  // still = truly frozen kid (sensor noise + breathing). fidget/dance = MOVING: a kid
  // wiggling during a hold must break the freeze — they belong ABOVE the threshold.
  const still = rows.filter(r => /still-noise \(MP\)|breath-sway/.test(r.scenario));
  const moving = rows.filter(r => /fidgety|dance \(MP\)|big-dance/.test(r.scenario));
  const absent = rows.find(r => r.absentExpected);
  const ok =
    still.every(r => r.p90 < thr) &&
    moving.every(r => r.p10 > thr) &&
    absent.present === 0;
  console.log(JSON.stringify(report, null, 2));
  console.log('RECAL-MATH ' + (ok ? 'PASS' : 'FAIL') + ` thr=${thr}`);
  process.exit(ok ? 0 : 1);
}

/* ---------- phase: video (real engine, fake camera person) ---------- */
async function phaseVideo() {
  await waitTest(60000);
  // tap through whatever gate is up until the camera starts (start → play-anyway → ready)
  for (let i = 0; i < 24; i++) {
    const what = await evalJs(`__test.tap()`);
    const st = await evalJs(`__test.poseStats()`);
    if (st && st.engine) break;
    await sleep(5000);
    if (i === 23) console.log('gate loop exhausted; last tap=' + what);
  }
  // give the engine time to produce fps logs + calibration samples
  await sleep(22000);
  const stats = await evalJs(`__test.poseStats()`);
  const logs = (await evalJs(`__test.logs(0)`)).filter(l => /\[POSE\]|\[CAL\]/.test(l.m)).map(l => `${l.t} ${l.m}`);
  const shot = await cdp('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(OUT, 'pose-overlay.png'), Buffer.from(shot.data, 'base64'));
  const report = { stats, poseLogs: logs };
  fs.writeFileSync(path.join(OUT, 'recal-video.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  const ok = /engine=mediapipe fps=[1-9]/.test(logs.join('\n')) && stats.present === true;
  console.log('RECAL-VIDEO ' + (ok ? 'PASS' : 'FAIL'));
  process.exit(ok ? 0 : 1);
}

(async () => {
  await connect();
  if (PHASE === 'video') await phaseVideo(); else await phaseMath();
})().catch(e => { console.error('recal error:', e.message); process.exit(2); });
