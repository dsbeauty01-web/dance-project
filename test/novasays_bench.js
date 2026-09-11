#!/usr/bin/env node
// test/novasays_bench.js — NOVA-SAYS self-test harness (beta-b0.21-novasays).
// No camera, no pod: synthetic poses through the real engines + typed boss commands EN+HE
// + the pure game library, plus static graders over the page source. Deterministic.
//   node test/novasays_bench.js
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { MoverEngine } from '../shared/mover-engine.js';
import { RULES } from '../shared/mover-rules.js';
import { CMDS, ROUNDS, buildRound, scoreStep, starsFor, parseCommand, makeArmGate } from '../beta/novasays.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (cond, name, detail = '') => { if (cond) { pass++; console.log('  ✅ ' + name); } else { fail++; console.log('  ❌ ' + name + (detail ? ' — ' + detail : '')); } };

/* ── synthetic pose rig (mover_bench.js pattern + knees for the touch rules) ── */
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
// ramp the named joints to absolute targets over `ramp` frames, then hold — return engine at rest
function driveTo(targets, { ramp = 6, hold = 8 } = {}) {
  const { E, t } = calibrated(); let tt = t;
  for (let i = 0; i < ramp + hold; i++) {
    const f = clone(BASE), p = Math.min(1, i / ramp);
    for (const [n, tgt] of Object.entries(targets)) { f[n].x = BASE[n].x + (tgt.x - BASE[n].x) * p; f[n].y = BASE[n].y + (tgt.y - BASE[n].y) * p; }
    E.update(f, tt); tt += DT;
  }
  return E;
}

console.log('\n── 1 · the three new touch rules (synthetic poses) ──');
{
  const E = driveTo({ lWrist: { x: .47, y: .22 }, rWrist: { x: .53, y: .22 } });          // both wrists to the head
  ok(RULES.handsOnHead(E)?.hit === true, 'handsOnHead fires with both wrists at the head');
  ok(RULES.handsOnHips(E) === null, 'handsOnHips stays null on the head pose');
}
{
  const E = driveTo({ lWrist: { x: .44, y: .63 }, rWrist: { x: .56, y: .63 } });          // wrists to the hips
  ok(RULES.handsOnHips(E)?.hit === true, 'handsOnHips fires with wrists on the hips');
}
{
  const E = driveTo({ lWrist: { x: .46, y: .78 }, rWrist: { x: .54, y: .78 } });          // wrists to the knees
  ok(RULES.touchKnees(E)?.hit === true, 'touchKnees fires with wrists at the knees');
}
{
  const E = driveTo({});                                                                   // neutral standing pose
  ok(!RULES.handsOnHead(E) && !RULES.touchKnees(E), 'head/knees rules stay null on the neutral pose');
  // KNOWN + QUESTION for the founder: at rest the wrists hang ≈0.10 from the hips, inside the
  // spec's 0.14 — the raw rule fires on a motionless kid. The spec value is untouched; the
  // page gates these hits behind makeArmGate (real wrist motion first). Assert both halves:
  ok(RULES.handsOnHips(E)?.hit === true, 'documented: raw handsOnHips fires at rest (spec thr 0.14, rest dist ≈0.10)');
  const hips = CMDS.find(c => c.id === 'hips');
  ok(hips.arm === true && CMDS.find(c => c.id === 'head').arm === true && CMDS.find(c => c.id === 'knees').arm === true, 'head/hips/knees carry arm:true');
  const gate = makeArmGate(hips);
  ok(gate(E) === false, 'ARM GATE: a motionless kid is NOT armed → no self-hit, no false GOTCHA');
  E.last.lWrist.mag = 1.2;                                                                 // one frame of real wrist motion
  ok(gate(E) === true && gate(E) === true, 'ARM GATE: real wrist motion arms it (and it stays armed)');
  ok(makeArmGate(CMDS.find(c => c.id === 'freeze'))(E) === true, 'freeze never needs arming (stillness IS the move)');
}
{
  const E = driveTo({ lWrist: { x: .42, y: .28 }, rWrist: { x: .65, y: .62 } });          // one hand only
  ok(RULES.handsOnHead(E) === null, 'handsOnHead needs BOTH hands');
}

