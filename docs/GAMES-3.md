# GAMES-3 — Upper Body · Up Groove · Hello Hello (on the engines + the approved light language · full logic code · one session per game · CLI commits only)

Foundations (exist on beta): `shared/mover-engine.js` + `mover-rules.js` + `cue-window.js` (b0.11) · `shared/light-engine.js` with LIGHTS-FINAL + WAVE-COMET-ACCURATE (b0.17/18) · `shared/pose-engine.js` (b0.10) · `shared/nova-bridge.js` + `pulse.js` (b0.15) · `beta/tiers.js`. **Template page = `beta/wave.html`** — clone its skeleton (stage, phase machine, pose loop, HUD, gate, pause/exit, PULSE) for each game; change only the parts written below. Read the 4 skills first. Beta only; each game = one tag; main frozen until "PROMOTE".

The light language (decided): move cue = bloomed orb+ring+ribbon · wave = the phase-driven comet · ribs/hips = the hoop + dashed anchor · freeze = ice glow on the body · clap = the snap. Kids tier = full gold juice; adult = cool amber.

═══════════════════════════════════════════════════════════════════
## GAME 1 · UPPER BODY (adult · 38s × 4 rounds slow/slow/fast/fast · tag beta-b0.19)
═══════════════════════════════════════════════════════════════════
Apply UPPERBODY-SMART.md's five blocks (engine detection with `RULES.ribSlide`, sides-only targets, graded hits, adult brain) — then the lights per this file:
```js
// cue at target lead:  L.hoopCue({ mover:'ribs', dir:nxt.dir, windowMs:R.win*2000, leadMs:R.lead*1000 })
// hit:                 L.hoopHit(); L.hit('shoulderC', iso?'iso':wrong?'wrong':'good', pts); if(iso) L.isoShimmer();
// the former F/B beats (19.55, 21.20, 25.55, 26.80): L.hoopCue({ mover:'ribs', dir:'F'|'B', windowMs:600, leadMs:400 }) — shown, unscored
// wobble (sustained): L.warm('hipC') — once per round max + her one line
// finish freeze (35.20, 1.0s): L.freezeStart(1000) / freezeBreak / freezeEnd(held) — enable the mask on this page (outputSegmentationMasks:true)
// verdict card + scorecard: unchanged; labels via L.flyUp above the head (PERFECT/GOOD/OK), adult tier = no fire mode, particles ×0.4
```
Timeline/targets: the measured map (R16.10 L17.37 · R23.00 L24.30 · R28.07 L29.37 · fast burst R31.90 L32.50 R33.27 L34.33 · FREEZE 35.20). Rounds: 1.0/1.0/1.25/1.25 with windows 1.0/0.9/0.75/0.65 × adult 0.7. Between rounds: `note('between-adult: strength="…" correction="«weak side» — reach the light further next round", then "ready?"')`.
Gate: real-camera runs ×3 (2 distances + a whole-body swayer → iso=false), harness 3× EN+HE, recording **beta-b0.19-upperbody** + 3 beeps, hold → "PROMOTE v1.2".

