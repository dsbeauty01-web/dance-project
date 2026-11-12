# NOVA-FINAL — Nova on Ditto (wide talk) + SoulX PiP face (2026-11-12)

Refael's approved spec: (1) Nova's talking = Ditto lips, Ditto Gold lock; (2) before the game she talks WIDE in her room;
(3) in-game face = small SoulX PiP top-left INSIDE her room, game layout unchanged, all games; (4) Freeze v4 = baked body
untouched, SoulX face, talks less; (5) live Ditto in real time.

## What was built (branch `nova-final`, merged to `beta`)
| piece | file |
|---|---|
| her wide talk body: `freezegame/idle_sway.mp4` (her room), 1.3x tighter wide shot (lanczos + unsharp 5:5:0.7, 24->25 fps), mouth closed with maya-lt `bench/lips_pro/close_mouth_stable.py --ref 95` on a 640 px head crop, composited back (feather) | `tools/pod/assets/nova_talk_wide.mp4` |
| one face server, two faces, one active: Ditto wide (`nova-wide-video`) / SoulX PiP (`nova-face-video`), `GET /face_mode`, voice delayed by DITTO_PRIME with the Ditto frames | `tools/pod/nova_face.py` (`FACE_RENDERER=dual`) |
| brain forwards the phase: speak-gate off = wide, on = pip (default off) | `pod/rt_lk.py` `NOVA_FACE_DUAL=1` |
| PiP tile for every game; panel active/inactive; bridge `onWide` | `shared/face-pip.js`, `shared/face-panel.js`, `shared/nova-bridge.js` |
| Freeze v4: side rail removed, PiP top-left in her room, WIDE Ditto stage in intro + ending, intro waits for her line | `beta/freeze4.html` |
| proof pod | `tools/pod/nova_final_{pod.sh,ctl.py,proof.py}` |

The untested nova-take8c page hooks (`shared/nova-face.js` red banner on every page) were reverted: superseded by the dual face server.

## Ditto Gold gate (maya-lt `tools/lipcheck/gold_gate.py`, gold.json unchanged)
| stage | input | result |
|---|---|---|
| pre | `idle_sway.mp4` full body | BLOCK — face 158 px |
| pre | `beta/sources/groove-1080/tests/control-idle2.mp4` | BLOCK 158 px — and it is a test montage (frozen holds + hard cuts), not a body |
| pre | 1.3x wide (her room, cap to shins) | **PASS — face 205 px** (on the delivered clip 239 px median) |
| body | `nova_talk_wide.mp4` | **PASS — jitter 0.02, open 0 %** (lipcheck notes: head sway 28 % of face height, prebake head-motion REJECT on disp) |
| take | W cut: her two arrival lines (EN+HE) x2 through the live face server, 48.6 s, 1080x1920 | **BLOCK** (table below) |

| take metric | Nova W cut | control: the closed body ALONE + same voice (no Ditto) | gold knees-up |
|---|---|---|---|
| speaking jitter | **1.53** | 0.18 | 2.28 / 2.82 |
| lips follow voice (corr) | **0.597** (lag +1) | 0.054 | 0.518 / 0.583 |
| pause jitter (lip_jerk_silent) | 3.35 BLOCK | 3.61 | 1.73 / 1.86 |
| landmark noise in pauses (noise_jerk_silent) | 2.88 | 3.44 | 1.14 / 1.18 |
| core silence lip motion | 2.43 BLOCK | 2.50 | 0.71 / 0.97 |
| pucker frames | 54 BLOCK | 54 | 0 |
| open frames in silence | 1 BLOCK | 0 | 0 |

Reading: speaking is better than every gold take; every SILENCE block is measured the same on her body without Ditto
(the control row), i.e. it is her stylised face + sway at 240 px (landmark noise 2.9-3.4 vs gold 1.1-1.2), not Ditto.
The one Ditto-made fault is 1 open frame in silence. Per the lock this take is NOT a result. QUESTION for Refael: a
Nova-specific silence bar (e.g. "not worse than her own closed body"), or keep BLOCK.

## Real time (live loop on the pod, RTX 4090 Secure, nproc 64)
| | Ditto server ms per 0.4 s chunk p50/p95 | face-server loop p50/p95 | late chunks | underruns |
|---|---|---|---|---|
| silence, 45 s | 89 / 96 | 118 / 125 | 0 / 112 | 0 |
| her voice, W | 91 / 98 | 118 / 127 | 0 / 234 | 2 (boot) |
| real run A (page, Chrome on the pod) | — | 119 / 134 | 0 / 316 | 5 (switches) |

= ~0.3 s of work per 1 s of voice (bar: well under 1 s; Nova 2026-11-11 was 1.1-1.2 s). What changed: chunk 10 (0.4 s)
with the render thread one chunk ahead (never waits for a publish), only one face renders at a time, no lk_bridge sidecar.
SoulX PiP: 387 / 396 ms per 0.96 s chunk.

## Pods (all `nova-*`, Secure RTX 4090, $0.89/h, terminated by ID, gone verified)
| pod | what | time | cost |
|---|---|---|---|
| 2z5b80ww49hqka | run #1: Ditto "no face in the first source frame" (205 px face) -> DITTO_FACE_ROBUST=1 | 03:34-03:43 | ~$0.13 |
| d2vsgzkcpfovfr | run #2: speed + W + real run A | 03:43-03:59 | ~$0.23 |
| df9maejzjmm1a0 | run #3: closed while still booting (Refael: close pods when not rendering; all games went into one run) | 04:05-04:09 | ~$0.05 |
| h0q82hhzwbwi50 | run #4: speed + Freeze v4 run (intro fix, PiP warm frame) + Wave + Upper Body runs; 17 min of it was the image pull on a slow host | 04:14-04:45 | ~$0.46 |
| **total** | | | **~$0.87** |