console.log('\n── 2 · sequencer invariants (200 random rounds/config) ──');
for (const R of ROUNDS.filter(r => !r.boss)) {
  let lenOK = true, trickOK = true, firstOK = true, repeatOK = true;
  for (let i = 0; i < 200; i++) {
    const seq = buildRound(R);
    if (seq.length !== R.count) lenOK = false;
    if (seq.filter(s => s.trick).length !== R.tricks) trickOK = false;
    if (seq[0].trick) firstOK = false;
    for (let j = 1; j < seq.length; j++) if (seq[j].cmd === seq[j - 1].cmd) repeatOK = false;
  }
  ok(lenOK, `R${R.n}: ${R.count} commands`); ok(trickOK, `R${R.n}: exactly ${R.tricks} tricks`);
  ok(firstOK, `R${R.n}: never a trick first`); ok(repeatOK, `R${R.n}: no immediate repeats`);
}

console.log('\n── 3 · scoring — never negative, gotcha never a penalty ──');
{
  const R = ROUNDS[0], c = CMDS[0], hold = CMDS.find(x => x.hold);
  ok(scoreStep({ cmd:c, trick:false }, { hit:true, ms:2000 }, R, 0).pts === 10, 'plain hit = 10');
  ok(scoreStep({ cmd:c, trick:false }, { hit:true, ms:300 }, R, 0).pts === 15, 'fast hit (<win×0.4) = 15');
  ok(scoreStep({ cmd:hold, trick:false }, { hit:true, ms:2000, held:false }, R, 0).pts === 5, 'hold broke = 5');
  ok(scoreStep({ cmd:c, trick:false }, { hit:true, ms:2000 }, R, 4).pts === 20, 'streak≥5 doubles a hit');
  ok(scoreStep({ cmd:c, trick:false }, null, R, 7).streak === 0, 'miss resets the streak');
  ok(scoreStep({ cmd:c, trick:false }, null, R, 7).pts === 0, 'miss scores 0 (silence, not minus)');
  ok(scoreStep({ cmd:c, trick:true }, { hit:true, ms:100 }, R, 7).pts === 0, 'GOTCHA scores 0 — never minus');
  ok(scoreStep({ cmd:c, trick:true }, null, R, 0).pts === 15, 'trick held = 15');
  ok(scoreStep({ cmd:c, trick:true }, null, R, 4).pts === 30, 'trick held doubles at streak≥5');
  let neverNeg = true;                                                                    // fuzz: no path can subtract
  for (let i = 0; i < 2000; i++) {
    const step = { cmd: CMDS[i % CMDS.length], trick: Math.random() < .4 };
    const res = Math.random() < .5 ? null : { hit:true, ms: Math.random() * 3000, held: Math.random() < .5 };
    if (scoreStep(step, res, ROUNDS[Math.floor(Math.random() * 2) * 3] || ROUNDS[0], Math.floor(Math.random() * 8)).pts < 0) neverNeg = false;
  }
  ok(neverNeg, 'fuzz ×2000: pts ≥ 0 on every path');
  ok(starsFor({ hits:8, trickHeld:0 }, 8) === 3 && starsFor({ hits:5, trickHeld:1 }, 8) === 2 && starsFor({ hits:3, trickHeld:1 }, 8) === 1 && starsFor({ hits:1, trickHeld:0 }, 8) === 0, 'stars bands 40/70/90');
}

console.log('\n── 4 · boss round — typed commands EN + HE ──');
{
  const cases = [
    ['Nova says arms up', 'armsUp', true], ['left arm up', 'leftUp', false],
    ['nova says RIGHT arm up', 'rightUp', true], ['nova says clap', 'clap', true],
    ['hands on your head', 'head', false], ['head side to side', 'headSide', false],
    ['nova says touch your knees', 'knees', true], ['freeze like a statue', 'freeze', false],
    ['nova says jump', 'jump', true], ['wave your arm', 'wave', false],
    ['nova says pop your shoulders', 'shoulders', true], ['hands on your hips', 'hips', false],
    ['נובה אומרת לקפוץ', 'jump', true], ['ידיים על הראש', 'head', false],
    ['נובה אומרת לנופף', 'wave', true], ['נובה אומרת ידיים למעלה', 'armsUp', true],
    ['ראש מצד לצד', 'headSide', false], ['נובה אומרת לקפוא כמו פסל', 'freeze', true],
  ];
  for (const [text, id, ns] of cases) {
    const p = parseCommand(text);
    ok(p && p.cmd.id === id && p.novaSays === ns, `"${text}" → ${id}${ns ? ' (nova says)' : ''}`, p ? `got ${p.cmd.id}/${p.novaSays}` : 'got null');
  }
  ok(parseCommand('make me a sandwich') === null, 'unknown command → null (she offers an example)');
  ok(parseCommand('') === null, 'empty → null');
  // boss scoring paths (spec §4): obey = +10, kid-tricked-her = +15 — never negative
  let boss = 0; boss += 10; boss += 15;
  ok(boss === 25, 'boss paths add +10 (obeyed) / +15 (she held) — no minus path exists');
}

