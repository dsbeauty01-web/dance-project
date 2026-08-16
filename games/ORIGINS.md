# games/ORIGINS.md — the REAL original games, traced to source (2026-08-16)

Every value below is copied from a real source file in this repo and cited by line.
Nothing invented. Where a value isn't found yet it is marked `MISSING`. Where the
GAMES-PERFECT.md tables disagree with the original, both are shown under `CONFLICT`.
**HOLD: no new page code until the founder approves this file.**

Sources (READ-ONLY): `nova-joined.html` (legacy app, all games), `nova-wave.html`,
`hello-hello.html`, `wavemagic.html`, `animal-freeze.html`, `handwave.html`, `nova-app.html`.

════════════════════════════════════════════════════════════════════════
## LAYOUT PER GAME (the thing that was wrong — each game differs)
| Game | Original layout | Source |
|---|---|---|
| **Up Groove** | column: header / **two panels (Nova + kid cam)** / button row; Nova ~63% | nova-joined.html L338, L364-378 (`#rec-nova-panel` + `#rec-cam-panel`) |
| **Wave** | **two panels side-by-side** — `#nova-side` 50% + `#cam-wrap` 50% | nova-wave.html L94-115 |
| **Hello** | **FULL-SCREEN CAMERA** (kid fills screen, `#cam` scaleX(-1) cover) + Nova small circle top-right | hello-hello.html L21, L25, L33 |
| **Wave Magic** | MISSING — extract from wavemagic.html |
| **Freeze** | pod-served `/freeze` (approved, locked) | pod/pages/animal-freeze.html |

**So Hello must NOT be two-panel — it's full-screen camera.** My current hello.html is wrong.

════════════════════════════════════════════════════════════════════════
## UP GROOVE
source: nova-joined.html — detectors L4346-4354, detection L4672-4703, timeline L4884-4932+, scoring L2372-2405
clock: song (nova-joined-small.mp4) 90s

detectors (ISO, normalized by shoulder width `sw`):
```
ISO.thr = { headbob:0.22, shrug:0.15, ribslide:0.18, hipbounce:0.18 }   // L4354
headbob   = isoPulse('headbob', nose.x - midShoulderX, now, sw) > 0.22   // L4687
shrug     = isoPulse('shrug',   leftSh.y - rightSh.y,  now, sw) > 0.15   // L4692
ribslide  = isoPulse('ribslide',midShoulderX - midHipX,now, sw) > 0.18   // L4695
hipbounce = isoPulse('hipbounce',hipSig,               now, sw) > 0.18   // L4700
combo     = 2+ isolations live OR high overall motion                    // L4702-4703
```
cues (verbatim, ms, `pts`): L4908+
```
 4000 combo LET'S GO! pts80 · 12000 combo KEEP MOVING · 22000 combo YEAH
 30100-34840 HEAD L/R (headbob pts100, ~1.08s windows, ~1.22s apart)
 35000-39740 SHOULDER L/R (shrug pts120)
 39900-44640 RIBS L/R (ribslide pts140)
 44800-49540 HIPS L/R (hipbounce pts130)
 ~50000 double-speed ladder UP the body · 60000-83000 MOVE IT ALL freestyle combo
```
scoring: hits / attempts / streak; STREAK shown ×2 at streak≥2 (L2405, L1591). points per move above.
lights: MISSING — confirm nova-light.js joint map for isolations
sfx: FRIEND-SFX WebAudio sparkle on WOW (L1941-1959)
CONFLICT: GAMES-PERFECT.md scoring (10/15/+20) vs original per-move (100/120/140/130) — founder rules.

════════════════════════════════════════════════════════════════════════
## WAVE
source: nova-wave.html — layout L94-115, detection L343-360, lights L569-621
clock: song/video 28.5s (handywave)
layout: two panels — `#nova-side` (50%) + `#cam-wrap` (50%)  (L94-115)

detectors (DOM = dominant-mover, cap:3, disc:0.6; normalized by shoulder width): L343-360
```
domScores = { S: shOsc/THRESH.shOsc, E: elbowOsc/THRESH.elOsc, W: wristOsc/THRESH.wxOsc } (each capped 3)
shoulder-roll pts120: shOsc>THRESH.shOsc && S dominant (S>E*0.6 && S>W*0.6)
elbow-pump    pts140: elbowOsc>THRESH.elOsc && E dominant
wrist-wave    pts160: wristOsc>THRESH.wxOsc
free          pts60 : motion>THRESH.motion
```
THRESH exact values: MISSING — extract THRESH const (near L328-346)
cues/timeline (times): MISSING — extract the beat-timed cue table from nova-wave.html
lights: nova-light.js — comet travels ALONG the arm (fingers→wrist→elbow), blooms as it passes; colour by quality (L592-621). NOT an outward burst.
CONFLICT: GAMES-PERFECT wave pts (15/wave) vs original (120/140/160) — founder rules.

════════════════════════════════════════════════════════════════════════
## HELLO
source: hello-hello.html — layout L21-44, detection note L14
clock: song 111s (shit.mp3 / hello track)
layout: FULL-SCREEN camera (kid fills screen, mirrored) + Nova small circle top-right + cue text top
detectors: body-relative, confidence-gated ≥0.5, ADDITIVE, one joint at a time (both wrists on clap/both-up) (L14)
cues (right/left/clap/both/head/freeze) + exact times: MISSING — extract the Hello timeline (hello-hello.html engine)
scoring: streak shown (L37); per-move points MISSING
sfx: MISSING
note: Hello is voice + song-led; no baked avatar (founder: hello not for bake).

════════════════════════════════════════════════════════════════════════
## WAVE MAGIC (pre-wave lesson)
source: wavemagic.html — ALL MISSING, extract layout + cues + step notes + scoring
clock: video 80.9s (pre-wave.mp4, video-led / __mp4Leads)

════════════════════════════════════════════════════════════════════════
## FREEZE (locked — extract for verification only, do not edit)
source: nova-joined.html — freeze=stillness L4663, TIMELINE_FREEZE L4832+
clock: song 60s (freeze.mp3)
cues: freeze at 8200/26000/... `holdMs:4000`, `pts:300` per freeze (L4842, L4857)
detector: genuine stillness only; clapping keeps wrists near each other (L4663)
sfx: freeze beep — MUST NOT leak into other games (grep-proof per page)

════════════════════════════════════════════════════════════════════════
## STILL-TO-EXTRACT (before building)
- Wave: THRESH exact numbers + the cue/beat table
- Hello: full cue timeline + per-move points + the full-screen layout details
- Wave Magic: everything (wavemagic.html)
- Up Groove + Wave: nova-light.js joint→light map + one-beat-early lead
- All: exact grace/cooldown/countdown tuned values

## RULE GOING FORWARD
Every ported table in a new page cites its origin: `/* ORIGIN: nova-joined.html L4908-4932 */`.
