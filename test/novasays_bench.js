#!/usr/bin/env node
// test/novasays_bench.js — NOVA-SAYS-V2 self-test harness (beta-b0.25-novasays2).
// No camera, no pod: synthetic poses through the real engines + typed boss commands EN+HE
// + the pure v2 library (chains, beat-scoring), plus static graders over the page source.
//   node test/novasays_bench.js
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { MoverEngine } from '../shared/mover-engine.js';
import { RULES } from '../shared/mover-rules.js';
import { CMDS, ROUNDS, buildRound, scoreStep, starsFor, parseCommand, clipName, ALL_CLIPS } from '../beta/novasays.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (cond, name, detail = '') => { if (cond) { pass++; console.log('  ✅ ' + name); } else { fail++; console.log('  ❌ ' + name + (detail ? ' — ' + detail : '')); } };

/* ── synthetic pose rig ── */
const V = 1;
const BASE = {
  nose: { x: .50, y: .20, vis: V },
  lShoulder: { x: .42, y: .35, vis: V }, rShoulder: { x: .58, y: .35, vis: V },
  lElbow: { x: .38, y: .50, vis: V }, rElbow: { x: .62, y: .50, vis: V },
  lWrist: { x: .35, y: .62, vis: V }, rWrist: { x: .65, y: .62, vis: V },
  lIndex: { x: .34, y: .66, vis: V }, rIndex: { x: .66, y: .66, vis: V },
  lHip: { x: .45, y: .62, vis: V }, rHip: { x: .55, y: .62, vis: V },
  lKnee: { x: .46, y: .80, vis: V }, rKnee: { x: .54, y: .80, vis: V },
};
const clone = o => JSON.parse(JSON.stringify(o));
const DT = 33;
function calibrated() {
  const E = new MoverEngine(); let t = 0;
  E.update(clone(BASE), t); t += DT;
  E.startCal();
  for (let i = 0; i < 40; i++) { const f = clone(BASE); for (const n of Object.keys(f)) { f[n].x += (Math.random() - .5) * .004; f[n].y += (Math.random() - .5) * .004; } E.update(f, t); t += DT; }
  E.finishCal();
  return { E, t };
}
function driveTo(targets, { ramp = 6, hold = 8 } = {}) {
  const { E, t } = calibrated(); let tt = t;
  for (let i = 0; i < ramp + hold; i++) {
    const f = clone(BASE), p = Math.min(1, i / ramp);
    for (const [n, tgt] of Object.entries(targets)) { f[n].x = BASE[n].x + (tgt.x - BASE[n].x) * p; f[n].y = BASE[n].y + (tgt.y - BASE[n].y) * p; }
    E.update(f, tt); tt += DT;
  }
  return E;
}

console.log('\n── 1 · the 7 v2 rules on synthetic poses ──');
{
  const E = driveTo({ lWrist:{x:.40,y:.18}, rWrist:{x:.60,y:.18}, lIndex:{x:.40,y:.14}, rIndex:{x:.60,y:.14} });
  ok(CMDS[0].rule(E)?.hit === true, 'armsUp fires on both-arms-up');
}
{
  const E = driveTo({ lWrist:{x:.38,y:.18}, lIndex:{x:.38,y:.14} });
  ok(CMDS[1].rule(E)?.hit === true, 'leftUp fires on left-arm-up');
  ok(CMDS[2].rule(E) == null, 'rightUp stays null on left-arm-up');
}
{
  // head: proximity + IN-RULE motion gate (v2 spec: E.last.lWrist.mag>0.3)
  const { E, t } = calibrated(); let tt = t;
  for (let i = 0; i < 6; i++) { const f = clone(BASE), p = (i + 1) / 6;                        // fast ramp → mag high on arrival
    f.lWrist = { x:.35 + (.47 - .35) * p, y:.62 + (.22 - .62) * p, vis:V }; f.rWrist = { x:.65 + (.53 - .65) * p, y:.62 + (.22 - .62) * p, vis:V };
    E.update(f, tt); tt += DT; }
  const headCmd = CMDS.find(c => c.id === 'head');
  ok(headCmd.rule(E)?.hit === true, 'head fires on a MOVING hands-to-head');
  const Erest = driveTo({ lWrist:{x:.47,y:.22}, rWrist:{x:.53,y:.22} }, { hold: 20 });         // long settle → mag ≈ 0
  ok(headCmd.rule(Erest) == null, 'head does NOT fire once still (motion gate in the rule)');
}
{
  const E = driveTo({});                                                                       // neutral
  for (const c of CMDS) ok(c.id === 'freeze' ? c.rule(E)?.hit === true : !c.rule(E, { audio:{ lastOnset:null } })?.hit, `${c.id}: ${c.id === 'freeze' ? 'fires when still (stillness IS the move)' : 'stays null on neutral'}`);
}

