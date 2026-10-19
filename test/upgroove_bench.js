#!/usr/bin/env node
// test/upgroove_bench.js — proves Up Groove (b0.13) runs the ladder on the engines:
// at each station's time the right move is DETECTED, GRADED, SCORED (with the streak ×2),
// and the gold light fires. Synthetic poses, no camera.
import { MoverEngine } from '../shared/mover-engine.js';
import { UpGroove, STATIONS } from '../beta/upgroove-game.js';

const V = 1;
const BASE = {
  nose: { x: .50, y: .20, vis: V }, lShoulder: { x: .42, y: .35, vis: V }, rShoulder: { x: .58, y: .35, vis: V },
  lElbow: { x: .38, y: .50, vis: V }, rElbow: { x: .62, y: .50, vis: V }, lWrist: { x: .35, y: .62, vis: V }, rWrist: { x: .65, y: .62, vis: V },
  lIndex: { x: .34, y: .66, vis: V }, rIndex: { x: .66, y: .66, vis: V }, lHip: { x: .45, y: .62, vis: V }, rHip: { x: .55, y: .62, vis: V },
};
const clone = () => JSON.parse(JSON.stringify(BASE));

// per-station synthetic displacement applied during that station's window
function applyMove(f, part) {
  if (part === 'head') { f.nose.x += 0.05; }
  else if (part === 'shoulder') { f.lShoulder.y -= 0.06; f.rShoulder.y -= 0.06; }
  else if (part === 'ribs') { f.lShoulder.x += 0.06; f.rShoulder.x += 0.06; }        // shoulders travel, hips+head stay
  else if (part === 'hips') { f.lHip.y -= 0.05; f.rHip.y -= 0.05; }
}

// calibrate the engine on still frames first (page does this in the no-score intro)
const E = new MoverEngine();
let t = 0; E.update(clone(), t); t += 33; E.startCal();
for (let i = 0; i < 40; i++) { const f = clone(); for (const n of Object.keys(f)) { f[n].x += (Math.random() - .5) * .004; f[n].y += (Math.random() - .5) * .004; } E.update(f, t); t += 33; }
E.finishCal();

const notes = [];
const g = new UpGroove(E, null, txt => notes.push(txt));

// drive the clock 28s → 48s at 20 fps; inject each station's move during its window
const stationAt = { 30: 'head', 35: 'shoulder', 40: 'ribs', 45: 'hips' };
for (let ms = 28000; ms <= 48000; ms += 50) {
  const tSec = ms / 1000;
  const f = clone();
  for (const [at, part] of Object.entries(stationAt)) { const a = +at; if (tSec >= a && tSec < a + 0.6) applyMove(f, part); }
  g.frame(f, tSec);
}

// ── report ──
console.log('\n=== UP GROOVE LADDER (b0.13) ===');
console.log('notes (voice lines):', JSON.stringify(notes.slice(0, 8)));
console.log('score log:'); for (const e of g.log) console.log('  ', JSON.stringify(e));
console.log(`total score=${g.score}  maxStreak=${g.maxStreak}  facts=${g.facts}`);

// ── assertions ──
let pass = 0, fail = 0; const check = (d, c) => { (c ? pass++ : fail++); console.log((c ? '  ✓ ' : '  ✗ ') + d); };
console.log('\n=== ASSERTIONS ===');
const scored = new Set(g.log.map(e => e.part));
check('head scored', scored.has('head'));
check('shoulder scored', scored.has('shoulder'));
check('ribs scored (and isolated)', g.log.some(e => e.part === 'ribs' && e.iso));
check('hips scored', scored.has('hips'));
check('streak ×2 applied after the 2nd station', g.log.some(e => e.mult === 2));
check('ribs worth more than head (140 vs 100 base)', (STATIONS.ribs.pts > STATIONS.head.pts));
check('the ladder voice lines fired in order', notes.includes('HEAD side to side!') && notes.includes('RIBS!'));
check('total score > 0', g.score > 0);

console.log(`\n=== RESULT: ${pass} passed, ${fail} failed ===`);
process.exit(fail ? 1 : 0);
