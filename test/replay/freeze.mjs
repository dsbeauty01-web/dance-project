/* test/replay/freeze.mjs — Phase 1 acceptance table for beta/freeze3.html (beta/lib/freeze-game.js).
     clip         want
     frozen-body  star · held ≥ 95% of windows
     still-sway   star · held ≥ 80%
     dance-hype   NO star · held ≤ 15%
     repo-idle-sway        star · held ≥ 80%     (a swaying kid still holds)
     repo-dance-active     NO star · held ≤ 15%  (was 100% held at the old 1.4 ceiling)
     refael-wave2-fast     NO star · held ≤ 10%  (REAL webcam + real arm motion; was 100% held at 1.4 — "freeze always scores")
     refael-slow-wave      report · held ≤ 45%   (real waits between lifts are real stillness)
     repo-dance-sub        report · held ≤ 60%
     empty-room   NO star · every round skipped · "I can't see you" shown
     model-fail   NO star · every round skipped · the game still ends
   "held %" = the freeze2 Hold judge over every 2.5 s window of the clip (start every 0.25 s), after calibrating
   on the clip's first 2 s — the same measure as test/freeze2_realdata_test.mjs, but on real keypoints. */
import { createFreezeGame, FREEZE_PACE } from '../../beta/lib/freeze-game.js';
import { createJudges } from '../../beta/freeze2/judges.js';
import { Hold } from '../../beta/freeze2/hold.js';
import { toJudge, frameAt } from '../../beta/lib/kp.js';
import { run, clip, json, seeded, table } from './sim.mjs';

const tune = json('beta/freeze2/script.json').tune;
const T0 = { ...tune, seenMin: FREEZE_PACE.seenMin };

export function heldPct(rec, tuneOverride){
  if (!rec) return null;
  const T = tuneOverride ? { ...tuneOverride, seenMin: FREEZE_PACE.seenMin } : T0;
  const dur = rec.frames.length / rec.fps, dt = 1 / rec.fps;
  // calibrate on the first calibS seconds, like the game
  const J = createJudges(T); J.startSample('still');
  for (let t = 0; t < FREEZE_PACE.calibS; t += dt){ const k = toJudge(frameAt(rec, t)); if (k) J.update(k, t); }
  J.stopSample(); J.finishCalibration();
  let held = 0, judged = 0;
  for (let s = 0; s + FREEZE_PACE.holdS <= dur + 1e-9; s += 0.25){
    const W = createJudges(T); Object.assign(W.st.thr, J.st.thr);
    // warm the energy filter on the second before the window (the game's judge never starts cold either)
    for (let t = s - 1; t < s; t += dt){ const k = toJudge(frameAt(rec, t)); if (k) W.update(k, t); }
    const h = new Hold(W, s, FREEZE_PACE.holdS, T);
    for (let t = s; t < s + FREEZE_PACE.holdS; t += dt){ const k = toJudge(frameAt(rec, t)); if (k) W.update(k, t); h.feed(k, t); }
    const r = h.result ?? h.finish();
    if (r !== 'noshow'){ judged++; if (r === 'held') held++; }
  }
  return judged ? held / judged : null;
}

const CASES = [
  { clip: 'frozen-body', want: 'star',  held: p => p >= 0.95, wantHeld: '>=95%' },
  { clip: 'still-sway',  want: 'star',  held: p => p >= 0.80, wantHeld: '>=80%' },
  { clip: 'dance-hype',  want: 'none',  held: p => p <= 0.15, wantHeld: '<=15%' },
  // [2026-10-18] the rows that were missing — a swaying kid must still hold, a NORMALLY MOVING human must not score:
  { clip: 'repo-idle-sway',     want: 'star',  held: p => p >= 0.80, wantHeld: '>=80%' },
  { clip: 'repo-dance-active',  want: 'none',  held: p => p <= 0.15, wantHeld: '<=15%' },
  { clip: 'refael-wave2-fast',  want: 'few',   held: p => p <= 0.10, wantHeld: '<=10%' },   // REAL webcam, REAL continuous arm motion (Refael) — the old 1.4 bar held this 100%.
                                                                                            // 4.4 s clip: the sim LOOPS it and the end→start jump reads as a teleport (= stillness), so one
                                                                                            // seam-straddling round may star; the non-wrapping window metric (held %) is the truth here.
  { clip: 'refael-slow-wave',   want: 'any',   held: p => p <= 0.45, wantHeld: '<=45%' },   // his slow follow-along WITH real waits: the waits are real stillness, so partly held is honest
  { clip: 'repo-dance-sub',     want: 'any',   held: p => p <= 0.60, wantHeld: '<=60%' },   // subtle dance ≈ sway: reported, loosely bounded
  { clip: 'empty-room',  want: 'skip' },
  { clip: 'model-fail',  want: 'skip', detector: 'fail' },
];

export function freezeReplay({ extra = [] } = {}){
  const rows = []; let fail = 0;
  for (const c of [...CASES, ...extra]){
    const rec = c.detector === 'fail' ? null : clip(c.clip);
    if (!rec && c.detector !== 'fail'){ rows.push({ clip: c.clip, verdict: 'MISSING' }); fail++; continue; }
    const { ended, events } = run(on => createFreezeGame({ tune, on, rng: seeded(11) }), rec, { detector: c.detector });
    const p = c.held ? heldPct(rec) : null;
    const cantSee = events.some(e => e.type === 'seen' && e.seen === false);
    let ok = !!ended;
    if (c.want === 'star') ok &&= ended.stars >= 1 && ended.skips === 0;
    if (c.want === 'none') ok &&= ended.stars === 0 && ended.skips === 0;
    if (c.want === 'skip') ok &&= ended.stars === 0 && ended.skips === ended.rounds && cantSee;
    if (c.want === 'few')  ok &&= ended.stars <= 1 && ended.skips === 0;      // at most one lucky real pause
    if (c.held) ok &&= p != null && c.held(p);
    if (!ok) fail++;
    rows.push({ clip: c.clip, want: c.want === 'none' ? 'NO star' : c.want === 'skip' ? 'skip, NO star' : c.want === 'few' ? '≤1 star' : c.want === 'any' ? '(report)' : 'star',
      rounds: ended?.rounds ?? '-', stars: ended?.stars ?? '-', skips: ended?.skips ?? '-',
      'held %': p == null ? '-' : (100 * p).toFixed(0) + '%', 'want held': c.wantHeld ?? '-',
      "can't-see caption": cantSee ? 'shown' : '-', ends: ended ? 'yes' : 'NO', medal: ended?.medal ?? '-', verdict: ok ? 'PASS' : 'FAIL' });
  }
  return { name: 'Freeze', fail, text: table('FREEZE (beta/freeze3.html) — replay table', ['clip','want','rounds','stars','skips','held %','want held',"can't-see caption",'ends','medal','verdict'], rows), rows };
}

if (import.meta.url === `file://${process.argv[1]}`){ const r = freezeReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
