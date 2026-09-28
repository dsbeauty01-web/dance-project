/* test/freeze2_realdata_test.mjs — the hold judge against MEASURED energy, not synthetic frames.
   node test/freeze2_realdata_test.mjs [tracedir]

   The pack's freeze2_hold_test.mjs builds its own keypoints, so it proves the judge's LOGIC but
   says nothing about the thresholds: its synthetic "dancing" is whatever amplitude the test chose.
   This replays real traces captured by test/energy-probe.html — game-kit's MoveNet watching a real
   body through Chrome's fake camera — through the SHIPPED Hold class, at the thresholds
   script.json actually calibrates to.

   The traces (scratchpad, regenerate with energy-probe.html; summary in docs/evidence/freeze2/):
     frozen-body   a motionless body (one frame held) = pure detector jitter
     still-sway    standing, gentle sway              = a child trying to hold still, wobbling
     dance-routine slow/medium dancing
     dance-hype    energetic dancing
   A freeze judge must call the first two HELD and the last two MISSED. */
import { readFileSync, existsSync } from 'fs';
import { Hold } from '../beta/freeze2/hold.js';
const S = JSON.parse(readFileSync(new URL('../beta/freeze2/script.json', import.meta.url))); const T = S.tune;
const DIR = process.argv[2] || new URL('./evidence/freeze2/', import.meta.url).pathname.replace(/^\//, '');
const TRACES = ['frozen-body', 'still-sway', 'dance-routine', 'dance-hype'];
/* held% = the share of 2.5s windows the judge would call 'held'. The bars are what the game must
   never get wrong: a child who IS holding still is never punished, a child who keeps dancing is
   caught. dance-routine is reported, not asserted — that routine's slow rounds contain real
   stillness (the choreography holds), so a high held% there is partly the correct answer. */
const BAR = {
  'frozen-body':   { min:95, why:'a motionless child must always be held' },
  'still-sway':    { min:80, why:'a wobbly standing child must mostly be held' },
  'dance-hype':    { max:15, why:'a child who keeps dancing must be caught' },
  'dance-routine': { report:true, why:'slow routine with real holds — reported, not asserted' },
};

// a stand-in for the judges instance: Hold only reads J.sw(k) and J.st.energy / J.st.thr.move
const fakeJ = thrMove => ({ sw: () => 0.2, st: { energy: 0, thr: { move: thrMove } } });

/* thr.move as finishCalibration computes it, for a child whose calibration sample read `still` */
const thrMoveFor = still => Math.min(T.moveCeil ?? Infinity, Math.max(T.moveFloor, still * T.moveK));

function replay(series, dt, thrMove, hold = 2.5){
  const J = fakeJ(thrMove), H = new Hold(J, 0, hold, T);
  let t = 0, r = null;
  for (const e of series){ t += dt; if (t > hold + 0.3) break; J.st.energy = e; r = H.feed({}, t); if (r) return r; }
  return r || H.finish();
}
/* every possible 2.5s window of the trace, so one lucky quiet second can't pass a whole dance */
function heldPct(series, dt, thrMove, hold = 2.5){
  const n = Math.ceil(hold / dt); let held = 0, tot = 0;
  for (let i = 0; i + n < series.length; i++){ if (replay(series.slice(i), dt, thrMove, hold) === 'held') held++; tot++; }
  return tot ? Math.round(held / tot * 100) : -1;
}

const loaded = TRACES.map(t => {
  const p = `${DIR}/${t}.json`;
  if (!existsSync(p)) { console.log(`SKIP  ${t} — no trace at ${p}`); return null; }
  return { t, ...JSON.parse(readFileSync(p, 'utf8')) };
}).filter(Boolean);
if (!loaded.length){ console.log('no traces found — run test/energy-probe.html first'); process.exit(1); }

console.log('trace          fps   p50    p90    max');
for (const L of loaded) console.log(`${L.t.padEnd(14)} ${String(L.fps).padEnd(5)} ${L.p50.toFixed(2)}  ${L.p90.toFixed(2)}  ${L.max.toFixed(2)}`);

/* the calibration readings this game will actually see: 0.24 and 0.43 are what the two live
   2026-09-27 sessions measured; 0.60 and 0.80 are a fidgety child and a swaying one. */
const CALS = [0.24, 0.43, 0.60, 0.80];
console.log('\nheld% per 2.5s window, at every calibration reading this game can produce:');
let pass = 0, fail = 0;
for (const still of CALS){
  const thr = thrMoveFor(still);
  console.log(`\n  calibration still=${still.toFixed(2)} → thr.move ${thr.toFixed(2)}`);
  for (const L of loaded){
    const pctHeld = heldPct(L.series, L.dt, thr);
    const bar = BAR[L.t] || { report:true };
    if (bar.report){ console.log(`    ----  ${L.t.padEnd(14)} held ${String(pctHeld).padStart(3)}%   ${bar.why}`); continue; }
    const ok = (bar.min == null || pctHeld >= bar.min) && (bar.max == null || pctHeld <= bar.max);
    ok ? pass++ : fail++;
    const want = bar.min != null ? `>=${bar.min}%` : `<=${bar.max}%`;
    console.log(`    ${ok ? 'PASS' : 'FAIL'}  ${L.t.padEnd(14)} held ${String(pctHeld).padStart(3)}%   want ${want.padEnd(6)} ${bar.why}`);
  }
}
console.log(`\n${pass} pass · ${fail} fail   (moveFloor ${T.moveFloor} · moveK ${T.moveK} · moveCeil ${T.moveCeil ?? 'NONE — uncapped'})`);
process.exit(fail ? 1 : 0);
