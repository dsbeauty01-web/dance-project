# NOVA-SAYS — the complete game (from scratch · engines + gesture bank + live V2V · full code · CLI builds, never guesses)

Kids tier. Command-driven (no music clock) with a soft music bed. Beta only: `beta/novasays.html`, pod route `/beta/novasays`. Tag `beta-b0.21-novasays`. Template skeleton = `beta/wave.html` (stage, phase machine, pose loop, HUD, gate, pause/exit, PULSE) — change only what's written here. Read the 4 skills first. Laws: INPUT-LOCK, live-V2V voice only, truth-gate, body map, never negative, one CLI on this page.

## THE GAME
"Nova says arms UP!" → do it. "Clap!" (no "Nova says") → DON'T. Move on a trick = **GOTCHA** ("I didn't say Nova says!") — playful, never a penalty. She DEMONSTRATES every real command with her baked gesture; tricks she only SAYS (no gesture, no light) — the kid must listen.

## STEP 0 — GESTURE INVENTORY (before code)
`ls /workspace/LiveTalking/data/avatars` + the registry → map each command to a VERIFIED baked gesture id. Known candidates: `gest_star` (arms up wide), `gest_bear`, `gest_flamingo`, `gest_frog`, `nova_wave_a` (wave), the GESTURE-BAKE set if baked (hello/lefthand/righthand/point/bothhands/goodbye → ids per registry). Paste the map. Missing gesture → the command is SPOKEN + lit only (`demo:null`), never a wrong body. Talking body = `nova_idle2`.

## 1 · THE COMMAND LIBRARY (rules exist in mover-rules.js; two small ones added here)
```js
// add to mover-rules.js RULES:
handsOnHead: E => { const l=E.dist('lWrist','head'), r=E.dist('rWrist','head'); return (l!=null&&r!=null&&l<0.18&&r<0.18) ? {hit:true} : null; },
handsOnHips: E => { const l=E.dist('lWrist','lHip'), r=E.dist('rWrist','rHip'); return (l!=null&&r!=null&&l<0.14&&r<0.14) ? {hit:true} : null; },
touchKnees:  E => { const l=E.dist('lWrist','lKnee'), r=E.dist('rWrist','rKnee'); return (l!=null&&r!=null&&l<0.16&&r<0.16) ? {hit:true} : null; },
```
```js
// beta/novasays.js — the library. say = what she speaks (EN; HE via the translation layer). demo = baked gesture id from STEP 0.
const CMDS = [
  { id:'armsUp',    say:'arms UP!',              rule:E=>RULES.armRaise(E)?.side==='BOTH'?{hit:true}:null, light:{joints:['lWrist','rWrist'],dir:'UP'}, demo:'gest_star' },
  { id:'leftUp',    say:'LEFT arm up!',          rule:E=>['L','BOTH'].includes(RULES.armRaise(E)?.side)?{hit:true}:null, light:{joints:['lWrist'],dir:'UP'}, demo:'gest_lefthand' },
  { id:'rightUp',   say:'RIGHT arm up!',         rule:E=>['R','BOTH'].includes(RULES.armRaise(E)?.side)?{hit:true}:null, light:{joints:['rWrist'],dir:'UP'}, demo:'gest_righthand' },
  { id:'clap',      say:'CLAP!',                 rule:E=>RULES.clap(E, audio.lastOnset), light:'clap', demo:'gest_clap' },
  { id:'head',      say:'hands on your HEAD!',   rule:RULES.handsOnHead, light:{joints:['head'],dir:null}, demo:'gest_head' },
  { id:'hips',      say:'hands on your HIPS!',   rule:RULES.handsOnHips, light:{joints:['lHip','rHip'],dir:null}, demo:'gest_hips' },
  { id:'knees',     say:'touch your KNEES!',     rule:RULES.touchKnees,  light:{joints:['lKnee','rKnee'],dir:'DOWN'}, demo:null },
  { id:'freeze',    say:'FREEZE like a statue!', rule:E=>RULES.freeze(E,0.12).still?{hit:true}:null, light:'ice', demo:'gest_bear', hold:1.5 },
  { id:'jump',      say:'JUMP!',                 rule:RULES.jump,        light:{joints:['hipC'],dir:'UP'}, demo:null },
  { id:'headSide',  say:'head side to side!',    rule:RULES.headSlide,   light:{joints:['head'],dir:'L'}, demo:null },
  { id:'shoulders', say:'pop your SHOULDERS!',   rule:RULES.shoulderPop, light:{joints:['lShoulder','rShoulder'],dir:'UP'}, demo:null },
  { id:'wave',      say:'WAVE your arm!',        rule:E=>waveR.check()||waveL.check(), light:'comet', demo:'nova_wave_a' },
];
```
Mirror: sides are camera-space in the engine; screen-space flip once (`MIRROR`) as in Wave.

