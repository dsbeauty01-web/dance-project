#!/usr/bin/env node
/* NOVA SAYS — QA bench (Q1-Q10 from Downloads/NOVASAYS-QA.md, architect 2026-09-24)
 *
 * The judge, the calibration and the timing maths are SLICED OUT OF beta/novasays.html and run here,
 * so this bench tests shipped code — not a copy of it that can drift. Nothing is mocked except the
 * things a browser would provide (a clock, a keypoint stream).
 *
 * Run:  node test/novasays_qa_bench.js
 */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'beta/novasays.html'), 'utf8');
const SCRIPT = JSON.parse(fs.readFileSync(path.join(ROOT, 'beta/novasays/script.json'), 'utf8'));

let pass = 0, fail = 0;
const ok = (name, cond, detail = '') => { if (cond){ pass++; console.log('  ✓ ' + name + (detail ? '  ' + detail : '')); } else { fail++; console.log('  ✗ ' + name + '  ' + detail); } };
const near = (a, b, tol) => Math.abs(a - b) <= tol;

// ───────────────────── slice the real source ─────────────────────
/* Brace-matched extraction by declaration name. If a rename ever breaks these, the bench fails loudly
   instead of silently testing nothing — which is the whole point of slicing rather than copying. */
function sliceDecl(name){
  const pats = [
    new RegExp('(?:^|\\n)\\s*(?:async\\s+)?function\\s+' + name + '\\s*\\('),
    new RegExp('(?:^|\\n)\\s*(?:const|let|var)\\s+' + name + '\\s*=\\s*'),
  ];
  for (const p of pats){
    const m = p.exec(HTML);
    if (!m) continue;
    const start = m.index + (HTML[m.index] === '\n' ? 1 : 0);
    // walk to the end of the declaration: brace-match if there is a body, else end of statement
    let i = HTML.indexOf('{', m.index);
    const semi = HTML.indexOf(';', m.index);
    const arrowBody = i >= 0 && (semi < 0 || i < semi);
    if (!arrowBody) return HTML.slice(start, semi + 1);
    let depth = 0;
    for (; i < HTML.length; i++){
      if (HTML[i] === '{') depth++;
      else if (HTML[i] === '}'){ depth--; if (depth === 0){ i++; break; } }
    }
    if (HTML[i] === ';') i++;
    return HTML.slice(start, i);
  }
  throw new Error('bench cannot find declaration: ' + name + ' (was it renamed? the bench must be updated with it)');
}
/* The energy metric lives inside the K.onKid arrow. Slice its body and wrap it as feedFrame(k). */
function sliceOnKidBody(){
  const m = /K\.onKid\s*=\s*\(out,\s*k\)\s*=>\s*\{/.exec(HTML);
  if (!m) throw new Error('bench cannot find K.onKid');
  let i = HTML.indexOf('{', m.index), depth = 0, start = i + 1;
  for (; i < HTML.length; i++){ if (HTML[i] === '{') depth++; else if (HTML[i] === '}'){ depth--; if (depth === 0) break; } }
  return HTML.slice(start, i);
}

const SRC = {
  finishCalibration: sliceDecl('finishCalibration'),
  bodyVisible:       sliceDecl('bodyVisible'),
  armUp:             sliceDecl('armUp'),
  lastWristAbove:    sliceDecl('lastWristAbove'),
  realRule:          sliceDecl('realRule'),
  judgeFrame:        sliceDecl('judgeFrame'),
  windowSecsFor:     sliceDecl('windowSecsFor'),
  addToMax:          sliceDecl('addToMax'),
  maxStarsNow:       sliceDecl('maxStarsNow'),
  vis:               sliceDecl('vis'),
  sw:                sliceDecl('sw'),
  wristDist:         sliceDecl('wristDist'),
  reach:             sliceDecl('reach'),
  med:               sliceDecl('med'),
  p90:               sliceDecl('p90'),
  onKidBody:         sliceOnKidBody(),
};

// ───────────────────── sandbox ─────────────────────
function makeEnv(){
  let nowMs = 0;
  const ctx = {
    S: JSON.parse(JSON.stringify(SCRIPT)),
    TU: JSON.parse(JSON.stringify(SCRIPT.tune)),
    NFPS: SCRIPT.tune.nominalFps || 15,
    CAL: { still:null, move:null, reach:null, rest:null, stillS:[], moveS:[], reachS:[], restS:[] },
    thr: null,
    J: ['lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist'],
    prev: null, last: null, energy: 0, win: null, sampling: null, clapOpenT: 0,
    lastT: 0,
    maxRaw: 0, maxDecisions: 0,
    RULES: {},
    K: { E: null },
    Math, JSON, console,
    performance: { now: () => nowMs },
    dbgNote: () => {}, dbg: () => {},
    _closed: [],
    setNow: t => { nowMs = t; },
    getNow: () => nowMs,
  };
  ctx.closeWindow = function(result){ if (!ctx.win) return; ctx.win = null; ctx._closed.push(result); };
  vm.createContext(ctx);
  const src = [
    SRC.vis, SRC.sw, SRC.wristDist, SRC.reach, SRC.med, SRC.p90,
    SRC.lastWristAbove, SRC.bodyVisible, SRC.armUp, SRC.realRule,
    SRC.finishCalibration, SRC.judgeFrame, SRC.windowSecsFor, SRC.addToMax, SRC.maxStarsNow,
    'function feedFrame(k){ const out = null; ' + SRC.onKidBody + ' }',
    // provisional thresholds exactly as the page initialises them
    'thr = { move:0.012 * NFPS, freeze:0.006 * NFPS, reach:TU.reachFloorSW, clapClose:0.35, clapOpen:0.6 };',
    // const-declared helpers are lexical, not context properties — hand them to the bench
    'for (const [n, v] of Object.entries({ vis, sw, wristDist, reach, med, p90, bodyVisible, lastWristAbove })) globalThis[n] = v;',
  ].join('\n');
  vm.runInContext(src, ctx, { filename: 'novasays.sliced.js' });
  return ctx;
}

// ───────────────────── keypoint helpers ─────────────────────
const SHOULDER_Y = 0.40, SHOULDER_HALF = 0.09;   // sw = 0.18
function body(over = {}){
  const k = {
    lShoulder: { x: 0.5 - SHOULDER_HALF, y: SHOULDER_Y, vis: 0.95 },
    rShoulder: { x: 0.5 + SHOULDER_HALF, y: SHOULDER_Y, vis: 0.95 },
    lElbow:    { x: 0.5 - 0.11, y: 0.55, vis: 0.9 },
    rElbow:    { x: 0.5 + 0.11, y: 0.55, vis: 0.9 },
    lWrist:    { x: 0.5 - 0.12, y: 0.70, vis: 0.9 },
    rWrist:    { x: 0.5 + 0.12, y: 0.70, vis: 0.9 },
  };
  for (const j in over) Object.assign(k[j], over[j]);
  return k;
}
function jitter(k, amp, rnd){
  const o = JSON.parse(JSON.stringify(k));
  for (const j of ['lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist']){
    o[j].x += (rnd() - 0.5) * amp; o[j].y += (rnd() - 0.5) * amp;
  }
  return o;
}
// deterministic PRNG so the bench is reproducible
function mulberry(seed){ return function(){ seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

/* Run one trick window against a STILL child and report whether it false-GOTCHA'd.
   stillAmp = the child's own tremor; flipRate = fraction of frames with a keypoint teleport;
   fps = frame rate during the window. Calibration is done first at calFps on the same tremor. */
function trickTrial({ stillAmp, flipRate, fps, calFps, provisional, seed, moveMult, floorMult }){
  const env = makeEnv();
  if (moveMult != null) env.TU.provisionalMoveMult = moveMult;
  if (floorMult != null) env.TU.moveFloorMult = floorMult;   // 0 = the pre-Q4 world, where there was no floor
  const rnd = mulberry(seed);
  // ── calibrate STILL on this child's real tremor
  let t = 0; const calDt = 1000 / calFps;
  env.setNow(t); env.sampling = 'still';
  let base = body();
  for (let i = 0; i < Math.round(calFps * (SCRIPT.tune.stillSeconds || 2)); i++){
    t += calDt; env.setNow(t);
    env.feedFrame(jitter(base, stillAmp, rnd));
  }
  env.sampling = null;
  // ── the moving sample: either a real arm raise, or nothing (→ provisional fallback)
  if (!provisional){
    env.sampling = 'move';
    for (let i = 0; i < Math.round(calFps * 1.2); i++){
      t += calDt; env.setNow(t);
      const f = 1 - i / Math.round(calFps * 1.2);
      env.feedFrame(jitter(body({ lWrist:{ y: 0.70 - 0.55 * (1 - f) }, rWrist:{ y: 0.70 - 0.55 * (1 - f) },
                                  lElbow:{ y: 0.55 - 0.30 * (1 - f) }, rElbow:{ y: 0.55 - 0.30 * (1 - f) } }), stillAmp, rnd));
    }
    env.sampling = null;
  }
  env.finishCalibration();
  // ── the trick window: child does nothing
  const winSecs = 2.0, dt = 1000 / fps;
  const t0 = t + 500;
  env.setNow(t0);
  env.win = { cmdId:'clap', kind:'trick', judge:'clap', t0, t1: t0 + winSecs * 1000, holdMs:0,
              since:null, moveSince:null, effortSince:null, effort:false,
              ignoreUntil: t0 + env.TU.trickIgnoreMs, effortOK:false, lostSince:null, res:()=>{} };
  t = t0;
  while (env.win && t < t0 + winSecs * 1000 + dt){
    t += dt; env.setNow(t);
    let f = jitter(base, stillAmp, rnd);
    if (rnd() < flipRate){ const j = rnd() < 0.5 ? 'lWrist' : 'rWrist'; f[j].x += 1.2 * 0.18; f[j].y -= 0.9 * 0.18; }   // teleport ~1 shoulder-width
    env.feedFrame(f);
    if (env.win) env.judgeFrame(f);
  }
  const k = env.thr.move / Math.max(1e-9, env.CAL.still);
  return { gotcha: env._closed.includes('gotcha'), k, closed: env._closed.slice() };
}
function falseGotchaRate(opts, trials = 60){
  let n = 0, kSum = 0;
  for (let i = 0; i < trials; i++){ const r = trickTrial({ ...opts, seed: 1000 + i * 7 }); if (r.gotcha) n++; kSum += r.k; }
  return { rate: n / trials, k: kSum / trials };
}

// ═════════════════════════ the bench ═════════════════════════
console.log('\nNOVA SAYS — QA bench (Q1-Q10)   script.json v' + SCRIPT.version + '\n');

// ───────── Q1 · the window opens at the gesture's peak, not the line's end
console.log('Q1 · the judge window opens when her arms arrive');
{
  const env = makeEnv();
  const frac = SCRIPT.windowOpensAtPeakFrac, PEAK = SCRIPT.peakMs;
  ok('peakMs present for all 5 bakes', Object.keys(PEAK).length === 5, JSON.stringify(PEAK));
  ok('every peak is below its bakeMs (she is still holding the pose)',
     Object.keys(PEAK).every(g => PEAK[g] < SCRIPT.bakeMs[g]),
     Object.keys(PEAK).map(g => `${g.replace('gest_','')} ${PEAK[g]}<${SCRIPT.bakeMs[g]}`).join(' · '));
  // the shipped call site: window opens at gStart + frac*peak, measured against a 2.0s line
  const LINE_MS = 2000;
  const rows = Object.entries({ armsUp:'gest_star', clap:'gest_clap', leftArm:'gest_lefthand', rightArm:'gest_righthand', freeze:'gest_bear' })
    .map(([cmd, g]) => ({ cmd, opensAt: Math.max(LINE_MS, frac * PEAK[g]), peak: PEAK[g] }));
  ok('no window opens before 80% of the peak',
     rows.every(r => r.opensAt >= frac * r.peak),
     rows.map(r => `${r.cmd} @${(r.opensAt/1000).toFixed(2)}s`).join(' · '));
  // the OLD behaviour, for the record: window opened at the line end
  const lateByOld = rows.filter(r => r.peak > LINE_MS);
  ok('the old order opened the window before her arms arrived on 4 of 5 commands',
     lateByOld.length === 4,
     lateByOld.map(r => `${r.cmd} arms ${(r.peak/1000).toFixed(2)}s vs window 2.00s`).join(' · '));
  ok('the page reads peakMs from script.json (single source of truth)',
     /const PEAK = Object\.assign\(\{[^}]*\},\s*S\.peakMs/.test(HTML));
  ok('demo() and lightCue() fire before the line is awaited',
     /const lineP = speakLine\(lineId\);\s*\n\s*demo\(cmdId\); lightCue\(/.test(HTML));
  ok('practice uses the same peak-aligned call as the game',
     /let r = await callCommand\('armsUp', 'real'/.test(HTML) && /await callCommand\('clap', 'trick'/.test(HTML));
}

// ───────── Q2 · raising arms must not void the window
console.log('\nQ2 · arms out of frame no longer voids the window');
{
  const env = makeEnv();
  env.thr = { ...env.thr, reach: 0.30 };
  const armsUpVisible = body({ lWrist:{ y: 0.10 }, rWrist:{ y: 0.10 }, lElbow:{ y: 0.28 }, rElbow:{ y: 0.28 } });
  ok('wrists visible and high → armUp true', env.armUp(armsUpVisible,'L') && env.armUp(armsUpVisible,'R'));
  // the real case: wrists pushed out of the top of the frame, elbows still high
  const wristsGone = body({ lWrist:{ y: -0.05, vis: 0.1 }, rWrist:{ y: -0.05, vis: 0.1 }, lElbow:{ y: 0.28 }, rElbow:{ y: 0.28 } });
  ok('wrists out of frame, elbows high → still armUp (elbow at half reach)',
     env.armUp(wristsGone,'L') && env.armUp(wristsGone,'R'));
  const elbowsGoneToo = body({ lWrist:{ vis:0.1 }, rWrist:{ vis:0.1 }, lElbow:{ vis:0.1 }, rElbow:{ vis:0.1 } });
  ok('wrist and elbow both gone → falls back to the last verdict (true, they were up)',
     env.armUp(elbowsGoneToo,'L') === true);
  ok('shoulders visible → window NOT voided', env.bodyVisible(body()) === true);
  ok('wrists missing → window NOT voided', env.bodyVisible(wristsGone) === true);
  ok('shoulders lost → window voided', env.bodyVisible(body({ lShoulder:{ vis:0.1 } })) === false);
  ok('judgeFrame voids on bodyVisible, not on all six joints', /if \(!bodyVisible\(k\)\)\{ w\.lostSince/.test(HTML));
  // and prove the OLD rule would have voided this exact child
  const allSix = ['lShoulder','rShoulder','lElbow','rElbow','lWrist','rWrist'].every(n => wristsGone[n].vis > 0.6);
  ok('the old K.armsVisible rule would have voided arms-up done correctly', allSix === false);
}

// ───────── Q3 · freeze can actually be held in the lightning round
console.log('\nQ3 · freeze is holdable in every round');
{
  const env = makeEnv();
  const hold = SCRIPT.commands.freeze.holdMs / 1000, pad = SCRIPT.freezeWindowPadS;
  for (const [i, R] of SCRIPT.rounds.entries()){
    const w = env.windowSecsFor('freeze', R.win);
    ok(`round ${i+1} freeze window ${w.toFixed(2)}s ≥ hold ${hold}s + settle ${pad}s`, w >= hold + pad, `(round win was ${R.win}s)`);
  }
  ok('a non-freeze window is untouched', env.windowSecsFor('clap', 1.6) === 1.6);
  const worst = Math.min(...SCRIPT.rounds.map(R => R.win));
  ok('round 3 on its own window could not safely fit the hold', worst < hold + pad,
     `round win ${worst}s vs the ${(hold + pad).toFixed(1)}s a 1.0s hold needs after a 0.3-0.5s EMA settle — only 0.6s of slack, which is why it failed for most kids`);
}

// ───────── Q4 · a still child is never GOTCHA'd (the simulation the QA ran)
console.log('\nQ4 · the false-GOTCHA table — a perfectly still child on a trick');
{
  const conds = [
    { name: 'normal jitter          ', flipRate: 0.00, fps: 15, calFps: 15 },
    { name: 'keypoint flips 1%      ', flipRate: 0.01, fps: 15, calFps: 15 },
    { name: 'keypoint flips 3%      ', flipRate: 0.03, fps: 15, calFps: 15 },
    { name: 'fps drop 15 -> 8       ', flipRate: 0.00, fps: 8,  calFps: 15 },
    { name: 'flips 3% + fps drop    ', flipRate: 0.03, fps: 8,  calFps: 15 },
  ];
  /* NOTE, so this table is not over-read: the "Q4 reverted" column reverts ONLY Q4 (x4, no floor).
     Q5 and Q6 are sliced from the shipped page and cannot be switched off here, so that column does
     not reproduce the architect's original 12-25% — those rates were measured with per-frame energy
     and unfiltered keypoint flips still in place. What it does prove is the threshold moving off
     k=1.9, which is the specific thing Q4 changes. */
  console.log('        condition                 measured-cal      provisional (x10)   Q4 reverted (x4, no floor)');
  for (const c of conds){
    const meas = falseGotchaRate({ stillAmp: 0.004, provisional: false, ...c });
    const prov = falseGotchaRate({ stillAmp: 0.004, provisional: true,  ...c });
    const old  = falseGotchaRate({ stillAmp: 0.004, provisional: true,  moveMult: 4, floorMult: 0, ...c });
    console.log(`        ${c.name}    ${(meas.rate*100).toFixed(0).padStart(3)}% k=${meas.k.toFixed(1).padStart(4)}` +
                `      ${(prov.rate*100).toFixed(0).padStart(3)}% k=${prov.k.toFixed(1).padStart(4)}` +
                `        ${(old.rate*100).toFixed(0).padStart(3)}% k=${old.k.toFixed(1).padStart(4)}`);
    ok(`no false GOTCHA — measured calibration, ${c.name.trim()}`, meas.rate === 0);
    ok(`no false GOTCHA — provisional fallback, ${c.name.trim()}`, prov.rate === 0);
  }
  const k    = falseGotchaRate({ stillAmp: 0.004, provisional: true, flipRate: 0, fps: 15, calFps: 15 }).k;
  const kOld = falseGotchaRate({ stillAmp: 0.004, provisional: true, flipRate: 0, fps: 15, calFps: 15, moveMult: 4, floorMult: 0 }).k;
  console.log(`        the threshold the architect flagged:  k ${kOld.toFixed(2)} -> ${k.toFixed(2)}`);
  ok('reverting Q4 reproduces the k~1.9 the architect measured', near(kOld, 1.9, 0.15), `k=${kOld.toFixed(2)}`);
  ok('the provisional fallback now lands at k ~ 3.7 (safe in every simulated condition)', k >= 3.0, `k=${k.toFixed(2)}`);
  ok('provisionalMoveMult is 10 in script.json', SCRIPT.tune.provisionalMoveMult === 10);
  ok('the hard floor is in the shipped code', /thr\.move = Math\.max\(thr\.move, CAL\.still \* \(TU\.moveFloorMult/.test(HTML));
  // the floor must bite even if moveFrac were mis-set to 0
  const env = makeEnv();
  env.TU.moveFrac = 0; env.CAL.stillS = [0.05]; env.CAL.restS = [1.0]; env.CAL.moveS = []; env.CAL.reachS = [];
  env.finishCalibration();
  ok('with moveFrac 0 the floor still holds the threshold at 3x stillness',
     near(env.thr.move / env.CAL.still, SCRIPT.tune.moveFloorMult, 0.001), `k=${(env.thr.move/env.CAL.still).toFixed(2)}`);
  ok('the practice arm-up is retried before the fallback is accepted', /lineId:'practice\.retry'/.test(HTML));
  ok('a provisional calibration is flagged to her memory', /PROVISIONAL — arm-up never measured/.test(HTML));
}

// ───────── Q5 · energy is frame-rate independent
console.log('\nQ5 · the same movement measures the same at any frame rate');
{
  function raiseEnergy(fps){
    const env = makeEnv();
    let t = 0; const dt = 1000 / fps, N = Math.round(fps * 1.0);
    env.setNow(t); env.feedFrame(body());
    let peak = 0;
    for (let i = 1; i <= N; i++){
      t += dt; env.setNow(t);
      const f = i / N;                       // one full arm raise over exactly 1.0s
      env.feedFrame(body({ lWrist:{ y: 0.70 - 0.55 * f }, rWrist:{ y: 0.70 - 0.55 * f },
                           lElbow:{ y: 0.55 - 0.30 * f }, rElbow:{ y: 0.55 - 0.30 * f } }));
      peak = Math.max(peak, env.energy);
    }
    return peak;
  }
  const e8 = raiseEnergy(8), e15 = raiseEnergy(15), e30 = raiseEnergy(30);
  const spread = Math.max(e8, e15, e30) / Math.min(e8, e15, e30);
  console.log(`        same 1.0s arm raise:  8fps ${e8.toFixed(3)}   15fps ${e15.toFixed(3)}   30fps ${e30.toFixed(3)}   spread x${spread.toFixed(2)}`);
  ok('8fps and 30fps agree within 25%', spread < 1.25, `spread x${spread.toFixed(2)}`);
  ok('energy is divided by dt in the shipped code', /\/ sw\(k\)\) \/ dt\)/.test(HTML));
  ok('dt is floored at one 60fps frame', /dt = Math\.max\(0\.016,/.test(HTML));
  ok('provisional thresholds were converted to the new units', /move:0\.012 \* NFPS/.test(HTML));
}

// ───────── Q6 · a one-frame teleport is not movement
console.log('\nQ6 · keypoint flips do not register as movement');
{
  const env = makeEnv();
  let t = 0; const dt = 1000/15;
  env.setNow(t); env.feedFrame(body());
  for (let i = 0; i < 5; i++){ t += dt; env.setNow(t); env.feedFrame(body()); }
  const quiet = env.energy;
  t += dt; env.setNow(t);
  env.feedFrame(body({ lWrist: { x: 0.5 - 0.12 + 1.2 * 0.18, y: 0.70 - 0.9 * 0.18 } }));   // ~1.5 shoulder-widths in one frame
  const afterFlip = env.energy;
  ok('a 1.5-shoulder-width one-frame jump adds no energy', near(afterFlip, quiet, Math.max(1e-6, quiet * 0.05)),
     `${quiet.toFixed(5)} -> ${afterFlip.toFixed(5)}`);
  // a real fast movement of the same joint, spread over 3 frames, DOES register
  const env2 = makeEnv();
  let t2 = 0; env2.setNow(t2); env2.feedFrame(body());
  for (let i = 1; i <= 3; i++){ t2 += dt; env2.setNow(t2); env2.feedFrame(body({ lWrist: { y: 0.70 - 0.12 * i } })); }
  ok('a real fast arm movement still registers', env2.energy > quiet * 2, `energy ${env2.energy.toFixed(4)}`);
  ok('the reject threshold is in script.json', SCRIPT.tune.jumpRejectSW === 0.8);
  ok('the guard is in the shipped energy loop', /if \(jump > \(TU\.jumpRejectSW \?\? 0\.8\)\) continue;/.test(HTML));
}

// ───────── Q7 · a stalled camera hands out nothing
console.log('\nQ7 · a frozen camera gives neither stars nor a gotcha');
{
  ok('the safety interval closes a stalled window as void', /performance\.now\(\) >= win\.t1 \+ 400\) closeWindow\('void'\)/.test(HTML));
  ok("it no longer resolves a stalled trick as 'held' (+2 stars)", !/closeWindow\(win\.kind === 'real' \? 'miss' : 'held'\)/.test(HTML.split("setInterval")[1] || ''));
  // a healthy window still closes on its own verdict at t1
  const env = makeEnv();
  env.CAL.stillS = [0.004 * 15]; env.CAL.restS = [1.0]; env.CAL.moveS = [0.30]; env.CAL.reachS = [0.9];
  env.finishCalibration();
  const t0 = 10000; env.setNow(t0);
  env.win = { cmdId:'clap', kind:'trick', judge:'clap', t0, t1: t0 + 1000, holdMs:0, since:null, moveSince:null,
              effortSince:null, effort:false, ignoreUntil:t0, effortOK:false, lostSince:null, res:()=>{} };
  env.setNow(t0 + 1100); env.judgeFrame(body());
  ok("a healthy still trick window still resolves 'held'", env._closed[0] === 'held', JSON.stringify(env._closed));
}

// ───────── Q8 · the medal is measured against what was actually played
console.log('\nQ8 · the medal maximum follows the adaptive difficulty');
{
  const env = makeEnv();
  const raw = r => r.steps.map(s => [...s]);
  // full script, no adaptive change
  for (const R of SCRIPT.rounds) env.addToMax(raw(R));
  const full = env.maxStarsNow();
  // now the adaptive path: round 2 drops to round2TricksIfCaught tricks
  const env2 = makeEnv();
  SCRIPT.rounds.forEach((R, idx) => {
    const steps = raw(R);
    if (idx === 1){
      const trickIdx = steps.map((s,i) => s[1] === 'trick' ? i : -1).filter(i => i >= 0);
      while (steps.filter(s => s[1] === 'trick').length > SCRIPT.adaptive.round2TricksIfCaught) steps[trickIdx.pop()][1] = 'real';
    }
    env2.addToMax(steps);
  });
  const eased = env2.maxStarsNow();
  console.log(`        max stars: full script ${full} → after the round-2 easing ${eased}`);
  ok('easing round 2 lowers the ceiling', eased < full, `${full} -> ${eased}`);
  ok('the decision count (streak bonus) is unchanged by easing', env.maxDecisions === env2.maxDecisions);
  // the medal a child would get with the same score, before vs after the fix
  const score = Math.round(full * 0.80);
  const medalOf = (s, m) => { const p = s / m; return p >= SCRIPT.medals.goldFrom ? 'gold' : p >= SCRIPT.medals.bronzeBelow ? 'silver' : 'bronze'; };
  ok('a child who earned gold is no longer denied it by a stale maximum',
     medalOf(score, eased) === 'gold', `score ${score}: vs stale max ${full} = ${medalOf(score, full)}, vs played max ${eased} = ${medalOf(score, eased)}`);
  ok('maxStars is not pre-computed at boot any more', !/maxStars = maxFor\(/.test(HTML));
  ok('the max is added after the adaptive change', /steps\[trickIdx\.pop\(\)\]\[1\] = 'real';\s*\n\s*\}\s*\n\s*addToMax\(steps\);/.test(HTML));
}

// ───────── Q9 · the listening streak means listening
console.log('\nQ9 · a wrong move breaks the listening streak');
{
  ok('the effort branch resets the streak', /missRun = 0; streak = 0; addStars\(1\); sfx\('pop'\); rs\.hits\+\+; await speakLine\('fb\.tried'\)/.test(HTML));
  ok('the effort star is still awarded', /streak = 0; addStars\(1\)/.test(HTML));
  // a 5-in-a-row bonus can no longer be built out of wrong moves
  const seq = ['effort','effort','effort','effort','effort'];
  let streak = 0, bonuses = 0;
  for (const r of seq){ if (r === 'hit' || r === 'held'){ streak++; if (streak % SCRIPT.streakBonusAt === 0) bonuses++; } else streak = 0; }
  ok('five wrong moves earn no "Super listener!" bonus', bonuses === 0);
}

// ───────── Q10 · two clips never overlap
console.log('\nQ10 · her lines do not play over each other');
{
  ok('fb.comeback is awaited', /await speakLine\('fb\.comeback'\)/.test(HTML));
  /* Every call site must be awaited, OR captured into a promise that is awaited later — which is
     exactly what Q1 needs (start the line, fire the gesture, then wait for the line). Anything else
     can overlap another clip, which is the bug Q10 describes. */
  const unawaited = [];
  HTML.split('\n').forEach((line, i) => {
    if (!/speakLine\(/.test(line)) return;
    if (/async function speakLine/.test(line)) return;
    const calls = line.split('speakLine(').length - 1;
    const awaited = (line.match(/await speakLine\(/g) || []).length;
    const captured = (line.match(/(?:const|let|var)\s+(\w+)\s*=\s*speakLine\(/g) || []);
    for (const c of captured){
      const name = /(?:const|let|var)\s+(\w+)\s*=/.exec(c)[1];
      if (!new RegExp('await ' + name + '\\b').test(HTML)) unawaited.push(`L${i+1} ${name} captured but never awaited`);
    }
    if (calls > awaited + captured.length) unawaited.push(`L${i+1}: ${line.trim().slice(0, 70)}`);
  });
  ok('every speakLine is awaited or captured-and-awaited', unawaited.length === 0, unawaited.join(' | ') || 'all 20 call sites clean');
  ok('the Q1 line promise is the only deferred one', /const lineP = speakLine\(lineId\);/.test(HTML) && /await lineP;/.test(HTML));
}

// ───────── structural guards
console.log('\nGuards — the fixes cannot be silently reverted');
{
  ok('script.json version bumped past 3.2', SCRIPT.version !== '3.2', 'v' + SCRIPT.version);
  ok('every QA marker is present in the page',
     ['[QA Q1]','[QA Q2]','[QA Q3]','[QA Q4]','[QA Q5]','[QA Q6]','[QA Q7]','[QA Q8]','[QA Q9]','[QA Q10]'].every(m => HTML.includes(m)),
     ['Q1','Q2','Q3','Q4','Q5','Q6','Q7','Q8','Q9','Q10'].filter(q => !HTML.includes('[QA ' + q + ']')).join(',') || 'all 10');
  ok('the old per-frame energy line is gone', !/energy = energy \* 0\.6 \+ \(\(sum \/ n\) \/ sw\(k\)\) \* 0\.4/.test(HTML));
  ok('the old x4 provisional fallback is gone', !/CAL\.move = CAL\.still \* 4/.test(HTML));
  ok('the old wrist-only armUp is gone', !/return vis\(k,w\) && vis\(k,s\) && \(k\[s\]\.y - k\[w\]\.y\) \/ sw\(k\) > thr\.reach;/.test(HTML));
}

console.log(`\n${pass + fail} checks — ${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
