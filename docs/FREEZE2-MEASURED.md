# Freeze v2 — what the camera actually measures (2026-09-27)

The pack's `script.json` said: *"Floors from the QA bench; the CLI re-verifies with the harness."*
This is that re-verification. It changed two numbers and added one.

## How it was measured

`test/energy-probe.html` runs the **shipped** pipeline — `shared/game-kit.js`'s MoveNet
(SINGLEPOSE_LIGHTNING, the same detector the game judges on) into `beta/freeze2/judges.js`
`update()` — while Chrome plays a video file as the webcam
(`--use-file-for-fake-video-capture`, separate Chrome profile). Energy is the judge's own unit:
joint displacement per second in shoulder-widths, so it is scale- and frame-rate independent.

Four bodies, ~20s each, 8-18 fps, 13 joints visible throughout:

| trace | what it is | p50 | p90 | max |
|---|---|---|---|---|
| `frozen-body` | ONE frame held in front of the detector — a body that literally cannot move | **0.43** | 0.58 | 0.72 |
| `still-sway` | standing, gentle sway — a child trying to hold still and wobbling | 0.80 | 1.40 | 2.36 |
| `dance-routine` | slow/medium dancing (the upper-body routine, which contains real holds) | 0.92 | 1.69 | 4.18 |
| `dance-hype` | energetic dancing | 2.42 | 3.93 | 5.21 |

Traces: `test/evidence/freeze2/*.json` (raw series included, so the judge can be replayed offline).

## What that proves

**A motionless body reads 0.43.** That is MoveNet's own jitter, not movement. It is also, to two
decimal places, the calibration number both 2026-09-27 sessions flagged as "suspect": **0.4298**
(Nova Says FAST) and **0.239** (v3). Nothing was wrong with the calibration — it was measuring the
detector's noise floor, correctly.

The bug was what the tune did with it. `thr.move = max(moveFloor, still × 4.0)` turned a 0.43
reading into **1.72**, and at 1.72 a dancing body is judged **held in 90% of 2.5s windows**
(`test/freeze2_realdata_test.mjs`). At a 0.80 reading it becomes 3.20, where even *energetic*
dancing is held **100%** of the time. That is the v1.0.1 failure — every freeze a free star,
the game only *looks* like it is judging.

## The change

| | was | now |
|---|---|---|
| `moveFloor` | 0.9 | **1.1** |
| `moveK` | 4.0 | **2.5** |
| `moveCeil` | — | **1.4** (new; `judges.js` clamps `thr.move` to it) |

Every calibration reading this game can produce now lands in **1.1-1.4**, the band the sweep says
works. An honest consequence, stated plainly: since the "still" sample is mostly detector jitter
rather than the child, per-child calibration barely moves this threshold any more. It is a guard
rail, not a personalisation.

## The bar it has to clear (`test/freeze2_realdata_test.mjs`, 12/12)

Every 2.5s window of every trace, replayed through the shipped `Hold` class, at each calibration
reading (0.24 · 0.43 · 0.60 · 0.80):

- a **motionless** child is held in **100%** of windows — never punished for freezing well
- a **wobbly standing** child is held in **90-100%**
- an **energetic dancer** is caught in **92-97%** (held in 3-8%)
- the slow routine reports 63-76% held and is **not** asserted — its choreography contains real
  stillness, so a high held% there is partly the correct answer

The pack's `test/freeze2_hold_test.mjs` still passes 11/11 — that one proves the judge's *logic*
on synthetic frames; this one proves the *thresholds* on real ones. Both are needed.

## Still open

Nobody has measured a **real child** through this build. These traces are adult/rendered bodies at
a laptop's frame rate; a 6-year-old at 2m in a bright room may read differently. The probe is
checked in precisely so that run is one command, not a rebuild.
