# WAVE — LIVE-REACTION ENGINE → FULL NOVA-WAVE (integration plan + calculations)

Goal: replace nova-wave.html's old `renderMagic` (the buildPath/alongPath "river" — the canned
point-to-point look) with the **live-reaction meteor engine** proven in `wave-fx.html`, driven by
the game's **actual moves** via `window.__cuePart`. Split-screen, over the live camera. No nonova.

---

## 1 · THE ENGINE (from wave-fx.html — port verbatim, it's approved)
State: `phase` (0..1 along the active chain), `dir` (+1/−1), `headTrail[]`, `sparks[]`, `prevVi`, `_last{}`, `sm{}` (EMA).
Per frame:
1. Read live keypoints → EMA α=0.5 → screen coords via **nova-wave's `coverMap()`** (contain), X mirrored.
2. Build the active chain's live points (per-joint gates; hold last-good on dropout — never disappear/jump).
3. **POINT** = `along(chainPts, phase)` — interpolated between the live current & next joint THIS frame.
4. **Motion-gated travel:** `step = moving ? dt/(perHop·segCount)·min(3, motion·9) : 0`; still → parks + soft head pulse.
5. **Reversal:** at `phase≥1` → `dir=-1`; at `phase≤0` → `dir=+1`. Bounces wrist↔wrist.
6. Comet head (3 additive radial passes), narrowing tip toward next joint, trailing beam (sine shimmer),
   color heats toward chain-center (`colorProg = 1−|2·segProg−1|`), bloom + sparkle on joint arrival, residual glow.
7. fade via `destination-out` rgba(0,0,0,0.16) (camera shows through), `lighter` for glow.

Constants (unchanged from wave-fx): GATE wrist .40 / elbow .45 / shoulder .50; `k = clamp(sw/220, .4, 3)`;
ramp #F2730C→#FFD27A→#FFFDF5; MOVE_GATE 0.05; perHop 900 ms.

---

## 2 · MOVE → CHAIN MAP (the only game-specific part — "the actual moves")
`window.__cuePart` is the live move. Each move feeds the engine a CHAIN (ordered live joints). The
engine reacts the same way to any chain — only the joints differ. Shoulders connect DIRECTLY (no mid).

| `__cuePart`      | CHAIN fed to engine                                                   | feel |
|------------------|------------------------------------------------------------------------|------|
| `wrist-wave`     | `[right_wrist,right_elbow,right_shoulder,left_shoulder,left_elbow,left_wrist]` | full arm→arm bounce meteor (the signature wave) |
| `shoulder-roll`  | `[right_shoulder,left_shoulder]`                                       | beam crossing shoulder↔shoulder, bounces |
| `elbow-pump`     | `[right_elbow,right_shoulder,left_shoulder,left_elbow]`                | elbows up through the shoulders, bounces |
| `free`           | no chain — pulse + sparkle on BOTH wrists, brightness ∝ motion         | freestyle glow |
| (none / armed pre-hit) | chain set, parked at START until the kid moves                   | guide pulse |

`START_POINT` = chain[0] (right side); `DIRECTION` = next joint in current dir (live). Reversal only
applies to multi-joint chains (wrist-wave, elbow-pump); shoulder-roll's 2-joint chain still bounces.

---

## 3 · TIMING CALCULATIONS (per move, vs the cue windows)
Song = handywave.mp4 ≈ 28.4 s. Cue windows (from CUES): practice cues `dur` 1.3–1.6 s; the 6-count
chain cues 0.76 s each (18.0→22.9, 0.83 s apart); freestyle 5 s.

- perHop = 900 ms baseline → full 6-joint wrist-wave chain = 5 hops × 0.9 = **4.5 s** one way *at baseline*,
  BUT travel is **motion-gated**, so real pace = the kid's actual wave (the baseline is only the cap, not a floor).
  A natural kids' arm-wave covers wrist→shoulder in ~0.8–1.2 s → with `motion·9` scaling, a real wave drives
  `phase` across in well under the cue window. Within a 1.5 s practice cue the meteor rides the part of the
  chain the kid actually moves; it does NOT need to complete the whole chain to look right.
- shoulder-roll: 1 hop → ≤0.9 s baseline; a real shrug (small motion) → parks/pulses on the shoulders mostly. ✔ matches "roll" being subtle.
- elbow-pump: 3 hops; the kid's elbow motion drives the cross. ✔
- 6-count chain (18–22.9 s): each 0.76 s cue is `wrist-wave`/`elbow-pump`/`shoulder-roll` in sequence →
  feeding each its chain produces a light that sweeps the relevant joints on the beat — the chain reads as a
  continuous arm-to-arm flow because consecutive cues overlap joints (wrist→elbow→shoulder→shoulder→elbow→wrist).
- Lead: `phase += dir·0.04` nudge so the comet guides ~1 frame ahead.

## 4 · COORDINATE CALCULATIONS (align to nova-wave's panel, NOT wave-fx's mapper)
- Use nova-wave's existing `coverMap()` → `{scale,ox,oy}` (object-fit:contain) and `X(p)=cw-(p.x*scale+ox)`,
  `Y(p)=p.y*scale+oy` (X mirrored to match `#cam scaleX(-1)` + `estimatePoses(flipHorizontal:true)`).
- `sw = dist(X,Y of left_shoulder,right_shoulder)`; `k = clamp(sw/220,.4,3)`. All radii/beam widths × k.
- Keypoints come from `window.__lastPoseKeypoints` (already set by nova-wave's poseLoop) — SAME live feed
  that drives detection. No second model, no second loop.

## 5 · INTEGRATION STEPS (edits to nova-wave.html)
1. Port the engine helpers into nova-wave (orb/glow3/along/bloom/drawSparks/ema/gates + state vars),
   namespaced so they don't collide with existing names.
2. Add `CHAIN_FOR(cuePart)` returning the joint-name list from the table in §2.
3. Replace the body of `renderMagic(ctx,m,X,Y,W,H)` with: build chain from `CHAIN_FOR(window.__cuePart)`
   → run the live-reaction step (motion-gated, reversal) → draw meteor. Reuse the passed `X,Y` (coverMap).
4. Motion: reuse nova-wave's `det.motion` (already computed in analyze) for the gate/pace — no new motion calc.
5. On new cue (`openCue`): reset engine state (`phase=0,dir=1,headTrail=[],prevVi=-1`) — already calls `resetSmartLight()`; hook there.
6. Keep `__cueState` (hit/streak/miss) → tint core mint(clean)/amber(messy) as in wave-fx.
7. DELETE/bypass the old buildPath/alongPath river + nova-light handwave usage in renderMagic.

## 6 · SELF-TEST (split-screen, fake body-cam, screenshot + log)
1. Light rides REAL joints (moves with the arm), per cue. ✔ POINT from live kps each frame.
2. `wrist-wave` cue → full arm→arm bounce; reverses at the wrist. (reversals ≥1, dir 1&−1)
3. `shoulder-roll` → clean shoulder↔shoulder beam, no gap, no mid.
4. Motion-gated: still → parks+pulse; moving → flows (phase advances only with motion).
5. Camera visible (destination-out fade), never on the face, no arrows.
6. Per-cue chain switches with `__cuePart`; elbow/shoulder hold on dropout.
7. node check / no console errors; runs the full ~28 s song.

## 7 · DELIVER
Updated `nova-wave.html` (split-screen, live camera) with the live-reaction meteor driven by the actual
moves via the §2 map. Test URL + fresh log. Prove #1 (rides my arm), #2 (wave bounce/reverse), #4 (motion-gated).
