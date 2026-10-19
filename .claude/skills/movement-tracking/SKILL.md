---
name: movement-tracking
description: Use this skill whenever designing, coding, migrating, or debugging camera-based movement detection for Nova (browser pose estimation — MediaPipe Pose Landmarker, MoveNet, RTMPose/ONNX) — scoring dance moves, freeze/stillness, isolations, waves, footwork, cues tied to joints, calibration, thresholds, or choosing the pose engine. v2 (Sept 2026): encodes the current open-source landscape, exactly what each engine can and cannot track, the MoveNet→MediaPipe migration map, per-game application, and how to plan future games around trackable motion.
---

# Movement Tracking v2 — the 2026 stack, what it honestly sees, and how Nova uses it

## 1 · THE ENGINES (open source, Sept 2026 — verified)
| Engine | Points | 3D? | Browser | Speed | Verdict for Nova |
|---|---|---|---|---|---|
| **MediaPipe Pose Landmarker** (BlazePose GHUM) | **33** (face, shoulders, elbows, wrists, **pinky/index/thumb**, hips, knees, ankles, **heels, foot-index**) | **z + world coords (meters, hips = origin)** + visibility + presence + **segmentation mask** | first-party JS (`@mediapipe/tasks-vision`), **WebGPU** on Chrome/Edge/Safari 17.4+ | real-time | **THE upgrade. 2026 consensus: "the only sensible choice for the browser."** |
| MoveNet (TF.js) | 17 | no | yes | Lightning ~30fps | our current engine; fine, but blind to feet-detail, hands, depth |
| RTMPose / RTMO / RTMW (OpenMMLab) | 17 / whole-body 133 | 2D (RTMW has 3D variants) | via ONNX Runtime Web (community libs exist) | RTMPose-m 75.8 AP, 90+ fps CPU | SOTA accuracy; heavier integration; a server/pod option later |
| ViTPose / RF-DETR Keypoint | 17 | no | server only | slower | max accuracy, not for the kid's browser |
| MediaPipe **Hand** Landmarker | 21 per hand | 3D-ish | JS, WebGPU | real-time | add-on for finger games (runs alongside Pose) |

**Decision:** migrate the browser detector **MoveNet → MediaPipe Pose Landmarker** (one bounded session). Keep MoveNet index mapping behind an adapter so old detectors keep working.

## 2 · MIGRATION MAP (MoveNet idx → MediaPipe idx)
```js
// shared/pose-adapter.js — normalize any engine to Nova's named joints
export const MP = { nose:0, lShoulder:11, rShoulder:12, lElbow:13, rElbow:14, lWrist:15, rWrist:16,
  lPinky:17, rPinky:18, lIndex:19, rIndex:20, lThumb:21, rThumb:22, lHip:23, rHip:24, lKnee:25, rKnee:26,
  lAnkle:27, rAnkle:28, lHeel:29, rHeel:30, lFoot:31, rFoot:32 };
export const MOVENET = { nose:0, lShoulder:5, rShoulder:6, lElbow:7, rElbow:8, lWrist:9, rWrist:10, lHip:11, rHip:12, lKnee:13, rKnee:14, lAnkle:15, rAnkle:16 };
export function toNova(result, engine){                       // → { name:{x,y,z,vis} } normalized, plus world[] if available
  const map = engine==='mediapipe' ? MP : MOVENET, src = engine==='mediapipe' ? result.landmarks[0] : result.keypoints;
  const out = {};
  for (const [name, i] of Object.entries(map)){ const p = src?.[i]; if(!p) continue;
    out[name] = engine==='mediapipe' ? { x:p.x, y:p.y, z:p.z, vis:p.visibility } : { x:p.x, y:p.y, z:0, vis:p.score }; }
  out.world = engine==='mediapipe' ? result.worldLandmarks?.[0] : null;   // meters, hips-origin
  out.mask  = engine==='mediapipe' ? result.segmentationMasks?.[0] : null;
  return out;
}
```
All detectors read `toNova()` names — never raw indices. Threshold re-tune after migration via the harness (values may shift ~10-20%; per-kid recalibration absorbs most of it).

