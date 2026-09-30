/* test/move_recipes_test.mjs — every recipe drives the right lights (a fake light layer records the calls) */
import { kid } from './kid.mjs';
globalThis.performance ??= { now: () => Date.now() };
const { createMoves } = await import('../shared/move-recipes.js');
function fakeLights(){ const log = []; const rec = name => (...a) => log.push([name, ...a]);
  const L = new Proxy({}, { get: (t, k) => k === 'comet' ? { start: rec('comet.start'), follow: rec('comet.follow'), end: rec('comet.end') } : k === 'log' ? log : rec(k) }); return L; }
let pass = 0, fail = 0; const out = []; const ok = (n, c) => { c ? pass++ : fail++; out.push(`${c ? 'PASS' : 'FAIL'}  ${n}`); };
const last = (log, name) => [...log].reverse().find(x => x[0] === name);
function frames(M, id, make, n = 12){ let r = null, t = 0; for (let f = 0; f < n; f++){ t += 1 / 15; r = M.live(id, make(f, t), t); } return r; }

// NOVA SAYS
{ const L = fakeLights(), M = createMoves(L); M.cue('says.armsUp');
  ok('says.armsUp cue → the pose ghost appears', last(L.log, 'pose')?.[1] === 'armsUp');
  frames(M, 'says.armsUp', () => kid({ lArm: 95, rArm: 95 })); const mid = last(L.log, 'limbs')[1];
  ok('says.armsUp half-way → both arms glow cyan ("move")', mid.lArm === 'move' && mid.rArm === 'move');
  frames(M, 'says.armsUp', () => kid({ lArm: 170, rArm: 170 })); const done = last(L.log, 'limbs')[1];
  ok('says.armsUp reached → both arms glow green', done.lArm === 'good' && done.rArm === 'good');
  M.result('says.armsUp', 'ok'); ok('says.armsUp ok → gold bursts at both hands + "YES!"', L.log.filter(x => x[0] === 'burst').length === 2 && last(L.log, 'word')?.[1] === 'YES!'); }
{ const L = fakeLights(), M = createMoves(L); M.cue('says.leftUp'); frames(M, 'says.leftUp', () => kid({ lArm: 170, rArm: 170 }));
  const st = last(L.log, 'limbs')[1]; ok('says.leftUp with BOTH arms up → the right arm glows soft orange (wrong)', st.rArm === 'wrong' && st.lArm === 'good'); }
{ const L = fakeLights(), M = createMoves(L); M.cue('says.handsHead'); frames(M, 'says.handsHead', () => kid({ hands: 'head' }));
  const st = last(L.log, 'limbs')[1]; ok('says.handsHead reached → green', st.lArm === 'good' && st.rArm === 'good'); }
{ const L = fakeLights(), M = createMoves(L); M.result('says.trick', 'miss'); ok('trick moved → "GOTCHA!" (no red, no burst)', last(L.log, 'word')?.[1] === 'GOTCHA!' && !last(L.log, 'burst'));
  M.result('says.trick', 'ok'); ok('trick held still → icy "SMART!"', last(L.log, 'word')?.[1] === 'SMART!' && last(L.log, 'snow')); }

// INTRO
{ const L = fakeLights(), M = createMoves(L); M.live('intro.presence', kid({ sw: 0.42 })); ok('presence too close → step-back arrows', last(L.log, 'guide')?.[1] === 'tooClose');
  frames(M, 'intro.presence', () => kid({ sw: 0.07 }), 8); ok('presence too far → come-closer arrows', last(L.log, 'guide')?.[1] === 'tooFar');
  const M2 = createMoves(fakeLights(), { mirror: true }); const L2 = fakeLights(), M3 = createMoves(L2, { mirror: true }); M3.live('intro.presence', kid({ cx: 0.2 }));
  ok('presence off to the side (mirrored screen) → arrow points back to centre', ['moveLeft', 'moveRight'].includes(last(L2.log, 'guide')?.[1]));
  frames(M, 'intro.presence', () => kid({}), 8); ok('presence good → arrows off', last(L.log, 'guide')?.[1] === 'ok'); }
{ const L = fakeLights(), M = createMoves(L); M.cue('intro.shoulderL'); frames(M, 'intro.shoulderL', () => kid({ lift: { l: 0.1, r: 0 } }));
  const half = last(L.log, 'meter'); frames(M, 'intro.shoulderL', () => kid({ lift: { l: 0.25, r: 0 } })); const full = last(L.log, 'meter');
  ok('shoulder meter fills as the shoulder rises (half → full)', half[1] === 'lShoulder' && half[2] > 0.3 && half[2] < 0.8 && full[2] >= 0.95); }
{ const L = fakeLights(), M = createMoves(L); const r = frames(M, 'intro.hello', (f, t) => kid({ rArm: 150 + 25 * Math.sin(t * 2 * Math.PI * 1.4), rBend: 10 }), 30);
  ok('hello wave → sparkles on the waving hand, judge says ok', last(L.log, 'sparkle')?.[1] === 'rWrist' && r?.ok); M.result('intro.hello', 'ok', r); ok('hello ok → "HI!"', last(L.log, 'word')?.[1] === 'HI!'); }

