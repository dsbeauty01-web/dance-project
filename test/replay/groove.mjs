/* test/replay/groove.mjs — Phase 4 acceptance for beta/groove.html (beta/lib/groove-game.js).
     dance clip → ≥ 80 % of bars starred · still clip → 0 % starred · empty-room → every bar skipped, 0 stars, the game ends
   Until Refael's ref-dance / ref-still arrive, Nova's dance-hype / frozen-body stand in (the table says which). */
import { createGrooveGame } from '../../beta/lib/groove-game.js';
import { run, clip, table } from './sim.mjs';

const pick = (ref, nova) => clip(ref) ? ref : nova;
const CASES = [
  { clip: pick('ref-dance', 'dance-hype'), want: 'dance', ok: e => e.stars - e.bonus >= 0.8 * e.rounds && e.skips === 0 },
  { clip: pick('ref-still', 'frozen-body'), want: 'still', ok: e => e.stars === 0 && e.skips === 0 },
  { clip: 'still-sway', want: 'sway (report)', ok: () => true },
  { clip: 'empty-room', want: 'empty', ok: e => e.stars === 0 && e.skips === e.rounds },
  { clip: 'model-fail', want: 'empty', detector: 'fail', ok: e => e.stars === 0 && e.skips === e.rounds },
];

export function grooveReplay(){
  const rows = []; let fail = 0;
  for (const c of CASES){
    const rec = c.detector === 'fail' ? null : clip(c.clip);
    if (!rec && c.detector !== 'fail'){ rows.push({ clip: c.clip, verdict: 'MISSING' }); fail++; continue; }
    const { ended } = run(on => createGrooveGame({ on, size: { w: rec?.w || 640, h: rec?.h || 480 } }), rec, { detector: c.detector });
    const ok = !!ended && c.ok(ended); if (!ok) fail++;
    const E = ended?.results.filter(r => r.outcome !== 'skip').map(r => r.energy) ?? [];
    const med = E.length ? [...E].sort((a, b) => a - b)[Math.floor(E.length / 2)] : null;
    rows.push({ clip: c.clip, want: c.want === 'dance' ? '>=80% bars ⭐' : c.want === 'still' ? '0% bars ⭐' : c.want === 'empty' ? 'all skip, 0 ⭐' : 'reported',
      bars: ended?.rounds ?? '-', '⭐ bars': ended ? ended.stars - ended.bonus : '-', '% bars ⭐': ended ? (100 * (ended.stars - ended.bonus) / ended.rounds).toFixed(0) + '%' : '-',
      bonus: ended?.bonus ?? '-', skips: ended?.skips ?? '-', 'energy p50 (sw/s)': med == null ? '-' : med.toFixed(2),
      bounces: ended ? `${ended.onBeat}/${ended.bounces} on-beat` : '-', ends: ended ? 'yes' : 'NO', verdict: ok ? 'PASS' : 'FAIL' });
  }
  return { name: 'Groove', fail, rows, text: table('GROOVE (beta/groove.html) — replay table · song animal-freeze-song.mp3 129.2 BPM · floor 0.25 sw/s (GUESS until ref-still)',
    ['clip', 'want', 'bars', '⭐ bars', '% bars ⭐', 'bonus', 'skips', 'energy p50 (sw/s)', 'bounces', 'ends', 'verdict'], rows) };
}

if (import.meta.url === `file://${process.argv[1]}`){ const r = grooveReplay(); console.log(r.text); process.exit(r.fail ? 1 : 0); }
