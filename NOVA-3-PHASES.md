# Nova — The 3 Context Phases

The whole Nova experience is one ~2–3 minute ritual built from **three context phases**.
Each phase has a different job, a different "Nova presence," and a different technical
mode. This doc is the source of truth for how a session should *feel*; the
`nova-joined.html` game implements it.

---

## Phase 1 — INTRO · GREET · PREP-TO-PLAY
**Job:** make the kid feel *met* before any game starts, and cover the worker warm-up.

- **Loading intro (while she loads).** The worker (LiveKit + Runway avatar) has a
  cold-start tax (free Render tier = 30–50s; warm = a few seconds). We fill that gap
  with a **cinematic intro splash** (`intro.mp4`, used in `v300.html`) so the kid is
  never staring at a dead screen. The splash plays *over* the boot; when Nova's audio
  + video tracks both arrive, we reveal her. **Rule: never show Nova until BOTH her
  audio and video have arrived** (avoids the 1s+ track-skew where she appears mute or
  speaks faceless).
- **Greet.** Nova (warm, big-sister energy) says hi, ideally by name if remembered
  (`localStorage` → `nova_kid_data`), asks the kid's name/age if new.
- **Prep-to-play.** Short, light: "wanna dance with me?" → game picker. Energy = warm,
  unhurried. This is conversation, **not** the game — MoveNet pose detection stays OFF
  here (running it during chat starves the CPU and makes Nova's audio choppy).

**In `nova-joined.html`:** `phase-arrival` → `phase-recognition` → `phase-picker` →
`phase-countdown`. The new video's own first ~28s (Nova walking up from far — "joining")
doubles as an on-rails greet/prep once the game starts: no cues fire until 28s.

---

## Phase 2 — THE PLAY (the game)
**Job:** the kid moves; Nova reacts as a present, alive companion.

- **Nova is an ORB, not the star.** During the prerendered MP4 she shrinks to the
  corner face-frame (`#nova-face-frame.in-game`). The big screen is *her body video*
  demonstrating the move; the orb is her face reacting to the *kid*.
- **How she reacts during the prerendered MP4:** the MP4 is fixed choreography, but
  Nova is live on top of it. The game sends **game-event packets** over the LiveKit
  data channel (`hit`, `first_hit`, `streak`, `freeze_hit`, `miss`) to the worker;
  the worker brain turns those into short spoken reactions, lip-synced on the orb.
  Reactions are **specific** ("your shoulders POPPED!") not generic, and **rate-limited**
  so the music stays primary. Orb glow states: watching (pink) / talking (green) /
  thinking (purple).
- **Anticipation.** ~800ms before each cue, Nova *names the next body part*
  ("shoulders up!") via fast browser TTS — presence *between* moves, not just after.

**In `nova-joined.html`:** the **4-point isolation** game — head → shoulders → ribs →
hips, three rounds (learn → faster → fast-fire) → an "ALL TOGETHER" finale. Single
media source (the MP4 carries its own music), so the game clock = `video.currentTime`,
zero A/V drift. Detection = scale-normalized "did you pulse this part?" amplitude on
MoveNet keypoints (forgiving for ages 6–10).

---

## Phase 3 — ENDING WITH A HOOK
**Job:** end warm, end proud, and leave a reason to come back tomorrow.

- **Warm wrap.** Stars + score + best streak, and Nova gives a **specific** goodbye that
  calls back a real moment from *this* session ("I loved that rib slide!") — fetched
  from the worker `/end-goodbye`, with a local fallback if the brain is slow.
- **The hook.** A persistent `#end-hook` line teases the **next** move she'll teach
  ("tomorrow I'll teach you the SPIN 🌀"). This is what turns a one-off into a *daily
  ritual* — the kid leaves wanting the next lesson. It renders independent of the brain
  so it always shows.
- **Memory.** "Save my Nova" persists name/age/streak so Phase 1 next time can greet by
  name and reference the streak — closing the loop.

---

## Phase → state cheat-sheet
| Phase | MoveNet | Nova size | Worker phase event | Energy |
|------|---------|-----------|--------------------|--------|
| 1 Intro/Greet/Prep | OFF | full / closeup | `greeting` | warm |
| 2 Play | ON | orb (corner) | `dance` | high → max |
| 3 Ending+Hook | OFF | closeup | `goodbye` | warm |
