/* test/replay/fps.mjs — night item F: the Laws must hold when the detector is slow. Every game's main acceptance
   cases re-run with the camera judged at 30 · 12 · 6 fps (a slow laptop with frame-skip judges ~5-18 fps,
   test/proof/perf.mjs). Same wants as the main tables: still → star, dancer → none, empty / failed → skip, ends. */
import { createFreezeGame } from '../../beta/lib/freeze-game.js';
import { createCopyGame } from '../../beta/lib/copy-game.js';
import { createGrooveGame } from '../../beta/lib/groove-game.js';
import { run, clip, json, seeded, table } from './sim.mjs';

const tune = json('beta/freeze2/script.json').tune;
const CASES = [
  { game: 'freeze', clip: 'frozen-body', ok: e => e.stars >= 1 && e.skips === 0 },
  { game: 'freeze', clip: 'dance-hype',  ok: e => e.stars === 0 },
  { game: 'freeze', clip: 'empty-room',  ok: e => e.stars === 0 && e.skips === e.rounds },
  { game: 'copy',   clip: 'own-left-up', poses: ['leftUp', 'rightUp'], ok: e => e.results[0].outcome === 'star' && e.results[1].outcome !== 'star' },
  { game: 'copy',   clip: 'pose-armsup', poses: ['armsUp', 'bear', 'star'], ok: e => e.results[0].outcome === 'star' && e.stars === 1 },
  { game: 'copy',   clip: 'empty-room',  poses: ['armsUp'], ok: e => e.skips === 1 },
  { game: 'groove', clip: 'dance-hype',  ok: e => e.stars - e.bonus >= 0.8 * e.rounds },
  { game: 'groove', clip: 'frozen-body', ok: e => e.stars === 0 },
  { game: 'groove', clip: 'empty-room',  ok: e => e.stars === 0 && e.skips === e.rounds },
];
const make = (c, rec) => on => c.game === 'freeze' ? createFreezeGame({ tune, on, rng: seeded(11) })
  : c.game === 'copy' ? createCopyGame({ poses: c.poses, on, size: { w: rec.w, h: rec.h } }) : createGrooveGame({ on, size: { w: rec.w, h: rec.h } });

export function fpsReplay(){
  const rows = []; let fail = 0;
  for (const c of CASES){
    const rec = clip(c.clip), row = { game: c.game, clip: c.clip + (c.poses ? ` (${c.poses.join(',')})` : '') };
    for (const fps of [30, 12, 6]){ const { ended } = run(make(c, rec), rec, { fps }); const ok = !!ended && c.ok(ended); if (!ok) fail++;
      row[`${fps} fps`] = ended ? `${ended.stars}⭐ ${ended.skips}skip ${ok ? '✓' : '✗'}` : 'NO END ✗'; }
    rows.push(row);
  }
  return { name: 'FPS', fail, rows, text: table('LAWS AT LOW FRAME RATES — judged at 30 · 12 · 6 fps (✓ = same verdict as the main tables)', ['game', 'clip', '30 fps', '12 fps', '6 fps'], rows) };
}
if (import.meta.url === `file://${process.argv[1]}`){ const r = fpsReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
