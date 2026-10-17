/* test/replay/edge.mjs — night item A: every game on every edge clip (test/clips/edge/, test/clips/synth.mjs) and on
   every tracked repo video (test/clips/repo-*.json). Per the Laws, on EVERY clip:
     · the game ends
     · TRUTH AUDIT: every star's window, re-read from the raw frames, had both shoulders ≥ 0.30 in ≥ 80 % of its
       frames (Copy also: the arm(s) the pose needs) — a star the camera didn't see is a FAIL
     · no star from noise: a dancing body never stars a Freeze; a frozen body never stars a Groove bar; a pose clip
       never stars a different pose in Copy */
import { readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { createFreezeGame } from '../../beta/lib/freeze-game.js';
import { createCopyGame, POSES } from '../../beta/lib/copy-game.js';
import { createGrooveGame } from '../../beta/lib/groove-game.js';
import { OWN, GATE, frameAt } from '../../beta/lib/kp.js';
import { run, json, seeded, table, ROOT } from './sim.mjs';

const tune = json('beta/freeze2/script.json').tune;
const OWN_POSE = { 'pose-armsup': 'armsUp', 'pose-star': 'star', 'own-left-up': 'leftUp', 'own-right-up': 'rightUp' };
const ALL_POSES = Object.keys(POSES);

const seenFrac = (rec, t0, t1, joints) => { let n = 0, ok = 0; const dt = 1 / rec.fps;
  for (let t = t0; t < t1; t += dt){ n++; const f = frameAt(rec, t); if (joints.every(j => (f?.[j]?.[2] ?? 0) >= GATE.min)) ok++; }
  return n ? ok / n : 0; };
function audit(rec, results, needFor = () => [], holdS = null){
  const bad = [];
  for (const r of results) if (r.outcome === 'star'){
    const need = ['lShoulder', 'rShoulder', ...needFor(r)];
    // Copy earns its star on the held match (the last confirmS before t1), not on the whole 6 s window
    const f = seenFrac(rec, holdS ? r.t1 - holdS : r.t0, r.t1, need); if (f < 0.8) bad.push(`${r.round ?? r.bar}:${(f * 100).toFixed(0)}`);
  }
  return bad;
}
const armsOf = pose => Object.keys(POSES[pose].arms).flatMap(side => OWN[side]);

export function clipList(){
  const out = [];
  const E = join(ROOT, 'test/clips/edge');
  if (existsSync(E)) for (const f of readdirSync(E).filter(f => f.endsWith('.json')).sort()) out.push({ name: f.slice(0, -5), path: `test/clips/edge/${f}` });
  for (const f of readdirSync(join(ROOT, 'test/clips')).filter(f => /^repo-.*\.json$/.test(f)).sort()) out.push({ name: f.slice(0, -5), path: `test/clips/${f}` });
  return out;
}

export function edgeReplay(){
  const rows = []; let fail = 0;
  for (const c of clipList()){
    const rec = json(c.path), base = c.name.split('.')[0];
    const why = [];
    // Freeze
    const F = run(on => createFreezeGame({ tune, on, rng: seeded(11) }), rec).ended;
    if (!F) why.push('freeze never ended');
    else { const b = audit(rec, F.results); if (b.length) why.push('freeze star unseen ' + b); if (base === 'dance-hype' && F.stars) why.push('freeze starred a dancer'); }
    // Copy — every pose once
    const C = run(on => createCopyGame({ poses: ALL_POSES, on, size: { w: rec.w, h: rec.h } }), rec).ended;
    if (!C) why.push('copy never ended');
    else { const b = audit(rec, C.results, r => [...armsOf(r.pose), ...(POSES[r.pose].otherDown ? OWN[POSES[r.pose].otherDown] : [])], 0.6); if (b.length) why.push('copy star unseen ' + b);
      const wrong = C.results.filter(r => r.outcome === 'star' && r.pose !== OWN_POSE[base]).map(r => r.pose);
      if (base in OWN_POSE || ['frozen-body', 'still-sway', 'dance-hype'].includes(base)) if (wrong.length) why.push('copy wrong pose ' + wrong); }
    // Groove
    const G = run(on => createGrooveGame({ on, size: { w: rec.w, h: rec.h } }), rec).ended;
    if (!G) why.push('groove never ended');
    else { const b = audit(rec, G.results); if (b.length) why.push('groove star unseen ' + b); if (base === 'frozen-body' && G.stars) why.push('groove starred a frozen body'); }
    const ok = !why.length; if (!ok) fail++;
    const s = e => e ? `${e.stars}⭐ ${e.skips}skip` : '-';
    rows.push({ clip: c.name, freeze: s(F), copy: s(C), groove: s(G), ends: F && C && G ? 'yes' : 'NO', 'truth audit': why.some(w => /unseen/.test(w)) ? 'FAIL' : 'ok', verdict: ok ? 'PASS' : 'FAIL ' + why.join('; ') });
  }
  return { name: 'Edge', fail, rows, text: table(`EDGE CASES — every game on every clip (${rows.length} clips)`, ['clip', 'freeze', 'copy', 'groove', 'ends', 'truth audit', 'verdict'], rows) };
}

if (import.meta.url === `file://${process.argv[1]}`){ const r = edgeReplay(); console.log(r.text); console.log(r.fail ? `\n${r.fail} FAIL` : '\nall PASS'); process.exit(r.fail ? 1 : 0); }