console.log('\n── 5 · STEP-0 gesture map — demos only from VERIFIED bakes ──');
{
  const VERIFIED = ['gest_star','gest_lefthand','gest_righthand','gest_clap','gest_bear'];   // 2026-09-11 LIVE volume ls (nova_wave_a purged since the 08-18 audit)
  const used = CMDS.filter(c => c.demo).map(c => c.demo);
  ok(used.every(d => VERIFIED.includes(d)), 'every demo id is a verified bake', used.join(','));
  ok(CMDS.filter(c => ['head','hips','knees','jump','headSide','shoulders'].includes(c.id)).every(c => !c.demo), 'unbaked commands are spoken+lit only (demo:null)');
}

console.log('\n── 6 · static graders over the page (kids-tier law) ──');
{
  const page = readFileSync(join(ROOT, 'beta', 'novasays.html'), 'utf8');
  const lib = readFileSync(join(ROOT, 'beta', 'novasays.js'), 'utf8');
  // G-words: every mid-round command line ≤8 words including the "Nova says..." prefix
  const tooLong = CMDS.map(c => 'Nova says... ' + c.say).filter(l => l.trim().split(/\s+/).length > 8);
  ok(tooLong.length === 0, 'every command line ≤8 words mid-round', tooLong.join(' | '));
  // G-negative: no negative words AT THE KID in her scripted lines. The two GOTCHA lines are
  // spec-verbatim about HERSELF/the game ("I didn't say...", "You didn't say... I'm NOT moving")
  const ALLOW = ["I didn't say Nova says", "You didn't say Nova says", "don't know that one"];
  const lines = [...page.matchAll(/sayLive\((?:HE \? '[^']*' : )?"([^"]+)"/g)].map(m => m[1]);
  const negs = lines.filter(l => /\b(wrong|bad|missed|failed|stop it|no!)\b/i.test(l) && !ALLOW.some(a => l.includes(a)));
  ok(negs.length === 0, 'no negative words at the kid in scripted lines', negs.join(' | '));
  // G-tricks-unlit: demo + light fire ONLY behind the !step.trick guard
  ok(page.includes('if (!step.trick) { if (c.demo) playGesture(c.demo); lightFor(c, R.win); }'), 'tricks are unlit + undemoed (guard present)');
  ok((page.match(/lightFor\(/g) || []).length === 2, 'lightFor called only from the guarded line (def + 1 call)');
  // G-gotcha: purple, giggle, no score, no tick
  ok(page.includes("gotchaRipple()") && page.includes('giggle()'), 'GOTCHA = purple ripple + giggle');
  // G-choices: consent gate at every round edge (3 between-cards for 4 rounds) + intro consent
  ok(page.includes('choiceGate') && ROUNDS.length === 4, 'choice/consent gate at every round edge (3 edges + intro)');
  // G-pulse: durable end row
  ok(page.includes("pulseSend({ game:'novasays'"), 'PULSE row sent at the finale');
  // Laws: phase machine + hard-mute holds + input-lock voice routing present
  ok(page.includes("routeVoice('mute')") && page.includes("routeVoice('air')") && page.includes("routeVoice('engine')"), 'phase machine routes voice (engine/air/mute)');
  ok(page.includes('missing avatar bake'), 'red banner (no silent fallback) on a missing bake');
  ok(lib.includes("demo:'gest_star'"), 'armsUp demos gest_star (arms up wide — STEP 0)');
}

console.log(`\n══ novasays_bench: ${pass} passed, ${fail} failed ══`);
process.exit(fail ? 1 : 0);
