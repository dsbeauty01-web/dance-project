# DEPLOY — pack9: the game kit + Upper Body (+ Wave re-based later). CLI: follow the steps; no design decisions.

## FILES
- `shared/game-kit.js` — the common foundation (MoveNet via TF.js, engines, lights, presence gate, phases, captions/voice hook, debug strip, scorecard, PULSE). Parse-checked.
- `beta/upperbody.html` — Upper Body on the kit. Parse-checked; kit↔page contract QA'd (all ids + K.* present).
- `beta/wave.html` — the video-led Wave (MoveNet). (Next pack re-bases it on the kit; deploy as-is now.)

## STEPS
1. Copy `shared/game-kit.js`, `beta/upperbody.html`, `beta/wave.html` into the repo at those paths (overwrite).
2. Import check (kit): it imports `MoverEngine` from `/shared/mover-engine.js`, `RULES, WaveRule` from `/shared/mover-rules.js`, `grade` from `/shared/cue-window.js`, `LightEngine` from `/shared/light-engine.js`, and optionally `/shared/nova-bridge.js` (routeVoice). If an export NAME differs on beta → change ONLY that import name in the kit and log `[ADAPT] old→new`. The kit calls on the light engine, guarded by existence checks: `cue, hit, clearCue, hoopCue, hoopHit, isoShimmer, warm, freezeStart, freezeEnd, flyUp, setJoints, P`. Verify each exists; missing ones are skipped by the page (log which are missing — the lights CLI adds them).
3. Reference video: `/media/upperbody-ref.mp4` = the 38s routine (`rapa_src.mp4` — the founder's Upper Body bake source). Verify by 6 frames (arms out → hands on hips → slides). Serve `/media/*`, `/shared/*`.
4. Self-test in REAL Chrome (claude-in-chrome), the routine video ALSO as the fake webcam: after 40s the debug strip must show `kid ≥300f/≥8j`, `cues ≥ 8`, `hits ≥ 4`, no ERR. Screenshots of: a hoop cue on the body, a hit flare, the round card, the scorecard.
5. Fix ONLY what the console names; one fix per re-run; log each (file, old→new).
6. Serve on a volume-less pod (any region) OR local — the game needs no pod. Open `/beta/upperbody` for the founder. 4 beeps.
7. Commit `beta-b0.26-kit-upperbody`. If the push is blocked by the repo rule, paste the exact message (do not disable protection).

## LAWS
No layout changes. No bake. MoveNet only. The kit is the architect's — adapt names only, never logic.