## 2 · ROUNDS + THE SEQUENCER
```js
const ROUNDS = [
  { n:1, label:'ROUND 1 · SLOW',      count:8,  win:2.5, tricks:1, gap:1.2 },
  { n:2, label:'ROUND 2 · FASTER',    count:10, win:1.8, tricks:3, gap:0.9 },
  { n:3, label:"ROUND 3 · YOU'RE THE BOSS", boss:true, count:6 },                 // the kid calls, Nova performs
  { n:4, label:'ROUND 4 · LIGHTNING', count:12, win:1.2, tricks:6, gap:0.6 },
];
function buildRound(R){ const pool=CMDS.filter(c=>c.demo||true); const seq=[]; const trickSlots=new Set();
  while(trickSlots.size<R.tricks){ const i=1+Math.floor(Math.random()*(R.count-1)); trickSlots.add(i); }   // never a trick first
  let last=null; for(let i=0;i<R.count;i++){ let c; do{ c=pool[Math.floor(Math.random()*pool.length)]; } while(c===last); last=c;
    seq.push({ cmd:c, trick:trickSlots.has(i) }); } return seq; }
```
```js
// the loop — one command at a time, command-driven clock (no music timeline)
async function playRound(R){
  hud.tag(R.label); roundStats={hits:0,trickHeld:0,gotcha:0,perfect:0};
  if (R.boss) return bossRound(R);
  const seq=buildRound(R);
  for (const step of seq){
    const c=step.cmd, line = step.trick ? c.say : `Nova says... ${c.say}`;
    await sayLive(line);                                                          // live V2V via note: "say exactly: …" — her voice in the air (routeVoice air)
    if (!step.trick){ if (c.demo) playGesture(c.demo); lightFor(c, R.win); }        // real command: she DEMOS it + the light shows the target
    const t0=performance.now(); let result=null;
    while (performance.now()-t0 < R.win*1000){ await nextPoseFrame(); const r=c.rule(E);
      if (r?.hit){ result = { hit:true, ms:performance.now()-t0 }; break; } }
    if (c.hold && result?.hit){ result.held = await holdStill(c.hold); }
    resolve(step, result, R); L.clearAll(); if (c.demo) returnToTalkBody();
    await sleep(R.gap*1000);
  }
  endRound(R);
}
```

## 3 · RESOLUTION + SCORING (never negative)
```js
function resolve(step, result, R){
  const c=step.cmd;
  if (!step.trick){
    if (result?.hit){ const fast = result.ms < R.win*400; let pts = 10 + (fast?5:0); if (c.hold && !result.held) pts=5;
      streak++; if (streak>=5) pts*=2; score+=pts; roundStats.hits++; if(fast) roundStats.perfect++;
      lightHit(c, pts); tick(streak); note(`fact: ${c.id} hit ${fast?'fast':'ok'} streak ${streak}`); }
    else { streak=0; L.softFade(); note(`fact: ${c.id} missed`); }                     // silence — no words on a miss
  } else {
    if (result?.hit){ streak=0; roundStats.gotcha++; L.gotchaRipple(); audio.giggle(); sayLive("GOTCHA! I didn't say Nova says!"); }
    else { let pts=15; streak++; if(streak>=5) pts*=2; score+=pts; roundStats.trickHeld++; L.flyUp(L.P('head'),'SNEAKY!'); tick(streak); note(`fact: trick held streak ${streak}`); }
  }
  hud.score(score);
}
// gotchaRipple: a playful purple ring (#b98cff) expanding from the chest, 500ms — not gold (gold = you did well), never red.
// endRound: stars = hits/count (★ ≥40%, ★★ ≥70%, ★★★ ≥90% incl. tricks held); between-rounds coaching from roundStats (lips on nova_idle2): "you caught «trickHeld» of my tricks!" + one next-cue + "ready for round «n»?" (consent gate).
```

