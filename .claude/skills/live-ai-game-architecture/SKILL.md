---
name: live-ai-game-architecture
description: Use this skill whenever designing, fixing, or judging any Nova game or flow that combines live voice AI (OpenAI Realtime / voice-to-voice), a talking avatar, a producer/director, and camera body tracking. Encodes how the companies that actually shipped this work at scale (Sword Health, Nex Playground, Peloton, Inworld/Convai, the managed avatar platforms) split the jobs — rules and camera referee the moment, pre-recorded lines react instantly, live AI talks only in the pauses — so Nova stops breaking where live AI is forced to be the game engine.
---

# Live AI + Body-Tracking Games — how the winners split the jobs (and how Nova must)

## 1 · THE EVIDENCE (what the companies that succeeded actually do)

**Sword Health** — digital physical therapy, ~4M AI-guided sessions in 2025, $3B valuation. The closest real-world twin of Nova: a camera watches the body and a live voice AI ("Phoenix") coaches in real time.
- The exercise itself is taught by **pre-recorded real-life video + audio**, with a rep counter, stars and a timer on screen — fixed, not AI.
- **Proprietary Vision AI** tracks the movement and judges each rep.
- **The live AI talks around the exercise:** asks how the member feels, suggests changes, motivates, answers questions ("Hey Phoenix"), gives exercise tips.
- They call low latency "the challenge" and built a **dedicated turn-taking model** and an **orchestration layer** between the camera, the conversation and the session.

**Nex Playground** — camera movement games for kids, 650K+ units sold in 2025 (company-reported).
- Characters (Sesame Street, Bluey) are **scripted and pre-recorded**. Pose tracking runs **on the device**. No live LLM in the game loop.

**Peloton IQ / Tonal** — camera form feedback with **pre-recorded human coaches**; the camera drives instant cues, not a live conversation.

**Inworld / Convai** (game NPC platforms) — live voice characters in games.
- Game events reach the AI as **context** ("Dynamic Context": game state fed in each turn) and **triggers** (the NPC may start talking on an event).
- Moment-to-moment game behavior still runs on **state machines and decision trees**.
- Their own warning: voice adds 300-500ms on top of the text response, which makes voice-first *gameplay* risky without client-side prediction.

**The managed avatar platforms** (HeyGen, Tavus, Anam, Simli) — the avatar is a swappable **"face layer" on top of a voice agent that already works**. Their rule: build the voice agent first and get it good, then add the face.
- In the only blind comparison (178 people), **responsiveness mattered far more than realism**.
- Realistic end-to-end turn latency for a live avatar: **600ms–1.5s**.

**Nobody** — no company found — lets the live voice AI act as the referee or the director of a fast physical game.

## 2 · THE LAW (the one principle everything follows from)

**A game needs every reaction instant and identical. Live voice AI is slow (≈1s+) and different every time. So the live AI must never be on the critical path of a game moment.**

Split every game into three layers:

| Layer | Owns | Speed | Nova's parts |
|---|---|---|---|
| **REFEREE** | What happened (did he freeze? did he move? score) | < 100ms | camera + pose detection + game rules, in the browser |
| **REACTOR** | The instant response to what happened | < 300ms | pre-recorded lines in her voice, the light, sounds, score pop, gesture clips |
| **TALKER** | Personality, memory, conversation | ~1s is fine | the live voice AI (Realtime), lips on the calm body |

The REFEREE decides. The REACTOR responds instantly. The TALKER speaks only in the pauses, using facts the REFEREE collected.

## 3 · THE RULES

