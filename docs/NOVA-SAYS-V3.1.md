# NOVA SAYS v3.1 — the smart flow (two engines, one handoff rule, no stuck moments) · ≤ 3:00

Skills applied: PRODUCER-SILENT (remember vs speak_now, boundaries), ai-companion-presence (silence has weight, instant fillers), lexi-ux (state badges, adaptive layout), simon-says-rules/digital (demo every command, two judges), game-cues-lights + vfx (instant feedback), movement-tracking (calibrate per kid).

## 1 · THE CORE IDEA — two engines, never both at once
Her confusion came from the producer injecting into a live conversation mid-flow. So the game is split into two engines that take turns:

| | LIVE (her brain, voice-to-voice) | SHOW (the page) |
|---|---|---|
| what it is | real conversation, lips on the calm body | a sequencer playing her pre-captured lines, her gesture bakes, lights, stars, sounds |
| when it runs | intro · the 2 round cards · ending | the 3 rounds |
| mic | OPEN to her | CLOSED to her (the camera judges; kid's shouts never make her answer) |
| music | OFF (music into the mic = garbage transcripts + she talks over it) | ON, bouncy, low |
| producer | may speak_now ONCE at each handoff | sends her NOTHING that makes her speak — only silent remember() facts |

**During rounds her brain is offstage.** It can't be interrupted, can't be confused, can't get stuck, because nobody asks it anything. The show runs on clips and the camera.

## 2 · THE HANDOFF RULE (the only moments the engines switch)
- **SHOW → LIVE (round ends):** music fades (0.5s) → mic opens → the producer sends ONE `speak_now` with the round's facts ("Round 1 done. 7 stars. Caught 1 of 1 trick. Best moment: froze perfectly. Say ONE excited line to {name}, ≤ 8 words.") → she speaks.
- **LIVE → SHOW (she finished):** the page waits for her audio `ended` event (not a timer) → mic closes → "Round two!" clip → music → next round.
- **Never stuck:** if she hasn't started speaking 3s after the handoff, the page plays a pre-captured card line ("Amazing! Round two!") and moves on. The game never waits on the brain.
- The producer's round facts are also `remember()`ed all round long (silently), so her card line and the ending are always true and specific.

## 3 · HOW SHE BEHAVES BETWEEN THINGS (she is never a frozen head)
- **Waiting for the kid (live phases):** calm body, soft breathing idle, badge "Listening 👂". She says nothing after a question (WAIT LAW); one gentle nudge at 13s, pre-worded.
- **In a round, between commands:** idle body sways slightly to the music, badge "Watching 👀". The gap after feedback is ≤ 0.4s — no dead air.
- **While the kid moves (the window):** she has just finished the gesture and stands tall, watching; the light is on the kid's side. No talking during the window.
- **After feedback:** a tiny reaction without words — the gold star flies, a sound — and straight into the next command.
- **Round card:** she turns to the kid, talking body, badge "Talking", the stars jar center screen.

## 4 · THE FLOW (≈2:50)
**INTRO — LIVE (0:00-0:28)**
Greet → name → WAIT → rule in one breath → "Ready?" → WAIT → yes. Silently during her lines: 3s still-baseline calibration.
Then SHOW takes over for the **practice** (clips): "Let's practice! Nova says… arms UP!" (a real one) → "Now listen… CLAP!" (the practice trick) → she laughs and explains if caught, cheers if not. Practice has no score.

**ROUND 1 — SHOW (0:28-1:00)** · 6 commands · 1 trick · 2.4s windows
armsUp · clap · anyArm · freeze · **[trick: armsUp]** · clap

**CARD 1 — LIVE (1:00-1:06)** · one fact line from her · then "Round two!"

**ROUND 2 — SHOW (1:06-1:42)** · 8 commands · 3 tricks · 2.0s
clap · armsUp · **[trick clap]** · leftArm · rightArm · **[trick armsUp]** · freeze · **[trick clap]**

**CARD 2 — LIVE (1:42-1:48)**

**ROUND 3 LIGHTNING — SHOW (1:48-2:30)** · 10 commands · 4 tricks · 1.6s · exact sides
armsUp · clap · armsUp · **[trick armsUp]** · rightArm · leftArm · **[trick clap]** · clap · **[trick rightArm]** · **[trick clap]** · finish: freeze

**ENDING — LIVE (2:30-2:55)** · the star jar + medal on screen · her specific celebration from facts · "Did you have fun?" · WAIT · react once · goodbye with the name · PULSE.

## 5 · SCORING — "the listening score"
The real skill in Simon Says is **listening**, so every decision counts, not just moves:
- **Did it on "Nova says"** → ⭐
- **Stayed still on a trick** → ⭐⭐ (the hard part, worth double)
- **Freeze held the full second** → ⭐ + the body ices over
- **Listening streak:** every right decision (a done command OR a held trick) builds a glowing streak bar. **5 in a row → a bonus ⭐ + "Super listener!"** (her clip). A GOTCHA resets only the streak — stars already won never leave the jar.
- **GOTCHA** → her laugh, a boing, a purple ripple, a 4px wobble. Zero stars, zero loss.
- **Round end:** stars this round + "Tricks caught: 2 of 3" — the one number that tells the kid how well he listened.
- **Medal** by % of the max stars (max ≈ 42): 🥉 < 50% · 🥈 50-79% · 🥇 80%+. Always a medal — every kid leaves with one.

## 6 · WHAT THE PRODUCER DOES (and never does)
- **Does:** runs the sequencer, judges the camera, fires lights/sounds/stars instantly, `remember()`s every result into her memory silently, sends exactly ONE `speak_now` per handoff (4 in the whole game: after the name/intro gate, card 1, card 2, ending).
- **Never:** sends her a message during a round · asks her to react to a move mid-round · opens the mic during a round · plays music while she talks live.

## 7 · PROOFS BEFORE THE FOUNDER PLAYS
- Log shows exactly 4 `speak_now` in a full game, all at handoffs; zero `[SPEAK]` during rounds.
- Every handoff: her line starts ≤ 3s, or the fallback clip plays — never a silence over 3s.
- Music level is 0 whenever the mic is open.
- Judges: 5 real + 5 trick per command via the harness — real ≥ 90%, still-kid tricks 100% held, moving-kid tricks 100% GOTCHA.
- A full run ≤ 3:00, recorded to Downloads + 3 beeps.