═══════════════════════════════════════════════════════════════════
## GAME 2 · UP GROOVE (kids · 90s · the ladder · tag beta-b0.20) — a REAL build from ORIGINS
═══════════════════════════════════════════════════════════════════
**Facts (ORIGINS, nova-joined.html):** song 90s · ladder HEAD 30-34 → SHOULDER 35-39 → RIBS 40-44 → HIPS 45-49 → double-speed ladder ~50-64 → arm chain fingers→elbows→wrists ~65-77 → freestyle ~78-85 → ending · ISO thresholds {headbob:.22, shrug:.15, ribslide:.18, hipbounce:.18} (L4354) · points head 100 / shoulder 120 / ribs 140 / hips 130 · streak ×2 at ≥2 (L4908+) · layout two-panel, Nova ~63% (nova-joined L94-115 class) · body: `nova_upgroove` 23.8s single loop as the base, parts a/b/c in rotation (existing). Music track: the Up Groove song file in the repo (grep `upgroove` audio; if only the video carries it, the video's audio is the track — state which).
**Exact section boundaries:** the CLI measures them from the track (beat-detect + the 30/35/40/45 anchors from ORIGINS) and pastes the map before wiring. Placeholders below are the ORIGINS anchors.

```js
// ── the section map (video/song clock) ──
const SECTIONS = [
  { t:8,  name:'groove-in', rule:null,          light:null,                          line:'"feel the beat first..."' },
  { t:30, name:'head',      rule:'headSlide',   light:{type:'orb', joint:'head'},    line:'"HEAD side to side!"',   pts:100, still:['shoulderC'] },
  { t:35, name:'shoulder',  rule:'shoulderPop', light:{type:'orb', joint:'shoulder'},line:'"shoulders now!"',       pts:120, still:['hipC'] },
  { t:40, name:'ribs',      rule:'ribSlide',    light:{type:'hoop', mover:'ribs'},   line:'"RIBS!"',                pts:140, still:['hipC','head'] },
  { t:45, name:'hips',      rule:'hipBounce',   light:{type:'hoop', mover:'hips'},   line:'"HIPS!"',                pts:130, still:['shoulderC'] },
  { t:50, name:'double',    rule:'ladder2x',    light:'ladder',                      line:'"again — FASTER!"',      pts:'ladder', fire:true },
  { t:65, name:'chain',     rule:'wave',        light:{type:'comet'},                line:'"fingers... elbows... wrists!"', pts:120 },
  { t:78, name:'freestyle', rule:'energy',      light:{type:'sparkle'},              line:'"YOUR moves — go wild!"', pts:5, cap:25 },
  { t:85, name:'ending' },
];
// beats inside a section: cue every beat (129-class BPM → measure), alternate sides L/R for slides, BOTH for shoulder pops every 4th beat.
```
```js
// ── the section engine (clone the wave tick) ──
let sec=-1, beatIdx=0, streak=0, score=0, hits={}, fire=false;
function tick(){ const t=clock.currentTime; const i=SECTIONS.findIndex((s,k)=> t>=s.t && (!SECTIONS[k+1] || t<SECTIONS[k+1].t));
  if (i!==sec){ sec=i; startSection(SECTIONS[i]); }
  cueBeats(SECTIONS[sec], t); if (SECTIONS[sec].name==='ending' && !done) { done=true; ending(); return; } requestAnimationFrame(tick); }
function startSection(S){ note(`section ${S.name}: say exactly ${S.line}`); hud.tag(S.name.toUpperCase()); L.setFire(!!S.fire && fire); }
function cueBeats(S, t){ if(!S.rule||S.rule==='energy') return; const nextBeat = beatGrid.next(t);       // from the measured grid
  if (nextBeat && !S.cued?.[nextBeat]){ (S.cued ||= {})[nextBeat]=true; const dir = S.name==='shoulder' ? (beatIdx%4===3?'BOTH':(beatIdx%2?'R':'L')) : (beatIdx%2?'R':'L'); beatIdx++;
    const lead = S.fire ? 0.8 : 1.2, win = S.fire ? 0.6 : 0.9; S.pending = { at: nextBeat, dir, win };
    if (S.light?.type==='orb')  L.cue({ joint: S.light.joint==='shoulder' ? (dir==='R'?'rShoulder':dir==='L'?'lShoulder':'shoulderC') : 'head', dir: S.name==='head'?dir:'UP', windowMs:win*1000, leadMs:lead*1000, still:S.still });
    if (S.light?.type==='hoop') L.hoopCue({ mover:S.light.mover, dir, windowMs:win*1000, leadMs:lead*1000 });
    if (S.light?.type==='comet') L.cometCue(beatIdx%2 ? CHAIN_R : CHAIN_L); } }
// pose frame:
function onPose(out){ L.setJoints(out); const S=SECTIONS[sec]; if(!S||!S.rule) return; const t=clock.currentTime;
  if (S.rule==='energy'){ const e=E.energy(['shoulderC','hipC','lWrist','rWrist','head']); if (e>0.5 && t-lastFree>0.5){ lastFree=t; score=Math.min(score+5, score+5); freeCap+=5; if(freeCap<=25) L.sparkle(); } return; }
  const p=S.pending; if(!p||p.hit) return; const g=grade(t,p.at,p.win); if(g===null) return;
  const r = S.rule==='wave' ? (waveR.check()||waveL.check()) : S.rule==='ladder2x' ? ladderRule(t) : RULES[S.rule](E);
  if(!r?.hit) return; p.hit=true;
  const side = r.side ? (MIRROR ? (r.side==='L'?'R':r.side==='R'?'L':r.side) : r.side) : p.dir, wrong = side!==p.dir && p.dir!=='BOTH';
  let pts = (S.pts==='ladder' ? ladderPts(t) : S.pts) * ({PERFECT:1.5,GOOD:1.2,OK:1}[g]); if(wrong) pts=Math.round(pts/2); if(r.iso) pts+=20;
  streak = wrong ? 0 : streak+1; if (streak>=2) pts*=2;                                            // ORIGINS: ×2 at ≥2
  fire = S.fire && streak>=3; L.setFire(fire); score+=Math.round(pts); hits[S.name]=(hits[S.name]||0)+1;
  if (S.light?.type==='hoop') L.hoopHit(); if (S.light?.type==='comet') L.cometHit(r.quality);
  L.hit(S.light?.joint==='shoulder'?'shoulderC':S.light?.joint||'shoulderC', r.iso?'iso':wrong?'wrong':'good', Math.round(pts)); if(r.iso) L.isoShimmer(); if(g==='PERFECT') L.flyUp(L.P('head'),'PERFECT');
  emitFact({fact:'ug_hit', section:S.name, g, iso:!!r.iso, wrong, streak}); }
// ladder2x: the four rules cycle every 2 beats (head→shoulder→ribs→hips) at double tempo; ladderRule(t) picks by beat index; ladderPts = the matching section's pts.
```
**Body:** `nova_upgroove` (23.8s) loops for the groove-in + ladder; parts a/b/c rotate for double-speed/chain/freestyle (existing rotation code). Layout: two-panel Nova ~63% (ORIGINS); talking phases widen her (Lexi law).
**Brain (kids tier):** TIERS.kids.voicePrompt + game block: "You lead UP GROOVE — an isolation ladder: head, shoulders, ribs, hips, then FASTER, then the arm chain, then freestyle. Say exactly the section lines you're given. Fact-hype max 4 per game, 4-6 words, specific. Silence between." Intro (lips, nova_idle2): "UP GROOVE! Head, shoulders, ribs, hips — ready?" → consent → music. Ending trio from real numbers (best section, streak max, score) + PULSE.
**Lights map:** head = orb on the head (kids: small halo variant) · shoulders = orb pops (BOTH = both shoulders) · ribs = rib hoop + dashed hip anchor · hips = hip hoop + dashed rib anchor · double-speed = same cues at 0.8 lead + FIRE mode on streak · chain = the phase-driven comet per arm · freestyle = `L.sparkle()` (gold Gaussian sparkles on any moving joint, capped) · ending = confetti (kids).
Gate: measured section map pasted → founder approves timings → build → harness 3× EN+HE → recording **beta-b0.20-upgroove** + 3 beeps → founder plays → "PROMOTE v1.3".

═══════════════════════════════════════════════════════════════════
## GAME 3 · HELLO HELLO (kids · 111s · video-led mirror · no bake · tag beta-b0.21)
═══════════════════════════════════════════════════════════════════
Per HELLO-BETA.md (sections measured from `nova-hello.mp4`'s motion energy — paste the map first; mirror-match = motion-energy correlation per section with ≤1s kid lag; scoring 20/10/0; big-finish ×2), with these upgrades from the skills:
```js
// SHADOW TWIN (the light): the kid's silhouette (mask) drawn as a soft gold ghost 12px offset behind them; alpha = 0.2 + 0.4·(running mirror score 0..1) — the feedback IS the shadow.
// SECTION VERDICT lights: 20 → L.hit on all major joints (flare cascade shoulders→hips, 120ms stagger) + confetti; 10 → one flare on shoulderC; 0 → nothing (silence has weight).
// CUES: none per beat (it's a mirror game — the VIDEO is the cue). One orb pulse on the kid's chest at each section start (L.cue joint:'shoulderC', dir:null, windowMs:400, leadMs:0) = "new section".
// DETECTION: kid energy per 0.5s bin = E.energy(['shoulderC','hipC','lWrist','rWrist','head']) normalized by the kid's p90 from section 0 (calibration); refE from hello-energy.json; pearson + best lag ≤2 bins.
```
Layout = the ORIGINAL full-screen camera (kid fills the screen, Nova's video small bottom-left ~28vw, ORIGINS hello-hello.html L21-37); talking phases flip Nova-dominant. Brain: TIERS.kids + "It's HELLO HELLO — a mirror greeting dance, the video leads. Say exactly the section lines. Hype ≤4, facts only." Lines per section (placeholders until the map): "Hello hello! Copy me — let's dance!" · "Follow my hands!" · "Big hello wave!" · "Bounce with me!" · "Be my mirror!" · "Everything — GO!". Ending trio: "«name», you mirrored «n» of «N» — «score» points!" + fun question + goodbye + PULSE.
Gate: section map pasted → approve → build → harness 3× EN+HE (+ one lazy run = low score, zero negatives) → recording **beta-b0.21-hello** + 3 beeps → founder plays → "PROMOTE v1.4".

═══════════════════════════════════════════════════════════════════
## ORDER + LAWS
═══════════════════════════════════════════════════════════════════
Upper Body (one session) → Up Groove (measure map · approve · build — two sessions) → Hello (measure · approve · build — two sessions). Each: harness → recording + beeps → founder plays → PROMOTE on his word only. Every value here is written or measured; a genuine gap = `[CLI-FILL]` logged, never a contradiction. Pods self-stop; one pod on the volume at a time.