## 4 · ROUND 3 — YOU'RE THE BOSS (the reverse game)
```js
async function bossRound(R){
  setPhase('boss');                                                                 // engine path, lips ON (she's the performer now), routeVoice('engine')
  await sayLive("YOUR turn to be the boss! Tell ME what to do — say 'Nova says' if you mean it!");
  for (let i=0;i<R.count;i++){
    const turn = await waitKidCommand(8000);                                       // validated kid-turn (INPUT-LOCK) → transcript
    if (!turn){ await sayLive('Take your time, boss.'); continue; }                 // one re-invite max, then next
    const parsed = parseCommand(turn.text);                                         // matches CMDS by keywords (arms/up/clap/head/hips/knees/freeze/jump/wave/shoulder) + detects "nova says"
    if (!parsed){ await sayLive("Ooh, I don't know that one — try 'Nova says jump'!"); continue; }
    if (parsed.novaSays){ await sayLive(`Nova says ${parsed.cmd.say} — okay!`); if (parsed.cmd.demo) await playGestureFull(parsed.cmd.demo); score+=10; L.hit('shoulderC','good',10); }
    else { await sayLive("You didn't say Nova says — I'm NOT moving! Ha!"); L.gotchaRipple(); score+=15; L.flyUp(L.P('head'),'BOSS!'); }   // the kid tricked HER → she stays still → the kid wins points
    hud.score(score);
  }
  endRound(R);
}
// parseCommand: lowercase; novaSays = /nova says|נובה אומרת/; cmd = first CMDS entry whose keyword list matches (add `keys:['arms','up',…]` per command; HE keys too).
```

## 5 · BODY + LIGHTS + AUDIO
- **Body map:** talk = `nova_idle2` (lips); real command = the mapped gesture via `engineSwitchAvatar(demo)` for its clip length then back to idle2; tricks = idle2 only (no demo). Boss round = idle2 + full gesture on obeyed commands.
- **Lights:** `lightFor(c)` → orb+ring on the target joints (kids tier), `'clap'` → `L.clapCue`, `'ice'` → `L.freezeStart(hold)`, `'comet'` → `L.cometCue(chain)`. Hits → `L.hit` / `clapHit` / `freezeEnd(true)` / `cometHit`. Tricks → NO light (listen, don't watch). GOTCHA → `gotchaRipple()`. Add `gotchaRipple`, `softFade`, `clearAll` to the light engine (owner: the lights CLI — request via CHANGELOG if not this session).
- **Audio:** soft music bed (repo: pick a calm loop from `freezegame/` or `/media`, volume 0.35, ducks to 0.2 when she speaks); tick pitch by streak; giggle sfx on GOTCHA (short, warm); ding on round end.
- **Presence gate before round 1:** shoulders+wrists visible ≥1s ("step back — I need your arms").

## 6 · VOICE + BRAIN (kids tier)
Prompt block: TIERS.kids.voicePrompt + "You are Nova playing NOVA SAYS. You are SNEAKY and delighted. Say exactly the command lines you're given — 'Nova says…' for real ones, bare commands for tricks, same cheeky energy for both so nobody can tell. GOTCHA is a laugh WITH the kid, never a scold. Between rounds: one fact ('you caught 3 of my tricks!'), one next-cue, one 'ready?'. Max 8 words mid-round."
Intro (lips): "I'm Nova, and I'm SNEAKY — only move when I say NOVA SAYS! Ready?" → consent → round 1. Ending trio from real numbers (hits, tricks caught, best round, score) + "did you have fun? tell me anything!" + named goodbye + PULSE.

## 7 · HUD + LAYOUT
Her 60 / kid 40 (wave.html layout), round dots ×4, score, a "tricks caught" counter with a 🕵️ icon, stars per round card, scorecard finale with PLAY AGAIN. Kids tier full gold; GOTCHA purple; nothing red.

## GATE + EVIDENCE
Gesture map pasted (STEP 0) → self-test all 4 rounds via harness (synthetic poses + typed boss commands EN+HE) → graders (kids: ≤8 words, negatives 0, tricks unlit, gotcha never scored minus, choices ≥3, PULSE) → 🔔 recording **beta-b0.21-novasays** + 3 beeps → HOLD → founder plays → "PROMOTE v1.5".
