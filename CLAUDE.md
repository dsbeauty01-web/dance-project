# CLAUDE.md — dance-project (Nova)

Nova is a live, voice-to-voice AI dance host for kids (camera + MoveNet + a MuseTalk avatar on RunPod). Games: **Freeze** (certified), **Upper Body**, Up Groove, Wave.

## Read before touching any game
The three skills in `.claude/skills/` are law. **Read all three before editing any game file:**
- `movement-tracking` — what the 2D camera can honestly score (never score depth/rotation).
- `game-cues-lights` — cue density, gold-light language, layout, graded windows.
- `performance-feedback-ai` — Nova's coaching voice (4:1 encourage:correct, external focus, never negative).

## The laws (never break, cite ORIGINS — never invent a value)
- **INPUT-LOCK** — a kid turn is real only on a validated transcript; noise/garble never generates.
- **Phase machine** — INTRO / GAME / HOLD / ENDING; `routeVoice()` is the only routing authority.
- **Body map** — `nova_idle2` talking · `nova_idlegroove_v2` dancing · pose clips on holds.
- **Truth-gate** — praise only real detection facts; silent on misses; never invented scores/numbers.
- **Live-V2V-only voice** — zero pre-rendered voice in live sessions.
- **FREEZE-APPROVED** — any freeze-page change needs `FREEZE-APPROVED` in a commit message (CI-enforced).
- **No invented values** — thresholds/timings must cite where they came from, never guessed.

## Tracks (guardian-safe)
- `main` = the commercial game, live for testers. FROZEN by CI. Changing a game file on main needs a `PROMOTE vX.Y` PR referencing a beta tag.
- `beta` = where ALL new game work lands, served at `/beta/...`. Versioned (`b0.x`), tagged, changelog'd.
- **All game work lands on `beta`, never directly on `main`.** Rollback: `bash tools/rollback.sh <tag>`.

## Deploy note
The pod serves code from its `/workspace` volume copy (not git pull). Deploy = `scp` the changed file to the running pod, then restart the service. Merge to main/beta is for record + GitHub Pages (the static commercial/beta pages).
