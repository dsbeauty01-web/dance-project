---
name: movement-tracking
description: Use this skill whenever designing, coding, or debugging camera-based movement detection for Nova (MoveNet/MediaPipe pose in the browser) — scoring dance moves, freeze/stillness, isolations, cues tied to body joints, calibration, thresholds. Encodes what 2D pose estimation CAN and CANNOT track reliably (research-verified 2026), so games never score the untrackable and detectors are calibrated per kid.
---

# Movement Tracking — what the camera can honestly see

## The hard truth (research, 2026)
Browser pose models (MoveNet 17 keypoints, MediaPipe BlazePose 33) are **2D**. They see the camera plane: left/right (x) and up/down (y). Depth is inferred, not measured. Keypoint error ≈ 5-15px → joint angles ±5-10°. MoveNet Lightning holds ~30fps in-browser on most devices (the safest cross-platform pick); Thunder is more accurate at 10-15fps. 256px input is enough for one kid close to the camera.

## CAN track reliably (build games on these)
- Lateral shifts: shoulders/hips/head moving left↔right (slides, isolations, sways)
- Vertical: bobs, bounces, shrugs, jumps (y of shoulders/hips)
- Arm raises, arm waves, reaches in the plane (wrist/elbow/shoulder chain)
- Stillness / freeze (total joint-motion energy near zero)
- Angles in the camera plane (elbow bend, knee bend, arm-above-head)
- Sequence order of the above ("left then right")
- Presence (enough confident joints) and gross body position in frame

## CANNOT track reliably (never score these directly)
- Toward/away movement (chest forward/back, leaning to camera) — depth is a guess; shoulder-width ratio is a weak proxy only
- Rotation/twist of the torso — limbs FLIP when pointing at or away from the camera
- Fast spins, motion blur, side-angle bodies
- Hands near/over the face (detection collapses), overlapping limbs, two people close
- Fine finger/hand articulation (MoveNet has none)
- Subtle "isolation quality" in absolute terms — only RELATIVE measures work (shoulders vs hips)

## DESIGN LAWS
1. **Camera-plane only.** Every scored move must be an x/y change of a joint. If a move is depth or rotation → don't score it; cue it as a "bonus/vibe" or redesign the move (e.g. front/back torso → replace with side slides).
2. **Relative, never absolute.** Measure shoulder-center vs hip-center, not raw pixels. Isolation = the tracked part moves while the reference part (hips) stays inside a still-threshold.
3. **Calibrate per kid** in a no-score window: median baselines + the kid's own motion range (p90-p10); thresholds = a fraction of THEIR range (≈35% for a deliberate move), floors applied. Different sizes/distances score fairly.
4. **Smooth + gate.** EMA on positions (≈0.6/0.4), confidence gate ≥0.35 per joint, min 8 confident joints for any verdict; absent kid → NOSHOW, never a miss.
5. **Velocity assists slow kids.** Moving toward the target inside the window (60% of threshold + positive velocity) counts.
6. **Sustained-only penalties.** A wobble flags only if held ≥400ms; single frames are forgiven.
7. **Windows, graded.** Every target has a time window; inside it grade PERFECT/GOOD/OK by timing distance, not binary.
8. **Camera placement instructions to parents:** waist-up-to-full-body, 2-3m, face visible, even light, no busy background, one kid in frame.
9. **Test with two distances + a small kid** before shipping a detector; paste [CAL] blocks as evidence.

## Anti-patterns
Scoring "front/back" or "rotation" · fixed thresholds across kids · binary hit/miss · penalizing empty frames · cueing hands-to-face poses · trusting one frame.
