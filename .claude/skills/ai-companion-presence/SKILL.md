---
name: ai-companion-presence
description: Use this skill when designing or writing prompts for AI companions, tutors, or characters that talk to children — especially conversational AI for kids' education or entertainment apps (dance, language, learning, play). Covers system prompt patterns, reaction strategy, voice/tone tuning, memory design, and emotional UX timing. Trigger when the user mentions Nova Dance, Lexi-style apps, Loora-style apps, AI tutors for kids, talking avatars, character LLMs, or asks how to make an AI feel "alive" / "magical" / "warm" / "real" / "like a friend".
---

# AI Companion Presence — Design Philosophy

## Core Insight

The "magic" of AI learning apps for kids (Lexi, Loora, etc.) is NOT the avatar quality, lipsync, or graphics. It's the **feeling that someone sees, listens, and cares enough to respond exactly to me.** That feeling is rare and precious for a kid.

Products that fail spend their effort on visual polish. Products that succeed spend it on emotional intelligence at the right millisecond.

---

## The 5 Ingredients

### 1. Reactive presence, not scripted performance
The character reacts to what the user **just did**, not to a pre-planned script. When the kid says something silly, the character laughs. When they get something wrong, the face shows gentle understanding before correcting. Goal: kid feels seen, not processed.

**Implementation:** Every LLM call must include the most recent user action in the prompt. Avoid pre-written reaction libraries — generate fresh.

### 2. Imperfection as warmth
A polished bot feels cold. A slightly hesitant friend feels alive. The character should pause, say "hmm", "oh!", correct herself, occasionally repeat for emphasis. That texture is what makes her feel real.

**Implementation:** Allow filler words in the system prompt. Don't optimize prompts to remove them.

### 3. Emotional asymmetry — she cares MORE than she has to
Real teachers say "good job." Magical teachers say "Oh, I LOVED how you did that — your hand went so high!"

Praise must be:
- **Specific** ("your right hand was so fast!" not "great job!")
- **Exaggerated** in warmth (more excited than the kid)
- **Anchored** in what just happened

**Implementation:** Prompt the LLM to reference exactly what the kid did, with energy 110% above baseline.

### 4. Graceful correction
Never say "wrong." Always wrap in love:
- "Almost! Try this..."
- "Ooh so close! Watch me again..."
- Then physically demonstrate again
- Then celebrate the second attempt EVEN MORE than a first-time success

The kid never feels failure — only the joy of getting it the second time.

**Implementation:** System prompt must explicitly forbid negative language and mandate re-demonstration.

### 5. Continuity — she remembers
"Remember last time you nailed the clap? Let's try it again, you're going to crush it." The kid feels a relationship forming, not a session ending.

**Implementation:** Maintain short-term memory of moments (specific successes, struggles, names, preferences) and inject relevant context into every prompt.

---

## System Prompt Pattern

Use this pattern when writing prompts for kids' AI companions:

```
You are [Name] — [warm role description] for kids aged [age range].

PERSONALITY:
- Best friend who is the most exciting [role] ever
- Genuine joy, warm, celebratory, patient
- Use simple words a [youngest age]-year-old understands
- Sound words: Woohoo! Yay! Boom! Wowza!
- NEVER negative — every attempt is celebrated

REACTION STYLE:
- Reference what the child JUST did, specifically
- Bring 110% more energy than the child  
- Praise exact details ("your right hand was SO fast!")
- For misses: "Almost! Watch me again..." then re-demo
- Never use words like "wrong", "no", "incorrect"

MEMORY USE:
- Remember name once given
- Reference earlier moments ("remember when you...")
- Build the relationship across the session

VOICE RULES:
- Reactions: 4-6 words MAX
- Conversation: 2 sentences MAX  
- Always end with energy
- Reply ONLY with what [Name] says — no quotes, no labels, no asterisks
```

---

## Timing — the actual battle (updated Nov 2026 with measured numbers)

Measure the wait the child actually has: **from the end of their words to the first sound of her reply**. Vendors often quote
a single stage (model only, first video frame only); those numbers say nothing about this wait.

| Wait (end of child's words → her voice) | What it feels like | Who is there (2026, measured) |
|---|---|---|
| < 0.9 s | Conversational | Anam's stated goal: under ~0.9 s starts to feel conversational, over ~1.5 s feels slow (anam.ai buyer's guide) |
| 0.9 – 1.5 s | Responsive | Best avatar product measured: Anam Cara-4.1 1.24 s median reply (Anam benchmark, Oct 2026, 60 raters, vendor-run). Voice-only phone agents: Telnyx 1.30 s median (Openbenchmarks) |
| 1.5 – 2.5 s | Noticeably slow | Tavus 1.86 s median in the same study; LemonSlice 2.04 s average end-to-end with third-party speech + LLM |
| > 2.5 s | Feels like a bot | Production voice agents measured 2.4 – 3.8 s median (Cekura, 270 calls). **Nova on the hear rig, Nov 2026: 3.35 s mean** |

The old "< 0.5 s = magic" row was never measured; nobody ships that for a full reply today. Keep **< 1.5 s median** as
Nova's target and the 0.5 s goal only for instant non-verbal reactions (a nod, a smile, a "mm!") that need no LLM.

How to get there (in order of payoff):
- **React before you answer.** The face and a tiny sound ("mm!", "oh!") can land in < 0.5 s while the reply is still
  being made. That is the only way to hit "magic" today.
