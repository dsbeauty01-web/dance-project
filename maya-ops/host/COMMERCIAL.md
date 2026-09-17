# MAKE HER COMMERCIAL — what shipped here, what's left (2026-09-15) · NO POD REQUIRED

## Shipped in this package (QA: 16/16 PASS, all offline)
1. presence.py — the ALIVE layer on every line: name + pause, human noise ("mm," / "right,") rate-limited,
   one playful beat where it fits, speakable numbers ("one-forty-nine — 149"), contractions, and the
   GESTURE + GAZE cue per sentence (SHOW/POINT/WAVE/LISTEN/IDLE · camera/product). Medical lines are hard-locked
   to LISTEN + camera and never get noise or jokes. Money lines never get a filler before the number.
2. cocreate.py — viewers steer: polls ("type 1 for X, 2 for Y") with live tally, nudge, winner announcement and
   named thanks; VIP/!ask jumps the queue and interrupts; first-vote shout-outs; vote milestones; quiet-chat
   "type 1 if…" prompt. This is the mechanic with the highest measured conversion lift in the research.
3. Bonding memory on air — returning viewers get "Welcome back, Dana — you asked about texture earlier."
   (reads the answers table; only fires when there IS something).
4. maya_ot.py wired: every answer, beat and room line passes through presence; co-creation runs on comments and
   on a timer; gestures now come from meaning, not intent-guessing.
5. qa_run.py extended with 6 commercial checks: no raw JSON spoken · name-first pause · human noise present ·
   edge line present · poll/VIP fired · speakable numbers.

## Still open (and honestly ranked)
A. GESTURE CLIPS — see GESTURE-CLIPS.md. 9 Kling clips, your manual job, no pod. Without them presence emits
   cues nothing can play. This is the #1 remaining "not natural".
B. The two live bugs from 09-15: unwrap the brain's JSON envelope before TTS (fires on buy-link answers) and
   fuzzy-match the instant layer so typos don't fall to the 32s path. Both are code, both need no pod.
C. RTMPS degrades ~23k frames (~25 min) → cap sessions at 20 min or fix the encoder settings.
D. Voice micro-imperfection is textual only; true breath/laugh needs the TTS provider's tags (ElevenLabs v3).

## Run it
python3 qa_run.py            # 16/16, no GPU, proves the whole behavior layer
Then on the next pod session the same runtime is already commercial — nothing new to configure.
