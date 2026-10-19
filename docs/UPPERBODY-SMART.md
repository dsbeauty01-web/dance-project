# UPPERBODY-SMART — re-base the game on the engines (surgical · keeps what's good · CLI commits only)

Target: `beta/upperbody.html` (726 lines, audited 2026-09-09). Tag `beta-b0.14`. KEEP: layout, 4 rounds, measured targets, demo calibration, grace miss, wobble warm + one line, sideStats coaching, scorecard, tiers. REPLACE the five blocks below — nothing else.

## 1 · DETECTION → the engine (replaces `Pose.loop` joint handling + `Game.onPose` math)
```js
import { MoverEngine } from '/shared/mover-engine.js';
import { RULES } from '/shared/mover-rules.js';
import { grade } from '/shared/cue-window.js';
import { startPose } from '/shared/pose-engine.js';           // b0.10 — emits toNova() frames; MediaPipe→MoveNet fallback
const E = new MoverEngine();
// calibration: demo window (round 1, t<DEMO_END) → E.startCal() at round start, E.finishCal() at DEMO_END (replaces cal.sx/sw/hx + finishCal; keep the ?slide=/?hip= overrides by mapping them onto the rule thresholds below)
startPose(camEl, k => { const out = E.update(k); L.setJoints(out); Game.onPose(out); });
```
```js
// Game.onPose — the new core (screen-space sides: MIRROR flips L/R once here)
onPose(out){
  if(this.phase!=='round') return;
  const t=routine.currentTime; if(this.round===0 && t<DEMO_END) return;        // calibrating (E is collecting)
  const nxt=this.targets[this.ti]; if(!nxt||nxt.hit) return this.trackWobble();
  const R=ROUNDS[this.round], w=R.win;
  if(nxt.dir==='FREEZE') return;
  if(t<nxt.t-w) return;
  if(t>nxt.t+w){ if(!this.graceUsed&&!nxt.missed){this.graceUsed=true;nxt.grace=true;} nxt.missed=true; this.ti++; L.clearCue('shoulderC'); return; }
  const r = RULES.ribSlide(E);                                                   // shoulderC moved on x; iso = hipC AND head still
  if(!r) return;
  const side = MIRROR ? (r.side==='L'?'R':'L') : r.side;                         // engine works in camera space
  const g = grade(t, nxt.t, w);                                                  // PERFECT / GOOD / OK
  const wrong = side!==nxt.dir;
  if(!wrong || Math.abs(t-nxt.t) < w*.5) this.hit(nxt, r.iso, wrong, g);
},
trackWobble(){ const still = E.isolated('shoulderC', ['hipC'], 0.12); this.wob = still ? 0 : this.wob+16;
  if(this.wob>400){ L.warm('hipC'); this.wob=0; if(!this._hipLine){ this._hipLine=true; Live.cue('Their hips are wobbling. ONE playful line: freeze those hips!'); } } },
```

## 2 · TARGETS → sides only (F/B removed for real)
```js
const TARGETS=[ {t:16.10,dir:'R'},{t:17.37,dir:'L'},{t:23.00,dir:'R'},{t:24.30,dir:'L'},{t:28.07,dir:'R'},{t:29.37,dir:'L'},
  {t:31.90,dir:'R'},{t:32.50,dir:'L'},{t:33.27,dir:'R'},{t:34.33,dir:'L'}, {t:35.20,dir:'FREEZE',hold:1.0} ];
// the former B/F slots (19.55, 21.20, 25.55, 26.80) become FLOW beats: L.cue({joint:'shoulderC', dir:null, windowMs:600, leadMs:400, still:[]}) — a soft pulse, no score.
delete sideStats.B; delete sideStats.F;   // sideStats = {R,L}
```
Verdict thresholds rescale: NAILED ≥8 of 10 · GOOD ≥5 · TRIED otherwise.

## 3 · SCORING → graded (replaces `hit()`'s pts line)
```js
hit(tg, iso, wrong, g){
  tg.hit=true; this.ti++; L.clearCue('shoulderC');
  const R=ROUNDS[this.round]; let pts = R.rate===1 ? 15 : 10;
  pts = Math.round(pts * ({PERFECT:1.5, GOOD:1.2, OK:1}[g]));
  if(wrong) pts=Math.round(pts/2);
  if(iso && R.rate===1){ pts+=10; L.isoShimmer(); this.roundIso++; }
  if(R.rate>1){ this.streak++; fire=this.streak>=3; L.setFire(fire); $('fire').classList.toggle('hidden',!fire); if(fire) pts*=2; } else { this.streak=0; fire=false; L.setFire(false); $('fire').classList.add('hidden'); }
  if(this.round===3) pts+=5;
  this.score+=pts; this.roundHits++; if(!wrong) this.sideStats[tg.dir]++;
  L.hit('shoulderC', iso?'iso':wrong?'wrong':'good', pts); if(g==='PERFECT') L.flyUp(L.P('shoulderC'), 'PERFECT');
  $('score').textContent=this.score;
  Live.fact(`ub_hit ${tg.dir} ${g}${iso?' iso':''}${wrong?' wrongside':''} streak ${this.streak}`);
}
```

## 4 · LIGHTS → the shared engine (delete §3 home-made block)
```js
import { LightEngine } from '/shared/light-engine.js';
const L = new LightEngine($('fx'), { tier:'adult', mirror:true });
// cue at target lead (replaces setCue): the ISOLATION PAIR — shoulders gold, hips + head dashed "stay still"
function cueTarget(nxt, R){ L.cue({ joint:'shoulderC', dir:nxt.dir, windowMs:R.win*2000, leadMs:R.lead*1000, still:['hipC','head'] }); }
// FREEZE target: L.ice() + L.cue({joint:'shoulderC', dir:null, windowMs:1000, leadMs:0, still:['lWrist','rWrist','hipC']})
```
Sounds come from the light engine (tick pitch by streak; the ding on verdicts).

## 5 · BRAIN (adult tier block — replaces the current persona text; keep the game-only rules)
"You are Nova — a calm, confident coach for UPPER BODY ISOLATION. Hands on the waist, the torso slides RIGHT and LEFT while hips and head stay FROZEN — that isolation is the whole art. Four rounds: two slow (stretch, call sides softly), two faster (short sounds, no sentences). Mid-round: max ONE line, ≤10 words, only from camera facts I hand you. Between rounds: one strength + one correction (external focus: 'reach the light further') + 'ready?'. Never negative words. Reply only with what Nova says."

## EVIDENCE + GATE
Real-camera runs ×3 (2 distances + one whole-body swayer): paste per-hit logs showing `ribSlide` fires with `iso` TRUE only when hips+head held, `PERFECT/GOOD/OK` grades, the swayer scoring iso=false; [CAL] blocks; grep-proof: zero `kp[` indices, zero F/B in targets. Harness 3× clean EN + HE.
🔔 Recording (real body, 4 rounds) → Downloads **beta-b0.14-upperbody** + 3 beeps 🔔🔔🔔 → HOLD → founder plays → "PROMOTE v1.2" on his word.
