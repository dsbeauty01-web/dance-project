# HANDOFF — Nova brain/voice agent (2026-07-28)

## From: the NOVA PULSE session-reporting work (frontend + worker only)

**One tiny ask for the brain/voice side — one ending line:**

> After Nova's goodbye at the end screen, have her ask the kid:
> **"did you have fun with me? tell me anything!"** — one sentence, nothing else.

### Why
The page now shows a feedback beat at the ending (😀 😐 😞) **and** captures any
kid line spoken after the ending marker as `feedback.text` in the session's PULSE
report. If Nova *invites* the kid to talk, we get spoken feedback for free — the
richest signal of all. The emoji tap is the fallback for kids who won't speak.

### Rules (so this stays inside the sacred pipe — I did NOT touch it)
- Just **one** short spoken line, right after the existing goodbye. No new turn logic.
- It must fire **after** the ending marker the page already logs
  (`[ENDING] ... end screen` / `goodbye-done`), so the kid's reply lands in the
  post-ending window the page is listening on.
- Nothing else changes — no prompt rewrites, no VAD/turn changes.

Everything else (collector, score, feedback UI, `/pulse` endpoint) is already built
and proven. This line is the only brain-side piece.
