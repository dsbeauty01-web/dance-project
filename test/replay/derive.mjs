/* test/replay/derive.mjs — Phase 2: measure the real bar from reference clips.
   node test/replay/derive.mjs [still sway dance]     (default: ref-still ref-sway ref-dance; if those aren't
   tracked yet, Nova's own frozen-body still-sway dance-hype — and the output says so)

   1 · per clip: body motion ÷ shoulder width per second (the freeze2 judge's own energy, judges.js update())
   2 · sweep moveFloor / moveK / moveCeil; keep every set where still ≥ 95 % held · sway ≥ 80 % · dance ≤ 15 %
   3 · print the set with the widest margin. Copy it into beta/freeze2/script.json "tune" with the clip names. */
import { createJudges } from '../../beta/freeze2/judges.js';
import { toJudge, frameAt } from '../../beta/lib/kp.js';
import { heldPct } from './freeze.mjs';
import { clip, json, table } from './sim.mjs';

const want = process.argv.slice(2);
let names = want.length === 3 ? want : ['ref-still', 'ref-sway', 'ref-dance'];
let usingRef = names.every(n => clip(n));
if (!usingRef && !want.length){ names = ['frozen-body', 'still-sway', 'dance-hype']; }
const [still, sway, dance] = names.map(clip);
if (!still || !sway || !dance){ console.log('missing clip(s):', names.filter(n => !clip(n)).join(', ')); process.exit(1); }

const tune = json('beta/freeze2/script.json').tune;
const pct = (a, p) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(s.length * p))]; };
function energy(rec){
  const J = createJudges(tune), E = [], dt = 1 / rec.fps;
  for (let t = 0; t < rec.frames.length / rec.fps; t += dt){ const k = toJudge(frameAt(rec, t)); if (k){ J.update(k, t); if (t > 0.5) E.push(J.st.energy); } }
  return { p10: pct(E, .1), p50: pct(E, .5), p90: pct(E, .9), max: Math.max(...E), n: E.length };
}

const stats = names.map((n, i) => ({ clip: n, role: ['still', 'sway', 'dance'][i], ...energy([still, sway, dance][i]) }));
console.log(usingRef ? '\nREFERENCE CLIPS (Refael)' : '\n⚠ Phase 2 pending clips — ref-still / ref-sway / ref-dance not tracked yet. Running on Nova\'s clips.');
console.log(table('motion per clip — energy in shoulder-widths per second (freeze2 judges.js update())', ['clip', 'role', 'p10', 'p50', 'p90', 'max', 'n'],
  stats.map(s => ({ ...s, p10: s.p10.toFixed(2), p50: s.p50.toFixed(2), p90: s.p90.toFixed(2), max: s.max.toFixed(2) }))));

const ok = [];
for (const moveFloor of [0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.6, 1.8, 2.0])
  for (const moveK of [1.5, 2.0, 2.5, 3.0, 4.0])
    for (const moveCeil of [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0]){
      if (moveCeil < moveFloor) continue;
      const T = { ...tune, moveFloor, moveK, moveCeil };
      const h = [heldPct(still, T), heldPct(sway, T), heldPct(dance, T)];
      if (h[0] >= 0.95 && h[1] >= 0.80 && h[2] <= 0.15) ok.push({ moveFloor, moveK, moveCeil, h, margin: Math.min(h[0] - 0.95, h[1] - 0.80, 0.15 - h[2]) });
    }
const cur = [heldPct(still, tune), heldPct(sway, tune), heldPct(dance, tune)];
console.log(`\ncurrent tune moveFloor ${tune.moveFloor} · moveK ${tune.moveK} · moveCeil ${tune.moveCeil}  →  still ${(cur[0]*100).toFixed(0)}% · sway ${(cur[1]*100).toFixed(0)}% · dance ${(cur[2]*100).toFixed(0)}% held`);
console.log(`${ok.length} of the swept sets meet still ≥95 · sway ≥80 · dance ≤15.`);
if (ok.length){
  // widest margin; among ties, the band centred between the sway p90 and the dance p50 (furthest from both)
  const mid = (stats[1].p90 + stats[2].p50) / 2;
  ok.sort((a, b) => b.margin - a.margin || Math.abs((a.moveFloor + a.moveCeil) / 2 - mid) - Math.abs((b.moveFloor + b.moveCeil) / 2 - mid));
  const b = ok[0];
  console.log(`best: moveFloor ${b.moveFloor} · moveK ${b.moveK} · moveCeil ${b.moveCeil}  →  still ${(b.h[0]*100).toFixed(0)}% · sway ${(b.h[1]*100).toFixed(0)}% · dance ${(b.h[2]*100).toFixed(0)}%  (margin ${(b.margin*100).toFixed(0)} pts)`);
}
console.log(`\nGroove floor (Phase 4) = 2 × the still clip's noise. Still clip energy p50 here: ${stats[0].p50.toFixed(3)} sw/s (freeze unit). The groove unit is printed by test/replay/groove.mjs.`);
