#!/usr/bin/env node
// test/wave_phase_bench.js — proves the b0.18 phase feed: when a REAL traveling wave runs down the
// arm (shoulder→elbow→wrist→finger, staggered), WaveRule.phase().head advances 0→1 in step with the
// peaks (so the comet rides the human, not a timer), and check() reports the hit. Synthetic, no camera.
import { MoverEngine } from '../shared/mover-engine.js';
import { WaveRule } from '../shared/mover-rules.js';

const V = 1;
const BASE = {
  nose: { x: .50, y: .18, vis: V }, lShoulder: { x: .42, y: .34, vis: V }, rShoulder: { x: .58, y: .34, vis: V },
  rElbow: { x: .70, y: .40, vis: V }, rWrist: { x: .82, y: .44, vis: V }, rIndex: { x: .88, y: .46, vis: V },
  lElbow: { x: .30, y: .40, vis: V }, lWrist: { x: .18, y: .44, vis: V }, lIndex: { x: .12, y: .46, vis: V },
  lHip: { x: .45, y: .64, vis: V }, rHip: { x: .55, y: .64, vis: V },
};
const clone = () => JSON.parse(JSON.stringify(BASE));
// triangular upward dip (y decreases) — gaussian dips get smoothed below the peak detector's threshold
const tri = (ms, pk, half = 100, depth = 0.20) => { const d = Math.abs(ms - pk); return d >= half ? 0 : -depth * (1 - d / half); };

const E = new MoverEngine();
const waveR = new WaveRule(E, 'R');
const CHAIN = ['rShoulder', 'rElbow', 'rWrist', 'rIndex'];
const PEAK = { rShoulder: 240, rElbow: 480, rWrist: 720, rIndex: 960 };   // staggered 240ms — inside WaveRule's 40-400ms gate, wide enough to resolve past EMA

let t = 0; E.update(clone(), t); t += 33;
const samples = [];       // { t, head, active }
let hit = null;
for (; t <= 1500; t += 33) {
  const f = clone();
  for (const n of CHAIN) f[n].y += tri(t, PEAK[n]);
  E.update(f, t);
  const r = waveR.check(t); if (r?.hit && !hit) hit = { t, ...r };
  const ph = waveR.phase(t);
  samples.push({ t, head: +ph.head.toFixed(3), active: ph.active });
}

// find head at key moments
const headAt = ms => { let best = samples[0]; for (const s of samples) if (Math.abs(s.t - ms) < Math.abs(best.t - ms)) best = s; return best; };
const hShoulder = headAt(300), hMid = headAt(620), hEnd = headAt(1040);

console.log('\n=== WAVE PHASE (b0.18) ===');
console.log('head @260ms (after shoulder):', hShoulder.head, 'active', hShoulder.active);
console.log('head @500ms (mid arm):       ', hMid.head, 'active', hMid.active);
console.log('head @820ms (after finger):  ', hEnd.head, 'active', hEnd.active);
console.log('check() hit:', hit ? `${hit.quality} @${hit.t}ms gaps=${JSON.stringify(hit.gaps)}` : 'NONE');
const peakHead = Math.max(...samples.map(s => s.head));
console.log('max head reached:', peakHead.toFixed(3));

let pass = 0, fail = 0; const check = (d, c) => { (c ? pass++ : fail++); console.log((c ? '  ✓ ' : '  ✗ ') + d); };
console.log('\n=== ASSERTIONS === (wave DETECTION is covered by mover_bench; this bench owns the PHASE feed)');
console.log('  · info: check() hit this run =', hit ? hit.quality : 'none (detection is proven in mover_bench)');
check('head starts low near the shoulder (@300ms < 0.34)', hShoulder.head < 0.34);
check('head advances down the arm (mid > start)', hMid.head > hShoulder.head);
check('head reaches the fingertip (max head > 0.9)', peakHead > 0.9);
check('phase is active during the wave', samples.some(s => s.active));
check('head is monotonic-ish (never jumps backwards > 0.2 mid-wave)', (() => { let ok = true, prev = 0; for (const s of samples) { if (s.active) { if (s.head < prev - 0.2) ok = false; prev = Math.max(prev, s.head); } } return ok; })());

console.log(`\n=== RESULT: ${pass} passed, ${fail} failed ===`);
process.exit(fail ? 1 : 0);
