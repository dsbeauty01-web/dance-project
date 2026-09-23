---
name: simon-says-digital
description: Use when building a camera-judged Simon Says (Nova Says) — lessons from Just Dance's Simon Says mode, camera limits, the two judges (real vs trick), trackable commands, instant feedback, presence gate, round shape, and the debug checklist when cues don't work.
---

# Simon Says — the digital / camera version
## 2 · The digital lessons
- **Just Dance built Simon Says into a dance.** The routine keeps playing; a "Simon says…" prompt pops in over it (freeze, jump, spin) and the player reacts inside the song. The music never stops for a command — **the command rides the dance.** That is the model: Nova dances, "Nova says" prompts pop.
- **Camera tracking is forgiving and flaky.** Webcam/phone-camera modes need bright even light, and "flailing roughly in the right direction" scores. So a camera-judged game must **only use commands the camera can verify cleanly** and must be generous on real commands, strict only on the trick (did you move at all?).
- **Feedback must be instant and visible** — a flare/sound the frame the move is seen. Voice praise comes after.


## 2b · What exists online (searched Sept 2026)
- **No browser game does body-Simon-Says with a camera judge.** Online "Simon Says" games (Kidmons, the Google webcam experiment, itch.io) are the COLOR-MEMORY Simon toy (repeat a light sequence) — a different game. The camera-judged body version is an empty seat.
- **Teachers run it over Zoom** and hit the same wall Nova solves: ask kids to step back so the upper body shows, pick commands clearly visible on camera (upper body, face), and admit that spotting who moved on a trick is hard on video — they fall back to honesty systems. Nova's camera judge is exactly the missing piece.
- **MovePlay (browser webcam games for kids, local pose tracking) — the closest cousin. Its rules worth copying:**
  - **The body IS the controller** — if a kid can play by tapping, it's a screen game in a webcam costume.
  - **Fixed short rounds (60-90s)** that end on their own; no endless sessions.
  - **"Move fast and stop on cue"** is taught by a game (Fruit Slash: swing big, pull back the instant a bomb appears) — the same muscle as a Simon trick. Stop-on-cue must be judged as instantly as the move.
  - **A compatibility/camera test before playing**; privacy — pose tracking runs in the browser, nothing uploaded; no accounts, no ads.

## 3 · Rules for a camera-judged Simon Says (Nova Says)
1. **Only trackable commands** (2D camera): arms up (both / left / right), clap, hands on head, freeze, jump, touch knees (full-body frames only). No spins, no turning around, nothing hidden from the camera.
2. **Two different judges:**
   - **Real command → "did they do THIS move?"** Generous window (≈1.5× the move's time), any reasonable attempt counts.
   - **Trick → "did they move AT ALL?"** Measure total motion in the trick window vs the kid's still-baseline. Big motion = GOTCHA; staying still = SNEAKY bonus. Never judge a trick by the specific move — a kid who half-starts and stops is still a caught kid, and that's the fun.
3. **The body is never the tell.** Nova performs the gesture on real AND trick commands (the bait). Only the words "Nova says" differ.
4. **Trick placement:** never first; after 2-4 real commands; never two tricks in a row in rounds 1-2; clustered after the fastest runs in later rounds.
5. **Pacing:** each command = say (≤1.4s) + demo + move window + a short beat of feedback. Rounds speed up by shortening the window, not by cutting the feedback.
6. **Instant channel vs voice:** the hit flare / GOTCHA ripple / sting sound fire the frame the judge decides. Her live voice only between rounds.
7. **Presence first:** don't start a round until the camera sees shoulders + wrists (+ knees if the round uses them). A kid out of frame is never "caught" and never "missed."
8. **No negative words, ever.** GOTCHA is a shared laugh. A missed real command is silent.
9. **Round shape (5-7 year olds):** R1 slow, 6-8 commands, 1 trick · R2 faster, 8-10, 2-3 tricks · R3 the kid is the boss (voice commands, she obeys or refuses if they forgot "Nova says") · R4 lightning, short, most tricks · ending: real numbers + favourite moment + come back tomorrow. Whole game ≤ 5 minutes.

## 4 · The debug checklist when "the cues don't work"
Check in this order, with the debug strip on:
1. **Presence:** is the pose engine running and seeing the joints each command needs? (joint count, confidence)
2. **Timing:** does the judge's window open after her line finishes and close before the next command? Log window start/end per command.
3. **Judge per command:** does each command's rule fire on a real attempt? Test each command alone, 5 attempts, count hits.
4. **Trick judge:** is it measuring ANY motion vs baseline, not the specific move?
5. **Light cue:** does the light appear on the right joint for real commands, and does it NOT reveal tricks?
6. **Instant feedback:** does the flare/sting fire the same frame as the judge's hit?
Only after all six pass is it a design problem.

## Anti-patterns
Demo only on real commands (the tell) · tricks first or evenly spaced · judging a trick by the specific move · commands the camera can't see · voice as the only feedback · long dead gaps between commands · elimination · rounds longer than ~90s for 5-7 year olds.