console.log('\n── 2 · sequencer invariants ×200 (tricks, chains, repeats) ──');
for (const R of ROUNDS.filter(r => !r.boss)) {
  let lenOK = true, trickOK = true, firstOK = true, repeatOK = true, chainOK = true;
  for (let i = 0; i < 200; i++) {
    const seq = buildRound(R);
    if (seq.length !== R.count) lenOK = false;
    if (seq.filter(s => s.trick).length !== R.tricks) trickOK = false;
    if (seq[0].trick) firstOK = false;
    for (let j = 1; j < seq.length; j++) if (seq[j].cmd === seq[j - 1].cmd) repeatOK = false;
    const chains = seq.filter(s => s.chain);
    if (chains.length > (R.chains || 0)) chainOK = false;
    for (const s of chains) if (s.trick || s.chain.id === 'freeze' || s.chain === s.cmd) chainOK = false;
    if (chains.length && seq.findIndex(s => s.chain) <= 2) chainOK = false;                    // never before i>2
  }
  ok(lenOK, `R${R.n}: ${R.count} commands`); ok(trickOK, `R${R.n}: exactly ${R.tricks} tricks`);
  ok(firstOK, `R${R.n}: never a trick first`); ok(repeatOK, `R${R.n}: no immediate repeats`);
  ok(chainOK, `R${R.n}: chains ≤${R.chains || 0}, never on tricks/freeze/self/early`);
}

console.log('\n── 3 · v2 scoring — chains, holds, never negative ──');
{
  const c = CMDS[0], hold = CMDS.find(x => x.hold), chain = CMDS[3];
  const span = 3000;
  ok(scoreStep({ cmd:c, trick:false }, { hit:true, ms:2000 }, span, 0).pts === 10, 'plain hit = 10');
  ok(scoreStep({ cmd:c, trick:false }, { hit:true, ms:1000 }, span, 0).pts === 15, 'fast hit (<40% span) = 15');
  ok(scoreStep({ cmd:hold, trick:false }, { hit:true, ms:2000, held:false }, span, 0).pts === 5, 'froze but wiggled = 5');
  ok(scoreStep({ cmd:c, trick:false, chain }, { hit:true, ms:2000, chainDone:true }, span, 0).pts === 20, 'chain both moves = ×2 (20)');
  ok(scoreStep({ cmd:c, trick:false, chain }, { hit:true, ms:2000, chainDone:false }, span, 0).pts === 5, 'chain half = /2 (5)');
  ok(scoreStep({ cmd:c, trick:false, chain }, { hit:true, ms:1000, chainDone:true }, span, 4).pts === 60, 'fast+chain+streak5 = 15×2×2 = 60');
  ok(scoreStep({ cmd:c, trick:false }, null, span, 7).pts === 0 && scoreStep({ cmd:c, trick:false }, null, span, 7).streak === 0, 'miss = 0, streak resets');
  ok(scoreStep({ cmd:c, trick:true }, { hit:true, ms:100 }, span, 7).pts === 0, 'GOTCHA = 0 — never minus');
  ok(scoreStep({ cmd:c, trick:true }, null, span, 0).pts === 15, 'trick held = 15');
  ok(scoreStep({ cmd:c, trick:true }, null, span, 4).pts === 30, 'trick held doubles at streak≥5');
  let neverNeg = true;
  for (let i = 0; i < 2000; i++) {
    const step = { cmd: CMDS[i % CMDS.length], trick: Math.random() < .4, chain: Math.random() < .2 ? CMDS[3] : null };
    const r = Math.random() < .5 ? null : { hit:true, ms: Math.random() * 4000, held: Math.random() < .5, chainDone: Math.random() < .5 };
    if (scoreStep(step, r, 2000 + Math.random() * 2000, Math.floor(Math.random() * 8)).pts < 0) neverNeg = false;
  }
  ok(neverNeg, 'fuzz ×2000: pts ≥ 0 on every path');
  ok(starsFor({ hits:8, trickHeld:0 }, 8) === 3 && starsFor({ hits:5, trickHeld:1 }, 8) === 2 && starsFor({ hits:3, trickHeld:1 }, 8) === 1 && starsFor({ hits:1, trickHeld:0 }, 8) === 0, 'stars bands 40/70/90');
}

