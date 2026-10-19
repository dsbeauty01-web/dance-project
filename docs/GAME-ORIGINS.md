# GAME-ORIGINS — extract the REAL original games (no guessing · trace everything · READ-only sources)

## THE PROBLEM THIS KILLS
The new game pages keep GUESSING cues, timings, thresholds, and scoring that were already perfected months ago. The originals exist in this repo. From now: **every value in a new page traces to a real source, cited in a comment. Zero invented numbers.**

## THE SOURCES (all in `dance-project`, all READ-ONLY references)
1. **`nova-joined.html`** (main) — THE legacy app, frozen but fully playable: the original Hello Hello engine (tuned to its 13.875s clock-class timing), Up Groove, Wave, Freeze — cues, detector thresholds, scoring, lights. Months of live-tested tuning. DO-NOT-EDIT, but read everything.
2. **`nova-app.html`** (main) — the older sibling, same era, cross-reference.
3. **Standalone originals on main:** `animal-freeze.html`, `hello-hello.html`, `nova-wave.html`, `handwave.html` — each carries its own original engine.
4. **Git history for anything missing:** `git log --all --oneline -- <file>` · read old states with `git show <commit>:<file> > /tmp/ref/<name>` (READ-ONLY extraction — never checkout/revert the working tree).
5. **The videos' own clocks:** the measured durations (Up Groove 90s, Wave 28.5s, Wave Magic 80.9s, Hello 111s, Bounce 73.6s) + the Up Groove ladder map already extracted (HEAD 30-34, SHOULDER 35-39, RIBS 40-44, HIPS 45-49, double-speed, chain, freestyle).

## THE JOB — build `games/ORIGINS.md` (before ANY new page code)
For EACH game — Up Groove, Wave, Wave Magic (pre-wave), Hello, Freeze — extract and document:

### Per game, the extraction table:
1. **Source file(s) + line ranges** where its original engine lives
2. **The cue table:** every cue with its exact time/beat (copy verbatim, note the clock source: song time / video time / beat index)
3. **Detector config:** which joints, which thresholds, which windows (the exact numbers — e.g., shoulder-pop rise value, freeze stillness threshold, wave flow sequence logic)
4. **Scoring:** events → points → streaks/bonuses, exactly as the original computes
5. **Lights:** which joints light on which cues, timing lead (the one-beat-early pattern)
6. **Sounds:** which SFX at which moments (and WHICH file — so Freeze's beep never leaks into other games)
7. **Anything time-tuned:** countdowns, grace windows, cooldowns — the little numbers that took weeks

### Format per game in ORIGINS.md:
```
## <GAME>
source: <file> lines <a-b> (+ git commit <hash> if from history)
clock: <song|video> <duration>
cues: [verbatim table]
detectors: {joint: threshold, ...} (source lines cited)
scoring: [rules verbatim]
lights: [map]
sfx: [file → moment]
tuned-values: [the magic numbers + what they do]
```

## RULES
- READ-only: no source file is edited, no git state is changed. Extractions go to /tmp/ref/ and into ORIGINS.md only.
- A value that can't be found in any source = mark `MISSING — needs founder ruling`, never invent a stand-in.
- Where GAMES-PERFECT.md's tables and the originals disagree: list BOTH side by side under `CONFLICT:` — the founder rules, not you.
- Deliverable: `games/ORIGINS.md` committed (named-file add), pasted in full in your report. **HOLD after — no new page code until the founder approves ORIGINS.md.**

## AFTER APPROVAL (the standing law)
Every new game page built under GAMES-PERFECT.md must cite its numbers: `/* ORIGIN: nova-joined.html L2140-2188 */` above each ported table. A PR with uncited tables fails review.
