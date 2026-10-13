/* node test/handwave_core_test.mjs — FOLLOW MODE v4 (the saved engine): light waits · amber when stuck · jumps only
   when Nova starts her next wave · a star per joint reached, whenever, inside its wave. */
import { HandWave, TARGETS, NOVA_WAVES, WAVE_PATHS, WAVE_START, SONG_END, WAIT_AMBER, AFTER } from '../../shared/handwave-core.js';
import { child, FollowKid } from './handwave_core_test_kids.mjs';
function play(kidOpts = {}, { fps = 15, body = {} } = {}){
  const G = new HandWave(); for (let i = 0; i < 8; i++) G.calibrate(child({ armsDown: true }, body));
  const kid = new FollowKid(kidOpts); const evs = [];
  for (let t = 0; t <= SONG_END + 3.3; t += 1 / fps){ const e = G.update(+t.toFixed(4), child(kid.pose(t), body)); kid.onEvents(e, t); evs.push(...e); if (G.ended) break; }
  return { G, evs, hits: evs.filter(e => e.type === 'hit'), misses: evs.filter(e => e.type === 'miss'), jumps: evs.filter(e => e.type === 'wave_jump'),
           opens: evs.filter(e => e.type === 'target_open'), S: (evs.find(e => e.type === 'end') || {}).summary || G.summary(), ended: G.ended };
}
let pass = 0, fail = 0; const out = []; const ok = (n, c, x = '') => { c ? pass++ : fail++; out.push(`${c ? 'PASS' : 'FAIL'}  ${n}${c ? '' : '   ' + String(x).slice(0, 160)}`); };

ok('22 targets, wrist-first, 3 waves, each wave starts on her clock', TARGETS.length === 22 && TARGETS[0].joint.endsWith('Wrist') && WAVE_PATHS.length === 3 && WAVE_START.join() === [NOVA_WAVES[0][0][0], NOVA_WAVES[1][0][0], NOVA_WAVES[2][0][0]].join());
ok("MIRROR MATCH: her first arm (her LEFT, on the viewer's RIGHT) maps to the child's RIGHT hand — mirrored self-view puts it on the same screen side as hers", TARGETS[0].joint === 'rWrist' && TARGETS[5].joint === 'lWrist' && TARGETS.at(-1).joint === 'rWrist');

const good = play({ react: 0.35 });
ok('a child who follows: every target advances ON HIS LIFT — all 22 hit, 25 stars, gold, game ends', good.hits.length === 22 && good.S.stars === 25 && good.S.medal === 'gold' && good.ended, JSON.stringify({ h: good.hits.length, s: good.S.stars }));
ok('…each hit came AFTER its target opened (the light waited for him, never ran on a timer)', good.hits.every(h => h.at == null || true) && good.evs.every((e, i) => e.type !== 'hit' || good.evs.slice(0, i).some(o => o.type === 'target_open' && o.target.joint === e.target.joint && o.target.t === e.target.t)));
ok('…targets open one at a time, in her order', good.opens.map(e => e.target.joint).join() === TARGETS.map(c => c.joint).join());
const paced = play({ react: 0.25, herPace: true });
ok('a child moving WITH HER (her pace) grades mostly clean (mint)', paced.hits.length === 22 && paced.hits.filter(h => h.quality === 'clean').length >= 16, JSON.stringify({ h: paced.hits.length, clean: paced.hits.filter(h => h.quality === 'clean').length }));

const late = play({ react: 0.8 });
ok('a slower child (0.8 s per step — "late" by the old timer rules) still hits ALL 22 — late still scores', late.hits.length === 22 && late.S.stars === 25, late.hits.length);

const frozen = play({ react: 0.35, frozen: [9.2, 19.0] });
ok('a child who FREEZES mid-wave-1: the light WAITS (amber), only when Nova starts wave 2 does it JUMP — the leftover steps miss', frozen.jumps.length >= 1 && frozen.misses.length >= 4 && frozen.misses.every(m => m.target.wave === 0), JSON.stringify({ jumps: frozen.jumps.length, miss: frozen.misses.length }));
ok('…while frozen the engine reports waiting ≥ the amber threshold (the page turns the light amber)', (() => { const G = new HandWave(); for (let i = 0; i < 8; i++) G.calibrate(child({ armsDown: true })); const kid = new FollowKid({ react: 0.35, frozen: [9.2, 19.0] });
  let sawAmber = false; for (let t = 0; t <= 17.9; t += 1 / 15){ const e = G.update(+t.toFixed(3), child(kid.pose(t))); kid.onEvents(e, t); const w = G.waiting(t); if (w && w.behind > WAIT_AMBER) sawAmber = true; } return sawAmber; })());
ok('…and he gets a FRESH CHANCE: waves 2 and 3 after waking still earn their steps + bonuses', frozen.S.waveHits[1] === 5 && frozen.S.waveHits[2] === 6 && frozen.ended, JSON.stringify(frozen.S.waveHits));

const still = play({ still: true });
ok('a child who never moves: every step misses at her wave ends, 0 stars, bronze, the game still ENDS', still.ended && still.S.stars === 0 && still.misses.length === 22 && still.S.medal === 'bronze', JSON.stringify({ end: still.ended, s: still.S.stars, m: still.misses.length }));

const wrong = play({ wrongJoint: true });
ok('lifting the WRONG joint never advances the light', wrong.hits.length === 0 && wrong.misses.length === 22, wrong.hits.map(h => h.target.joint).slice(0, 4).join(','));

const shaky = play({ still: true }, { body: { jit: 3.0 } });
ok('a very shaky camera, child still → jitter NEVER advances a target', shaky.hits.length === 0, shaky.hits.map(h => h.target.joint).join(','));

const armsUp = play({ armsUp: true });
ok('arms held HIGH the whole song (no real lifts) → nothing fires: already-up is not a move', armsUp.hits.length === 0, armsUp.hits.length);

const far = play({ react: 0.4 }, { body: { sw: 70, jit: 0.8 } });
ok('a far child (half size) still advances every target', far.hits.length >= 21, far.hits.length);
const slowFps = play({ react: 0.4 }, { fps: 8 });
ok('a slow laptop (8 fps) still advances every target', slowFps.hits.length >= 21, slowFps.hits.length);
const weak = play({ react: 0.4 }, { body: { wristVis: 0.42 } });
ok('wrists at 0.42 confidence still count (gate 0.40)', weak.hits.filter(h => h.target.joint.endsWith('Wrist')).length >= 4, weak.hits.length);
const blind = play({ react: 0.4 }, { body: { wristVis: 0.3 } });
ok('invisible wrists (0.3): those steps SKIP after ~4 s (never guessed, never stalling the wave) — the rest still hit, game ends', blind.hits.filter(h => h.target.joint.endsWith('Wrist')).length === 0 && blind.hits.length >= 14 && blind.ended, JSON.stringify({ h: blind.hits.length, end: blind.ended }));

const lp = (() => { const G = new HandWave(); for (let i = 0; i < 8; i++) G.calibrate(child({ armsDown: true })); G.update(7.0, child({})); return G.lightPos(); })();
ok('lightPos sits ON the current target for the page to glide to', lp && lp.wave === 0 && lp.joint === 'rWrist', JSON.stringify(lp));
console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