console.log('\n── 4 · boss round — typed commands EN + HE (7-command parser) ──');
{
  const cases = [
    ['Nova says arms up', 'armsUp', true], ['left arm up', 'leftUp', false],
    ['nova says RIGHT arm up', 'rightUp', true], ['nova says clap', 'clap', true],
    ['hands on your head', 'head', false], ['freeze like a statue', 'freeze', false],
    ['nova says jump', 'jump', true],
    ['נובה אומרת לקפוץ', 'jump', true], ['ידיים על הראש', 'head', false],
    ['נובה אומרת ידיים למעלה', 'armsUp', true], ['נובה אומרת קפוא', 'freeze', true],
    ['יד שמאל למעלה', 'leftUp', false], ['נובה אומרת מחיאת כף', 'clap', true],
  ];
  for (const [text, id, ns] of cases) {
    const p = parseCommand(text);
    ok(p && p.cmd.id === id && p.novaSays === ns, `"${text}" → ${id}${ns ? ' (nova says)' : ''}`, p ? `got ${p.cmd.id}/${p.novaSays}` : 'got null');
  }
  ok(parseCommand('make me a sandwich') === null, 'unknown → null');
}

console.log('\n── 5 · STEP-0: clips + gesture map ──');
{
  ok(ALL_CLIPS.length === 31, '31 clips defined (28 command + 2 gotcha + giggle)', String(ALL_CLIPS.length));
  ok(clipName({ cmd: CMDS[0], trick:false }, 'en') === 'armsUp_real_en.mp3' && clipName({ cmd: CMDS[4], trick:true }, 'he') === 'freeze_trick_he.mp3', 'clip naming matches audio/says/ layout');
  const missing = ALL_CLIPS.filter(n => { try { readFileSync(join(ROOT, 'audio', 'says', n)); return false; } catch { return true; } });
  ok(missing.length === 0, 'all 31 clips exist in audio/says/', missing.join(','));
  const VERIFIED = ['gest_star','gest_lefthand','gest_righthand','gest_clap','gest_bear'];   // 2026-09-11 LIVE volume ls
  ok(CMDS.filter(c => c.demo).every(c => VERIFIED.includes(c.demo)), 'every demo id is a live-verified bake');
  ok(CMDS.filter(c => ['jump','head'].includes(c.id)).every(c => !c.demo), 'jump + head are body-only (demo:null)');
}

console.log('\n── 6 · static graders over the page (v2 identity + kids law) ──');
{
  const page = readFileSync(join(ROOT, 'beta', 'novasays.html'), 'utf8');
  ok(!page.includes('/freezegame/'), 'IDENTITY §8: zero /freezegame/ references (grep-proof)');
  ok(page.includes('SneakyBed') && page.includes('bed.nextBarStart'), 'commands ride the SneakyBed bar grid');
  ok(page.includes('actx.currentTime'), 'clock law: scheduling off the WebAudio clock');
  ok(page.includes('if (!step.trick && c.demo) playGesture(c.demo'), 'demo fires only on real commands');
  ok(page.includes('if (!step.trick) scheduleAt(at + bed.beat, () => lightFor('), 'tricks are UNLIT (light behind !trick guard)');
  ok(page.includes('gotchaRipple') && page.includes("play(clips['giggle.mp3'])"), 'GOTCHA = purple ripple + pre-recorded giggle+line');
  ok(page.includes("setBody(BODY.groove)") && page.includes("groove:'nova_idlegroove_v2'"), '§5: she GROOVES the whole round (never a statue)');
  ok(page.includes('missing voice clip') && page.includes('missing avatar bake'), 'red banners: missing clip OR bake = refuse to start');
  ok(page.includes("routeVoice('mute')") && page.includes("routeVoice('air')") && page.includes("routeVoice('engine')"), 'phase machine routes voice');
  ok(page.includes('bossRound') && page.includes('parseCommand'), 'boss round (live V2V) present');
  ok(page.includes("pulseSend({ game:'novasays2'"), 'PULSE at the finale');
  ok(page.includes('QUICK!'), 'fast hits fly QUICK!');
  const lines = [...page.matchAll(/sayLive\((?:HE \? '[^']*' : )?"([^"]+)"/g)].map(m => m[1]);
  const ALLOW = ["You didn't say Nova says", "don't know that one"];
  const negs = lines.filter(l => /\b(wrong|bad|missed|failed|no!)\b/i.test(l) && !ALLOW.some(a => l.includes(a)));
  ok(negs.length === 0, 'no negative words at the kid in live lines', negs.join(' | '));
}

console.log(`\n══ novasays_bench (v2): ${pass} passed, ${fail} failed ══`);
process.exit(fail ? 1 : 0);
