// beta/novasays.js — NOVA SAYS game library (NOVA-SAYS.md §1-§4 · beta-b0.21-novasays).
// PURE logic only: the command library, round sequencer, boss-round parser, and scoring.
// The page (beta/novasays.html) supplies E/lights/voice; test/novasays_bench.js imports
// this file directly and drives it with synthetic poses + typed commands (EN+HE).
import { RULES } from '../shared/mover-rules.js';

// ── §1 THE COMMAND LIBRARY ──────────────────────────────────────────────────
// say = what she speaks (EN). sayHe = [CLI-FILL] Hebrew line (no spec source — drafted
// for the ?lang=he path, founder review before HE certification).
// demo = baked gesture id from STEP 0 inventory (2026-08-18 full avatar audit):
//   VERIFIED on the volume: gest_star, gest_lefthand, gest_righthand, gest_clap,
//   gest_bear, nova_wave_a. NOT baked (gest_head / gest_hips do not exist) → demo:null,
//   the command is SPOKEN + lit only — never a wrong body (NOVA-SAYS STEP 0).
// ctx = { audio, waveR, waveL } supplied by the page per frame.
export const CMDS = [
  { id:'armsUp',    say:'arms UP!',              sayHe:'ידיים למעלה!',        keys:['arms','both','ידיים'],                 rule:(E)=>RULES.armRaise(E)?.side==='BOTH'?{hit:true}:null,                 light:{joints:['lWrist','rWrist'],dir:'UP'},      demo:'gest_star' },
  { id:'leftUp',    say:'LEFT arm up!',          sayHe:'יד שמאל למעלה!',      keys:['left','שמאל'],                          rule:(E)=>['L','BOTH'].includes(RULES.armRaise(E)?.side)?{hit:true}:null,   light:{joints:['lWrist'],dir:'UP'},               demo:'gest_lefthand' },
  { id:'rightUp',   say:'RIGHT arm up!',         sayHe:'יד ימין למעלה!',      keys:['right','ימין'],                         rule:(E)=>['R','BOTH'].includes(RULES.armRaise(E)?.side)?{hit:true}:null,   light:{joints:['rWrist'],dir:'UP'},               demo:'gest_righthand' },
  { id:'clap',      say:'CLAP!',                 sayHe:'למחוא כפיים!',        keys:['clap','כפיים','כף'],                    rule:(E,ctx)=>RULES.clap(E, ctx?.audio?.lastOnset ?? null),                 light:'clap',                                      demo:'gest_clap' },
  { id:'head',      say:'hands on your HEAD!',   sayHe:'ידיים על הראש!',      keys:['head','ראש'],                           rule:(E)=>RULES.handsOnHead(E),                                             light:{joints:['head'],dir:null},                  demo:null, arm:true },
  { id:'hips',      say:'hands on your HIPS!',   sayHe:'ידיים על המותניים!',  keys:['hips','waist','מותניים','מותן'],        rule:(E)=>RULES.handsOnHips(E),                                             light:{joints:['lHip','rHip'],dir:null},           demo:null, arm:true },
  { id:'knees',     say:'touch your KNEES!',     sayHe:'לגעת בברכיים!',       keys:['knees','knee','ברכיים','ברך'],          rule:(E)=>RULES.touchKnees(E),                                              light:{joints:['lKnee','rKnee'],dir:'DOWN'},       demo:null, arm:true },
  { id:'freeze',    say:'FREEZE like a statue!', sayHe:'לקפוא כמו פסל!',      keys:['freeze','statue','פסל','לקפוא','קפאו'], rule:(E)=>RULES.freeze(E,0.12).still?{hit:true}:null,                       light:'ice',                                       demo:'gest_bear', hold:1.5 },
  { id:'jump',      say:'JUMP!',                 sayHe:'לקפוץ!',              keys:['jump','לקפוץ','קפצי','קפוץ','קפיצה'],   rule:(E)=>RULES.jump(E),                                                    light:{joints:['hipC'],dir:'UP'},                  demo:null },
  { id:'headSide',  say:'head side to side!',    sayHe:'ראש מצד לצד!',        keys:['side','מצד'],                           rule:(E)=>RULES.headSlide(E),                                               light:{joints:['head'],dir:'L'},                   demo:null },
  { id:'shoulders', say:'pop your SHOULDERS!',   sayHe:'להקפיץ כתפיים!',      keys:['shoulder','shoulders','כתפיים','כתף'],  rule:(E)=>RULES.shoulderPop(E),                                             light:{joints:['lShoulder','rShoulder'],dir:'UP'}, demo:null },
  { id:'wave',      say:'WAVE your arm!',        sayHe:'לנופף ביד!',          keys:['wave','לנופף','נפנוף'],                 rule:(E,ctx)=>(ctx?.waveR?.check()||ctx?.waveL?.check())?{hit:true}:null,   light:'comet',                                     demo:'nova_wave_a' },
];

