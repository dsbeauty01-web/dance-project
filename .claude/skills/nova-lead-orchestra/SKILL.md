---
name: nova-lead-orchestra
description: Use when writing or changing how a live voice avatar (Nova, Maya) LEADS a conversation toward an activity, and how the voice brain, a background producer brain and delayed lip-sync (Ditto) work together without glitches.
---

# Nova: she leads, the producer whispers, the lips follow (2026-11-26)

Why this exists: Refael's play 2026-11-26 lasted 97 s and never reached the game. She asked 0 questions and started
0 topics; he asked "what now?" three times. Cause: one big prompt that forbade her to lead ("never offer a game, never
start the game, don't mention the light") and a page that waited for the child to go quiet. Evidence:
docs/NOVA-LEAD-2026-11-26.md.

## 1. Who leads: the system, through her
Every leading product does the same thing (Duolingo Lily, Speak, Ello, OpenAI's realtime guide, Pipecat Flows,
LiveKit tasks):
1. **Steps, not one prompt.** The talk is a short list of steps. Each step has ONE goal, ONE exit condition, and a
   tiny prompt of its own (swap with `session.update` at the step edge). Personality is a separate fixed block.
2. **The system moves on the moment the exit is met.** Never "wait until the chat ends by itself".
3. **Scripted opener, free middle, system-whispered closer.** For Nova the activity is the GAME, so there is no
   free chat before it: opener -> name -> light -> go. Free chat lives between rounds and in the ending.
4. **Every line of hers ends with the child's next action** (a cue: "watch your shoulder!"), except the name ask.
   A question from the child gets one short answer + the next action in the same line.
5. **Every step has a ladder**: re-ask once, then go on without it. Nothing can block the game.
6. **Predicted branches**: for closed answers (name, yes, ready) the reply is a written line with a slot, not a
   free generation. Written/cached lines are ~1 s faster than generated ones.
7. **Length by job**: cue <= 6 words, answer <= 10, between-rounds <= 2 short sentences. Few-shot at that length.
8. **Unclear audio**: one "Hm? Say that again?" per step, then the ladder moves on.

Nova intro budget: greeting -> game start <= 30 s. Name -> light <= 3 s.

| Step | Her line | Exit | Ladder |
|---|---|---|---|
| GREET | "Hi! I'm Nova! What's your name?" (cached) | line played | - |
| NAME | - | name caught | 6 s quiet: ask once more · 12 s or 2 unclear: go on, no name |
| LIGHT | "<Name>! Magic light - lift that shoulder!" light + check start WITH the line | shoulder hit | 6 s: "Like this - one shoulder, up!" · 12 s: pass ("Magic! Let's go!"), logged |
| GO | "Music on - dance! Music off - freeze!" | line played | game starts; no listening pause |

## 2. Voice-to-voice first
Native speech-to-speech (gpt-realtime voice out) is the default voice path: lowest delay, no accent drift, no holes
between clauses. A separate TTS (ElevenLabs) is only for pre-made clips or a language the native voice cannot do.
Nova: brain's first sound 0.35-0.75 s after the child stops (native) vs 1.0-1.5 s (text -> ElevenLabs v4).

## 3. The producer (second brain) never touches her mouth
Model: Talker-Reasoner (DeepMind), OpenAI chat-supervisor, Duolingo's "System".
- The producer (pose/game events, score, memory, tips) writes NOTES to an outbox. It never speaks.
- A note = a FACT + timestamp + expiry + class. "held freeze 4 s, best yet", not a sentence.
- **Safe window** = her last line FINISHED PLAYING in the browser (face server report, not a timer) AND the child
  silent >= 400 ms AND no response active. Notes are delivered only there. One note per window.
- Stale notes are dropped (praise expires in 3-5 s). Never queue old praise.
- A spoken note rides in the NEXT `response.create` as per-response `instructions`. A silent note is context only.
  Never `response.create`, `session.update` or an item insert while a response is active.
- A note is never given as if the child said it (tag it as a stage note; prompt rule: never answer notes).
- Slow thinking (round plan, memory) runs out-of-band (`conversation: "none"`, text only) or between rounds.
- **Two classes only**: `cue` (game-timed: "Freeze!", counts, instant praise) = cached clips, may pre-empt chat by
  flush-then-play. `background` = everything else, waits for the safe window.
- If the child speaks, the child wins; pending notes wait or expire.

## 4. Lip-sync limits (same for Ditto, HeyGen, LemonSlice, Anam, Tavus)
- One utterance at a time, one speech queue for everything (live voice, clips, hums). No overlap.
- Audio inside a line must be continuous: a gap looks like the end of the line (open mouth in silence, Gold BLOCK).
  Seal each line; never leave a hole between pieces.
- "She is speaking" = playback, not generation. With a ~1 s delay line the brain is done ~1 s before the child
  hears the end. Mic gate, notes and "already said" all key off playback-finished.
- Interrupt = flush everything, wait for the clear, then new audio. Never auto-resend a half-played line.
- Budget with Ditto in sync: written line ~1.5 s, free answer ~2.5 s. The instant "mm"/reaction word covers the gap.

## 5. Failure -> guard
| Failure | Guard |
|---|---|
| She follows, chat drifts | steps with exit + ladder; line ends with next action |
| Double-speak | one queue; "said" decided by playback report |
| Note cuts her line | safe window only; local guard on active response |
| Answers a note like the child said it | tagged note + rule, or out-of-band |
| Stale praise | expiry, drop |
| Lips move in silence | sealed lines, no holes |

Sources: OpenAI realtime prompting guide (developers.openai.com/cookbook/examples/realtime_prompting_guide),
blog.duolingo.com/ai-and-video-call, ello.com/blog/teaching-a-child-in-1000-ms, docs.pipecat.ai (Flows),
docs.livekit.io/agents (tasks, avatar), arxiv.org/abs/2410.08328, github.com/openai/openai-realtime-agents,
docs.liveavatar.com, lemonslice.com/docs/livekit.md, anam.ai/docs.
