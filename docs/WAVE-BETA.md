# WAVE-BETA — b0.2 (adult tier · MediaPipe first use · the traveling-wave detector · full code · beta only)

Track: `beta` → `/beta/wave`. Main untouched until "PROMOTE". Read skills first (movement-tracking v2, game-cues-lights, performance-feedback-ai). Laws: phase machine, live-V2V voice, INPUT-LOCK, clock law, ORIGINS wins on conflicts.

## THE GAME (facts)
28.5s sprint · body = `nova_wave_a` (52.4s bake, no visible loop) · layout = the ORIGINAL two-panel 50/50 (nova-wave.html, ORIGINS) · tier = ADULT (calm coach, ≤10 words, one correction allowed, cool amber juice, no grace) · voice: 4 scripted lines + ONE quality note after — no mid-run chatter.

## 1 · POSE ENGINE — MediaPipe via the adapter (first migration, contained here)
```js
import { PoseLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import { toNova } from '../shared/pose-adapter.js';          // from the movement-tracking skill §2 — create it here
const vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm');
const pose = await PoseLandmarker.createFromOptions(vision, { baseOptions:{ modelAssetPath:'/models/pose_landmarker_lite.task', delegate:'GPU' },
  runningMode:'VIDEO', numPoses:1, outputSegmentationMasks:false });
function poseLoop(){ const r = pose.detectForVideo(usercam, performance.now()); if(r.landmarks?.length) onPose(toNova(r,'mediapipe')); requestAnimationFrame(poseLoop); }
```
Fallback: if WebGPU/GPU delegate fails → `delegate:'CPU'`; if the model fails to load → the old MoveNet path via `toNova(r,'movenet')` (log `[POSE] engine=`). Mirror: usercam is scaleX(-1) — screen-left = kid's right; the chain detector is side-agnostic so no flip bugs.

## 2 · THE TIMELINE (clock = the music, WebAudio)
```js
const CUES = [
  { t:0.0,  say:'"Wave time — arms like water."',                  cue:null },
  { t:5.0,  say:'"Let it travel: fingers, wrist, elbow."',          cue:{ arm:'R', comet:true } },   // screen-right arm first (ORIGINS order)
  { t:15.0, say:'"Other arm — pass it across."',                    cue:{ arm:'L', comet:true } },
  { t:24.0, say:'"Hold the wave — and freeze it."',                 cue:{ hold:true } },
  { t:27.5, ending:true },
];
// phases: 0-5 arms-free (no score) · 5-15 RIGHT-arm waves · 15-24 LEFT-arm waves · 24-27.5 hold-both 1.5s+
```

## 3 · THE TRAVELING-WAVE DETECTOR (the MediaPipe win)
A wave = a peak that TRAVELS along the chain in order: shoulder → elbow → wrist → index, evenly spaced.
```js
const CH = { R:['rShoulder','rElbow','rWrist','rIndex'], L:['lShoulder','lElbow','lWrist','lIndex'] };
const hist = {};                                              // name → [{t,y}] last 1.2s
function push(name,y,t){ (hist[name] ||= []).push({t,y}); hist[name] = hist[name].filter(p=>t-p.t<1200); }
function lastPeakT(name){ const h=hist[name]; if(!h||h.length<5) return null;   // local minimum of y (screen y grows downward → arm "up" = min y)
  for(let i=h.length-3;i>1;i--){ if(h[i].y<h[i-1].y && h[i].y<h[i+1].y && (h[i-1].y-h[i].y)>CAL.peakMin) return h[i].t; } return null; }
let waves=[], lastWaveT=0;
function onPose(k){
  const t=performance.now(); for(const arm of ['R','L']) for(const n of CH[arm]) if(k[n]?.vis>0.5) push(n,k[n].y,t);
  const arm = activeArm();  if(!arm) return;                  // from the timeline phase
  const peaks = CH[arm].map(lastPeakT);
  if (peaks.every(p=>p!=null) && t-lastWaveT>600){
    const gaps = [peaks[1]-peaks[0], peaks[2]-peaks[1], peaks[3]-peaks[2]];
    const ordered = gaps.every(g=>g>40 && g<400);              // travels forward, each joint peaks after the previous
    if (ordered){ const spread = Math.max(...gaps)-Math.min(...gaps);   // evenness = smoothness
      const quality = spread<90 ? 'smooth' : spread<180 ? 'good' : 'rough';
      scoreWave(arm, quality, gaps); lastWaveT=t; }
  }
}
// CAL.peakMin = 0.35 × the kid's arm-motion range measured in 0-5s (arms-free window) — per-person calibration law.
```
Hold detector (24-27.5): both wrists + indices total motion energy < CAL.still for ≥1.5s → +25.

## 4 · SCORING (ORIGINS scale) + JUICE (cool)
```js
function scoreWave(arm,q,gaps){ const pts = q==='smooth'?160 : q==='good'?140 : 120;   // ORIGINS 120-160 band
  score+=pts; stats[arm].push({q,gaps}); fx.comet(arm, q); tick(q);                  // comet = amber light traveling the chain on the hit
  emitFact({fact:'wave', arm, quality:q}); }
// cool juice: amber (#e6a93a) comet along shoulder→index on each hit, no fire mode, no confetti; the hold gets a thin ice ring.
```
HUD: numbers (adult), per-arm smoothness meter (3 bars), no stars.

## 5 · HER VOICE (adult tier)
Intro (engine path, lips on nova_idle2): "Wave — arms like water. Ready?" → consent → music. The 4 lines above fire via notes on the clock — voice in the air over the wave body. NO other mid-run lines (speak-gate hard: 0 extra). Ending (engine path):
`note('ending-adult: score=…, right={smooth,good,rough counts}, left={…}. ONE quality note, external-focus, e.g. "smoother on the left — lead with the wrist"; then the real score; then goodbye with the name.')` → PULSE.

## 6 · GRADERS + GATE
Graders (tier=adult): words ≤10, negatives 0, internal-focus 0, extra mid-run lines 0, holds silent, exactly one correction in the ending, PULSE row. Detector proof: 3 runs (two distances + a slow waver) → paste the wave logs (gaps, quality) + [CAL] blocks. Machine harness 3× clean EN+HE.
🔔 Recording → Downloads **beta-b0.2-wave** + 3 beeps 🔔🔔🔔 → founder plays `/beta/wave` → "approved" → next file. "PROMOTE v1.1" only on his word → merges beta/wave → main wave page.