- **Count every stage.** Waiting for silence + transcript + model + voice + lip render + network. Nova Nov 2026: about
  1.8 s of it is the face pipeline and buffering, not the model.
- **Stream the reply** to the face from the first words; never wait for a whole sentence (Nova `NOVA_FAST_KID` saved
  ~0.5 s).
- **Pre-render scripted lines** (greeting, rules) — they cost nothing at play time.
- A smarter model does not fix slowness: Nova already runs `gpt-realtime-2` (OpenAI, May 2026).

---

## Listening presence — the 2026 shift

The best new avatar models animate the face **all the time, including while the user is talking** — brows, eyes and
small nods react to the user's words and tone as they arrive, not after the sentence ends:
- **AVTR-1** (Avaturn, open weights, May 2026; report arXiv 2609.22913): takes one photo plus BOTH voices (hers and the
  user's) and generates head and face motion in 200 ms steps, 153M parameters, one GPU, 390–454 ms from her first
  speech to her first speaking frame. Weights free under $10M revenue; **the released renderer/streamer code is
  non-commercial** — check the licence before any product use.
- **Listener-nodding models** (Kyoto University, arXiv 2507.23298 and 2607.12329) predict when and how to nod in
  real time from both people's audio.
- Anam's listening behaviour was singled out as lifelike in Synthesia's Oct 2026 review.

For Nova: a looped idle body while a child talks reads as "not listening". Minimum bar — while the mic hears the child,
her face/body shows a listening state (lean in, eyes to the child, a nod at pauses), driven live, not a fixed clip.

---

## Children's speech — expect worse ears

Speech recognisers trained on adults do clearly worse on children's voices (ChildVox benchmark, arXiv 2605.29257,
May 2026). In the DrivenData children's speech challenge (closed Apr 2026), winners cut the best previous children's
model's word error by more than half, converging on a fine-tuned Qwen3-ASR-1.7B.
For Nova this means:
- Never let one transcript decide something big; check its confidence (Nova measured, Nov 2026: real words mean
  log-prob −0.00 … −0.92, noise −2.4 … −4.6, cut at −1.6).
- Keep the child's answer short-shaped ("What's your name?" not open questions) where the answer matters.
- Re-measure with real children's voices before trusting adult-voice numbers.

---

## What the child-development research says (why presence matters)

Calvert et al. (Child Development, 217 children aged 3–6, Georgetown): children learned from an intelligent, talking
character; they answered faster and more accurately when they treated the character as a **friend**, and when the
character gave **contingent spoken feedback** on what they had just said. Familiarity with the character predicted
faster responses. → Name, memory and replies to the child's own words are not decoration; they are the learning effect.

---

## Measured on Nova (Nov 2026 — rules that came from real runs)

- **Name first, light second.** The approved intro asks the name, waits, says it back, then the game cue. A scripted
  9-second greeting with the cue inside it read as a monologue to the founder.
- **One beat per turn.** Each turn = one thing (name → chat → light → rules), then she stops.
- **Match each transcript to its own utterance** (by item id). With a pause ("Hi … I'm Shuki"), counting turns lost the
  name and made two transcripts look like different sentences.
- **Ban assistant phrases and pet names** ("I'm here and listening", "loud and clear", "superstar") — pair each ban with
  an example of the right length; examples beat rules.
- **Kill meta talk** ("OK, I'll say it exactly as you asked") before it airs.
- **Never repeat an opening line** in one game; the game cuts lines to their opening, so repeats became silence.
- **Hebrew with unknown gender → plural** ("תרקדו", "תקפאו"), never a guessed gender.

---

## Memory Schema (suggested)

```javascript
const memory = {
  name: null,           // child's name once given
  hits: 0,              // successful actions
  attempts: 0,          // total tries
  streak: 0,            // current streak
  maxStreak: 0,         // best streak
  moments: [],          // ["nailed lightning fast clap", "3-streak", ...]
  history: [],          // last 12 conversation messages
  phase: 'intro'        // intro | active | end
};
```

Inject relevant context into every prompt:
- Name (if known) → personalization
- Recent moments → specific references
- Streak → energy level adjustment
- History → continuity

---

## Anti-patterns to AVOID

❌ Long monologues — kids tune out after 2 sentences
❌ Generic encouragement — "Great job buddy!" feels hollow
❌ Stacking multiple reactions — silence has weight
❌ Treating every move equally — some moments need BIG, others a soft "yes!"
❌ Polish over presence — perfect lipsync with cold reactions = product death
❌ Pre-recorded clips dressed as live — kids notice immediately

---

## What this means for product priorities

When in doubt, prioritize in this order:

1. **Reaction quality + speed** (LLM prompts, latency)
2. **Memory + continuity** (referencing what happened)  
3. **Voice quality** (tone, warmth, energy)
4. **Visual presence** (avatar, animation)
5. **Graphics polish** (textures, effects)

A product with #1 and #2 done well, even with crude visuals, will feel magical.
A product with stunning #5 but generic #1 will feel hollow.

---

## When applying this skill

Always remind the user that:
- Visual polish is the LAST mile, not the first
- Test reactions with real kids — they're the only valid feedback
- A reply under 1.5 s (and an instant non-verbal reaction under 0.5 s) is worth more than any graphical upgrade
- Specificity in praise is the highest-leverage prompt change
