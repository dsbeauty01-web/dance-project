// test/shoulder_beat_f4_test.mjs — beta/lib/shoulder-beat.js on recorded bodies (test/clips, real MoveNet tracks).
// Run: node test/shoulder_beat_f4_test.mjs <dir with the clip jsons>   (default test/clips)
import { readFileSync } from 'node:fs';
import { createShoulderBeat, SHOULDER, LINES } from '../beta/lib/shoulder-beat.js';
import { toJudge } from '../beta/lib/kp.js';
const dir = process.argv[2] || new URL('./clips/', import.meta.url).pathname;
let fail = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
function run(name){
  const c = JSON.parse(readFileSync(dir + '/' + name + '.json', 'utf8'));
  const b = createShoulderBeat({ aspect: c.h / c.w }); b.start(0); let r = null, at = null, peak = 0;
  for (const f of c.frames){ const t = f.t * 1000; const k = toJudge(f);
    r = (k && b.feed(k, t)) || b.tick(t) || r; peak = Math.max(peak, b.progress());
    if (b.done){ at = t; break; } }
  return { r: b.done, at, peak, dur: c.frames.at(-1).t };
}
const want = { 'frozen-body': null, 'repo-idle-sway': null, 'empty-room': null, 'repo-pre-upgroove': 'win' };
for (const [n, w] of Object.entries(want)){
  let res; try { res = run(n); } catch (e) { ok(false, n + ' unreadable: ' + e.message); continue; }
  console.log('  ', n, JSON.stringify(res));
  ok(res.r === w || (w === null && res.r !== 'win'), `${n}: expected ${w ?? 'no win'}, got ${res.r}`);
}
// clock: a timeout only releases, never wins (law-shoulder)
{ const b = createShoulderBeat(); b.start(0); const ev = []; for (let t = 0; t <= 21000; t += 100){ const e = b.tick(t); if (e) ev.push([t, e]); }
  ok(JSON.stringify(ev) === JSON.stringify([[8100, 'retry'], [20100, 'release']]), 'clock: one retry after 8 s, release after 20 s, never a win: ' + JSON.stringify(ev)); }
ok(LINES.en.win.split(/\s+/).length <= 5 && LINES.he.win.split(/\s+/).length <= 5, 'win line ≤ 5 words (factShrug)');
ok(SHOULDER.thr === 0.15 && SHOULDER.winMs === 1100 && SHOULDER.hits === 2, 'numbers = main nova-commercial ISO');
console.log(fail ? `${fail} FAILED` : 'ALL PASS'); process.exit(fail ? 1 : 0);
