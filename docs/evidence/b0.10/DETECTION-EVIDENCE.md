# b0.10 — DETECTION: MediaPipe Pose Landmarker engine + adapter on Freeze beta

DETECTION-MIGRATE.md executed. **Beta only — nothing merged to main. HOLD.**

## What changed (DETECTION only — nothing else touched)
- `shared/pose-adapter.js` — verified **verbatim** against movement-tracking SKILL §2 (toNova + MP/MOVENET maps).
- `shared/pose-engine.js` — **new.** Loads MediaPipe Pose Landmarker via `@mediapipe/tasks-vision`, self-hosted model `pose_landmarker_lite.task` under `/models/`, delegate **GPU → CPU → MoveNet** fallback, `runningMode:'VIDEO'`, `numPoses:1`, `outputSegmentationMasks:false`. Emits `onPose(toNova(result, engine))` per frame; logs `[POSE] engine=<n> fps=<n>` every 5s.
- `beta/freeze.html` — the stillness detector now reads **named joints via toNova only**. Visibility gate 0.5 (MediaPipe) / 0.35 (MoveNet), min 8 confident joints. `?pose=1` debug overlay added.
- `pod/rt_lk.py` — `/beta/freeze` route + `/shared` + `/models` static mounts (BETA-TRACK STEP 2). No brain/voice logic touched.

## Two real bugs the migration surfaced (fixed on beta; reported for main)
1. **`window.Pose` guard was always false** — both `Pose.init()` call sites gate on `window.Pose`, but a top-level `const Pose` is not a window property, so the **real-camera detector never started** from the live/offline paths. Machine sessions masked it because `__test.pose()` sets stillness directly. Fixed with `window.Pose = Pose`. **The same dead guard exists on `main`'s `pod/pages/animal-freeze.html` — reported, NOT touched (detection session, beta only).**
2. **`<base href="…github.io/dance-project/">` pinned the relative engine import off-origin** — `import('../shared/pose-engine.js')` resolved to GitHub Pages instead of the serving origin (pod/localhost). Fixed by resolving against `location.href`.

## Evidence

### Recalibration — synthetic-frame harness through the REAL page math (`test/recal_pose.js math`)
Each scenario feeds toNova()-shaped frames through `Pose.ingest` (the exact game path). **RESULT: PASS.**

| scenario (MediaPipe, 0..1 coords) | present | motion p10 | p50 | p90 | vs threshold 0.045 |
|---|---|---|---|---|---|
| still + sensor noise | 100% | 0.020 | 0.022 | 0.024 | **below → STILL ✓** |
| breathing sway | 100% | 0.020 | 0.022 | 0.024 | **below → STILL ✓** |
| fidgety (real movement) | 100% | 0.054 | 0.059 | 0.064 | above → breaks freeze ✓ |
| dancing | 100% | 0.060 | 0.089 | 0.115 | above → breaks freeze ✓ |
| big dancing | 100% | 0.095 | 0.155 | 0.202 | above → breaks freeze ✓ |
| kid absent (5 joints) | **0%** | — | — | — | NOSHOW, never a "moved" miss ✓ |
| MoveNet still (px coords) | 100% | 0.018 | 0.019 | 0.021 | below ✓ |
| MoveNet dancing (px coords) | 100% | 0.058 | 0.093 | 0.120 | above ✓ |

Per-kid calibration path (`finishCal`) on a still-with-breath baseline held the certified floor: `[CAL] freeze stillThr=0.045 from 240 samples`.

**Threshold verdict:** the certified **0.045** floor survives the MoveNet→MediaPipe migration unchanged. MediaPipe's still-band (~0.024) sits ~14% higher than MoveNet's normalized still-band — inside the skill's predicted 10-20% shift — with a clean ≥2× margin to the movement band (0.054+). No value invented; the floor is the one from main's certification, and per-kid calibration absorbs the shift.

### Real engine end-to-end (`test/recal_pose.js video`, fake-camera person)
```
[POSE] engine=mediapipe fps=0    (first 5s window, model still warming)
[POSE] engine=mediapipe fps=9
[POSE] engine=mediapipe fps=10
[POSE] engine=mediapipe fps=6
[POSE] engine=mediapipe fps=11
```
Real MediaPipe engine, GPU delegate, tracking a real dancing body: motion 0.134 > 0.045 → correctly **MOVING**, present=true. Overlay screenshot: `pose-overlay-real-camera.png` (green joint dots on the dancer, HUD `mediapipe m=… thr=0.045 MOVING`).

### MACHINE-CERTIFY graders on the live pod `/beta/freeze` (2 EN sessions completed)
| session | G1 voice | G2 presence | G3 silence | G4 flow | G5 lock | **G6 body map (DETECTION)** |
|---|---|---|---|---|---|---|
| en-1 | FAIL | PASS | PASS | FAIL | FAIL | **PASS** |
| en-2 | FAIL | PASS | PASS | FAIL | PASS | **PASS** |

**G6 (the detection grader) passes cleanly on the new engine.** The G1/G4/G5 failures are the **pre-existing brain/voice-tuning issues** (name echo, intro 46-56s > 40s, intro line count) that also fail on main and are **out of scope for a DETECTION-only session** — DETECTION-MIGRATE.md law: "touch nothing else." The 3×-clean-EN + 3×-HE bar cannot be met by a detection change alone; it is gated on separate brain work. Certification pod self-stopped (RunPod terminated it ~11 min post-boot); nothing left running.

## Grep-proof (zero raw keypoint indices / engine API in game code)
`grep -nE "keypoints|estimatePoses|poseDetection|SINGLEPOSE|left_shoulder|right_shoulder" beta/freeze.html`
→ one hit, a code comment on line 1279. No raw indices, no engine calls in the detector.
