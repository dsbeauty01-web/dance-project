/* test/replay/copy.mjs — Phase 3 acceptance for beta/copy.html (beta/lib/copy-game.js).
   Every clip is played against every pose, one round each (the pose shown, then the 6 s window).
     a Nova pose clip → ⭐ for ITS pose, NO star for every other pose
     own-left-up → ⭐ leftUp, NO star rightUp (mirror proof) · own-right-up → the reverse
     empty-room → every round skips, no star */
import { createCopyGame, POSES } from '../../beta/lib/copy-game.js';
import { run, clip, table } from './sim.mjs';

/* upperbody is NOT an armsOut hold (its arms-out section is a moving dance: longest continuous match 0.10 s), so it is
   only asserted to give NO star for the other poses. The repo has no held arms-out clip → armsOut star unproven. */
const EXPECT = { 'pose-armsup': 'armsUp', 'pose-star': 'star', 'pose-bear': 'bear', 'upperbody': 'NONE',
                 'own-left-up': 'leftUp', 'own-right-up': 'rightUp', 'empty-room': 'SKIP' };
const NAMES = Object.keys(POSES);

export function copyReplay(){
  const rows = []; let fail = 0;
  for (const [c, want] of Object.entries(EXPECT)){
    const rec = clip(c); if (!rec){ rows.push({ clip: c, verdict: 'MISSING' }); fail++; continue; }
    const row = { clip: c, want: want === 'SKIP' ? 'skip all' : want === 'NONE' ? 'no star' : '⭐ ' + want }; let ok = true;
    for (const p of NAMES){
      const { ended } = run(on => createCopyGame({ poses: [p], on, size: { w: rec.w, h: rec.h } }), rec);
      const o = ended?.results?.[0]?.outcome;
      row[p] = o === 'star' ? '⭐' : o === 'skip' ? 'skip' : o === 'notyet' ? '·' : '?';
      if (!ended) ok = false;
      else if (want === 'SKIP') ok &&= o === 'skip';
      else if (want === 'NONE') ok &&= o !== 'star';
      else if (p === want) ok &&= o === 'star';
      else ok &&= o !== 'star';
    }
    row.verdict = ok ? 'PASS' : 'FAIL'; if (!ok) fail++; rows.push(row);
  }
  return { name: 'Copy Nova', fail, rows, text: table('COPY NOVA (beta/copy.html) — replay matrix: clip × pose (⭐ star · "·" not yet · skip)', ['clip', 'want', ...NAMES, 'verdict'], rows) };
}

if (import.meta.url === `file://${process.argv[1]}`){ const r = copyReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