## 3 · WHAT WE CAN TRACK WELL (build games on these)
- **Camera-plane motion** of any joint: left/right slides, up/down bobs, arm raises, waves through the arm chain, jumps, knee bends, kicks in the plane
- **Stillness** (total motion energy) — the freeze — even better with 33 points + visibility gating
- **Sequence/order** (left then right), **timing vs the beat**, **streaks**
- **Relative isolation**: shoulders vs hips, head vs shoulders (the tracked part moves, the reference stays)
- **NEW with MediaPipe:** foot taps/steps/stomps (heel + foot-index), **hand direction** (pinky/index/thumb → is the hand leading the wave?), rough **depth lean** via world-z of shoulders vs hips (model-estimated — BONUS only, wide threshold, never core score), **silhouette** from the mask (the kid glows as a shape — effects, not scoring)

## 4 · WHAT WE STILL CANNOT (never core-score)
- Precise toward/away distance (z is estimated, not measured) · true torso rotation/twist · fast spins & motion blur · side-profile bodies · two kids overlapping · fine finger shapes without the Hand model · hands over the face (head must be visible)

## 5 · DESIGN LAWS
1 camera-plane core scoring · 2 relative not absolute · 3 per-kid calibration in a no-score window (p90-p10 range, thresholds ≈35% of range, floors) · 4 EMA smoothing (0.6/0.4) + visibility ≥0.5 (MediaPipe) / score ≥0.35 (MoveNet) + min-joint count · 5 velocity assist inside windows · 6 sustained-only penalties (≥400ms) · 7 graded windows PERFECT/GOOD/OK · 8 parent camera rules (2-3m, full body, face visible, even light) · **9 world-z depth = bonus-only with confidence gating** · **10 hand/foot points only when visibility ≥0.6** · 11 two-distance + small-kid test before shipping.

## 6 · APPLICATION TO THE CURRENT GAMES
- **Freeze (kids):** stillness over 33 points, visibility-weighted → fewer false breaks from flickering joints; the mask can "ice over" the kid at the cut (effect). No scoring change.
- **Up Groove (kids):** the ladder maps cleanly — head-x (nose vs shoulder-center), shoulder-y pops, ribs = shoulder-center-x vs hip-center-x, hips-x vs ankles. The chain section gains real **wrist→index** finger-lead detection.
- **Wave (adult):** the big win — the wave is a TRAVELING sequence: shoulder-y → elbow-y → wrist-y → **index-y** peaks in order. Score ORDER + spacing = true smoothness.
- **Upper Body (adult):** sides = shoulder-center-x vs hip-center-x (as now). **Front/back returns as BONUS only** via world-z lean (wide threshold, visibility-gated) — never core.
- **Hello (kids):** mirror-match via motion-energy correlation — add the mask silhouette for a "shadow twin" effect.

## 7 · PLANNING FUTURE GAMES (what the tech invites)
- **Footwork games:** step-touch, heel-toe, stomps on the beat (heel/foot-index) — kids AND adults
- **Hand-shape games:** finger waves, "spider hands," jazz hands — with the Hand Landmarker add-on
- **Body-roll / wave-through-body:** peak-order down the spine chain (shoulders→hips→knees) = the boogaloo roll, scorable as sequence timing
- **Party/multi mode:** MoveNet MultiPose or RTMO — two kids side by side, mirror battles
- **Silhouette play:** the mask makes the kid a glowing shape — statues that turn to ice, shadow-copy games
- **"Did they do THE move" (later):** skeleton action recognition (ST-GCN class) trained on Nova's moves — beyond thresholds
- Rule for every new game: write the move as **joint + axis + reference + timing** first; if it can't be written that way, redesign the move before designing the game.

## Anti-patterns
Raw engine indices in game code · scoring z as core · fixed thresholds across kids · binary hits · trusting one frame · hands-over-face poses · designing a move the camera can't name.