1. **The live AI never referees.** It never decides whether a move happened. It is told the facts afterwards.
2. **Every in-game reaction is pre-recorded** (in her voice, recorded through the same voice engine so it sounds like her): "STATUE!", "Gotcha!", "Get ready…", "Faster!", "Last one!". Fired by rules, instantly.
3. **The live AI speaks only at natural pauses:** before the game, between rounds, after the game, and when the child talks to her. Never mid-round.
4. **No producer pushing commands into her mid-sentence.** Facts go into her memory silently (`remember`); she uses them when she next speaks. The game code is the director — not a second AI.
5. **Pauses are designed in.** Every game has breathers (between rounds, 5-10s) where she can talk. If a game has no pauses, she doesn't talk during it.
6. **Instant feedback first, voice second.** The light / sound / score fire on the frame the REFEREE decides. Her voice (pre-recorded) follows within 300ms. Her live voice, if any, comes at the next pause.
7. **The game never waits for the AI.** If the live AI is slow, silent or broken, the game continues with recorded lines. Every live moment has a recorded fallback that fires after ~3s.
8. **Detection only for what the camera sees reliably** (big moves, stillness, arms up/out, freeze). Forgiving thresholds, calibrated per child. Judges tested offline before any child plays.
9. **The avatar is a face layer, optional.** Games must work with the avatar off (voice + recorded clips). Lips only when she talks live on the calm body; on game bodies her lines play without lip-sync.
10. **Responsiveness over realism.** A fast reaction with a simple visual beats a realistic face that answers late.
11. **Fewer moving parts per moment.** Any single game moment should depend on at most two components (e.g. camera + recorded clip). The chain of live AI → producer → TTS → lip-sync → stream is only allowed outside game moments.
12. **Privacy by design (kids):** pose tracking in the browser, no video uploaded; the live AI receives facts, never frames.

## 4 · APPLYING IT TO NOVA

### The intro (already mostly right)
- TALKER: greet, ask the name, wait, react, chat. ✅ (v1.0.8-1.0.9)
- The shoulder-light beat: REFEREE judges the lift, REACTOR fires the glow + recorded "Yes!", TALKER mentions it at her next turn using the fact. No live AI inside the beat.

### Freeze
| Moment | Layer | What happens |
|---|---|---|
| Before | TALKER | "Hi Noam! Ready to dance? When the music stops — freeze!" |
| Music plays | — | She dances on the groove body. **No talking.** |
| 3s before a stop | REACTOR | recorded "Get ready…" (optional, rule-timed) |
| Music stops | REFEREE + REACTOR | camera judges; "FREEZE!" sting + ice light instantly |
| Hold ends | REFEREE + REACTOR | "STATUE! ⭐" or "Gotcha! 😄" recorded, score pops |
| Between rounds (5-8s) | TALKER | one live line from facts: "That flamingo freeze was PERFECT, Noam!" |
| After | TALKER | real score, "did you have fun?", goodbye by name |

### Simon Says (Nova Says)
- REFEREE: pose judges (real = did he do it; trick = did he move at all).
- REACTOR: every command and every reaction pre-recorded; pose picture on screen.
- TALKER: only the intro, between rounds, the ending — and the boss round (the child speaks commands; she obeys) is the one place live AI belongs mid-game, because it IS a conversation.

### Any new game — the checklist before building
1. Where are the pauses? (If none, no live talk inside the game.)
2. What does the REFEREE judge, and can the camera see it reliably? (Test offline first.)
3. List every REACTOR line; record them in her voice.
4. Which facts does the TALKER get, and at which pauses does she speak?
5. Does the game still work with the live AI off? (It must.)
6. How many components does each game moment depend on? (≤ 2.)

## 5 · ANTI-PATTERNS (every one of these broke Nova before)
- The live AI praising or judging a move ("great, hold it like that!") → lies and late reactions.
- A producer injecting "say X now" into her live session mid-flow → cut-off sentences, confusion, silence.
- Live AI lines during a fast round → talks over the child, fights the music.
- Commands spoken by the live AI in a rhythm game → drifting timing, no challenge.
- A game that can't run without the pod, LiveKit and the AI all alive at once.
- Tuning thresholds on a live child instead of offline tests first.
- Adding the avatar before the voice-only version works.
