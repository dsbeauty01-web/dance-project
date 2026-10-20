// test/freeze_live_judge_test.mjs — v1.3 JUDGE-TRUTH (2026-10-19)
// Runs the LIVE pod page's judge (the `Pose` object inside beta/freeze.html, extracted
// verbatim) over the recorded clips in test/clips/ and checks the held fraction against the
// same bar the measured judge (beta/freeze2) passes. Catches the two bugs that made
// "Freeze always scores": per-frame motion (not per second) and duplicate-frame dilution.
//   node test/freeze_live_judge_test.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(ROOT, 'beta/freeze.html'), 'utf8');

// --- extract `const JUDGE = {...};` and `const Pose = { ... };` verbatim from the page
const jStart = html.indexOf('const JUDGE = {');
const pStart = html.indexOf('const Pose = {', jStart);
const pEnd = html.indexOf('\n};\n', pStart) + 4;
if (jStart < 0 || pStart < 0 || pEnd < 4) { console.error('judge not found in beta/freeze.html'); process.exit(1); }
const src = html.slice(jStart, pEnd);

// --- page stubs the judge touches
let nowMs = 0;
const factory = new Function('performance', 'Stage', 'statusEl', 'console', 'DEBUG_POSE', 'drawPoseDebug', 'camEl',
  src + '\nreturn { JUDGE, Pose };');
const stubs = () => factory(
  { now: () => nowMs }, { set() {}, readyCheck() {} }, { textContent: '' },
  { log() {}, warn() {} }, false, () => {}, null);

const JOINTS = ['nose','lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist','lHip','rHip','lKnee','rKnee','lAnkle','rAnkle','lEye','rEye','lEar','rEar'];
function toNova(frame, w, h) {
  const o = {};
  for (const k of JOINTS) { const p = frame[k]; if (p) o[k] = { x: p[0] * w, y: p[1] * h, vis: p[2] }; }
  return o;
}

/* run(clip, {dupHz}) — feed the clip through the page judge; calibrate on the first 2 s, then
   judge every 2.5 s window exactly like the page's scoring loop (FULL_AT 0.75, hold breaks after
   0.25 s of continuous motion). Returns the share of windows that would earn a star.
   dupHz re-feeds each frame as if the page ran at that rate over a slower camera (the live bug). */
const FULL_AT = 0.75, HOLD_S = 2.5;
function run(clip, opts = {}) {
  const { Pose, JUDGE } = stubs();
  Pose.engine = 'movenet';
  const w = clip.w || 640, h = clip.h || 480;
  const t0 = clip.frames[0]?.t || 0, calEnd = t0 + 2.0;
  let calibrated = false;
  const motions = [];
  let win = null, wins = 0, stars = 0, lastT = null;
  for (let i = 0; i < clip.frames.length; i++) {
    const f = clip.frames[i];
    const feeds = opts.dupHz ? Math.max(1, Math.round(opts.dupHz / (clip.fps || 30))) : 1;
    for (let r = 0; r < feeds; r++) {
      nowMs = f.t * 1000 + (feeds > 1 ? r * (1000 / opts.dupHz) : 0);
      Pose.ingest(toNova(f, w, h));
    }
    if (!calibrated && f.t >= calEnd) { Pose.finishCal(); calibrated = true; win = { start: f.t, seen: 0, still: 0, win: 0, over: 0, broken: false }; lastT = f.t; }
    if (!calibrated) continue;
    const dt = (f.t - lastT) * 1000; lastT = f.t;
    win.win += dt;
    if (Pose.present) { win.seen += dt; motions.push(Pose.motion);
      if (Pose.still) { win.still += dt; win.over = 0; }
      else { win.over += dt; if (win.over >= JUDGE.breakHoldS * 1000) win.broken = true; } }
    if (f.t - win.start >= HOLD_S) {
      const seenFrac = win.win ? win.seen / win.win : 0;
      if (seenFrac >= 0.8) { wins++; const frac = win.seen ? win.still / win.seen : 0; if (!win.broken && frac >= FULL_AT) stars++; }
      win = { start: f.t, seen: 0, still: 0, win: 0, over: 0, broken: false };
    }
  }
  if (!calibrated) Pose.finishCal();
  motions.sort((a, b) => a - b);
  const p = q => motions.length ? motions[Math.floor(motions.length * q)] : 0;
  return { held: wins ? stars / wins : 0, wins, thr: Pose.stillThr, p50: p(0.5), p90: p(0.9), dups: Pose.dups, frames: Pose.frames };
}

const ROWS = [
  // clip                       min held   max held   note                         (null max = report only)
  ['frozen-body',               0.95,      1.00,      'standing still → star'],
  ['repo-dance-active',         0.00,      0.15,      'active dance → no star'],
  ['dance-hype',                0.00,      0.15,      'hype dance → no star'],
  ['refael-wave2-fast',         0.00,      0.10,      'Refael waving arms → no star'],
  ['refael-slow-wave',          0.00,      null,      'Refael slow wave with pauses → report'],
  ['repo-dance-sub',            0.00,      null,      'subtle dance (p50 0.66 sw/s ≈ gentle sway) → report, borderline by design'],
];

let fail = 0;
console.log('\nLIVE PAGE JUDGE (beta/freeze.html Pose) — held fraction per clip\n');
console.log('| clip | windows starred | want | thr sw/s | motion p50/p90 | dups dropped | result |');
console.log('|---|---|---|---|---|---|---|');
for (const [name, lo, hi, note] of ROWS) {
  const file = path.join(ROOT, 'test/clips', name + '.json');
  if (!fs.existsSync(file)) { console.log(`| ${name} | — | — | — | — | — | SKIP (no clip) |`); continue; }
  const clip = JSON.parse(fs.readFileSync(file, 'utf8'));
  const r = run(clip);
  const ok = hi == null ? true : (r.held >= lo - 1e-9 && r.held <= hi + 1e-9);
  if (!ok) fail++;
  console.log(`| ${name} | ${(r.held * 100).toFixed(0)}% | ${hi == null ? 'report' : (lo * 100).toFixed(0) + '–' + (hi * 100).toFixed(0) + '%'} | ${r.thr.toFixed(2)} | ${r.p50.toFixed(2)}/${r.p90.toFixed(2)} | ${r.dups}/${r.frames} | ${hi == null ? 'INFO' : ok ? 'PASS' : 'FAIL'} — ${note} |`);
}

// --- the duplicate-frame bug: feeding at 60 Hz with a 30 fps camera must NOT change the verdict
const wave = path.join(ROOT, 'test/clips/refael-wave2-fast.json');
if (fs.existsSync(wave)) {
  const clip = JSON.parse(fs.readFileSync(wave, 'utf8'));
  const a = run(clip), b = run(clip, { dupHz: 60 });
  const ok = Math.abs(a.held - b.held) < 0.05 && b.dups > 0;
  if (!ok) fail++;
  console.log(`\nduplicate-frame guard: 30fps feed held ${(a.held * 100).toFixed(0)}% · 60Hz re-feed held ${(b.held * 100).toFixed(0)}% (dropped ${b.dups} duplicates) → ${ok ? 'PASS' : 'FAIL'}`);
}

console.log(fail ? `\nLIVE JUDGE: ❌ ${fail} failing` : '\nLIVE JUDGE: ✅ all green');
process.exit(fail ? 1 : 0);
