/* PER-LIGHT MATRIX v4.1 — every one of the 22 chain lights tested BOTH ways, no shortcuts:
     TRUE : the child lifts that joint at HER exact time → the light MUST advance, "with her"
     FALSE: the child never lifts that joint in that wave → the light must NOT advance, waits
            (amber where the wait is long enough), falls only at her next wave / song end,
            and the rest of the game stays intact.
   Run: node test/perlight_matrix.mjs — exits 1 on ANY failure. */
import { HandWave, TARGETS, NOVA_WAVES, WAVE_START, SONG_END, WAIT_AMBER, AFTER, LEAD } from '../../shared/handwave-core.js';
import { child } from './handwave_core_test_kids.mjs';

const key = j => j[0] + (j.endsWith('Wrist') ? 'W' : j.endsWith('Elbow') ? 'E' : 'S');
const AMT = { Wrist: 0.32, Elbow: 0.24, Shoulder: 0.13 };
const kindOf = j => j.replace(/^[lr]/, '');
const FPS = 30;

function perfectPose(t, skip){
  const p = {};
  for (const c of TARGETS){
    if (skip.has(c.idx)) continue;
    const dt = t - c.t;
    if (dt > 0 && dt < 0.55){ const k = key(c.joint), v = AMT[kindOf(c.joint)] * Math.sin(Math.min(1, dt / 0.5) * Math.PI);
      p[k] = Math.max(p[k] || 0, v); }
  }
  return p;
}
function run(skipIdx){
  const skip = new Set();
  if (skipIdx != null){ const me = TARGETS[skipIdx];
    for (const c of TARGETS) if (c.wave === me.wave && c.joint === me.joint && c.idx >= skipIdx) skip.add(c.idx); }
  const G = new HandWave(); for (let i = 0; i < 8; i++) G.calibrate(child({ armsDown: true }));
  const evs = []; const amberFor = new Set();
  for (let t = 0; t <= SONG_END + 3.3 && !G.ended; t += 1 / FPS){
    const e = G.update(+t.toFixed(4), child(perfectPose(t, skip)));
    evs.push(...e.map(x => ({ ...x, _t: +t.toFixed(2) })));
    const w = G.waiting(t); if (w && w.behind > WAIT_AMBER && G.active) amberFor.add(G.active.idx);
  }
  return { evs, amberFor, hits: evs.filter(e => e.type === 'hit'), misses: evs.filter(e => e.type === 'miss'),
           S: (evs.find(e => e.type === 'end') || {}).summary || G.summary(), ended: G.ended };
}
let pass = 0, fail = 0; const rows = [];
const ok = (n, c, x = '') => { c ? pass++ : fail++; rows.push(`${c ? 'PASS' : 'FAIL'}  ${n}${c ? '' : '   ← ' + String(x).slice(0, 200)}`); };

/* ── TRUE: the perfect child, light by light ── */
const P = run(null);
ok('PERFECT CHILD: all 22 lights, 25/25 stars, gold, ends', P.hits.length === 22 && P.S.stars === 25 && P.S.medal === 'gold' && P.ended,
   JSON.stringify({ h: P.hits.length, s: P.S.stars, m: P.misses.map(m => m.target.idx + ':' + m.why) }));
for (const c of TARGETS){
  const h = P.hits.find(h => h.target.idx === c.idx);
  ok(`  TRUE  ${String(c.idx + 1).padStart(2)} ${c.joint.padEnd(9)} her t=${c.t.toFixed(2)} → hit "with her" (at ${h ? h.at : '—'})`,
     !!h && h.withHer && Math.abs(h.at) <= 0.9, h ? `at=${h.at} withHer=${h.withHer}` : 'NO HIT');
}

/* ── FALSE: everything except that joint in that wave ── */
for (const c of TARGETS){
  const R = run(c.idx);
  const hitMe = R.hits.find(h => h.target.idx === c.idx);
  const missMe = R.misses.find(m => m.target.idx === c.idx);
  const missSet = new Set(TARGETS.filter(x => x.wave === c.wave && x.idx >= c.idx).map(x => x.idx));
  const wrongMiss = R.misses.filter(m => !missSet.has(m.target.idx));
  const expectHits = TARGETS.length - missSet.size;
  const why = c.wave < 2 ? 'wave_over' : 'song_end';
  const fallT = c.wave < 2 ? Math.max(WAVE_START[c.wave + 1] - LEAD, c.t + AFTER) : SONG_END + 2.5;
  const amberPossible = fallT - c.t > WAIT_AMBER + 0.15;
  ok(`  FALSE ${String(c.idx + 1).padStart(2)} ${c.joint.padEnd(9)} skipped → no star, ${amberPossible ? 'amber' : 'seam-jump'}, falls at ${why}, rest intact (${expectHits} hits)`,
     !hitMe && !!missMe && missMe.why === why && R.amberFor.has(c.idx) === amberPossible
       && R.hits.length === expectHits && wrongMiss.length === 0 && R.ended,
     JSON.stringify({ hit: !!hitMe, why: missMe && missMe.why, amber: R.amberFor.has(c.idx), hits: R.hits.length, expect: expectHits, wrong: wrongMiss.map(m => m.target.idx + ':' + m.why), end: R.ended }));
}
console.log(rows.join('\n'));
console.log(`\n${pass} pass · ${fail} fail  (22 × TRUE + 22 × FALSE + perfect run)`);
process.exit(fail ? 1 : 0);
