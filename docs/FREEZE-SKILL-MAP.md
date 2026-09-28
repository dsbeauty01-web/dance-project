# FREEZE → mapped to the skill (live-ai-game-architecture) · and the new Freeze

Source of "current": the last detailed Freeze reports — the nephew test (2026-09-13, main v1.0.2) and the Freeze current-state report (2026-08-27) — plus the fixes since (v1.0.3-1.0.9: Hebrew STT pinned, gender, wait law, producer-silent). The CLI must confirm nothing else changed before building.

## 1 · THE CURRENT FREEZE, LAYER BY LAYER

| Moment | What happens now | Layer it uses | Skill verdict |
|---|---|---|---|
| Intro | Live AI greets, asks the name, explains, waits for yes (lips, calm body) | TALKER | ✅ correct |
| Music / dancing | Groove body loops; she may say one live line per gap ("air" voice) | TALKER inside the game | ❌ rule 3 — live AI mid-round |
| ~4.5s before a stop | Producer sends a cue → live AI says a warning ("עוד שנייה קופאים!") | producer → live AI | ❌ rules 1, 4 — live AI on a timed game beat |
| The stop | Melody cuts → bare beat → recorded "FREEZE!" sting; pose clip snaps on top of her | REACTOR | ✅ sting · ⚠️ pose-clip snap looked like "a different Nova" |
| The hold (2.5s) | Camera judges stillness; she is hard-muted | REFEREE | ✅ correct |
| After the hold | Ding + a live AI verdict line ("כמו פלמינגו צבעוני!") — arrives 2-4s late, sometimes cut off | REACTOR + TALKER mixed | ❌ rule 2 — the verdict must be recorded and instant |
| Kid talks mid-game | Stored, no answer until the ending | — | ⚠️ felt "dead" — because there is NO pause where she could answer |
| Round structure | 11-12 freezes in one 132s block, no breaks | — | ❌ rule 5 — no designed pauses |
| Ending | Live AI with real stats, "did you have fun?", goodbye | TALKER | ✅ correct |

**Count:** the freeze moment today depends on music + sting + camera + pose clip + producer + live AI + TTS = 7 parts (rule 11 says ≤ 2). Every nephew-test complaint — late reactions, cut-off sentences, voice fighting the music, "she ignores me" — sits in the ❌ rows.

## 2 · THE NEW FREEZE (same game, split correctly)

**Shape: 3 short rounds with breathers, ≈ 3 minutes.**

| Phase | Time | Layer | What happens |
|---|---|---|---|
| Intro | ~25s | TALKER | Greet, name, one-line rule: "When the music stops — FREEZE!", wait for yes. |
| Round 1 | ~40s | REFEREE + REACTOR | 4 freezes, gaps 8-10s. |
| Breather 1 | ~8s | TALKER | ONE live line from facts ("Noam, your flamingo was the stillest!"). If he answers, she answers once. Then "Round two!" (recorded) on his yes / tap / 8s. |
| Round 2 | ~40s | REFEREE + REACTOR | 4 freezes, faster gaps (6-8s), one fake-out. |
| Breather 2 | ~8s | TALKER | Same as breather 1, different fact. |
| Round 3 | ~40s | REFEREE + REACTOR | 4 freezes, the last one a long "star" freeze (5s). |
| Ending | ~25s | TALKER | Real score and best animal, "did you have fun?", goodbye by name. |

**Inside a round — nothing live, everything instant:**
- **Before a stop (optional, not every time):** recorded "Get ready…" or a musical riser — skipped on the fake-out so it stays a surprise.
- **The stop:** melody cuts → recorded "FREEZE!" + **her video simply pauses on its current frame** (she literally freezes mid-dance — zero switching, perfect sync) + ice glow on her and on the kid.
- **The animal twist (kept, simpler):** a big animal picture shows which freeze it is (flamingo / frog / bear / star); judged by stillness, same as now.
- **After the hold:** within 0.3s, a recorded line in her voice — "STATUE! ⭐", "Perfect flamingo!", "Almost!" (never negative) — plus the score pop. Then the music comes back and her video un-pauses.
- **Kid talks mid-round:** the 👂 chip shows she heard; she answers at the next breather (it's never more than ~40s away).

**The producer:** sends her NOTHING that makes her speak during a round. Facts go into her memory silently after every freeze. Exactly **3 speak moments** in the whole game: breather 1, breather 2, ending. Each has a recorded fallback if she's silent for 3s.

## 3 · WHAT GETS RECORDED (her voice, same voice engine — one voice)
"FREEZE!" (have) · "Get ready…" ×2 · "STATUE!" ×2 · "Almost!" ×2 · per animal: "Perfect flamingo!" / "Rock-solid frog!" / "Steady bear!" / "Superstar freeze!" · "Round two!" · "Last round!" · "Last one — the STAR freeze!" · fallbacks: "Amazing — round two!" / "So good — last round!" / "What a freezer! See you tomorrow!". EN + HE (gender forms only where needed).

## 4 · WHAT STAYS EXACTLY AS IS
The intro flow (v1.0.8-1.0.9), the sting, the melody-cut → bare-beat sound, the stillness judge (certified), the Hebrew STT pin, the gender rule, the ending with real stats.

## 5 · WHY THIS SHOULD FEEL BETTER TO A KID
- Every freeze gets an instant, clear reaction — no 2-4s silence.
- She never talks over the music or gets cut off.
- She actually answers him — in the breathers, soon after he speaks.
- Her freeze looks natural (the video pauses) instead of a different clip popping in.
- Short rounds with breathers keep a 5-8 year old focused.
