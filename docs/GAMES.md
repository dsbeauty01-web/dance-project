# Nova's three games — what they see, how they decide, where they stop

For Refael. Plain words. Every number here was measured on a recording, and the recording is named. Anything not
measured yet says **GUESS** or **STAND-IN**.

The games live on the `beta` branch: `beta/index.html` is the launcher, and `beta/demo.html` is the lobby demo.
The camera is read by **MoveNet** (in the browser, nothing sent anywhere). It finds 17 body points; the games use
shoulders, elbows, wrists, nose, and hips/knees only to check you're in the picture. **Feet are never scored.**

## The rules every game follows

| rule | how it's kept | checked by |
|---|---|---|
| A star only for a move the camera really saw | every star comes from the detector; no timers, no "if the model fails, give credit" | `test/replay/edge.mjs` re-reads the raw frames behind every star (42 edge clips + every video in the repo) |
| Can't see you → skip, never a penalty, game keeps going | "I can't see you — step back" + arrows; the round doesn't count for or against | empty-room, detector-failure, dark, too-close clips |
| No numbers on a kid screen | stars ⭐ during play, 🥇🥈🥉 at the end; no points, no %, no score | `tools/laws/kid-screen-guard.mjs` in CI |
| Amber for "not yet", never red | amber caption + amber ring; mint/gold for success | same guard (fails on any red) |
| The game always ends | rounds are timed; nothing waits forever for a move | every replay checks "ends: yes" |
| Medal | gold ≥ 90 % of the rounds it could see, silver ≥ 60 %, bronze below; no star → no medal, a warm "let's play again" | `beta/lib/kp.js medalFor` |

Before every game the **Camera Doctor** checks where you stand: step back, come closer, move this way, or "I can see
you ✓". It never blocks: it moves on by itself after 6 seconds.

---

## ❄️ Freeze (`beta/freeze3.html`)

**The game:** dance while the music plays. When it stops, freeze like the animal on the screen.

**What it detects:** how much the upper body moves, in shoulder-widths per second (so it doesn't matter how far
you stand). After the music stops you get 0.6 s to stop, then you must stay still for the rest of the 2.5 s.

**The bar:**

| number | value | where it came from |
|---|---|---|
| "moving" threshold | 1.1 – 1.4 shoulder-widths/s (per-child calibration, capped) | real bodies through a real camera, 2026-09-27: still 0.43 · sway 0.80 · energetic dance 2.42 (docs/FREEZE2-MEASURED.md) |
| must be seen | 80 % of the freeze | mission rule |
| freeze length | 2.5 s | the window the judge was measured on |

**Replay proof:** a body that can't move gets a star every time (held 100 %), a gentle swayer 100 %, a dancer never
(0 %). An empty room and a broken detector skip every round and the game still ends.

**Limits:** the bar was measured on real bodies in September. Refael's three phone clips (still / sway / dance) will
re-check it (`node test/replay/derive.mjs`). In a dark room the confidence drops below the freeze judge's 0.4 and
rounds are skipped, not lost.

## 🙌 Copy Nova (`beta/copy.html`)

**The game:** Nova shows a pose (a small video of her doing it, plus a dotted ghost of the pose drawn on your own
body). You copy it. Hold it for a moment → ⭐ and a burst of light.

**What it detects, per arm:** the elbow's bend, which way the upper arm points, and whether the wrist is above or
below the shoulder. It always uses YOUR arms: your left hand is your left hand (proved on video,
`docs/evidence/6h/mirror-proof.png`).

**The bar:**

| number | value | where it came from |
|---|---|---|
| elbow tolerance | ± 25° | mission rule |
| upper-arm tolerance | ± 30° | mission rule |
| pose targets | arms up 155° · star 104–110° · bear 118–122° (elbows ~130°) · one hand up 167° · arms out 86° | measured on Nova's own clips (test/clips/README.md) |
| hold | 3 frames AND 0.6 s | measured: arms passing through a pose match for ≤ 0.38 s, a real hold ≥ 2.04 s |
| one-hand poses | the other arm must be SEEN down | night run: a hidden arm used to let "right hand up" pass while both were up |

**Replay proof:** each of Nova's pose clips stars only its own pose; "left hand up" never stars "right hand up".
Unseen arms skip the round.

**Limits:** "arms out" has no clip of Nova holding it still, so its star isn't proven yet. "Hands on head" has no
clip at all; its targets are a GUESS.

## 🎵 Groove (`beta/groove.html`)

**The game:** move to the music (bounce, sway, arms up). Every 4 beats is a "bar". A bar where you really moved →
⭐. Never a fail.

**What it detects:** how fast your shoulders, elbows and wrists move (energy), bounces of your shoulders and
whether they land on the beat, side-to-side sway, arms above your shoulders.

**The bar:**

| number | value | where it came from |
|---|---|---|
| song | animal-freeze-song.mp3, 129.2 BPM, first beat 0.151 s | measured off the live Freeze |
| star floor | 0.43 shoulder-widths/s | **STAND-IN**: 2 × the noise of a body that can't move on a jittery camera (0.215, measured on a synthetic ±3 px clip). Replace with 2 × Refael's ref-still. Dancing reads 1.6–4.4 |
| on-beat | a bounce within ± 150 ms of a beat | mission rule (see limits) |
| bonus ⭐ | every 8 bars, if ≥ 50 % of the bounces in bars you moved were on-beat | mission rule + night fix |

**Replay proof:** a dancer stars every bar (100 %); a frozen body none, even on a jittery camera; an empty room skips
every bar and the game ends.

**Limits:** at this tempo ±150 ms covers 65 % of all time, so random bouncing already counts as "on the beat" more
than half the time. The bonus rewards bouncing more than timing. Needs Refael's decision: ±80 ms, or an 80 % bar.

---

## What's measured, what's waiting

| waiting for | changes |
|---|---|
| Refael's 3 phone clips (still / sway / dance) | Freeze bar re-check, Groove floor from a real body |
| One real play per game with "Save my play" | real-world confidence, skips, any surprise |
| Hosting | GitHub Pages serves `main` only. The beta games need a place to run on a real camera |

## For the talking avatar later

Every game emits `round_start · hit · skip_unseen · miss · medal` to `window.novaEvents` (and into the Save-my-play
file). That's what Nova will react to. Nothing speaks yet.

## Speed

On a computer without a GPU, the detector is the slow part (18 judgments a second, 5 on a slow one). The lights
keep going on the frames in between, and the rules still work at 6 judgments a second. On a normal laptop
the browser uses the GPU and it's much faster. Details: `docs/evidence/night/f-perf.md`.