// FREEZE
{ const L = fakeLights(), M = createMoves(L); M.cue('freeze.dance'); ok('freeze.dance → speed glow on', last(L.log, 'speedGlow')?.[1] === true);
  M.cue('freeze.stop'); ok('freeze.stop → speed glow off + ice on', last(L.log, 'speedGlow')?.[1] === false && last(L.log, 'ice')?.[1] === true);
  frames(M, 'freeze.stop', f => kid({ lArm: 30 + 30 * Math.sin(f * 1.3) }), 16); ok('a wobbling left arm during the freeze → it glows soft orange', last(L.log, 'ice')?.[2]?.wobble === 'lArm');
  const L2 = fakeLights(), M2 = createMoves(L2); M2.cue('freeze.stop'); frames(M2, 'freeze.stop', () => kid({}), 16); ok('perfectly still → no orange part', !last(L2.log, 'ice')?.[2]?.wobble);
  M.result('freeze.stop', 'ok'); ok('freeze held → snow burst + "STATUE!"', last(L.log, 'snow') && last(L.log, 'word')?.[1] === 'STATUE!'); }
{ const L = fakeLights(), M = createMoves(L); M.cue('freeze.shape.flamingo'); frames(M, 'freeze.shape.flamingo', () => kid({ lKnee: 80 }));
  ok('flamingo shape → the ghost fills as the knee is up', last(L.log, 'pose')?.[1] === 'flamingo' && last(L.log, 'pose')?.[2]?.l >= 0.75); }

// WAVE
{ const L = fakeLights(), M = createMoves(L); M.cue('wave.arm', { arm: 'right', dir: 'out', ms: 900 });
  const cue = last(L.log, 'waveCue'); ok('wave cue → dots run shoulder→elbow→wrist on the right arm', JSON.stringify(cue[1]) === JSON.stringify(['rShoulder', 'rElbow', 'rWrist']));
  M.cue('wave.arm', { arm: 'left', dir: 'in' }); ok('wave cue "in" → dots run wrist→shoulder', last(L.log, 'waveCue')[1][0] === 'lWrist');
  ok('wave start → the comet starts', !!last(L.log, 'comet.start'));
  M.result('wave.arm', 'ok', { done: { arm: 'left', dir: 'in' } }); ok('wave ok (left, in) → burst on the LEFT SHOULDER', last(L.log, 'burst')?.[1] === 'lShoulder'); }

// UP GROOVE
{ const L = fakeLights(), M = createMoves(L); M.cue('groove.bounce', { nextBeatAt: t => t + 0.5 }); ok('groove cue → the beat ring turns on', last(L.log, 'beatRing')?.[1] === true);
  M.result('groove.bounce', 'ok'); ok('on the beat → gold hit', last(L.log, 'hit')?.[1] === 'on'); M.result('groove.bounce', 'near'); ok('close → cyan hit', last(L.log, 'hit')?.[1] === 'near'); }

// UPPER BODY
{ const L = fakeLights(), M = createMoves(L); M.cue('upper.slide'); frames(M, 'upper.slide', f => kid({ slide: f < 5 ? 0 : 0.34 }), 20);
  const r = last(L.log, 'rail')[1]; ok('chest slide → the bead rides to the side, hips still', r.slide > 0.8 && r.hipsStill === true);
  M.result('upper.slide', 'ok', r); ok('slide ok → the star snaps at that side', last(L.log, 'flash')); }
{ const L = fakeLights(), M = createMoves(L); M.cue('upper.popR'); frames(M, 'upper.popR', () => kid({ lift: { l: 0, r: 0.25 } })); M.result('upper.popR', 'ok');
  ok('shoulder pop → meter filled, then the star snaps on the shoulder', last(L.log, 'flash')?.[1] === 'rShoulder'); }

// SAFETY
{ const L = fakeLights(), M = createMoves(L); let crashed = false; try { M.live('says.armsUp', null); M.live('says.armsUp', {}); M.live('nope', kid({})); M.result('nope', 'ok'); M.cue('nope'); M.clear(); } catch (e){ crashed = e.message; }
  ok('unknown ids, empty/null keypoints, clear-all → no crash', !crashed); }

console.log(out.join('\n')); console.log(`\n${pass} pass · ${fail} fail`); process.exit(fail ? 1 : 0);
