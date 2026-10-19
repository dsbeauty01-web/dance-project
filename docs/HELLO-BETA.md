# HELLO-BETA — b0.3 (kids tier · video-led mirror dance · mirror-match scoring · shadow-twin · full code · beta only)

Track: `beta` → `/beta/hello`. The ORIGINAL hello-hello.html on main stays untouched until "PROMOTE". Read the 3 skills first. Laws: `__mp4Leads` (the video is the clock), phase machine, live-V2V voice, INPUT-LOCK, no bake (voice + MP4 by founder ruling), ORIGINS layout wins.

## THE GAME (facts)
111s · `nova-hello.mp4` (832×1104@30, own audio) leads · NO bake: Nova = the video mid-game, `nova_idle2` with lips only in intro + ending · layout = the ORIGINAL full-screen CAMERA (kid fills the screen, Nova's video small corner — hello-hello.html L21-37 per ORIGINS) · tier = KIDS (110% energy, ≤6 words, 4:1 praise, stars, grace, full gold juice, choices).

## 1 · STEP 0 — THE SECTION MAP (measure, don't guess)
Run motion-energy segmentation on nova-hello.mp4 (frame-diff per 0.5s, smoothed) → the video's own section boundaries (energy steps). Expect ~6 sections. Also detect her audio's beat grid. Paste the map for approval; placeholders:
```js
const SECTIONS = [ {t:0,name:'hello',line:'"Hello hello! Copy me — let\'s dance!"'},
  {t:18,name:'groove',line:'"Follow my hands!"'}, {t:36,name:'wave-hi',line:'"Big hello wave!"'},
  {t:55,name:'bounce',line:'"Bounce with me!"'},  {t:74,name:'mirror',line:'"Be my mirror!"'},
  {t:92,name:'big-finish',line:'"Everything — GO!"'}, {t:105,name:'end'} ];
```
The video's per-section motion-energy curve is also saved (`hello-energy.json`) — it's the reference the kid is matched against.

## 2 · POSE + THE SHADOW-TWIN (MediaPipe mask — kids effect)
```js
// PoseLandmarker with outputSegmentationMasks:true (delegate GPU, lite model). toNova() adapter as in WAVE-BETA §1.
// Shadow-twin: draw the mask as a soft gold silhouette 12px offset behind the kid on the fx canvas — "your golden shadow dances with you".
function drawTwin(mask){ fxCtx.save(); fxCtx.globalAlpha=.35; fxCtx.filter='blur(6px)'; fxCtx.drawImage(maskToCanvas(mask), 12, 8); fxCtx.restore(); }
// The twin brightens with the mirror score (alpha .2→.6) — the feedback IS the shadow.
```

## 3 · MIRROR-MATCH SCORING (motion-energy correlation, per section)
```js
// kid energy per 0.5s bin: mean joint displacement over visible joints (vis>0.5), normalized by the kid's own p90 (calibration in section 0 = 'hello', no score).
let kidE=[], refE=hello-energy.json;                        // both normalized 0-1, same 0.5s bins on the VIDEO clock
function sectionScore(sec){
  const a=kidE.slice(sec.i0,sec.i1), b=refE.slice(sec.i0,sec.i1);
  const r = pearson(a,b);                                     // −1..1
  const lag = bestLagWithin(a,b,2);                            // kids lag the video — allow up to 1s
  const rr = Math.max(r, lag.r);
  return rr>=0.75 ? {pts:20,verdict:'MIRROR!'} : rr>=0.5 ? {pts:10,verdict:'nice copy!'} : {pts:0,verdict:null};   // never negative; 0 = silent
}
// per section end: fx.flare all joints on 20, fx.pop on 10, nothing on 0 (silence has weight). Stars: ★ per 10, ★★ per 20.
// bonus: 'big-finish' section ×2. Grace: the first 0-section of the game is forgiven in the star count.
```

## 4 · HER VOICE (kids tier) — on the video clock
```js
sched(0.0, () => note(`start: say exactly ${SECTIONS[0].line}`));
for (const s of SECTIONS.slice(1,-1)) sched(s.t, () => note(`section ${s.name}: say exactly ${s.line} — one line, then quiet.`));
// hype ≤4 per game, ONLY on section verdicts (fact-fed): note(`verdict:${v} section:${name}. React 4-6 words, specific ("your bounce matched mine!").`)
sched(SECTIONS.at(-1).t, () => { setPhase('ending'); note(`ending: name=… stars=… score=… best=…. Real numbers → "did you have fun? tell me anything!" → goodbye with the name.`); });
```
Intro (engine path, lips): greet → name → "copy everything I do — ready?" → consent → the video starts. Choices: which hello (if 2 variants exist later), ready?, play again.

## 5 · LAYOUT (ORIGINS, kids juice)
Full-screen usercam (mirrored), Nova's video small corner (ORIGINS position, ~28vw, bottom-left), fx canvas over the kid (twin + flares), HUD stars top-center, state badge, Pause/Exit. Gold only glows. During intro/ending the layout flips to Nova-dominant (Lexi adaptive) then back.

## 6 · GRADERS + GATE
Kids graders: words ≤6, negatives 0, internal-focus 0, ≤1 line per section, hype ≤4, choices ≥3, silence on 0-sections, PULSE row. Detector proof: 3 runs (a kid-sized tester at 2 distances + one deliberately lazy run → low scores, zero negatives). Harness 3× clean EN+HE.
🔔 Recording → Downloads **beta-b0.3-hello** + 3 beeps 🔔🔔🔔 → founder plays `/beta/hello` → "approved". "PROMOTE v1.2" on his word → main.