## Run #4 numbers
| | Ditto wide p50/p95 per 0.4 s | late | SoulX PiP p50/p95 per 0.96 s |
|---|---|---|---|
| speed (silence) | 124 / 166 ms | 1/118 | — |
| Freeze v4 run | 122 / 149 ms | 1/219 | 363 / 413 ms |
| + Wave + Upper Body | 122 / 143 ms | 1/413 | 365 / 412 ms |

Freeze v4: her intro line said WIDE in full (asked 5.4 s, her voice 9.8-14.9 s, game at 18.1 s), PiP face in the game,
ending WIDE. Wave: intro WIDE 14.0-23.5 s, then the clip + PiP, 3 timed lines, ending WIDE. Upper Body: intro WIDE
13.7-23.6 s, round 1 with PiP, between card WIDE — then the page's own round-end bug made the phase flap hold/between
every second (the paused clip sat past FINISH_AT and re-fired the hold). Fixed in `beta/upperbody.html` (the clock only
drives game/hold); NOT re-run on a pod.

Gold take gate on the Freeze v4 live Ditto cut (intro + ending, 39.7 s, face 237 px): **BLOCK** — corr 0.661, speaking
jitter 1.64 (gold knees 2.28-2.82), 0 open frames in silence; blocks: pause jitter 2.90 (its landmark noise alone 2.77),
core silence motion 2.54, 106 pucker frames — the same silence numbers her closed body gives with no Ditto at all
(control above).

## All games (Refael 2026-11-12: "make sure ALL of Nova is like this now")
`shared/nova-live.js` = the Freeze v4 setup as one engine: `createNovaLive({ pane, hide })` · `ready()` · `phase('intro'|'between'|'ending'|'game'|'hold')`
· `say()` (game: first sentence ≤ 6 words, one per gap) · `waitLine()`. The brain takes `?intro=page:<game>` (page owns every beat, PAGE_RULES = FREEZE_RULES without the freeze words).

| game | status |
|---|---|
| Freeze v4 (`beta/freeze4.html`) | done (own wiring, same behaviour) |
| Upper Body (`beta/upperbody.html`) | done through `shared/game-kit.js` (every kit page gets it); intro line [CLI-FILL] |
| Wave (`beta/wave.html`) | done; intro line [CLI-FILL]; each timed line is its own beat |
| Nova Says (`beta/novasays.html`) | done (run #5): WIDE intro said, game = page body clips + PiP. Bodies are page clips now: groove = `freezegame/dance-active.mp4`, `gest_star` = `freeze-star.mp4`, `gest_bear` = `freezebear.mp4`; `gest_lefthand/righthand/clap` have no clip in the repo → spoken + lit only (NOVA-SAYS.md rule). QUESTION: bake those three |
| Up Groove (`beta/upgroove.html`) | done (run #6): on `nova-live.js`; bodies = its own clip bank (`nova-joined-small.mp4`), WIDE intro, PiP in game, freezes = hard mute; `?legacy=1` = old SARAY path. Run #5 found the page's `#nova-stage video{opacity:0}` rule hid both live videos — fixed |
| Freeze (`beta/freeze.html`, the certified one) | not touched (main is frozen; Freeze v4 is its successor) |


## Runs #5-#6 (2026-11-12 evening, Refael "finish all")
| pod | what | time | cost |
|---|---|---|---|
| 8s4vc8jykjv1w1 | Upper Body (round-end fix), Nova Says, Up Groove | 17:41-18:01 | ~$0.30 |
| 8i30io3jrbr9rl | Up Groove (visibility fix) + Nova Says again | 18:02-18:18 | ~$0.23 |

Upper Body fix verified: one hold → between, no flapping (run #4 flapped every second).
Nova Says on run #6 did not reach her intro inside the 95 s cap: Chrome on the pod has no WebGL, pose runs at 1 fps on the
CPU and the start-up took ~60 s (run #5 made it in time). Also found: the Ditto "not streaming" red line showed from page
load until attach — fixed in `nova-live.js` after the run (not re-run).

| Ditto Gold take gate (knees-up) | corr | speaking jitter | pause jitter (noise) | core silence | pucker | open in silence | verdict |
|---|---|---|---|---|---|---|---|
| Freeze v4 (run #4) | 0.661 | 1.64 | 2.90 (2.77) | 2.54 | 106 | 0 | BLOCK |
| Upper Body (run #5) | 0.752 | 2.53 | 2.98 (2.70) | 2.53 | 107 | 0 | BLOCK |
| Nova Says (run #5, intro part) | 0.664 | 1.48 | 3.24 (2.90) | 2.60 | 70 | 1 | BLOCK |
| Up Groove (run #6) | 0.655 | 1.44 | 3.31 (2.95) | 2.47 | 75 | 0 | BLOCK |
| her closed body, no Ditto (control) | 0.054 | 0.18 | 3.61 (3.44) | 2.50 | 54 | 0 | BLOCK |
| gold knees-up | 0.52-0.58 | 2.28-2.82 | 1.73-1.86 (1.1) | 0.71-0.97 | 0 | 0 | — |
