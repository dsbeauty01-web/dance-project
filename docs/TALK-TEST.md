# TALK-TEST — does Nova feel live? (2026-10-21, self-run)

Pod: beta test pod 1lki7qacrcx9yw (one body, 3 Mbit stream, beta a997e2d+). Self-test, no human.
Method note: the volume's /workspace/convo.log is SHARED across every session that ran on it today
(maya commercial, math tutoring, other games all appear in it), so law attribution by timestamp is
unreliable — this report uses the clean per-session **ws transcript** (beta/sources/talk-test/ws-transcript.txt)
for my session, and convo.log only to confirm the INPUT-LOCK line fired for my input.

## 1. VOICE IN — real V2V (fake mic = real speech WAV via Chrome --use-file-for-fake-audio-capture)
Three lines played as the mic, one at a time (EN/HE/EN). The espeak-ng TTS is ROBOTIC, so the brain's
speech-recognition mis-transcribed it — this is a harness limit, not a product fault.
| spoken | brain produced a transcript? | she answered? | notes |
|---|---|---|---|
| "Hi Nova!" | yes, but garbled → "Me" | yes ("Hi!") | the garble was **dropped by INPUT-LOCK**, then she still greeted |
| "אני מוכן" | yes (partial) | yes | within the intro flow |
| "what do we play?" | yes, garbled → "Tik tik tik." | yes ("Hey superstar, what's your name?") | ~0.97 s heard→reply |
**Verdict:** the V2V pipeline carries mic audio → brain → transcript → spoken reply, ~1 s latency. Content
fidelity was poor because the TTS is robotic; a real child's voice would transcribe far better. Re-test with a
real human recording to judge comprehension.

## 2. CHAT LANE — typed into the page chat box (clean text, no ASR)
| typed | brain heard (you_text)? | answered? | latency | her answer |
|---|---|---|---|---|
| "Hi Nova!" | yes | yes | 1.04 s | "Still right here." / "Oh hey, love hearing you! What should I call you?" |
| "אני מוכן" | yes | yes | **7.0 s** (slow outlier) | "I'm not going anywhere." |
| "what do we play?" | yes | yes | 1.04 s | "It's the Animal Freeze game: dance when the music plays, freeze when it stops! Ready to roll?" |
On-topic, warm, correct game explanation. One slow Hebrew turn (7 s).

## Median response latency: **1.04 s** (n=6, across both lanes; range 0.03–7.0 s)

## 3. LAWS (from my session's ws transcript)
| law | result | evidence |
|---|---|---|
| INPUT-LOCK drops garble | **PASS** | `[INPUT-LOCK] dropped (garble/empty): Me` — the mis-ASR was dropped, not spoken to |
| No digits spoken | **PASS** | none of her 8 lines this session contain a digit |
| Never negative | **PASS** | all replies warm/neutral ("no rush at all", "Still right here") |
| Holds silent (nothing in air during HOLD) | **NOT EXERCISED** | the run stayed in intro/ready-gate; no countdown/music/freeze, so no HOLD occurred |
| No negative on a broken freeze | **NOT EXERCISED** | no freeze happened |
| CONSENT gate | **NOT EXERCISED** | my prompts never asked a factual question that would trip a self-answer |
| TRUTH-GATE | **NOT EXERCISED** | same — no factual claim to gate |
To exercise holds/consent/truth-gate/broken-freeze, the session must reach GAME phase (say YES, let the
music run, break a freeze). This intro-only run could not — a follow-up game-phase test is needed for those 4.

## 4. Evidence (beta/sources/talk-test/)
- talk-90s.mp4 — her stream (video + her voice) through the whole test
- ws-transcript.txt — full brain websocket transcript (my session, clean)
- console.log — page body/phase/reveal events
WAVs + ws.json were temp; the shared convo.log was NOT committed (it holds other sessions' data).

## ONE LINE
**She feels live: YES** — ~1 s warm, varied, on-topic replies and a working garble-guard make her read as
present and alive; caveats are the 7 s Hebrew outlier, a robotic-TTS voice-in that needs a real-voice retest,
and four game-phase laws (holds/consent/truth-gate/broken-freeze) still unverified because this run never
left the intro.
