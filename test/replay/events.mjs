/* test/replay/events.mjs — night item D: the brain's event stream (beta/lib/events.js) must match the replay table
   1:1 — one round_start per round, one hit per star, one skip_unseen per skip, one miss per judged round without a
   star, exactly one medal (same medal as the game). */
import { createFreezeGame } from '../../beta/lib/freeze-game.js';
import { createCopyGame, POSES } from '../../beta/lib/copy-game.js';
import { createGrooveGame } from '../../beta/lib/groove-game.js';
import { toNovaEvent } from '../../beta/lib/events.js';
import { run, clip, json, seeded, table } from './sim.mjs';

const tune = json('beta/freeze2/script.json').tune;
const MAKERS = {
  freeze: (rec, on) => createFreezeGame({ tune, on, rng: seeded(11) }),
  copy:   (rec, on) => createCopyGame({ poses: Object.keys(POSES), on, size: { w: rec?.w || 640, h: rec?.h || 480 } }),
  groove: (rec, on) => createGrooveGame({ on, size: { w: rec?.w || 640, h: rec?.h || 480 } }),
};
const CLIPS = ['frozen-body', 'dance-hype', 'pose-armsup', 'own-left-up', 'empty-room', 'model-fail'];

export function eventsReplay(){
  const rows = []; let fail = 0; const sample = [];
  for (const game of Object.keys(MAKERS)) for (const c of CLIPS){
    const rec = c === 'model-fail' ? null : clip(c), log = [];
    const { ended } = run(on => MAKERS[game](rec, (type, d) => { const e = toNovaEvent(game, type, d); if (e) log.push(e); on(type, d); }), rec, { detector: c === 'model-fail' ? 'fail' : 'ok' });
    const n = ev => log.filter(e => e.event === ev).length, medal = log.filter(e => e.event === 'medal');
    const bonus = ended.bonus ?? 0;
    const want = { round_start: ended.rounds, hit: ended.stars, skip_unseen: ended.skips, miss: ended.judged - (ended.stars - bonus), medal: 1 };
    const got = { round_start: n('round_start'), hit: n('hit'), skip_unseen: n('skip_unseen'), miss: n('miss'), medal: medal.length };
    const ok = Object.keys(want).every(k => want[k] === got[k]) && medal[0]?.detail.medal === ended.medal;
    if (!ok) fail++;
    if (game === 'freeze' && c === 'frozen-body') sample.push(...log.slice(0, 6));
    rows.push({ game, clip: c, 'round_start': `${got.round_start}/${want.round_start}`, hit: `${got.hit}/${want.hit}`, skip_unseen: `${got.skip_unseen}/${want.skip_unseen}`,
      miss: `${got.miss}/${want.miss}`, medal: `${medal[0]?.detail.medal ?? 'none'}`, verdict: ok ? 'PASS' : 'FAIL' });
  }
  return { name: 'Events', fail, rows, sample, text: table('BRAIN EVENTS — event stream vs replay table (got/want)', ['game', 'clip', 'round_start', 'hit', 'skip_unseen', 'miss', 'medal', 'verdict'], rows) };
}
if (import.meta.url === `file://${process.argv[1]}`){ const r = eventsReplay(); console.log(r.text); console.log('\nsample (freeze · frozen-body):'); for (const e of r.sample) console.log(' ', JSON.stringify(e)); process.exit(r.fail ? 1 : 0); }
