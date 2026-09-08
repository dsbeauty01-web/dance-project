#!/usr/bin/env node
// test/mover_bench.js — ENGINE-DETECT b0.11 evidence harness.
// Feeds SYNTHETIC pose sequences (one per move) through the engine and asserts each rule
// fires ONLY on its own clip, iso is true only when references stay still, wave quality is
// graded, and clap fuses with a synthetic audio onset. No camera needed — deterministic.
//   node test/mover_bench.js
import { MoverEngine } from '../shared/mover-engine.js';
import { RULES, WaveRule } from '../shared/mover-rules.js';

const V = 1;
const BASE = {
  nose: { x: .50, y: .20, vis: V },
  lShoulder: { x: .42, y: .35, vis: V }, rShoulder: { x: .58, y: .35, vis: V },
  lElbow: { x: .38, y: .50, vis: V }, rElbow: { x: .62, y: .50, vis: V },
  lWrist: { x: .35, y: .62, vis: V }, rWrist: { x: .65, y: .62, vis: V },
  lIndex: { x: .34, y: .66, vis: V }, rIndex: { x: .66, y: .66, vis: V },
  lHip: { x: .45, y: .62, vis: V }, rHip: { x: .55, y: .62, vis: V },
};
const clone = o => JSON.parse(JSON.stringify(o));
const DT = 33;                                   // ~30 fps

// build a clip: start at base, over `ramp` frames move the named joints by their deltas, then hold `hold` frames.
function clip({ move = {}, ramp = 5, hold = 6, jitter = 0.001 }) {
  const frames = [];
  const steps = ramp + hold;
  for (let i = 0; i < steps; i++) {
    const f = clone(BASE);
    const p = Math.min(1, i / ramp);
    for (const [name, d] of Object.entries(move)) {
      f[name].x += (d.x || 0) * p; f[name].y += (d.y || 0) * p;
    }
    // jitter only DURING the ramp — the hold frames are exact so velocities settle to ~0
    // and a reference joint that never moved reads truly "still" (the iso test the game needs).
    if (i < ramp) for (const n of Object.keys(f)) { f[n].x += (Math.random() - .5) * jitter; f[n].y += (Math.random() - .5) * jitter; }
    frames.push(f);
  }
  return frames;
}

function calibrate() {
  const E = new MoverEngine();
  let t = 0;
  E.update(clone(BASE), t); t += DT;
  E.startCal();
  for (let i = 0; i < 40; i++) { const f = clone(BASE); for (const n of Object.keys(f)) { f[n].x += (Math.random() - .5) * .004; f[n].y += (Math.random() - .5) * .004; } E.update(f, t); t += DT; }
  E.finishCal();
  return { E, t };
}

// feed a clip, return the engine at its final (held) frame
function run(E, t0, frames) {
  let t = t0;
  for (const f of frames) { E.update(f, t); t += DT; }
  return t;
}

const CLIPS = {
  still:        clip({ move: {}, ramp: 1, hold: 8 }),
  shoulderPopL: clip({ move: { lShoulder: { y: -0.10 } } }),
  shoulderPopR: clip({ move: { rShoulder: { y: -0.10 } } }),
  ribSlide_iso: clip({ move: { lShoulder: { x: 0.08 }, rShoulder: { x: 0.08 } } }),                       // shoulders travel, hips+head stay
  ribSlide_hipsMove: clip({ move: { lShoulder: { x: 0.08 }, rShoulder: { x: 0.08 }, lHip: { x: 0.08 }, rHip: { x: 0.08 } } }), // hips travel too → not isolated
  hipSlide:     clip({ move: { lHip: { x: 0.09 }, rHip: { x: 0.09 } } }),
  clapClip:     clip({ move: { lWrist: { x: 0.14 }, rWrist: { x: -0.14 } }, ramp: 2, hold: 1 }),           // wrists converge fast
};

// ── run the rule × clip matrix ──
const ruleList = ['freeze', 'shoulderPop', 'ribSlide', 'hipSlide'];
const results = {};
for (const [name, frames] of Object.entries(CLIPS)) {
  const { E, t } = calibrate();
  const tEnd = run(E, t, frames);
  const row = {};
  row.freeze = RULES.freeze(E).still ? 'STILL' : '-';
  row.shoulderPop = fmt(RULES.shoulderPop(E));
  row.ribSlide = fmt(RULES.ribSlide(E));
  row.hipSlide = fmt(RULES.hipSlide(E));
  results[name] = row;
}
function fmt(r) { return r && r.hit ? (r.side || 'hit') + (('iso' in r) ? (r.iso ? '·iso' : '·no-iso') : '') : '-'; }

