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
| df9maejzjmm1a0 | run #3: real run A with the intro fix + PiP warm frame | see below | see below |