// ── §2 ROUNDS + THE SEQUENCER ───────────────────────────────────────────────
export const ROUNDS = [
  { n:1, label:'ROUND 1 · SLOW',      count:8,  win:2.5, tricks:1, gap:1.2 },
  { n:2, label:'ROUND 2 · FASTER',    count:10, win:1.8, tricks:3, gap:0.9 },
  { n:3, label:"ROUND 3 · YOU'RE THE BOSS", boss:true, count:6 },                 // the kid calls, Nova performs
  { n:4, label:'ROUND 4 · LIGHTNING', count:12, win:1.2, tricks:6, gap:0.6 },
];

// rnd injectable so the bench is deterministic (defaults to Math.random in the page)
export function buildRound(R, rnd = Math.random) {
  const pool = CMDS;                                                    // spec: pool = the full library
  const seq = []; const trickSlots = new Set();
  while (trickSlots.size < (R.tricks || 0)) { const i = 1 + Math.floor(rnd() * (R.count - 1)); trickSlots.add(i); }   // never a trick first
  let last = null;
  for (let i = 0; i < R.count; i++) {
    let c; do { c = pool[Math.floor(rnd() * pool.length)]; } while (c === last); last = c;
    seq.push({ cmd: c, trick: trickSlots.has(i) });
  }
  return seq;
}

// ── §3 RESOLUTION + SCORING (pure — never negative, gotcha never minus) ─────
// Returns { event, pts, streak, fast } and NEVER a negative pts.
//   real+hit → 'hit' (10, +5 fast, hold-broke → 5, ×2 at streak≥5)
//   real+miss → 'miss' (0 — silence, no words)
//   trick+moved → 'gotcha' (0 — a laugh, never a penalty)
//   trick+held → 'trickHeld' (15, ×2 at streak≥5)
export function scoreStep(step, result, R, streak) {
  const c = step.cmd;
  if (!step.trick) {
    if (result?.hit) {
      const fast = result.ms < R.win * 400;
      let pts = 10 + (fast ? 5 : 0);
      if (c.hold && !result.held) pts = 5;
      streak++; if (streak >= 5) pts *= 2;
      return { event:'hit', pts, streak, fast };
    }
    return { event:'miss', pts:0, streak:0, fast:false };
  }
  if (result?.hit) return { event:'gotcha', pts:0, streak:0, fast:false };
  let pts = 15; streak++; if (streak >= 5) pts *= 2;
  return { event:'trickHeld', pts, streak, fast:false };
}

// endRound stars (spec §3): ★ ≥40%, ★★ ≥70%, ★★★ ≥90% of commands landed (hits + tricks held)
export function starsFor(stats, count) {
  const landed = (stats.hits + stats.trickHeld) / count;
  return landed >= 0.9 ? 3 : landed >= 0.7 ? 2 : landed >= 0.4 ? 1 : 0;
}

// ── §4 BOSS-ROUND PARSER — typed/spoken kid commands, EN+HE ─────────────────
// [CLI-FILL] match order is specific-first (left/right before arms, side before head)
// so "left arm up" never resolves to the generic armsUp entry.
// [CLI-FILL] ARM GATE (truth-gate): the proximity rules (head/hips/knees, arm:true) can be
// TRUE on a kid standing at rest — bench-measured resting wrist↔hip distance ≈0.10 < the spec
// threshold 0.14 — so a bare proximity hit would praise (or GOTCHA) a kid who never moved.
// The spec threshold is untouched; a hit just also needs one frame of real wrist motion first
// (mag > 0.8 body-units/s — the clap rule's own cited wrist-speed value).
export function makeArmGate(c) {
  if (!c.arm) return () => true;
  let armed = false;
  return E => {
    if (!armed) { const lm = E.last?.lWrist?.mag ?? 0, rm = E.last?.rWrist?.mag ?? 0; if (lm > 0.8 || rm > 0.8) armed = true; }
    return armed;
  };
}

const MATCH_ORDER = ['leftUp','rightUp','headSide','head','hips','knees','shoulders','clap','freeze','jump','wave','armsUp'];
export function parseCommand(text) {
  const t = (text || '').toLowerCase();
  if (!t.trim()) return null;
  const novaSays = /nova says|נובה אומרת/.test(t);
  for (const id of MATCH_ORDER) {
    const c = CMDS.find(x => x.id === id);
    if (c.keys.some(k => t.includes(k))) return { novaSays, cmd: c };
  }
  return null;
}