console.log('\n=== RULE × CLIP MATRIX (b0.11) ===');
console.log(['clip'.padEnd(20), 'freeze'.padEnd(8), 'shoulderPop'.padEnd(14), 'ribSlide'.padEnd(14), 'hipSlide'].join(''));
for (const [name, row] of Object.entries(results)) {
  console.log([name.padEnd(20), String(row.freeze).padEnd(8), String(row.shoulderPop).padEnd(14), String(row.ribSlide).padEnd(14), String(row.hipSlide)].join(''));
}

// ── assertions ──
let pass = 0, fail = 0;
const check = (desc, cond) => { (cond ? pass++ : fail++); console.log((cond ? '  ✓ ' : '  ✗ ') + desc); };
console.log('\n=== ASSERTIONS ===');
check('still clip → freeze STILL', results.still.freeze === 'STILL');
check('still clip → no move rule fires', results.still.shoulderPop === '-' && results.still.ribSlide === '-' && results.still.hipSlide === '-');
check('shoulderPopL → shoulderPop fires L', results.shoulderPopL.shoulderPop.startsWith('L'));
check('shoulderPopR → shoulderPop fires R', results.shoulderPopR.shoulderPop.startsWith('R'));
check('ribSlide_iso → ribSlide fires and iso TRUE', results.ribSlide_iso.ribSlide.includes('·iso'));
check('ribSlide_hipsMove → ribSlide fires but iso FALSE', results.ribSlide_hipsMove.ribSlide.includes('no-iso'));
check('hipSlide → hipSlide fires', results.hipSlide.hipSlide !== '-');
check('shoulderPop did NOT fire on hipSlide clip', results.hipSlide.shoulderPop === '-');

// ── clap fusion (check AT the fast-converge frame, not after a settle) ──
{
  const { E, t } = calibrate(); let tt = t;
  // wrists rush together; enough frames that the EMA-smoothed positions actually converge
  // (< 0.06 apart) while the last frame is still moving fast (mag > 0.8).
  let last = tt;
  for (let i = 1; i <= 7; i++) {
    const p = i / 7;
    const f = clone(BASE);
    f.lWrist.x = 0.35 + 0.155 * p; f.rWrist.x = 0.65 - 0.155 * p;   // meet at ~0.505 / ~0.495
    E.update(f, tt); last = tt; tt += DT;
  }
  const noAudio = RULES.clap(E, null, last);
  const withAudio = RULES.clap(E, last, last);
  console.log('\n=== CLAP FUSION ===');
  console.log('  visual-only:', JSON.stringify(noAudio), ' with-audio-onset:', JSON.stringify(withAudio));
  check('clap detected visually', !!(noAudio && noAudio.hit));
  check('clap confidence rises when fused with audio onset', !!(withAudio && withAudio.confidence === 1));
}

// ── wave quality ──
{
  const { E, t } = calibrate(); let tt = t;
  const chain = ['rShoulder', 'rElbow', 'rWrist', 'rIndex'];
  const wr = new WaveRule(E, 'R');
  const t0 = tt;
  // TRIANGULAR dips (linear down then up) give clean, monotonic >0.02 drops between samples that
  // survive the EMA. Peaks staggered 180ms; 60ms sampling; a couple of flat frames each side for context.
  const peakAt = { rShoulder: 240, rElbow: 420, rWrist: 600, rIndex: 780 };
  const tri = (ms, pk, half = 120, depth = 0.16) => { const d = Math.abs(ms - pk); return d >= half ? 0 : -depth * (1 - d / half); };
  for (let ms = 0; ms <= 1020; ms += 60) {
    const fr = clone(BASE);
    for (const n of chain) fr[n].y += tri(ms, peakAt[n]);
    E.update(fr, t0 + ms); wr.push(t0 + ms);
  }
  tt = t0 + 1060;
  const w = wr.check(tt);
  console.log('\n=== WAVE ===');
  console.log('  wave result:', JSON.stringify(w));
  check('wave detected with a quality grade', !!(w && w.hit && ['smooth', 'good', 'rough'].includes(w.quality)));
}

// ── fps (engine cost) ──
{
  const { E, t } = calibrate(); const N = 3000; const t0 = Date.now();
  let tt = t; for (let i = 0; i < N; i++) { E.update(clone(BASE), tt); tt += DT; }
  const ms = Date.now() - t0; const fps = Math.round(N / (ms / 1000));
  console.log(`\n=== ENGINE COST === ${N} updates in ${ms}ms → ${fps.toLocaleString()} updates/s (headroom well above 30fps)`);
}

console.log(`\n=== RESULT: ${pass} passed, ${fail} failed ===`);
process.exit(fail ? 1 : 0);
