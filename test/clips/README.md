# Replay clips — the permanent replay set

Every beta game (`beta/freeze3.html`, `beta/copy.html`, `beta/groove.html`) is tested by replaying these
recordings through the game's own logic (`beta/lib/*-game.js`): `node test/replay_all.mjs`.

## Format (play-recording)

```
{ when, v:1, src, w, h, fps, detector,
  frames:[ { t, lShoulder:[x,y,conf], rShoulder, lElbow, rElbow, lWrist, rWrist, nose, lHip, rHip, lKnee, rKnee, lAnkle, rAnkle } ] }
```

x, y are normalized 0..1 of the **un-mirrored camera image** (y down); conf is MoveNet's raw score.
Gates are applied when reading (`beta/lib/kp.js`): joint < 0.30 = absent, ankles < 0.45 = absent.
A frame with no person has no joints.

## How they were made

`node test/clips/track.mjs [name …]` runs `test/clips/track.html` in headless Chromium: MoveNet
SINGLEPOSE_LIGHTNING (TF.js 4.20, pose-detection 2.1.3, `enableSmoothing:true`, the games' detector) on
every frame of `test/clips/src/<name>.webm` at the clip's own frame rate — no frame skipped or duplicated.
Tracking uses the WASM backend (headless Chromium has no GPU; WebGL on software rendering took ~1.2 s/frame).
Same model and weights: against WebGL on `frozen-body` the largest keypoint difference was 0.0092 of the
frame and 0.12 confidence.

The videos are WebM (VP9) because the test browser has no H.264. All are 360×640.

| clip | made from | what it is |
|---|---|---|
| `frozen-body` | one frame of `freezegame/idle_sway.mp4` (0.5 s), held 10 s, light per-frame noise (`noise=alls=6`) | a body that cannot move: only detector jitter |
| `still-sway` | `freezegame/idle_sway.mp4` forward + reversed (10 s) | standing, small sway, feet planted |
| `dance-hype` | `freezegame/dance-hype.mp4` (10 s) | energetic dancing |
| `empty-room` | right 26 % of `freezegame/studio-bg.jpg` (the part with no one in it), 10 s, noise | no person. MoveNet returns no pose on every frame. **The full `studio-bg.jpg` is NOT empty: Nova stands in it.** |
| `pose-star` | `freezegame/freeze-star.mp4` | Nova's star freeze (arms out) |
| `pose-bear` | `freezegame/freezebear.mp4` | Nova's bear freeze (arms up, elbows bent) |
| `pose-armsup` | nova-avatar `hidden-demo/assets/nova_dance/both_hands_up.mp4` | both hands up |
| `own-left-up` | nova-avatar `…/nova_dance/right_hand_up.mp4` | Nova raises her **own left** hand (it's on the image's right) |
| `own-right-up` | nova-avatar `…/nova_dance/left_hand_up.mp4` | Nova raises her **own right** hand |
| `upperbody` | `media/upperbody-ref.mp4`, first 12 s | upper-body moves |
| `model-fail` | (no file) | the replay feeds `null` every frame, as the page does when the detector throws |

The nova-avatar clips are named from the viewer's side, so `right_hand_up.mp4` shows her own left hand.
The replay clips are named by the body's own hand.

## Mirror proof (measured 2026-10-17)

`docs/evidence/6h/mirror-proof.png`: on `own-left-up` (Nova's own left hand up), MoveNet's **`left_wrist` (lWrist)** rises
(0.67 shoulder-widths above the shoulder at 3.0 s), while `rWrist` stays 0.87 sw below. On `own-right-up` it is
`rWrist` (+0.55 sw). So on the un-mirrored camera image MoveNet's `left_*` is the **player's own left**. The
mission text said the opposite ("camera left_* = player's RIGHT"). That holds only if the frame is flipped
before detection, and no beta game does that. The page mirrors the **picture** for display only (CSS), and the
light layer mirrors its drawing to match. `beta/lib/kp.js` `OWN` is built on this measurement.

## Phase 2: Refael's reference clips

Pending. When `ref-still.mp4`, `ref-sway.mp4` and `ref-dance.mp4` arrive: drop them into `test/clips/src/`
(convert to WebM, or track in real Chrome), run `node test/clips/track.mjs ref-still ref-sway ref-dance`, then
`node test/replay/derive.mjs`. That prints the motion of each clip and the `moveFloor / moveK / moveCeil` that meet
still ≥ 95 % · sway ≥ 80 % · dance ≤ 15 %.
