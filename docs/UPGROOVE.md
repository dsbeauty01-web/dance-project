# UP GROOVE — the game, with the new lights built in · page, detector and lights written and tested

## 0 · The game in one line
Music plays, Nova grooves, the child **bounces on the big beat** (every 2nd beat — one bounce every ~0.93s). A ring on his chest closes exactly on the beat; land the bounce on it → gold burst, a ripple under his feet, "+100".

## 1 · Flow (≈ 2 minutes)
| Phase | Time | Who | What happens |
|---|---|---|---|
| Intro | ~25s | TALKER (live) | Greet, name, one-line rule, wait for yes (existing intro) |
| Round 1 | ~16s | REFEREE + REACTOR | "Watch me — bounce on the big beat!" (4 beats Nova alone) → "Your turn!" → 12 bounces |
| Breather 1 | ~8s | TALKER via Stage | One live line from real facts ("9 of 12 on the beat!"), recorded fallback if silent |
| Round 2 | ~14s | REFEREE + REACTOR | 12 bounces |
| Breather 2 | ~8s | TALKER via Stage | same |
| Round 3 | ~14s | REFEREE + REACTOR | "Last round — biggest bounces!" → 12 bounces |
| Ending | ~25s | TALKER via Stage | score, medal, "Did you have fun?" |

## 2 · Three layers (live-ai-game-architecture skill)
- **REFEREE:** `BounceDetector` finds the deepest moment of each bounce (mid-body height, measured in his own torso lengths, hysteresis so jitter can't fake a bounce). `scoreHit` compares it with the beat: **on** (±130ms) / **near** (±230ms) / off. Camera delay (`latencyS`) and speaker delay (`AC.outputLatency`) are compensated.
- **REACTOR (instant, no live AI):**
  - **Approach ring** on the chest: starts big, closes to the target ring exactly when he hears the beat — he can see the beat coming.
  - **On** → gold burst on the chest + gold ripple under the feet + "+100"; streaks multiply; recorded "Groovy!"/"Yes!" every 3rd on-beat, "You've got the groove!" at a 5-streak.
  - **Near** → cyan ripple + cyan ring (encouraging, never red).
  - **Off** → nothing (no punishment).
- **TALKER:** only through the Stage (`shared/stage.js`): breathers and ending, quiet-moment rule, recorded fallbacks. Nothing live in rounds.

## 3 · Files
- `beta/upgroove.html` — the game (parse-checked; every line id exists; kit + Stage calls exist).
- `beta/upgroove/script.json` — rounds, tempo, detector, timing windows, lights, points.
- `beta/upgroove/lines-en.json` — 10 recorded lines (her voice).
- `shared/motion-detect.js`, `shared/nova-lights.js` — shared with Wave.
- Needs `shared/stage.js` (from the stage-freeze2 branch).

## 4 · Steps (beta only; the live game untouched)
1. Branch `upgroove` from `stage-freeze2`. Copy the files in.
2. `node test/motion_detect_test.mjs` → 21 pass.
3. [ADAPT] — log each: song path + bpm + beat offset (same as Freeze), the LiveKit tag, bridge verbs (same as Freeze v2 on the stage), `onSpeech` relay, the kit keypoint names (lHip/rHip/lAnkle/rAnkle must exist — if ankles don't, the ripple falls back to below the hips automatically).
4. Lines: record EN (+ HE m/f) with `tools/capture_realtime_lines.py --lines beta/upgroove/lines-en.json --out audio/upgroove/en`.
5. Deploy `/beta/upgroove.html`, `/beta/upgroove/*`, `/audio/upgroove/**`, `/shared/motion-detect.js`, `/shared/nova-lights.js`.
6. **Timing calibration (5 minutes, no child needed):** open `/beta/upgroove.html?dots=1`, an adult bounces exactly on the beat for one round. The debug line shows `offMs` per bounce. Mean offMs = how far off the pipeline is → add it (in seconds) to `latencyS`. Repeat once. Paste the before/after offMs lists.
7. Mirror check: `?dots=1` → dots on the joints; else flip `lights.mirror`.
8. Proofs: the test run, the calibration lists, one full EN run log (zero live lines in rounds; the 3 Stage speak moments), a short screen recording of the ring closing + a gold hit. Then the link → 4 beeps → HOLD.

## 5 · The detector's tested behavior
| Case | Result |
|---|---|
| bouncing on the beat (≥9 of 12 graded ON) | 40/40 |
| bouncing 300ms late (mostly NOT on) | 40/40 |
| fast song 100 bpm on the beat | 39/40 |
| far child (half size) | 40/40 |
| slow laptop 8 fps (≥8 of 12 on) | 40/40 |
| standing still → no bounces | 40/40 |
| tiny dips (0.02 torso) ignored | 40/40 |
| camera delay compensated | 40/40 |

## 6 · What could still be wrong (only a real body can tell)
- The real camera + model delay on the founder's laptop (step 6 measures it).
- Whether a 5–8 year old's bounce is deep enough (minDip 0.05 torso lengths) — lower it if real kids are missed, raise it if fidgets count.
- Whether every-2nd-beat at 129 bpm feels right — change `everyBeats` or the song.
